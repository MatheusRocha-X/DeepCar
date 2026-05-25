from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Boolean, Index
from sqlalchemy.sql import func
from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(500), nullable=False)
    marca = Column(String(100), nullable=False, index=True)
    modelo = Column(String(100), nullable=False, index=True)
    versao = Column(String(200), nullable=True)
    ano = Column(Integer, nullable=True, index=True)
    km = Column(Integer, nullable=True, index=True)
    preco = Column(Float, nullable=True, index=True)
    cambio = Column(String(50), nullable=True)
    combustivel = Column(String(50), nullable=True)
    cidade = Column(String(100), nullable=True, index=True)
    estado = Column(String(2), nullable=True, index=True)
    vendedor_tipo = Column(String(50), nullable=True)
    descricao = Column(Text, nullable=True)
    fotos = Column(JSON, default=list)
    source_url = Column(String(1000), nullable=False, unique=True)
    source_name = Column(String(50), nullable=False, index=True)
    score = Column(Float, default=0.0, index=True)
    insights = Column(JSON, default=list)
    fipe_preco = Column(Float, nullable=True)
    ativo = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_vehicles_marca_modelo", "marca", "modelo"),
        Index("ix_vehicles_estado_cidade", "estado", "cidade"),
        Index("ix_vehicles_preco_km", "preco", "km"),
    )
