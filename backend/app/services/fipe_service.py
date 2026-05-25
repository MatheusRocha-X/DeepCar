"""
FIPE table lookup service.

Uses the free public FIPE API from parallelum.com.br to get the official
reference price for a vehicle by brand/model/year.

Results are cached in-memory (FIPE updates monthly so a long TTL is fine).
"""
import asyncio
import logging
import re
from typing import Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://parallelum.com.br/fipe/api/v1/carros"
_TIMEOUT = httpx.Timeout(10.0)

# In-memory cache: key → (value, expires_at)
_cache: dict = {}
_CACHE_TTL_HOURS = 12


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and datetime.now() < entry[1]:
        return entry[0]
    return None


def _cache_set(key: str, value, ttl_hours: float = _CACHE_TTL_HOURS):
    _cache[key] = (value, datetime.now() + timedelta(hours=ttl_hours))


async def _get_json(client: httpx.AsyncClient, url: str):
    cache_key = url
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    
    for attempt in range(4):
        try:
            resp = await client.get(url, timeout=_TIMEOUT)
            if resp.status_code == 429:
                wait = 2 ** attempt  # 1, 2, 4, 8 seconds
                logger.debug(f"FIPE 429, waiting {wait}s (attempt {attempt+1})")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            _cache_set(cache_key, data)
            return data
        except httpx.HTTPStatusError:
            raise
        except Exception as e:
            logger.debug(f"FIPE API error for {url}: {e}")
            return None
    
    logger.debug(f"FIPE API gave up after retries: {url}")
    return None


def _normalize(text: str) -> str:
    """Lowercase, remove accents (basic), collapse spaces."""
    text = text.lower().strip()
    replacements = {
        "á": "a", "à": "a", "â": "a", "ã": "a",
        "é": "e", "ê": "e", "è": "e",
        "í": "i", "ï": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ü": "u",
        "ç": "c", "ñ": "n",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text)


def _best_match(query: str, items: list[dict], key: str = "nome") -> Optional[dict]:
    """Find the best matching item from a list using simple substring matching."""
    q = _normalize(query)
    # Exact match first
    for item in items:
        if _normalize(item.get(key, "")) == q:
            return item
    # Starts-with match
    for item in items:
        if _normalize(item.get(key, "")).startswith(q):
            return item
    # Contains match
    for item in items:
        if q in _normalize(item.get(key, "")):
            return item
    # Partial: first word of query in item name
    first_word = q.split()[0] if q.split() else q
    if len(first_word) >= 3:
        for item in items:
            if first_word in _normalize(item.get(key, "")):
                return item
    return None


def _parse_fipe_price(valor_str: str) -> Optional[float]:
    """Parse 'R$ 45.274,00' → 45274.0"""
    try:
        cleaned = valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(cleaned)
    except Exception:
        return None


async def get_fipe_price(
    marca: str,
    modelo: str,
    ano: int,
) -> Optional[dict]:
    """
    Returns a dict with:
        preco: float
        referencia: str  (e.g. "fevereiro de 2024")
        codigo_fipe: str
        nome_completo: str
    Returns None if not found.
    """
    if not marca or not modelo or not ano:
        return None

    async with httpx.AsyncClient() as client:
        # 1. Get brands list
        brands = await _get_json(client, f"{_BASE}/marcas")
        if not brands:
            return None

        brand_match = _best_match(marca, brands)
        if not brand_match:
            logger.debug(f"FIPE: brand not found for '{marca}'")
            return None

        cod_marca = brand_match["codigo"]

        # 2. Get models for brand
        models_data = await _get_json(client, f"{_BASE}/marcas/{cod_marca}/modelos")
        if not models_data:
            return None

        modelos_list = models_data.get("modelos", [])
        model_match = _best_match(modelo, modelos_list)
        if not model_match:
            logger.debug(f"FIPE: model not found for '{modelo}' (brand={marca})")
            return None

        cod_modelo = model_match["codigo"]

        # 3. Get years for model
        years = await _get_json(
            client, f"{_BASE}/marcas/{cod_marca}/modelos/{cod_modelo}/anos"
        )
        if not years:
            return None

        # Match year — year codes look like "2022-1" (petrol), "2022-3" (diesel), "32000-99" (0km)
        year_match = None
        for y in years:
            code_year = str(y.get("codigo", "")).split("-")[0]
            if code_year == str(ano):
                year_match = y
                break

        if not year_match:
            # Try closest year within 1 year
            for delta in [1, -1, 2, -2]:
                target = str(ano + delta)
                for y in years:
                    code_year = str(y.get("codigo", "")).split("-")[0]
                    if code_year == target:
                        year_match = y
                        break
                if year_match:
                    break

        if not year_match:
            logger.debug(f"FIPE: year {ano} not found for {marca} {modelo}")
            return None

        cod_ano = year_match["codigo"]

        # 4. Get price
        price_data = await _get_json(
            client,
            f"{_BASE}/marcas/{cod_marca}/modelos/{cod_modelo}/anos/{cod_ano}",
        )
        if not price_data:
            return None

        preco = _parse_fipe_price(price_data.get("Valor", ""))
        if not preco:
            return None

        return {
            "preco": preco,
            "referencia": price_data.get("MesReferencia", ""),
            "codigo_fipe": price_data.get("CodigoFipe", ""),
            "nome_completo": price_data.get("Modelo", ""),
        }


async def preload_brands() -> bool:
    """
    Pre-fetch the brands list into cache so batch lookups
    don't all hit /marcas simultaneously and trigger 429s.
    Call once before running calcular_score_batch_com_fipe.
    """
    brands_url = f"{_BASE}/marcas"
    if _cache_get(brands_url) is not None:
        return True  # Already cached
    async with httpx.AsyncClient() as client:
        brands = await _get_json(client, brands_url)
        return brands is not None
