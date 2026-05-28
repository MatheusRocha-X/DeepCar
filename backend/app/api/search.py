from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.models.schemas import SearchFilters, SearchResponse, OrderBy
from app.services.vehicle_service import search_vehicles, has_meaningful_search_filters

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: Optional[str] = Query(None, description="Busca por texto livre"),
    marca: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    ano_min: Optional[int] = Query(None, ge=1950),
    ano_max: Optional[int] = Query(None, le=2030),
    km_min: Optional[int] = Query(None, ge=0),
    km_max: Optional[int] = Query(None, ge=0),
    preco_min: Optional[float] = Query(None, ge=0),
    preco_max: Optional[float] = Query(None, ge=0),
    vendedor_tipo: Optional[str] = Query(None),
    combustivel: Optional[str] = Query(None),
    cambio: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    cidade: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    passagem_leilao: Optional[bool] = Query(None),
    order_by: Optional[OrderBy] = Query(OrderBy.score),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    filters = SearchFilters(
        q=q,
        marca=marca,
        modelo=modelo,
        ano_min=ano_min,
        ano_max=ano_max,
        km_min=km_min,
        km_max=km_max,
        preco_min=preco_min,
        preco_max=preco_max,
        vendedor_tipo=vendedor_tipo,
        combustivel=combustivel,
        cambio=cambio,
        estado=estado,
        cidade=cidade,
        source=source,
        passagem_leilao=passagem_leilao,
        order_by=order_by,
        page=page,
        per_page=per_page,
    )
    result = await search_vehicles(db, filters)

    # Trigger a background scrape on page 1 whenever the user applies filters.
    # The scheduler debounces repeated triggers (30-min cooldown per query).
    if page == 1 and has_meaningful_search_filters(filters):
        from app.scrapers.scheduler import scraper_scheduler
        scraper_scheduler.start_smart_scrape_for_filters(filters)

    return result
