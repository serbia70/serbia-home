import asyncio
import json
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class ZidaScraper(BaseScraper):
    BASE_URL = "https://www.4zida.rs"
    SEARCH_URL = "https://www.4zida.rs/prodaja-stanova/beograd"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []
        try:
            await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # Extract listing data from JSON-LD
            items = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const results = [];
                    const seen = new Set();

                    scripts.forEach(script => {
                        try {
                            const data = JSON.parse(script.textContent);
                            // Look for ItemList with listing data
                            if (data.itemListElement && data['@type'] === 'ItemList') {
                                data.itemListElement.forEach(item => {
                                    if (item.url && !seen.has(item.url)) {
                                        seen.add(item.url);
                                        const offer = item.itemOffered || {};
                                        const offer_data = offer.offers || {};
                                        const address = offer.address || {};

                                        results.push({
                                            url: item.url,
                                            name: item.name || '',
                                            price: offer_data.price || 0,
                                            currency: offer_data.priceCurrency || 'EUR',
                                            area: offer.floorSize ? offer.floorSize.value : null,
                                            rooms: offer.numberOfRooms || '',
                                            location: address.addressLocality || address.addressCountry || '',
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
                price = float(item["price"])
                if price > 100000:
                    continue

                listings.append(Listing(
                    id=listing_id(item["url"]),
                    title=item.get("name", "") or f"Stan Beograd",
                    price_eur=price,
                    area_sqm=float(item["area"]) if item["area"] else None,
                    rooms=str(item["rooms"]) if item["rooms"] else "",
                    location=item.get("location", ""),
                    url=item["url"],
                    source="4zida",
                ))
        finally:
            await page.close()
        return listings
