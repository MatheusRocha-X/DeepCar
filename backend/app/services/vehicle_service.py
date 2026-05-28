from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct, delete, update as sa_update
from sqlalchemy.orm import load_only
from typing import Optional, List, Any
from datetime import datetime, timezone, timedelta
import re
from app.models.vehicle import Vehicle
from app.core.database import AsyncSessionLocal
from app.core.listing_flags import detect_listing_flags
import logging
import asyncio
import unicodedata
import time
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)
from app.models.favorite import Favorite
from app.models.schemas import SearchFilters, VehicleCreate, OrderBy
from app.core.cache import cache_get, cache_set
from app.core.text_normalizer import normalize_city, normalize_text_key
from app.services.score_service import calcular_score
import hashlib
import json


def _build_cache_key(prefix: str, data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, default=str)
    return f"{prefix}:{hashlib.md5(serialized.encode()).hexdigest()}"


SMART_SCRAPE_FILTER_FIELDS = (
    "q",
    "marca",
    "modelo",
    "ano_min",
    "ano_max",
    "km_min",
    "km_max",
    "preco_min",
    "preco_max",
    "vendedor_tipo",
    "combustivel",
    "cambio",
    "estado",
    "cidade",
    "source",
    "passagem_leilao",
)

QUERY_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "thp": ("thp", "turbo"),
    "turbo": ("turbo", "thp"),
}

QUERY_YEAR_PATTERN = re.compile(r"\b(?:19[5-9]\d|20\d\d|2030)\b")
QUERY_YEAR_RANGE_PATTERN = re.compile(
    r"\b(19[5-9]\d|20\d\d|2030)\s*(?:-|/|a|ate|até)\s*(19[5-9]\d|20\d\d|2030)\b",
    re.IGNORECASE,
)

KNOWN_QUERY_BRAND_TERMS: dict[str, str] = {
    "alfa": "Alfa Romeo",
    "audi": "Audi",
    "bmw": "BMW",
    "byd": "BYD",
    "caoa": "Caoa Chery",
    "chery": "Caoa Chery",
    "chevrolet": "Chevrolet",
    "citroen": "Citroën",
    "dodge": "Dodge",
    "fiat": "Fiat",
    "ford": "Ford",
    "gm": "Chevrolet",
    "gwm": "GWM",
    "honda": "Honda",
    "hyundai": "Hyundai",
    "jac": "JAC",
    "jeep": "Jeep",
    "kia": "Kia",
    "lexus": "Lexus",
    "mercedes": "Mercedes-Benz",
    "mini": "MINI",
    "mitsubishi": "Mitsubishi",
    "nissan": "Nissan",
    "peugeot": "Peugeot",
    "porsche": "Porsche",
    "ram": "Ram",
    "renault": "Renault",
    "seat": "SEAT",
    "subaru": "Subaru",
    "suzuki": "Suzuki",
    "toyota": "Toyota",
    "volkswagen": "Volkswagen",
    "volvo": "Volvo",
    "vw": "Volkswagen",
}

BRAND_TYPO_MIN_LENGTH = 5
BRAND_TYPO_MAX_DISTANCE = 3
OLX_BRANDS_CACHE_TTL_SECONDS = 21600
OLX_REGION_CACHE_TTL_SECONDS = 900
OLX_BASE_CATEGORY_PATH = "autos-e-pecas/carros-vans-e-utilitarios"

_olx_brands_cache: dict[str, Any] = {"expires_at": 0.0, "options": []}
_olx_region_cache: dict[tuple[str, str], tuple[float, list[str]]] = {}

OLX_BRAND_PATH_OVERRIDES = {
    "am gen": "am-gen",
    "caoa chery": "caoa-chery",
    "caoa changan": "caoa-changan",
    "cbt jipe": "cbt-jipe",
    "chevrolet": "gm-chevrolet",
    "citroen": "citroen",
    "citroën": "citroen",
    "land rover": "land-rover",
    "mercedes benz": "mercedes-benz",
    "mercedes-benz": "mercedes-benz",
    "ram": "ram",
    "vw": "vw-volkswagen",
    "volkswagen": "vw-volkswagen",
}


def _has_filter_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _clean_filter_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_filter_key(value: Any) -> str:
    return normalize_text_key(_clean_filter_text(value))


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current_row[right_index - 1] + 1
            delete_cost = previous_row[right_index] + 1
            replace_cost = previous_row[right_index - 1] + (left_char != right_char)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row

    return previous_row[-1]


def _resolve_brand_query_candidate(term: str) -> Optional[str]:
    normalized_term = _normalize_filter_key(term)
    if len(normalized_term) < BRAND_TYPO_MIN_LENGTH:
        return None

    if normalized_term in KNOWN_QUERY_BRAND_TERMS:
        return KNOWN_QUERY_BRAND_TERMS[normalized_term]

    candidates = [
        brand
        for brand in KNOWN_QUERY_BRAND_TERMS
        if brand[:1] == normalized_term[:1]
        and brand[-1:] == normalized_term[-1:]
        and abs(len(brand) - len(normalized_term)) <= 2
    ]
    if not candidates:
        return None

    matched_term = min(candidates, key=lambda brand: _levenshtein_distance(normalized_term, brand))
    if _levenshtein_distance(normalized_term, matched_term) > BRAND_TYPO_MAX_DISTANCE:
        return None

    return KNOWN_QUERY_BRAND_TERMS[matched_term]


def _canonicalize_scrape_query_text(value: Any) -> str:
    terms = [term.strip() for term in _clean_filter_text(value).split() if term.strip()]
    if not terms:
        return ""

    canonical_terms: list[str] = []
    for term in terms:
        canonical_terms.append(_resolve_brand_query_candidate(term) or term)

    return " ".join(canonical_terms)


def _build_query_term_groups(value: Any) -> list[list[str]]:
    groups: list[list[str]] = []
    raw_terms = [term.strip() for term in _clean_filter_text(value).split() if len(term.strip()) >= 2]

    for term in raw_terms:
        normalized_term = _normalize_filter_key(term)
        candidates = list(QUERY_TERM_ALIASES.get(normalized_term, (term,)))
        brand_candidate = _resolve_brand_query_candidate(term)
        if brand_candidate:
            candidates.append(brand_candidate)
        group: list[str] = []
        seen: set[str] = set()

        for candidate in candidates:
            normalized_candidate = _normalize_filter_key(candidate)
            if not normalized_candidate or normalized_candidate in seen:
                continue
            group.append(candidate)
            seen.add(normalized_candidate)

        if group:
            groups.append(group)

    return groups


def _extract_query_year_bounds(value: Any) -> tuple[str, Optional[int], Optional[int]]:
    raw_value = _clean_filter_text(value)
    if not raw_value:
        return "", None, None

    extracted_years: list[int] = []
    for start_year, end_year in QUERY_YEAR_RANGE_PATTERN.findall(raw_value):
        extracted_years.extend([int(start_year), int(end_year)])

    cleaned_value = QUERY_YEAR_RANGE_PATTERN.sub(" ", raw_value)

    for match in QUERY_YEAR_PATTERN.findall(cleaned_value):
        extracted_years.append(int(match))

    cleaned_value = QUERY_YEAR_PATTERN.sub(" ", cleaned_value)
    cleaned_value = re.sub(r"\s+", " ", cleaned_value).strip(" ,-/")

    if not extracted_years:
        return raw_value, None, None

    return cleaned_value, min(extracted_years), max(extracted_years)


def _resolve_effective_year_bounds(filters: SearchFilters) -> tuple[Optional[int], Optional[int]]:
    _, query_year_min, query_year_max = _extract_query_year_bounds(filters.q)
    year_min = filters.ano_min if filters.ano_min is not None else query_year_min
    year_max = filters.ano_max if filters.ano_max is not None else query_year_max
    return year_min, year_max


def _matches_query_terms_in_text(value: Any, query: Any) -> bool:
    searchable_text = _normalize_filter_key(value)
    if not searchable_text:
        return False

    for group in _build_query_term_groups(query):
        if not any(_normalize_filter_key(candidate) in searchable_text for candidate in group):
            return False

    return True


def _format_query_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _contains_text(haystack: Any, needle: Any) -> bool:
    haystack_text = _clean_filter_text(haystack).casefold()
    needle_text = _clean_filter_text(needle).casefold()
    return bool(needle_text) and needle_text in haystack_text


def _contains_normalized_text(haystack: Any, needle: Any) -> bool:
    haystack_text = _normalize_filter_key(haystack)
    needle_text = _normalize_filter_key(needle)
    return bool(needle_text) and needle_text in haystack_text


def _accent_count(value: str) -> int:
    return sum(1 for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) == "Mn")


def _city_display_value(variants: set[str]) -> str:
    candidates = {normalize_city(variant) or _clean_filter_text(variant) for variant in variants if _clean_filter_text(variant)}
    return max(
        candidates,
        key=lambda city: (_accent_count(city), len(city), _normalize_filter_key(city), city.casefold()),
    )


def _group_cities_by_state(rows: list[tuple[Optional[str], Optional[str]]]) -> tuple[dict[str, list[str]], dict[str, dict[str, list[str]]]]:
    grouped: dict[str, dict[str, set[str]]] = {}

    for estado, cidade in rows:
        state = _clean_filter_text(estado).upper()
        raw_city = _clean_filter_text(cidade)
        city_key = _normalize_filter_key(raw_city)
        if not state or not city_key:
            continue
        state_groups = grouped.setdefault(state, {})
        state_groups.setdefault(city_key, set()).add(raw_city)

    cities_dict: dict[str, list[str]] = {}
    city_aliases: dict[str, dict[str, list[str]]] = {}

    for state, city_groups in grouped.items():
        display_values: list[str] = []
        aliases_by_key: dict[str, list[str]] = {}
        for city_key, variants in city_groups.items():
            display_values.append(_city_display_value(variants))
            aliases_by_key[city_key] = sorted(variants, key=lambda city: (_normalize_filter_key(city), city.casefold()))

        cities_dict[state] = sorted(set(display_values), key=lambda city: (_normalize_filter_key(city), city.casefold()))
        city_aliases[state] = aliases_by_key

    return cities_dict, city_aliases


async def _resolve_city_aliases(db: AsyncSession, estado: Optional[str], cidade: Any) -> list[str]:
    city_key = _normalize_filter_key(cidade)
    if not city_key:
        return []

    query = (
        select(Vehicle.estado, Vehicle.cidade)
        .where(Vehicle.ativo == True, Vehicle.estado != None, Vehicle.cidade != None)
        .distinct()
    )

    state = _clean_filter_text(estado).upper()
    if state:
        query = query.where(Vehicle.estado == state)

    result = await db.execute(query)
    _, city_aliases = _group_cities_by_state(result.all())

    if state:
        return city_aliases.get(state, {}).get(city_key, [])

    merged_aliases: set[str] = set()
    for aliases_by_key in city_aliases.values():
        merged_aliases.update(aliases_by_key.get(city_key, []))
    return sorted(merged_aliases, key=lambda value: (_normalize_filter_key(value), value.casefold()))


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def has_meaningful_search_filters(filters: SearchFilters) -> bool:
    return any(_has_filter_value(getattr(filters, field, None)) for field in SMART_SCRAPE_FILTER_FIELDS)


def build_smart_scrape_display_query(filters: SearchFilters) -> str:
    if not has_meaningful_search_filters(filters):
        return ""

    parts: list[str] = []
    q = _clean_filter_text(filters.q)
    marca = _clean_filter_text(filters.marca)
    modelo = _clean_filter_text(filters.modelo)

    if q:
        parts.append(q)
        if marca:
            parts.append(f"marca {marca}")
        if modelo:
            parts.append(f"modelo {modelo}")
    else:
        if marca:
            parts.append(marca)
        if modelo:
            parts.append(modelo)
        if not parts:
            parts.append("carro")

    combustivel = _clean_filter_text(filters.combustivel)
    cambio = _clean_filter_text(filters.cambio)
    vendedor_tipo = _clean_filter_text(filters.vendedor_tipo)
    cidade = _clean_filter_text(filters.cidade)
    estado = _clean_filter_text(filters.estado)
    source = _clean_filter_text(filters.source)
    passagem_leilao = filters.passagem_leilao

    if combustivel:
        parts.append(f"combustivel {combustivel}")
    if cambio:
        parts.append(f"cambio {cambio}")
    if vendedor_tipo:
        parts.append(f"vendedor {vendedor_tipo}")
    if cidade:
        parts.append(f"cidade {cidade}")
    if estado:
        parts.append(f"estado {estado}")

    if filters.ano_min is not None and filters.ano_max is not None:
        parts.append(f"ano {filters.ano_min}-{filters.ano_max}")
    elif filters.ano_min is not None:
        parts.append(f"ano {filters.ano_min}+")
    elif filters.ano_max is not None:
        parts.append(f"ano ate {filters.ano_max}")

    if filters.km_min is not None and filters.km_max is not None:
        parts.append(f"km {filters.km_min}-{filters.km_max}")
    elif filters.km_min is not None:
        parts.append(f"km {filters.km_min}+")
    elif filters.km_max is not None:
        parts.append(f"km ate {filters.km_max}")

    if filters.preco_min is not None and filters.preco_max is not None:
        parts.append(f"preco {_format_query_number(filters.preco_min)}-{_format_query_number(filters.preco_max)}")
    elif filters.preco_min is not None:
        parts.append(f"preco {_format_query_number(filters.preco_min)}+")
    elif filters.preco_max is not None:
        parts.append(f"preco ate {_format_query_number(filters.preco_max)}")

    if source:
        parts.append(f"fonte {source}")
    if passagem_leilao is True:
        parts.append("com passagem por leilao")
    elif passagem_leilao is False:
        parts.append("sem passagem por leilao")

    return " ".join(part for part in parts if part)


def build_smart_scrape_query(filters: SearchFilters) -> str:
    if not has_meaningful_search_filters(filters):
        return ""

    terms: list[str] = []
    seen: set[str] = set()
    query_text, query_year_min, query_year_max = _extract_query_year_bounds(filters.q)
    year_min = filters.ano_min if filters.ano_min is not None else query_year_min
    year_max = filters.ano_max if filters.ano_max is not None else query_year_max

    def add_term(value: Any) -> None:
        text = _clean_filter_text(value)
        key = text.casefold()
        if not text or key in seen:
            return
        terms.append(text)
        seen.add(key)

    add_term(_canonicalize_scrape_query_text(query_text))
    add_term(_canonicalize_scrape_query_text(filters.marca))
    add_term(filters.modelo)

    if year_min is not None and year_max is not None and year_min == year_max:
        add_term(year_min)
    elif year_min is not None and year_max is None:
        add_term(year_min)
    elif year_max is not None and year_min is None:
        add_term(year_max)

    if not terms:
        terms.append("carro")

    return " ".join(terms)


def build_olx_query_params(filters: SearchFilters) -> dict[str, str]:
    params: dict[str, str] = {}
    year_min, year_max = _resolve_effective_year_bounds(filters)

    fuel_map = {
        "gasolina": "1",
        "alcool": "2",
        "álcool": "2",
        "flex": "3",
        "diesel": "5",
        "hibrido": "6",
        "híbrido": "6",
        "eletrico": "7",
        "elétrico": "7",
    }
    gearbox_map = {
        "manual": "1",
        "automatico": "2",
        "automático": "2",
        "cvt": "2",
        "semi-automatico": "3",
        "semi-automático": "3",
        "automatizado": "4",
    }
    seller_map = {
        "pessoa fisica": "0",
        "pessoa física": "0",
        "particular": "0",
        "loja": "1",
        "concessionaria": "1",
        "concessionária": "1",
        "profissional": "1",
    }

    if filters.preco_min is not None:
        params["ps"] = str(int(filters.preco_min))
    if filters.preco_max is not None:
        params["pe"] = str(int(filters.preco_max))
    if filters.km_min is not None:
        params["ms"] = str(int(filters.km_min))
    if filters.km_max is not None:
        params["me"] = str(int(filters.km_max))
    if year_min is not None:
        params["rs"] = str(int(year_min))
    if year_max is not None:
        params["re"] = str(int(year_max))

    fuel_value = fuel_map.get(_normalize_filter_key(filters.combustivel))
    if fuel_value:
        params["fu"] = fuel_value

    gearbox_value = gearbox_map.get(_normalize_filter_key(filters.cambio))
    if gearbox_value:
        params["gb"] = gearbox_value

    seller_value = seller_map.get(_normalize_filter_key(filters.vendedor_tipo))
    if seller_value:
        params["f"] = seller_value

    return params


def should_scrape_olx_for_filters(filters: SearchFilters) -> bool:
    source = _normalize_filter_key(filters.source)
    return not source or source == "olx"


async def _get_olx_brand_options() -> list[dict[str, str]]:
    now = time.time()
    if _olx_brands_cache["expires_at"] > now and _olx_brands_cache["options"]:
        return _olx_brands_cache["options"]

    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": f"https://www.olx.com.br/{OLX_BASE_CATEGORY_PATH}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        }
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
            response = await client.get("https://www.olx.com.br/api/filters/v1/brands/car")
            response.raise_for_status()
        payload = response.json()
        options = [option for option in payload if isinstance(option, dict)]
        _olx_brands_cache["expires_at"] = now + OLX_BRANDS_CACHE_TTL_SECONDS
        _olx_brands_cache["options"] = options
        return options
    except Exception as exc:
        logger.warning("Failed to fetch OLX brands: %s", exc)
        return list(_olx_brands_cache.get("options", []))


def _fallback_olx_brand_path(brand: str) -> Optional[str]:
    normalized_brand = _normalize_filter_key(brand)
    if not normalized_brand:
        return None

    if normalized_brand in OLX_BRAND_PATH_OVERRIDES:
        return OLX_BRAND_PATH_OVERRIDES[normalized_brand]

    slug = normalized_brand.replace("/", " ").replace("_", " ")
    slug = "-".join(part for part in slug.split() if part)
    return slug or None


async def resolve_olx_brand_path(marca: Optional[str]) -> Optional[str]:
    canonical_brand = _resolve_brand_query_candidate(_clean_filter_text(marca)) or _clean_filter_text(marca)
    normalized_brand = _normalize_filter_key(canonical_brand)
    if not normalized_brand:
        return None

    options = await _get_olx_brand_options()
    if not options:
        return _fallback_olx_brand_path(canonical_brand)

    candidates: list[tuple[int, str]] = []
    for option in options:
        label = _clean_filter_text(option.get("label"))
        friendly_path = _clean_filter_text((option.get("extraData") or {}).get("friendlyPath"))
        href = _clean_filter_text(option.get("href"))
        option_keys = {_normalize_filter_key(label), _normalize_filter_key(friendly_path)}

        if normalized_brand in option_keys:
            return friendly_path or href.rstrip("/").split("/")[-1] or None

        if any(normalized_brand and normalized_brand in key for key in option_keys if key):
            candidates.append((0, friendly_path or href.rstrip("/").split("/")[-1]))
            continue

        if label:
            distance = _levenshtein_distance(normalized_brand, _normalize_filter_key(label))
            candidates.append((distance, friendly_path or href.rstrip("/").split("/")[-1]))

    if not candidates:
        return _fallback_olx_brand_path(canonical_brand)

    distance, path = min(candidates, key=lambda item: item[0])
    if path and distance <= BRAND_TYPO_MAX_DISTANCE:
        return path

    return _fallback_olx_brand_path(canonical_brand)


def _extract_olx_search_base_url(source_url: Any) -> Optional[str]:
    raw_url = _clean_filter_text(source_url)
    if not raw_url:
        return None

    try:
        parsed = urlparse(raw_url)
    except Exception:
        return None

    host = (parsed.hostname or "").lower()
    if not host.endswith(".olx.com.br"):
        return None

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 3:
        return None

    region_slug = path_parts[0]
    category_parts = path_parts[1:4]
    if category_parts[:2] != ["autos-e-pecas", "carros-vans-e-utilitarios"]:
        return None

    return f"https://{host}/{region_slug}/{OLX_BASE_CATEGORY_PATH}"


async def resolve_olx_base_urls(db: AsyncSession, filters: SearchFilters, brand_path: Optional[str] = None) -> list[str]:
    state = _clean_filter_text(filters.estado).upper()
    city_key = _normalize_filter_key(filters.cidade)
    query_text, _, _ = _extract_query_year_bounds(filters.q)

    has_direct_search_signal = any(
        _has_filter_value(value)
        for value in (
            _clean_filter_text(query_text) if _normalize_filter_key(query_text) != "carro" else "",
            filters.marca,
            filters.modelo,
            filters.ano_min,
            filters.ano_max,
        )
    )
    has_structured_only_signal = any(
        _has_filter_value(value)
        for value in (
            filters.preco_min,
            filters.preco_max,
            filters.km_min,
            filters.km_max,
            filters.combustivel,
            filters.cambio,
            filters.vendedor_tipo,
            filters.estado,
            filters.cidade,
        )
    )

    # Broad state-only OLX searches behave better through the global category URL.
    # The region-specific SSR routes can collapse to the OLX homepage under curl
    # fallback, which leaves the smart scrape stuck at zero collected listings.
    if (
        state
        and not city_key
        and not brand_path
        and not has_direct_search_signal
        and has_structured_only_signal
    ):
        return [f"https://www.olx.com.br/{OLX_BASE_CATEGORY_PATH}"]

    if not state and not city_key:
        default_url = f"https://www.olx.com.br/{OLX_BASE_CATEGORY_PATH}"
        if brand_path:
            return [f"{default_url}/{brand_path}"]
        return [default_url]

    cache_key = (state or "", city_key or "")
    now = time.time()

    cached = _olx_region_cache.get(cache_key)
    if cached and cached[0] > now:
        base_urls = list(cached[1])
    else:
        query = (
            select(Vehicle.source_url)
            .where(
                Vehicle.ativo == True,
                Vehicle.source_name == "OLX",
                Vehicle.source_url != None,
            )
            .distinct()
        )

        if state:
            query = query.where(Vehicle.estado == state)

        if city_key:
            aliases = await _resolve_city_aliases(db, state or None, filters.cidade)
            if aliases:
                query = query.where(or_(*[Vehicle.cidade == alias for alias in aliases]))
            else:
                query = query.where(Vehicle.cidade.ilike(f"%{filters.cidade}%"))

        result = await db.execute(query)
        base_urls = []
        seen_urls: set[str] = set()
        for (source_url,) in result.all():
            base_url = _extract_olx_search_base_url(source_url)
            if not base_url or base_url in seen_urls:
                continue
            seen_urls.add(base_url)
            base_urls.append(base_url)

        base_urls.sort()
        _olx_region_cache[cache_key] = (now + OLX_REGION_CACHE_TTL_SECONDS, list(base_urls))

    if not base_urls and city_key and state:
        state_only_filters = filters.model_copy(update={"cidade": None})
        return await resolve_olx_base_urls(db, state_only_filters, brand_path=brand_path)

    if not base_urls:
        default_url = f"https://www.olx.com.br/{OLX_BASE_CATEGORY_PATH}"
        base_urls = [default_url]

    if brand_path:
        return [f"{base_url.rstrip('/')}/{brand_path}" for base_url in base_urls]

    return base_urls


async def build_olx_request_options(db: AsyncSession, filters: SearchFilters) -> dict[str, Any]:
    if not should_scrape_olx_for_filters(filters):
        return {"enabled": False}

    brand_path = await resolve_olx_brand_path(filters.marca)
    base_urls = await resolve_olx_base_urls(db, filters, brand_path=brand_path)
    return {
        "enabled": True,
        "base_urls": base_urls,
        "extra_query_params": build_olx_query_params(filters),
    }


def vehicle_matches_filters(vehicle_data: dict, filters: SearchFilters) -> bool:
    query_text, query_year_min, query_year_max = _extract_query_year_bounds(filters.q)
    year_min = filters.ano_min if filters.ano_min is not None else query_year_min
    year_max = filters.ano_max if filters.ano_max is not None else query_year_max

    if query_text:
        searchable_text = " ".join(
            _clean_filter_text(vehicle_data.get(field))
            for field in ("titulo", "marca", "modelo", "versao", "descricao", "estado", "cidade")
        )
        if not _matches_query_terms_in_text(searchable_text, query_text):
            return False

    if filters.marca and not _contains_text(vehicle_data.get("marca"), filters.marca):
        return False
    if filters.modelo and not _contains_text(vehicle_data.get("modelo"), filters.modelo):
        return False

    ano = _coerce_float(vehicle_data.get("ano"))
    if year_min is not None and (ano is None or ano < year_min):
        return False
    if year_max is not None and (ano is None or ano > year_max):
        return False

    km = _coerce_float(vehicle_data.get("km"))
    if filters.km_min is not None and (km is None or km < filters.km_min):
        return False
    if filters.km_max is not None and (km is None or km > filters.km_max):
        return False

    preco = _coerce_float(vehicle_data.get("preco"))
    if filters.preco_min is not None and (preco is None or preco < filters.preco_min):
        return False
    if filters.preco_max is not None and (preco is None or preco > filters.preco_max):
        return False

    if filters.vendedor_tipo and _clean_filter_text(vehicle_data.get("vendedor_tipo")).casefold() != _clean_filter_text(filters.vendedor_tipo).casefold():
        return False
    if filters.combustivel and _clean_filter_text(vehicle_data.get("combustivel")).casefold() != _clean_filter_text(filters.combustivel).casefold():
        return False
    if filters.cambio and _clean_filter_text(vehicle_data.get("cambio")).casefold() != _clean_filter_text(filters.cambio).casefold():
        return False
    if filters.estado and _clean_filter_text(vehicle_data.get("estado")).casefold() != _clean_filter_text(filters.estado).casefold():
        return False
    if filters.cidade and not _contains_normalized_text(vehicle_data.get("cidade"), filters.cidade):
        return False
    if filters.source and _clean_filter_text(vehicle_data.get("source_name")).casefold() != _clean_filter_text(filters.source).casefold():
        return False
    if filters.passagem_leilao is not None:
        flag_value = vehicle_data.get("possui_passagem_leilao")
        if flag_value is None:
            flag_value = detect_listing_flags(vehicle_data)["possui_passagem_leilao"]
        if bool(flag_value) != filters.passagem_leilao:
            return False

    return True


async def search_vehicles(db: AsyncSession, filters: SearchFilters):
    skip_cache = filters.page == 1 and has_meaningful_search_filters(filters)
    cache_key = _build_cache_key("search", filters.model_dump())
    if not skip_cache:
        cached = await cache_get(cache_key)
        if cached:
            return cached

    query = select(Vehicle).where(Vehicle.ativo == True)
    query_text, query_year_min, query_year_max = _extract_query_year_bounds(filters.q)
    year_min = filters.ano_min if filters.ano_min is not None else query_year_min
    year_max = filters.ano_max if filters.ano_max is not None else query_year_max

    if query_text:
        for group in _build_query_term_groups(query_text):
            group_terms = []
            for candidate in group:
                term = f"%{candidate}%"
                group_terms.extend([
                    Vehicle.titulo.ilike(term),
                    Vehicle.marca.ilike(term),
                    Vehicle.modelo.ilike(term),
                    Vehicle.versao.ilike(term),
                    Vehicle.descricao.ilike(term),
                    Vehicle.estado.ilike(term),
                    Vehicle.cidade.ilike(term),
                ])
            query = query.where(
                or_(*group_terms)
            )

    if filters.marca:
        query = query.where(Vehicle.marca.ilike(f"%{filters.marca}%"))
    if filters.modelo:
        query = query.where(Vehicle.modelo.ilike(f"%{filters.modelo}%"))
    if year_min is not None:
        query = query.where(Vehicle.ano >= year_min)
    if year_max is not None:
        query = query.where(Vehicle.ano <= year_max)
    if filters.km_min is not None:
        query = query.where(Vehicle.km >= filters.km_min)
    if filters.km_max is not None:
        query = query.where(Vehicle.km <= filters.km_max)
    if filters.preco_min is not None:
        query = query.where(Vehicle.preco >= filters.preco_min)
    if filters.preco_max is not None:
        query = query.where(Vehicle.preco <= filters.preco_max)
    if filters.vendedor_tipo:
        query = query.where(Vehicle.vendedor_tipo == filters.vendedor_tipo)
    if filters.combustivel:
        query = query.where(Vehicle.combustivel == filters.combustivel)
    if filters.cambio:
        query = query.where(Vehicle.cambio == filters.cambio)
    state = _clean_filter_text(filters.estado).upper()
    if state:
        query = query.where(Vehicle.estado == state)
    if filters.cidade:
        city_aliases = await _resolve_city_aliases(db, state or None, filters.cidade)
        if city_aliases:
            query = query.where(or_(*[Vehicle.cidade == city for city in city_aliases]))
        else:
            query = query.where(Vehicle.cidade.ilike(f"%{filters.cidade}%"))
    if filters.source:
        query = query.where(Vehicle.source_name == filters.source)
    if filters.passagem_leilao is not None:
        query = query.where(Vehicle.possui_passagem_leilao == filters.passagem_leilao)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    order_map = {
        OrderBy.score: Vehicle.score.desc(),
        OrderBy.menor_preco: Vehicle.preco.asc(),
        OrderBy.maior_preco: Vehicle.preco.desc(),
        OrderBy.menor_km: Vehicle.km.asc(),
        OrderBy.mais_recente: Vehicle.created_at.desc(),
    }
    order_clause = order_map.get(filters.order_by, Vehicle.score.desc())
    query = query.order_by(order_clause)

    offset = (filters.page - 1) * filters.per_page
    query = query.offset(offset).limit(filters.per_page)

    result = await db.execute(query)
    vehicles = result.scalars().all()

    total_pages = (total + filters.per_page - 1) // filters.per_page if total > 0 else 0

    response = {
        "total": total,
        "page": filters.page,
        "per_page": filters.per_page,
        "total_pages": total_pages,
        "results": [_vehicle_to_card(v) for v in vehicles],
    }

    if not skip_cache:
        await cache_set(cache_key, response, ttl=180)
    return response


def _needs_olx_detail_enrichment(vehicle_data: dict) -> bool:
    source_name = _clean_filter_text(vehicle_data.get("source_name")).casefold()
    if source_name != "olx":
        return False

    if vehicle_data.get("possui_passagem_leilao"):
        return False

    description = _clean_filter_text(vehicle_data.get("descricao"))
    return not description or description.startswith("Opcionais:")


async def _enrich_olx_vehicle_detail_if_needed(db: AsyncSession, vehicle: Vehicle) -> Vehicle:
    vehicle_data = _vehicle_to_dict(vehicle)
    if not _needs_olx_detail_enrichment(vehicle_data):
        return vehicle

    try:
        from app.scrapers.olx_scraper import OLXScraper

        scraper = OLXScraper(max_pages=1)
        enriched_data = await scraper.enrich_vehicle_dict(vehicle_data)
    except Exception as exc:
        logger.warning("Failed to enrich OLX vehicle %s from detail page: %s", vehicle.id, exc)
        return vehicle

    if enriched_data == vehicle_data:
        return vehicle

    flags = detect_listing_flags(enriched_data, preco_referencia=vehicle.fipe_preco)
    score, insights = calcular_score(
        enriched_data,
        preco_medio_mercado=None,
        fipe_preco=vehicle.fipe_preco,
    )

    vehicle.descricao = enriched_data.get("descricao")
    vehicle.possui_passagem_leilao = flags["possui_passagem_leilao"]
    vehicle.valor_referente_entrada = flags["valor_referente_entrada"]
    vehicle.preco_suspeito = flags["preco_suspeito"]
    vehicle.score = score
    vehicle.insights = insights
    vehicle.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(vehicle)
    return vehicle


async def get_vehicle_by_id(db: AsyncSession, vehicle_id: int):
    cache_key = f"vehicle:{vehicle_id}"
    cached = await cache_get(cache_key)
    if cached and not _needs_olx_detail_enrichment(cached):
        return cached

    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.ativo == True))
    vehicle = result.scalar_one_or_none()

    if not vehicle:
        return None

    vehicle = await _enrich_olx_vehicle_detail_if_needed(db, vehicle)

    data = _vehicle_to_dict(vehicle)
    await cache_set(cache_key, data, ttl=600)
    return data


# Static Brazilian car brands/models — merged with live DB data so filters are never empty
STATIC_BRANDS: dict[str, list[str]] = {
    "Fiat": ["Argo", "Cronos", "Fastback", "Mobi", "Pulse", "Strada", "Toro", "Uno", "Palio", "Siena", "Bravo", "500", "Doblo", "Fiorino"],
    "Volkswagen": ["Gol", "Polo", "Virtus", "Nivus", "T-Cross", "Taos", "Saveiro", "Amarok", "Up", "Fox", "Voyage", "Tiguan", "Golf"],
    "Chevrolet": ["Onix", "Onix Plus", "Tracker", "Spin", "S10", "Montana", "Equinox", "Trailblazer", "Blazer", "Cruze", "Cobalt", "Celta", "Classic"],
    "Ford": ["Ka", "EcoSport", "Ranger", "Territory", "Bronco Sport", "Maverick", "Focus", "Fiesta", "Edge", "Explorer"],
    "Honda": ["Civic", "City", "HR-V", "CR-V", "WR-V", "Fit", "Accord", "Pilot", "Odyssey"],
    "Toyota": ["Corolla", "Yaris", "Hilux", "SW4", "RAV4", "Prado", "Camry", "Fortuner", "Land Cruiser"],
    "Hyundai": ["HB20", "HB20S", "Creta", "Tucson", "Santa Fe", "Elantra", "Sonata", "Azera", "i30"],
    "Renault": ["Kwid", "Sandero", "Logan", "Duster", "Stepway", "Captur", "Oroch", "Fluence", "Scenic"],
    "Nissan": ["March", "Versa", "Kicks", "Frontier", "Sentra", "Livina", "X-Trail", "Murano"],
    "Jeep": ["Renegade", "Compass", "Commander", "Wrangler", "Cherokee", "Grand Cherokee", "Gladiator"],
    "BMW": ["116i", "118i", "120i", "320i", "328i", "418i", "420i", "520i", "528i", "X1", "X3", "X5", "X6", "M3", "M5"],
    "Mercedes-Benz": ["A 200", "A 250", "C 180", "C 200", "C 220", "C 300", "E 200", "E 250", "GLA 200", "GLE 350", "CLA 200"],
    "Audi": ["A3", "A4", "A5", "A6", "Q3", "Q5", "Q7", "TT", "RS3", "RS5"],
    "Mitsubishi": ["ASX", "Outlander", "Eclipse Cross", "L200 Triton", "Pajero", "Pajero Sport"],
    "Peugeot": ["208", "2008", "3008", "5008", "508", "Partner"],
    "Citroën": ["C3", "C4 Cactus", "C5 Aircross", "Berlingo", "Jumper"],
    "Kia": ["Sportage", "Stinger", "Optima", "Sorento", "Carnival", "Cerato", "Picanto", "Stonic"],
    "Subaru": ["Impreza", "Outback", "Forester", "XV", "Legacy", "BRZ"],
    "Volvo": ["XC40", "XC60", "XC90", "S60", "V60", "S90", "V90"],
    "Land Rover": ["Defender", "Discovery", "Discovery Sport", "Range Rover", "Range Rover Evoque", "Range Rover Sport"],
    "Caoa Chery": ["Tiggo 2", "Tiggo 3X", "Tiggo 5X", "Tiggo 7", "Tiggo 8", "Arrizo 6"],
    "BYD": ["Dolphin", "Seal", "Tan", "Han", "Yuan Plus", "Song Plus", "Atto 3"],
    "GWM": ["Haval H6", "Haval H6 GT", "Ora 03", "Poer", "Tank 300"],
    "Suzuki": ["Jimny", "Swift", "Vitara", "S-Cross", "Baleno"],
    "Porsche": ["Cayenne", "Macan", "Panamera", "718 Cayman", "718 Boxster", "911"],
    "Dodge": ["RAM 1500", "RAM 2500", "Challenger", "Charger", "Durango", "Journey"],
    "Jeep": ["Renegade", "Compass", "Commander", "Wrangler"],
}

STATIC_SOURCE_OPTIONS = ["OLX", "iCarros"]


async def get_filter_options(db: AsyncSession):
    cache_key = "filter_options"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    marcas_result = await db.execute(
        select(distinct(Vehicle.marca)).where(Vehicle.ativo == True, Vehicle.marca != None).order_by(Vehicle.marca)
    )
    marcas_db = [r[0] for r in marcas_result.all() if r[0]]

    modelos_result = await db.execute(
        select(Vehicle.marca, Vehicle.modelo)
        .where(Vehicle.ativo == True, Vehicle.marca != None, Vehicle.modelo != None)
        .distinct()
        .order_by(Vehicle.marca, Vehicle.modelo)
    )
    modelos_dict: dict[str, list] = {}
    for marca, modelo in modelos_result.all():
        if marca and modelo:
            if marca not in modelos_dict:
                modelos_dict[marca] = []
            if modelo not in modelos_dict[marca]:
                modelos_dict[marca].append(modelo)

    # Merge static Brazilian brands/models so filters always have options
    for brand, models in STATIC_BRANDS.items():
        if brand not in marcas_db:
            marcas_db.append(brand)
        if brand not in modelos_dict:
            modelos_dict[brand] = list(models)
        else:
            for m in models:
                if m not in modelos_dict[brand]:
                    modelos_dict[brand].append(m)

    marcas = sorted(set(marcas_db))

    estados_result = await db.execute(
        select(distinct(Vehicle.estado)).where(Vehicle.ativo == True, Vehicle.estado != None).order_by(Vehicle.estado)
    )
    estados = [r[0] for r in estados_result.all() if r[0]]

    cidades_result = await db.execute(
        select(Vehicle.estado, Vehicle.cidade)
        .where(Vehicle.ativo == True, Vehicle.estado != None, Vehicle.cidade != None)
        .distinct()
        .order_by(Vehicle.estado, Vehicle.cidade)
    )
    cidades_dict, _ = _group_cities_by_state(cidades_result.all())

    combustiveis_result = await db.execute(
        select(distinct(Vehicle.combustivel)).where(Vehicle.ativo == True, Vehicle.combustivel != None)
    )
    combustiveis = sorted([r[0] for r in combustiveis_result.all() if r[0]])

    cambios_result = await db.execute(
        select(distinct(Vehicle.cambio)).where(Vehicle.ativo == True, Vehicle.cambio != None)
    )
    cambios = sorted([r[0] for r in cambios_result.all() if r[0]])

    vendedores_result = await db.execute(
        select(distinct(Vehicle.vendedor_tipo)).where(Vehicle.ativo == True, Vehicle.vendedor_tipo != None)
    )
    vendedores = sorted([r[0] for r in vendedores_result.all() if r[0]])

    fontes_result = await db.execute(
        select(distinct(Vehicle.source_name)).where(Vehicle.ativo == True)
    )
    fontes = sorted({*STATIC_SOURCE_OPTIONS, *[r[0] for r in fontes_result.all() if r[0]]})

    preco_result = await db.execute(
        select(func.min(Vehicle.preco), func.max(Vehicle.preco)).where(Vehicle.ativo == True, Vehicle.preco != None)
    )
    preco_row = preco_result.one()

    ano_result = await db.execute(
        select(func.min(Vehicle.ano), func.max(Vehicle.ano)).where(Vehicle.ativo == True, Vehicle.ano != None)
    )
    ano_row = ano_result.one()

    options = {
        "marcas": marcas,
        "modelos": modelos_dict,
        "estados": estados,
        "cidades": cidades_dict,
        "combustiveis": combustiveis,
        "cambios": cambios,
        "vendedor_tipos": vendedores,
        "fontes": fontes,
        "preco_min": preco_row[0],
        "preco_max": preco_row[1],
        "ano_min": ano_row[0],
        "ano_max": ano_row[1],
    }

    await cache_set(cache_key, options, ttl=600)
    return options


async def get_favorites(db: AsyncSession, session_id: str):
    result = await db.execute(
        select(Favorite).where(Favorite.session_id == session_id).order_by(Favorite.created_at.desc())
    )
    favorites = result.scalars().all()

    vehicle_ids = [f.vehicle_id for f in favorites]
    if not vehicle_ids:
        return []

    vehicles_result = await db.execute(
        select(Vehicle).where(Vehicle.id.in_(vehicle_ids), Vehicle.ativo == True)
    )
    vehicles_map = {v.id: v for v in vehicles_result.scalars().all()}

    response = []
    for fav in favorites:
        vehicle = vehicles_map.get(fav.vehicle_id)
        if vehicle:
            response.append({
                "id": fav.id,
                "session_id": fav.session_id,
                "vehicle_id": fav.vehicle_id,
                "vehicle": _vehicle_to_card(vehicle),
                "created_at": fav.created_at,
            })

    return response


async def add_favorite(db: AsyncSession, session_id: str, vehicle_id: int):
    existing = await db.execute(
        select(Favorite).where(
            Favorite.session_id == session_id,
            Favorite.vehicle_id == vehicle_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    vehicle_check = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    if not vehicle_check.scalar_one_or_none():
        return None

    fav = Favorite(session_id=session_id, vehicle_id=vehicle_id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


async def remove_favorite(db: AsyncSession, session_id: str, vehicle_id: int):
    result = await db.execute(
        select(Favorite).where(
            Favorite.session_id == session_id,
            Favorite.vehicle_id == vehicle_id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        return False
    await db.delete(fav)
    await db.commit()
    return True


async def create_or_update_vehicle(db: AsyncSession, vehicle_data: dict) -> Vehicle:
    flags = detect_listing_flags(vehicle_data, preco_referencia=vehicle_data.get("fipe_preco"))
    vehicle_data = {
        **vehicle_data,
        "possui_passagem_leilao": bool(vehicle_data["possui_passagem_leilao"]) if "possui_passagem_leilao" in vehicle_data else flags["possui_passagem_leilao"],
        "valor_referente_entrada": bool(vehicle_data["valor_referente_entrada"]) if "valor_referente_entrada" in vehicle_data else flags["valor_referente_entrada"],
        "preco_suspeito": bool(vehicle_data["preco_suspeito"]) if "preco_suspeito" in vehicle_data else flags["preco_suspeito"],
    }

    existing = await db.execute(
        select(Vehicle).where(Vehicle.source_url == vehicle_data["source_url"])
    )
    existing_vehicle = existing.scalar_one_or_none()

    if existing_vehicle:
        for key, value in vehicle_data.items():
            if hasattr(existing_vehicle, key):
                setattr(existing_vehicle, key, value)
        existing_vehicle.ativo = True
        existing_vehicle.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_vehicle)
        return existing_vehicle
    else:
        vehicle = Vehicle(**vehicle_data)
        db.add(vehicle)
        await db.commit()
        await db.refresh(vehicle)
        return vehicle


async def delete_stale_vehicles(days: int = 7) -> int:
    """
    Apaga permanentemente veículos não re-raspados nos últimos `days` dias.
    Remove também os favoritos associados (sem FK cascade no schema).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with AsyncSessionLocal() as db:
        stale_result = await db.execute(
            select(Vehicle.id).where(
                or_(
                    Vehicle.updated_at < cutoff,
                    and_(Vehicle.updated_at == None, Vehicle.created_at < cutoff),
                )
            )
        )
        stale_ids = [row[0] for row in stale_result.all()]

        if not stale_ids:
            logger.info("Stale cleanup: nenhum veículo para apagar")
            return 0

        # Remove favoritos órfãos antes de deletar os veículos
        await db.execute(delete(Favorite).where(Favorite.vehicle_id.in_(stale_ids)))

        result = await db.execute(delete(Vehicle).where(Vehicle.id.in_(stale_ids)))
        await db.commit()

        count = result.rowcount
        from app.core.cache import cache_delete_pattern
        await cache_delete_pattern("search:*")
        await cache_delete_pattern("filter_options")
        logger.info(f"Stale cleanup: {count} veículos apagados (>{days} dias sem scrape)")
        return count


async def refresh_active_listings(batch_size: int = 200) -> int:
    """
    Checks a batch of active listings (oldest updated first) via HTTP HEAD.
    Marks as ativo=False those that return 404 or 410 (anúncio removido).
    Skips on network errors (temporary failures).
    """
    import httpx

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Vehicle.id, Vehicle.source_url)
            .where(Vehicle.ativo == True)
            .order_by(
                Vehicle.updated_at.asc().nullsfirst(),
                Vehicle.created_at.asc(),
            )
            .limit(batch_size)
        )
        rows = result.all()

    if not rows:
        logger.info("Refresh: nenhum veículo ativo para checar")
        return 0

    inactive_ids: list[int] = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    sem = asyncio.Semaphore(20)

    async def _check(vid: int, url: str):
        async with sem:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
                    r = await client.head(url, headers=headers)
                    if r.status_code in (404, 410):
                        inactive_ids.append(vid)
                    elif r.status_code == 405:
                        # HEAD not allowed — try GET
                        r2 = await client.get(url, headers=headers)
                        if r2.status_code in (404, 410):
                            inactive_ids.append(vid)
            except Exception:
                pass  # Network/timeout errors are temporary — skip

    await asyncio.gather(*[_check(vid, url) for vid, url in rows])

    if inactive_ids:
        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(Vehicle)
                .where(Vehicle.id.in_(inactive_ids))
                .values(ativo=False)
            )
            await db.commit()
        from app.core.cache import cache_delete_pattern
        await cache_delete_pattern("search:*")
        await cache_delete_pattern("filter_options")

    logger.info(f"Refresh: {len(rows)} URLs checadas, {len(inactive_ids)} desativadas")
    return len(inactive_ids)


def _vehicle_to_card(v: Vehicle) -> dict:
    return {
        "id": v.id,
        "titulo": v.titulo,
        "marca": v.marca,
        "modelo": v.modelo,
        "versao": v.versao,
        "ano": v.ano,
        "km": v.km,
        "preco": v.preco,
        "cidade": v.cidade,
        "estado": v.estado,
        "vendedor_tipo": v.vendedor_tipo,
        "fotos": v.fotos or [],
        "source_url": v.source_url,
        "source_name": v.source_name,
        "possui_passagem_leilao": v.possui_passagem_leilao,
        "valor_referente_entrada": v.valor_referente_entrada,
        "preco_suspeito": v.preco_suspeito,
        "score": v.score,
        "insights": v.insights or [],
        "fipe_preco": v.fipe_preco,
        "combustivel": v.combustivel,
        "cambio": v.cambio,
        "created_at": v.created_at,
    }


def _vehicle_to_dict(v: Vehicle) -> dict:
    return {
        "id": v.id,
        "titulo": v.titulo,
        "marca": v.marca,
        "modelo": v.modelo,
        "versao": v.versao,
        "ano": v.ano,
        "km": v.km,
        "preco": v.preco,
        "cambio": v.cambio,
        "combustivel": v.combustivel,
        "cidade": v.cidade,
        "estado": v.estado,
        "vendedor_tipo": v.vendedor_tipo,
        "descricao": v.descricao,
        "fotos": v.fotos or [],
        "fipe_preco": v.fipe_preco,
        "source_url": v.source_url,
        "source_name": v.source_name,
        "possui_passagem_leilao": v.possui_passagem_leilao,
        "valor_referente_entrada": v.valor_referente_entrada,
        "preco_suspeito": v.preco_suspeito,
        "score": v.score,
        "insights": v.insights or [],
        "ativo": v.ativo,
        "created_at": v.created_at,
        "updated_at": v.updated_at,
    }
