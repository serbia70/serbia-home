import asyncio
import json
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class ZidaScraper(BaseScraper):
    BASE_URL = "https://www.4zida.rs"
    SEARCH_URL = "https://www.4zida.rs/prodaja-stanova/beograd/do-100000-evra"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []
        try:
            await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # Extract listing data from JSON-LD ItemList
            items = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const results = [];
                    const seen = new Set();
                    scripts.forEach(script => {
                        try {
                            const data = JSON.parse(script.textContent);
                            if (data.itemListElement && data['@type'] === 'ItemList') {
                                data.itemListElement.forEach(item => {
                                    if (item.url && !seen.has(item.url)) {
                                        seen.add(item.url);
                                        const obj = item.item || {};
                                        const offers = obj.offers || {};
                                        const offered = obj.itemOffered || {};
                                        const addr = (offered.address || {});
                                        const img = obj.image || {};
                                        results.push({
                                            url: item.url,
                                            name: obj.name || '',
                                            price: offers.price || 0,
                                            area: (offered.floorSize || {}).value || null,
                                            rooms: offered.numberOfRooms || '',
                                            location: addr.addressLocality || '',
                                            image: img.contentUrl || img.url || '',
                                        });
                                    }
                                });
                            }
                        } catch(e) {}
                    });
                    return results;
                }
            """)

            for item in items:
                try:
                    price = float(item["price"])
                except (ValueError, TypeError):
                    continue
                if price > 100000 or price == 0:
                    continue

                area = float(item["area"]) if item["area"] else None

                listings.append(Listing(
                    id=listing_id(item["url"]),
                    title=item.get("name", "") or "Stan Beograd",
                    price_eur=price,
                    area_sqm=area,
                    rooms=str(item["rooms"]) if item["rooms"] else "",
                    location=item.get("location", ""),
                    url=item["url"],
                    source="4zida",
                    image_url=item.get("image"),
                ))
        finally:
            await page.close()
        return listings
