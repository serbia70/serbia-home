import asyncio
import json
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class KupujemScraper(BaseScraper):
    BASE_URL = "https://www.kupujemprodajem.com"
    SEARCH_URL = "https://www.kupujemprodajem.com/pretraga?pretraga=stan+beograd&cena_max=100000&kategorija=23"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []
        api_urls = set()

        async def on_response(response):
            url = response.url
            if url in api_urls:
                return
            api_urls.add(url)
            if "/api/web/v1/" not in url:
                return
            if "ingest.sentry" in url:
                return
            print(f"  KP API hit: {url}")
            try:
                if "application/json" in (response.headers.get("content-type", "")):
                    body = await response.json()
                    data_preview = json.dumps(body, ensure_ascii=False)[:500]
                    print(f"  KP API data: {data_preview}")
            except Exception:
                pass

        page.on("response", on_response)
        await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
        await asyncio.sleep(15)
        await page.close()
        return listings
