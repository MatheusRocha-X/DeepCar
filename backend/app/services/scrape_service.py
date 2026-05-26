import asyncio
import json
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from typing import Optional

from sqlalchemy import func, select

from app.core.cache import cache_delete_pattern
from app.core.database import AsyncSessionLocal
from app.models.vehicle import Vehicle
from app.scrapers.olx_scraper import OLXScraper
from app.services.score_service import calcular_score_batch
from app.services.vehicle_service import create_or_update_vehicle

logger = logging.getLogger(__name__)

DEFAULT_MANUAL_SCRAPE_PAGES = 3
ACTIVE_SOURCE_NAMES = ("OLX",)
SOURCE_DB_NAMES = {
    "olx": "OLX",
}
ACTIVE_SCRAPERS = {
    "olx": OLXScraper,
}
INITIAL_BOOTSTRAP_TARGETS = {
    "olx": 500,
}
OLX_PAGE_SIZE_ESTIMATE = 50
OLX_BOOTSTRAP_CHUNK_PAGES = 5
OLX_BOOTSTRAP_MIN_MAX_PAGES = 15
OLX_BOOTSTRAP_SAFETY_MULTIPLIER = 3

_bootstrap_status = {
    "status": "idle",
    "running": False,
    "done": False,
    "triggered": False,
    "needs_initial_load": False,
    "message": "Base inicial pronta.",
    "current_source": None,
    "targets": dict(INITIAL_BOOTSTRAP_TARGETS),
    "saved_by_source": {source: 0 for source in INITIAL_BOOTSTRAP_TARGETS},
    "started_at": None,
    "updated_at": None,
    "finished_at": None,
    "error": None,
}


async def _invalidate_catalog_cache() -> None:
    await cache_delete_pattern("search:*")
    await cache_delete_pattern("filter_options")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_bootstrap_status(**updates) -> None:
    saved_by_source = updates.pop("saved_by_source", None)
    targets = updates.pop("targets", None)

    if targets is not None:
        _bootstrap_status["targets"] = dict(targets)
    if saved_by_source is not None:
        _bootstrap_status["saved_by_source"].update(saved_by_source)

    _bootstrap_status.update(updates)
    _bootstrap_status["updated_at"] = _now_iso()


def _snapshot_bootstrap_status() -> dict:
    targets = dict(_bootstrap_status["targets"])
    saved_by_source = dict(_bootstrap_status["saved_by_source"])
    remaining_by_source = {
        source: max(targets.get(source, 0) - saved_by_source.get(source, 0), 0)
        for source in targets
    }
    total_target = sum(targets.values())
    total_saved = sum(min(saved_by_source.get(source, 0), targets.get(source, 0)) for source in targets)

    return {
        **_bootstrap_status,
        "targets": targets,
        "saved_by_source": saved_by_source,
        "remaining_by_source": remaining_by_source,
        "total_target": total_target,
        "total_saved": total_saved,
    }


def get_initial_bootstrap_status() -> dict:
    return _snapshot_bootstrap_status()


async def _run_olx_worker(
    pages: int,
    query: Optional[str] = None,
    start_page: int = 1,
) -> dict:
    worker_script = Path(__file__).resolve().parents[2] / "olx_query_worker.py"
    if not worker_script.exists():
        raise FileNotFoundError(f"OLX worker script not found: {worker_script}")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    command = [sys.executable, str(worker_script), query or "", str(pages), str(start_page)]
    completed = await asyncio.to_thread(
        subprocess.run,
        command,
        cwd=str(worker_script.parent),
        capture_output=True,
        text=True,
        env={**os.environ, "OLX_WORKER_RESULT_JSON": "1"},
        creationflags=creationflags,
        check=False,
    )

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown error").strip()
        raise RuntimeError(f"OLX worker failed: {detail}")

    stdout_lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    if not stdout_lines:
        return {"saved": 0, "query": query or "", "pages": pages}

    try:
        return json.loads(stdout_lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OLX worker returned invalid output: {stdout_lines[-1]}") from exc


async def _save_vehicle_batch(raw_vehicles: list[dict], source_label: str) -> int:
    valid_vehicles = [
        vehicle for vehicle in raw_vehicles
        if vehicle.get("titulo") and vehicle.get("source_url") and vehicle.get("modelo")
    ]

    if not valid_vehicles:
        return 0

    scored_vehicles = calcular_score_batch(valid_vehicles, calcular_media_por_modelo=True)
    saved_count = 0
    for vehicle_data in scored_vehicles:
        try:
            async with AsyncSessionLocal() as db:
                await create_or_update_vehicle(db, vehicle_data)
            saved_count += 1
        except Exception as exc:
            logger.warning("Failed to save vehicle from %s: %s", source_label, exc)

    return saved_count


async def run_single_source_scraper(
    name: str,
    pages: int = DEFAULT_MANUAL_SCRAPE_PAGES,
    *,
    start_page: int = 1,
    query: Optional[str] = None,
) -> dict:
    if name not in ACTIVE_SCRAPERS:
        raise ValueError(f"Fonte desconhecida: {name}. Use: {', '.join(ACTIVE_SCRAPERS)}")

    logger.info("Running scraper '%s' with %s pages from page %s", name, pages, start_page)

    if name == "olx":
        worker_result = await _run_olx_worker(pages=pages, query=query, start_page=start_page)
        saved_count = int(worker_result.get("saved", 0) or 0)
        logger.info("Scraper '%s' finished with %s saved vehicles via worker", name, saved_count)
        return {"source": name, "saved": saved_count}

    scraper_class = ACTIVE_SCRAPERS[name]
    scraper = scraper_class(max_pages=pages, query=query, start_page=start_page)
    raw_vehicles = await scraper.scrape(max_pages=pages)
    saved_count = await _save_vehicle_batch(raw_vehicles, name)
    logger.info("Scraper '%s' finished with %s saved vehicles", name, saved_count)
    return {"source": name, "saved": saved_count}


async def run_manual_scrapers(target: str = "all", pages: int = DEFAULT_MANUAL_SCRAPE_PAGES) -> dict:
    if target == "all":
        sources = list(ACTIVE_SCRAPERS.keys())
    elif target in ACTIVE_SCRAPERS:
        sources = [target]
    else:
        raise ValueError(f"Fonte desconhecida: {target}. Use: {', '.join(ACTIVE_SCRAPERS)} ou 'all'")

    saved_by_source: dict[str, int] = {}
    total_saved = 0

    for name in sources:
        try:
            result = await run_single_source_scraper(name, pages=pages)
        except Exception as exc:
            logger.error("Scraper '%s' failed in manual run: %s", name, exc)
            saved_by_source[name] = 0
            continue

        saved_count = int(result.get("saved", 0) or 0)
        saved_by_source[name] = saved_count
        total_saved += saved_count

    if total_saved:
        await _invalidate_catalog_cache()

    return {
        "target": target,
        "pages": pages,
        "total_saved": total_saved,
        "saved_by_source": saved_by_source,
    }


async def get_active_source_counts() -> dict[str, int]:
    counts = {source: 0 for source in SOURCE_DB_NAMES}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Vehicle.source_name, func.count())
            .where(Vehicle.source_name.in_(ACTIVE_SOURCE_NAMES))
            .group_by(Vehicle.source_name)
        )
        rows = result.all()

    source_by_db_name = {db_name: source for source, db_name in SOURCE_DB_NAMES.items()}
    for source_name, count in rows:
        source = source_by_db_name.get(source_name)
        if source:
            counts[source] = int(count or 0)
    return counts


async def count_active_source_vehicles() -> int:
    counts = await get_active_source_counts()
    return sum(counts.values())


def _get_olx_bootstrap_max_pages(target: int) -> int:
    estimated_pages = math.ceil(max(target, 1) / max(OLX_PAGE_SIZE_ESTIMATE, 1))
    return max(OLX_BOOTSTRAP_MIN_MAX_PAGES, estimated_pages * OLX_BOOTSTRAP_SAFETY_MULTIPLIER)


async def _bootstrap_olx_target(target: int, current_count: int) -> int:
    if current_count >= target:
        return current_count

    start_page = max(1, math.floor(current_count / OLX_PAGE_SIZE_ESTIMATE) + 1)
    max_pages = _get_olx_bootstrap_max_pages(target)
    while current_count < target and start_page <= max_pages:
        remaining = target - current_count
        pages = min(
            OLX_BOOTSTRAP_CHUNK_PAGES,
            max(1, math.ceil(remaining / OLX_PAGE_SIZE_ESTIMATE)),
        )
        result = await run_single_source_scraper("olx", pages=pages, start_page=start_page)
        chunk_saved = int(result.get("saved", 0) or 0)
        if chunk_saved <= 0:
            break

        refreshed_counts = await get_active_source_counts()
        current_count = int(refreshed_counts.get("olx", current_count) or 0)
        await _invalidate_catalog_cache()
        _update_bootstrap_status(
            current_source="olx",
            saved_by_source={"olx": current_count},
            message=f"Carregando anúncios iniciais da OLX ({min(current_count, target)}/{target}).",
        )
        start_page += pages

    if current_count < target:
        logger.info(
            "Initial OLX bootstrap stopped at %s/%s after scanning until page %s",
            current_count,
            target,
            max_pages,
        )

    return current_count


async def bootstrap_active_scrapers_if_needed(
    targets: Optional[dict[str, int]] = None,
) -> dict:
    target_counts = dict(targets or INITIAL_BOOTSTRAP_TARGETS)
    existing_counts = await get_active_source_counts()

    _bootstrap_status.update(
        {
            "status": "idle",
            "running": False,
            "done": False,
            "triggered": False,
            "needs_initial_load": False,
            "message": "Base inicial pronta.",
            "current_source": None,
            "targets": dict(target_counts),
            "saved_by_source": {source: existing_counts.get(source, 0) for source in target_counts},
            "started_at": None,
            "updated_at": _now_iso(),
            "finished_at": None,
            "error": None,
        }
    )

    needs_initial_load = any(existing_counts.get(source, 0) < target for source, target in target_counts.items())
    if not needs_initial_load:
        logger.info(
            "Initial scrape skipped because initial targets are already satisfied: %s",
            existing_counts,
        )
        _update_bootstrap_status(
            status="skipped",
            done=True,
            message="Base inicial já carregada.",
            finished_at=_now_iso(),
        )
        return {
            "triggered": False,
            "existing_active": sum(existing_counts.values()),
            "counts_by_source": existing_counts,
            "total_saved": 0,
            "saved_by_source": {},
        }

    logger.info("Initial scrape bootstrap starting with target counts %s", target_counts)
    _update_bootstrap_status(
        status="running",
        running=True,
        triggered=True,
        needs_initial_load=True,
        message="DeepCar está iniciando e carregando os anúncios iniciais da OLX.",
        started_at=_now_iso(),
        finished_at=None,
        error=None,
    )

    try:
        olx_count = await _bootstrap_olx_target(target_counts["olx"], existing_counts.get("olx", 0))
        final_counts = await get_active_source_counts()
        total_saved = sum(
            max(final_counts.get(source, 0) - existing_counts.get(source, 0), 0)
            for source in target_counts
        )
        if total_saved:
            await _invalidate_catalog_cache()
        _update_bootstrap_status(
            status="completed",
            running=False,
            done=True,
            needs_initial_load=False,
            current_source=None,
            saved_by_source={
                "olx": max(final_counts.get("olx", 0), olx_count),
            },
            message="Base inicial carregada. Agora voce ja pode explorar os anuncios.",
            finished_at=_now_iso(),
        )
        logger.info("Initial scrape bootstrap finished with %s saved vehicles", total_saved)
        return {
            "triggered": True,
            "existing_active": sum(existing_counts.values()),
            "counts_by_source": final_counts,
            "total_saved": total_saved,
            "saved_by_source": {
                source: max(final_counts.get(source, 0) - existing_counts.get(source, 0), 0)
                for source in target_counts
            },
        }
    except Exception as exc:
        final_counts = await get_active_source_counts()
        _update_bootstrap_status(
            status="error",
            running=False,
            done=True,
            needs_initial_load=False,
            current_source=None,
            saved_by_source=final_counts,
            message="A carga inicial encontrou um problema, mas a aplicacao continua disponivel.",
            finished_at=_now_iso(),
            error=str(exc),
        )
        raise