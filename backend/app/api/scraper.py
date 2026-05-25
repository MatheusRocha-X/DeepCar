from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.scrapers.scheduler import scraper_scheduler
from app.services.scrape_service import get_initial_bootstrap_status
import json

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/run/{source}")
async def run_scraper(
    source: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    valid_sources = ["olx", "all"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Fonte inválida. Use: {valid_sources}")

    background_tasks.add_task(scraper_scheduler.run_source, source, db)
    return {"message": f"Scraper iniciado para: {source}"}


@router.post("/live")
async def live_scrape(
    background_tasks: BackgroundTasks,
    q: str = Query(..., min_length=2, description="Busca a ser rastreada em tempo real"),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara um scrape rápido (2 páginas OLX) para a query do usuário.
    Roda em background — o frontend deve re-buscar após ~15s.
    """
    background_tasks.add_task(scraper_scheduler.live_scrape, q, db)
    return {"message": f"Buscando '{q}' ao vivo...", "query": q, "eta_seconds": 15}


@router.get("/live/stream")
async def live_scrape_stream(
    q: str = Query(..., min_length=2, description="Busca a ser rastreada em tempo real"),
):
    """
    SSE endpoint: transmite progresso do scraping em tempo real.
    Eventos: {"source": str, "saved": int} por lote, depois {"done": true, "total": int}.
    """
    async def event_generator():
        try:
            async for event in scraper_scheduler.stream_live_scrape(q):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True, 'total': 0})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
async def scraper_status():
    return scraper_scheduler.get_status()


@router.get("/bootstrap-status")
async def bootstrap_status():
    return get_initial_bootstrap_status()


@router.post("/cancel")
async def cancel_scrape(
    q: str = Query(..., min_length=1, description="Busca ativa que deve ser cancelada"),
):
    return scraper_scheduler.cancel_query_scrape(q)


@router.get("/progress")
async def scrape_progress(
    q: str = Query(..., min_length=1, description="Busca ativa para consultar o progresso"),
):
    return scraper_scheduler.get_query_progress(q)
