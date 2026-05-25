import asyncio
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("olx_query_worker")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal, create_tables
from app.models.schemas import SearchFilters
from app.scrapers.olx_scraper import OLXScraper
from app.services.score_service import calcular_score_batch
from app.services.vehicle_service import build_olx_request_options, create_or_update_vehicle, vehicle_matches_filters


async def main() -> int:
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    start_page = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    filters_payload = sys.argv[4] if len(sys.argv) > 4 else ""
    filters = SearchFilters.model_validate_json(filters_payload) if filters_payload else None
    emit_result_json = os.getenv("OLX_WORKER_RESULT_JSON") == "1"

    await create_tables()

    if query:
        logger.info("Starting OLX query worker for '%s' (%s pages from page %s)", query, pages, start_page)
    else:
        logger.info("Starting OLX source worker (%s pages from page %s)", pages, start_page)

    request_options = {"enabled": True, "base_urls": None, "extra_query_params": None}
    if filters is not None:
        async with AsyncSessionLocal() as db:
            request_options = await build_olx_request_options(db, filters)

    if not request_options.get("enabled", True):
        if emit_result_json:
            print(json.dumps({
                "saved": 0,
                "matched": 0,
                "collected": 0,
                "query": query,
                "pages": 0,
                "start_page": start_page,
            }))
        return 0

    base_urls = request_options.get("base_urls") or None
    extra_query_params = request_options.get("extra_query_params") or None
    effective_pages = pages * max(1, len(base_urls or []))

    raw = await OLXScraper(
        max_pages=pages,
        query=query or None,
        start_page=start_page,
        extra_query_params=extra_query_params,
        base_urls=base_urls,
    ).scrape(max_pages=pages)
    raw_count = len(raw)
    valid = [v for v in raw if v.get("titulo") and v.get("source_url") and v.get("modelo")]
    if filters is not None:
        valid = [v for v in valid if vehicle_matches_filters(v, filters)]
    matched_count = len(valid)

    if not valid:
        logger.info("No OLX vehicles collected for '%s'", query)
        if emit_result_json:
            print(json.dumps({
                "saved": 0,
                "matched": matched_count,
                "collected": raw_count,
                "query": query,
                "pages": effective_pages,
                "start_page": start_page,
            }))
        return 0

    scored = calcular_score_batch(valid, calcular_media_por_modelo=True)
    saved = 0
    for vehicle_data in scored:
        try:
            async with AsyncSessionLocal() as db:
                await create_or_update_vehicle(db, vehicle_data)
            saved += 1
        except Exception as e:
            logger.warning("Failed to save OLX vehicle for '%s': %s", query, e)

    logger.info("Finished OLX query worker for '%s': %s saved", query, saved)
    if emit_result_json:
        print(json.dumps({
            "saved": saved,
            "matched": matched_count,
            "collected": raw_count,
            "query": query,
            "pages": effective_pages,
            "start_page": start_page,
        }))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))