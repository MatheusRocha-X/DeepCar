from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from app.core.text_normalizer import normalize_text_key


AUCTION_POSITIVE_PATTERNS = (
    r"\bpassagem por leilao\b",
    r"\bproveniente de leilao\b",
    r"\brecuperad[oa] de leilao\b",
    r"\bveiculo de leilao\b",
    r"\bcarro de leilao\b",
    r"\bleilao\b",
)

AUCTION_NEGATIVE_PATTERNS = (
    r"\bsem passagem por leilao\b",
    r"\bnunca teve passagem por leilao\b",
    r"\bnao tem passagem por leilao\b",
    r"\bnunca foi leilao\b",
    r"\bnao e leilao\b",
    r"\bsem leilao\b",
)

ENTRY_PRICE_PATTERNS = (
    r"\bvalor referente a entrada\b",
    r"\bvalor ref(?:erente)? a entrada\b",
    r"\bvalor da entrada\b",
    r"\bentrada \+ parcelas?\b",
    r"\bentrada \+ saldo\b",
    r"\bassumir parcelas?\b",
    r"\bassumir financiamento\b",
    r"\btransferencia de financiamento\b",
    r"\bsaldo devedor\b",
    r"\bparcela(?:s)? de\b",
    r"\bprestac(?:ao|oes) de\b",
    r"\bagio\b",
)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _coerce_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_listing_search_text(vehicle_data: dict[str, Any]) -> str:
    parts = [
        _clean_text(vehicle_data.get("titulo")),
        _clean_text(vehicle_data.get("descricao")),
        _clean_text(vehicle_data.get("marca")),
        _clean_text(vehicle_data.get("modelo")),
        _clean_text(vehicle_data.get("versao")),
        _clean_text(vehicle_data.get("source_url")),
    ]
    return normalize_text_key(" ".join(part for part in parts if part))


def has_auction_passage(vehicle_data: dict[str, Any]) -> bool:
    searchable_text = build_listing_search_text(vehicle_data)
    if not searchable_text:
        return False

    if any(re.search(pattern, searchable_text) for pattern in AUCTION_NEGATIVE_PATTERNS):
        return False

    return any(re.search(pattern, searchable_text) for pattern in AUCTION_POSITIVE_PATTERNS)


def has_entry_price_signal(vehicle_data: dict[str, Any]) -> bool:
    searchable_text = build_listing_search_text(vehicle_data)
    if not searchable_text:
        return False

    return any(re.search(pattern, searchable_text) for pattern in ENTRY_PRICE_PATTERNS)


def is_suspicious_price(
    preco: float,
    ano: Optional[int],
    preco_referencia: Optional[float] = None,
) -> bool:
    if preco <= 0:
        return False

    if preco_referencia and preco_referencia > 0 and preco / preco_referencia < 0.20:
        return True

    if ano:
        idade = max(0, date.today().year - ano)
        if idade <= 5 and preco < 10000:
            return True
        if idade <= 10 and preco < 5000:
            return True

    return preco < 3000


def detect_listing_flags(
    vehicle_data: dict[str, Any],
    *,
    preco_referencia: Optional[float] = None,
) -> dict[str, bool]:
    possui_passagem_leilao = has_auction_passage(vehicle_data)
    valor_referente_entrada = has_entry_price_signal(vehicle_data)
    preco = _coerce_float(vehicle_data.get("preco"))
    ano = _coerce_int(vehicle_data.get("ano"))
    preco_suspeito = bool(
        valor_referente_entrada
        or (preco is not None and is_suspicious_price(preco, ano, preco_referencia))
    )

    return {
        "possui_passagem_leilao": possui_passagem_leilao,
        "valor_referente_entrada": valor_referente_entrada,
        "preco_suspeito": preco_suspeito,
    }