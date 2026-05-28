from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.core.config import settings
from app.core.database import create_tables, AsyncSessionLocal
from app.api import search_router, vehicles_router, favorites_router, filters_router, scraper_router, images_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DeepCar API...")
    schema_info = await create_tables()
    logger.info("Database tables created/verified")
    startup_scrape_task = None

    from app.scrapers.scheduler import scraper_scheduler
    from app.services.maintenance_service import rescore_existing_vehicles, update_missing_fipe_prices
    from app.services.scrape_service import bootstrap_active_scrapers_if_needed
    from app.services.vehicle_service import delete_stale_vehicles, refresh_active_listings

    async def _scheduled_scrape():
        logger.info("Scheduled scraper starting...")
        async with AsyncSessionLocal() as db:
            await scraper_scheduler.run_source("all", db)

    async def _scheduled_cleanup():
        await delete_stale_vehicles(days=7)

    async def _scheduled_refresh():
        await refresh_active_listings(batch_size=200)

    async def _scheduled_fipe_update():
        logger.info("Daily FIPE update starting...")
        result = await update_missing_fipe_prices(limit=None)
        logger.info(
            "Daily FIPE update finished: %s updated, %s not found",
            result["updated"],
            result["not_found"],
        )

    async def _scheduled_rescore():
        logger.info("Daily rescore starting...")
        updated = await rescore_existing_vehicles(limit=None)
        logger.info("Daily rescore finished: %s vehicles reprocessed", updated)

    added_columns = schema_info.get("vehicle_columns_added", []) if isinstance(schema_info, dict) else []
    if added_columns:
        logger.info("Backfilling derived vehicle flags for new columns: %s", ", ".join(added_columns))
        updated = await rescore_existing_vehicles(limit=None)
        logger.info("Derived vehicle flag backfill finished: %s vehicles reprocessed", updated)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_scheduled_scrape, "interval", hours=6, id="scraper_run", misfire_grace_time=300)
    scheduler.add_job(_scheduled_cleanup, "interval", hours=12, id="stale_cleanup", misfire_grace_time=300)
    scheduler.add_job(_scheduled_refresh, "interval", hours=2, id="refresh_listings", misfire_grace_time=300)
    scheduler.add_job(
        _scheduled_fipe_update,
        "cron",
        hour=3,
        minute=0,
        id="daily_fipe_update",
        misfire_grace_time=3600,
        max_instances=1,
    )
    scheduler.add_job(
        _scheduled_rescore,
        "cron",
        hour=4,
        minute=0,
        id="daily_rescore",
        misfire_grace_time=3600,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: scraper every 6h, refresh every 2h, cleanup every 12h, FIPE daily at 03:00, rescore daily at 04:00"
    )

    async def _startup_bootstrap():
        try:
            result = await bootstrap_active_scrapers_if_needed()
            if result["triggered"]:
                logger.info(
                    "Startup scrape completed with %s vehicles saved",
                    result["total_saved"],
                )
        except Exception as exc:
            logger.error("Startup scrape bootstrap failed: %s", exc)

    startup_scrape_task = asyncio.create_task(_startup_bootstrap())

    yield

    if startup_scrape_task and not startup_scrape_task.done():
        startup_scrape_task.cancel()

    scheduler.shutdown(wait=False)
    logger.info("Shutting down DeepCar API...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API do DeepCar — buscador inteligente de veículos",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(search_router, prefix="/api")
app.include_router(vehicles_router, prefix="/api")
app.include_router(favorites_router, prefix="/api")
app.include_router(filters_router, prefix="/api")
app.include_router(scraper_router, prefix="/api")
app.include_router(images_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
