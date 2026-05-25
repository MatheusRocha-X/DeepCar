"""
Normalizes car brand and model names coming from different scrapers.
Maps variant spellings → canonical form used across the application.
"""

from app.core.text_normalizer import normalize_city, normalize_text_key


def _key(raw: str) -> str:
    """Lowercase, strip accents, collapse whitespace/hyphens/underscores."""
    return normalize_text_key(raw)


# Maps normalized key → canonical brand name used in the DB and UI
_BRAND_MAP: dict[str, str] = {
    # ── Citroën ────────────────────────────────────────────────────────────
    "citroen": "Citroën",
    # ── Volkswagen ─────────────────────────────────────────────────────────
    "volkswagen": "Volkswagen",
    "vw": "Volkswagen",
    # ── BMW ────────────────────────────────────────────────────────────────
    "bmw": "BMW",
    # ── Mercedes-Benz ──────────────────────────────────────────────────────
    "mercedes benz": "Mercedes-Benz",
    "mercedesbenz": "Mercedes-Benz",
    "mercedes": "Mercedes-Benz",
    "mercedes-benz": "Mercedes-Benz",
    "mercedes benz ag": "Mercedes-Benz",
    # ── Caoa Chery ─────────────────────────────────────────────────────────
    "caoa chery": "Caoa Chery",
    "coa chery": "Caoa Chery",
    "caoa": "Caoa Chery",
    "chery": "Caoa Chery",
    # ── Land Rover ─────────────────────────────────────────────────────────
    "land rover": "Land Rover",
    "landrover": "Land Rover",
    # ── Alfa Romeo ─────────────────────────────────────────────────────────
    "alfa romeo": "Alfa Romeo",
    "alfa": "Alfa Romeo",
    # ── MINI ───────────────────────────────────────────────────────────────
    "mini": "MINI",
    "mini cooper": "MINI",
    # ── BYD ────────────────────────────────────────────────────────────────
    "byd": "BYD",
    # ── GWM ────────────────────────────────────────────────────────────────
    "gwm": "GWM",
    # ── JAC ────────────────────────────────────────────────────────────────
    "jac": "JAC",
    "jac motors": "JAC",
    # ── SEAT ───────────────────────────────────────────────────────────────
    "seat": "SEAT",
    # ── Škoda ──────────────────────────────────────────────────────────────
    "skoda": "Škoda",
    # ── Kia ────────────────────────────────────────────────────────────────
    "kia": "Kia",
    "kia motors": "Kia",
    # ── Others with consistent canonical form ──────────────────────────────
    "fiat": "Fiat",
    "chevrolet": "Chevrolet",
    "gm": "Chevrolet",
    "ford": "Ford",
    "toyota": "Toyota",
    "honda": "Honda",
    "hyundai": "Hyundai",
    "renault": "Renault",
    "nissan": "Nissan",
    "jeep": "Jeep",
    "peugeot": "Peugeot",
    "audi": "Audi",
    "mitsubishi": "Mitsubishi",
    "subaru": "Subaru",
    "volvo": "Volvo",
    "jaguar": "Jaguar",
    "porsche": "Porsche",
    "lexus": "Lexus",
    "suzuki": "Suzuki",
    "dodge": "Dodge",
    "ram": "Ram",
    "lifan": "Lifan",
    "geely": "Geely",
    "haval": "Haval",
    "smart": "Smart",
    "opel": "Opel",
    "isuzu": "Isuzu",
    "mazda": "Mazda",
    "infiniti": "Infiniti",
    "acura": "Acura",
    "maserati": "Maserati",
    "ferrari": "Ferrari",
    "lamborghini": "Lamborghini",
    "bentley": "Bentley",
    "rolls royce": "Rolls-Royce",
    "rollsroyce": "Rolls-Royce",
}

# Model names that must be all-uppercase (acronyms / abbreviations)
_UPPERCASE_MODELS = {
    "hb20", "hb20s", "hb20x", "suv", "crv", "hrv", "wrv", "brz",
    "byd", "gwm", "jac",
}

# Model names with specific mixed case
_MODEL_CANONICAL: dict[str, str] = {
    "hb20": "HB20",
    "hb20s": "HB20S",
    "hb20x": "HB20X",
    "cr v": "CR-V",
    "crv": "CR-V",
    "cr-v": "CR-V",
    "hr v": "HR-V",
    "hrv": "HR-V",
    "hr-v": "HR-V",
    "wr v": "WR-V",
    "wrv": "WR-V",
    "wr-v": "WR-V",
    "t cross": "T-Cross",
    "t-cross": "T-Cross",
    "c3": "C3",
    "c4": "C4",
    "c5": "C5",
    "sw4": "SW4",
    "hb 20": "HB20",
    "hb 20s": "HB20S",
}


def normalize_brand(raw: str | None) -> str | None:
    """Return canonical brand name, or title-cased raw if not in the map."""
    if not raw:
        return raw
    raw = raw.strip()
    if not raw:
        return raw
    k = _key(raw)
    if k in _BRAND_MAP:
        return _BRAND_MAP[k]
    # Not in map — apply basic title case as fallback
    return raw.title()


def normalize_model(raw: str | None) -> str | None:
    """Return canonical model name, applying known fixes and title case."""
    if not raw:
        return raw
    raw = raw.strip()
    if not raw:
        return raw
    k = _key(raw)
    if k in _MODEL_CANONICAL:
        return _MODEL_CANONICAL[k]
    # title() handles most models correctly
    result = raw.title()
    # Fix common title() artifacts: "Hb20" → keep known exceptions whole
    result_key = _key(result)
    if result_key in _MODEL_CANONICAL:
        return _MODEL_CANONICAL[result_key]
    return result
