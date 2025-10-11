"""Experimental scrapers for sites without official APIs."""

from .line_snapshot import LineSnapshotService, line_snapshot_service
from .navitia_scraper import NavitiaScraper
from .ratp_http import RatpHttpScraper
from .ratp_traffic import RatpTrafficScraper
from .ratp_playwright import RatpPlaywrightScraper, ScrapedDeparture, ScraperResult

__all__ = [
    "LineSnapshotService",
    "NavitiaScraper",
    "RatpHttpScraper",
    "RatpTrafficScraper",
    "RatpPlaywrightScraper",
    "ScrapedDeparture",
    "ScraperResult",
    "line_snapshot_service",
]
