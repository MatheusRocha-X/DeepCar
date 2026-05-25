from app.api.search import router as search_router
from app.api.vehicles import router as vehicles_router
from app.api.favorites import router as favorites_router
from app.api.filters import router as filters_router
from app.api.scraper import router as scraper_router
from app.api.images import router as images_router

__all__ = [
    "search_router",
    "vehicles_router",
    "favorites_router",
    "filters_router",
    "scraper_router",
    "images_router",
]
