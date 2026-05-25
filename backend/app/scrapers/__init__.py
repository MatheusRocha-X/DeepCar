from app.scrapers.base_scraper import BaseScraper, BaseVehicleData
from app.scrapers.olx_scraper import OLXScraper
from app.scrapers.icarros_scraper import ICarrosScraper
from app.scrapers.scheduler import ScraperScheduler, scraper_scheduler

__all__ = [
    "BaseScraper",
    "BaseVehicleData",
    "OLXScraper",
    "ICarrosScraper",
    "ScraperScheduler",
    "scraper_scheduler",
]
