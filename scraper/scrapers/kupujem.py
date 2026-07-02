import asyncio
import json
import re
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
        api_urls_seen = set()

        async def on_response(response):
            url = response.url
            if url in api_urls_seen:
                return
            api_urls_seen.add(url)
            if "/api/web/v1/" not in url:
                return
            try:
                body = await response.json()
                if isinstance(body, dict) and body.get("success") and body.get("data"):
                    items = body["data"]
                    if isinstance(items, list) and len(items) > 0:
                        for ad in items:
                            try:
                                ad_id = ad.get("id", "")
                                price = float(ad.get("price", ad.get("priceValue", 0)) or 0)
                                title = ad.get("name", ad.get("title", "")) or ""
                                area = ad.get("area", ad.get("areaSqm", 0)) or None
                                if price <= 0 or price > 100000 or not ad_id:
                                    continue
                                listings.append(Listing(
                                    id=listing_id(str(ad_id)),
                                    title=str(title)[:100],
                                    price_eur=price,
                                    area_sqm=float(area) if area else None,
                                    url=f"https://www.kupujemprodajem.com/oglasi/{ad_id}",
                                    source="kupujemprodajem",
                                ))
                            except (ValueError, AttributeError):
                                continue
            except Exception:
                pass

        page.on("response", on_response)
        await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
        await asyncio.sleep(12)
        await page.close()
        return listings
