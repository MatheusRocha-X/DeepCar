from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class VendedorTipo(str, Enum):
    pessoa_fisica = "Pessoa Física"
    loja = "Loja"
    concessionaria = "Concessionária"


class Combustivel(str, Enum):
    flex = "Flex"
    gasolina = "Gasolina"
    diesel = "Diesel"
    eletrico = "Elétrico"
    hibrido = "Híbrido"


class Cambio(str, Enum):
    manual = "Manual"
    automatico = "Automático"
    cvt = "CVT"
    automatizado = "Automatizado"


class OrderBy(str, Enum):
    score = "score"
    menor_preco = "menor_preco"
    maior_preco = "maior_preco"
    menor_km = "menor_km"
    mais_recente = "mais_recente"


class VehicleBase(BaseModel):
    titulo: str
    marca: str
    modelo: str
    versao: Optional[str] = None
    ano: Optional[int] = None
    km: Optional[int] = None
    preco: Optional[float] = None
    cambio: Optional[str] = None
    combustivel: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    vendedor_tipo: Optional[str] = None
    descricao: Optional[str] = None
    fotos: Optional[List[str]] = []
    source_url: str
    source_name: str
    possui_passagem_leilao: bool = False
    valor_referente_entrada: bool = False
    preco_suspeito: bool = False
    score: Optional[float] = 0.0
    insights: Optional[List[str]] = []


class VehicleCreate(VehicleBase):
    pass


class VehicleResponse(VehicleBase):
    id: int
    ativo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VehicleCard(BaseModel):
    id: int
    titulo: str
    marca: str
    modelo: str
    versao: Optional[str] = None
    ano: Optional[int] = None
    km: Optional[int] = None
    preco: Optional[float] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    vendedor_tipo: Optional[str] = None
    fotos: Optional[List[str]] = []
    source_url: str
    source_name: str
    possui_passagem_leilao: bool = False
    valor_referente_entrada: bool = False
    preco_suspeito: bool = False
    score: Optional[float] = 0.0
    insights: Optional[List[str]] = []
    combustivel: Optional[str] = None
    cambio: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SearchFilters(BaseModel):
    q: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    ano_min: Optional[int] = Field(None, ge=1950, le=2030)
    ano_max: Optional[int] = Field(None, ge=1950, le=2030)
    km_min: Optional[int] = Field(None, ge=0)
    km_max: Optional[int] = Field(None, ge=0)
    preco_min: Optional[float] = Field(None, ge=0)
    preco_max: Optional[float] = Field(None, ge=0)
    vendedor_tipo: Optional[str] = None
    combustivel: Optional[str] = None
    cambio: Optional[str] = None
    estado: Optional[str] = None
    cidade: Optional[str] = None
    source: Optional[str] = None
    passagem_leilao: Optional[bool] = None
    order_by: Optional[OrderBy] = OrderBy.score
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class SearchResponse(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    results: List[VehicleCard]


class FilterOptions(BaseModel):
    marcas: List[str]
    modelos: dict[str, List[str]]
    estados: List[str]
    cidades: dict[str, List[str]]
    combustiveis: List[str]
    cambios: List[str]
    vendedor_tipos: List[str]
    fontes: List[str]
    preco_min: Optional[float] = None
    preco_max: Optional[float] = None
    ano_min: Optional[int] = None
    ano_max: Optional[int] = None


class FavoriteCreate(BaseModel):
    session_id: str
    vehicle_id: int


class FavoriteResponse(BaseModel):
    id: int
    session_id: str
    vehicle_id: int
    vehicle: Optional[VehicleCard] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ScraperStatus(BaseModel):
    source: str
    status: str
    last_run: Optional[datetime] = None
    total_collected: int = 0
    errors: int = 0
