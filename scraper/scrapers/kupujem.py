import asyncio
from typing import List

from scraper.models import Listing
from scraper.scrapers.base import BaseScraper


class KupujemScraper(BaseScraper):
    """KupujemProdajem uses a heavy SPA with no accessible API.
       Currently not scrapeable in headless CI environment."""
    SEARCH_URL = "https://www.kupujemprodajem.com/pretraga?pretraga=stan+beograd&cena_max=100000&kategorija=23"

    async def scrape(self) -> List[Listing]:
        return []
