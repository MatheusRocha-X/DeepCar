import re
import unicodedata


_LOWERCASE_CITY_PARTS = {"da", "das", "de", "do", "dos", "e"}


def normalize_text_key(raw: str | None) -> str:
    """Return an accent-insensitive comparison key for arbitrary text."""
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFD", raw)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[\s\-_/]+", " ", normalized)
    return normalized


def _smart_title(raw: str) -> str:
    words = re.split(r"(\s+)", raw.strip())
    titled: list[str] = []
    word_index = 0

    for chunk in words:
        if not chunk or chunk.isspace():
            titled.append(chunk)
            continue

        parts = re.split(r"(-)", chunk)
        normalized_parts: list[str] = []
        for part in parts:
            if part == "-":
                normalized_parts.append(part)
                continue

            lowered = part.lower()
            if word_index > 0 and lowered in _LOWERCASE_CITY_PARTS:
                normalized_parts.append(lowered)
            else:
                normalized_parts.append(part[:1].upper() + part[1:].lower())
            word_index += 1

        titled.append("".join(normalized_parts))

    return "".join(titled)


def normalize_city(raw: str | None) -> str | None:
    """Return a cleaned city label preserving accents when present."""
    if not raw:
        return raw

    cleaned = re.sub(r"\s+", " ", raw).strip()
    if not cleaned:
        return cleaned

    return _smart_title(cleaned)