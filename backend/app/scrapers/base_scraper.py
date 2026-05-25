from abc import ABC, abstractmethod
from typing import List, Optional
import logging
import random
import asyncio
from app.core.text_normalizer import normalize_city
from app.scrapers.normalizer import normalize_brand, normalize_model

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class BaseVehicleData:
    def __init__(self):
        self.titulo: Optional[str] = None
        self.marca: Optional[str] = None
        self.modelo: Optional[str] = None
        self.versao: Optional[str] = None
        self.ano: Optional[int] = None
        self.km: Optional[int] = None
        self.preco: Optional[float] = None
        self.cambio: Optional[str] = None
        self.combustivel: Optional[str] = None
        self.cidade: Optional[str] = None
        self.estado: Optional[str] = None
        self.vendedor_tipo: Optional[str] = None
        self.descricao: Optional[str] = None
        self.fotos: List[str] = []
        self.source_url: Optional[str] = None
        self.source_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "titulo": self.titulo,
            "marca": normalize_brand(self.marca),
            "modelo": normalize_model(self.modelo),
            "versao": self.versao,
            "ano": self.ano,
            "km": self.km,
            "preco": self.preco,
            "cambio": self.cambio,
            "combustivel": self.combustivel,
            "cidade": normalize_city(self.cidade),
            "estado": self.estado.strip().upper() if self.estado else self.estado,
            "vendedor_tipo": self.vendedor_tipo,
            "descricao": self.descricao,
            "fotos": self.fotos,
            "source_url": self.source_url,
            "source_name": self.source_name,
        }

    def is_valid(self) -> bool:
        return bool(
            self.titulo
            and self.source_url
            and self.source_name
            and (self.marca or self.modelo)
        )


class BaseScraper(ABC):
    def __init__(self, source_name: str, max_pages: int = 10):
        self.source_name = source_name
        self.max_pages = max_pages
        self.logger = logging.getLogger(f"scraper.{source_name}")

    @abstractmethod
    async def scrape(self, max_pages: Optional[int] = None) -> List[dict]:
        pass

    def _get_random_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    async def _random_delay(self, min_ms: int = 1000, max_ms: int = 3000):
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    def _parse_preco(self, text: str) -> Optional[float]:
        if not text:
            return None
        cleaned = text.replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            value = float(cleaned)
            if 1000 <= value <= 10_000_000:
                return value
        except (ValueError, TypeError):
            pass
        return None

    def _parse_km(self, text: str) -> Optional[int]:
        if not text:
            return None
        cleaned = text.lower().replace("km", "").replace(".", "").strip()
        try:
            value = int(cleaned)
            if 0 <= value <= 2_000_000:
                return value
        except (ValueError, TypeError):
            pass
        return None

    def _parse_ano(self, text: str) -> Optional[int]:
        if not text:
            return None
        import re
        match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', text)
        if match:
            return int(match.group())
        return None

    def _normalize_cambio(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        if "automátic" in text_lower or "automatic" in text_lower:
            return "Automático"
        if "cvt" in text_lower:
            return "CVT"
        if "automatizado" in text_lower:
            return "Automatizado"
        if "manual" in text_lower:
            return "Manual"
        return text.strip()

    def _normalize_combustivel(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        if "flex" in text_lower:
            return "Flex"
        if "gasolina" in text_lower:
            return "Gasolina"
        if "diesel" in text_lower:
            return "Diesel"
        if "elétric" in text_lower or "electric" in text_lower:
            return "Elétrico"
        if "híbrid" in text_lower or "hybrid" in text_lower:
            return "Híbrido"
        return text.strip()

    def _normalize_vendedor(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        if "concession" in text_lower:
            return "Concessionária"
        if "loja" in text_lower or "dealer" in text_lower or "pj" in text_lower:
            return "Loja"
        return "Pessoa Física"
