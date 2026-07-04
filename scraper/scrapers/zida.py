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

    async def _fetch_publish_date(self, url: str) -> str | None:
        page = await self.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)
            date_str = await page.evaluate("""
                () => {
                    const m = document.body.innerText.match(/ažuriran[:\\s]+(\\d{1,2}\\.\\d{1,2}\\.\\d{4})/i);
                    return m ? m[1] : null;
                }
            """)
            if date_str:
                parts = date_str.split(".")
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return None
        except Exception:
            return None
        finally:
            await page.close()

    async def _fetch_dates_batch(self, urls: list[str], batch_size: int = 5) -> dict[str, str]:
        results = {}
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            tasks = [self._fetch_publish_date(url) for url in batch]
            dates = await asyncio.gather(*tasks)
            for url, date in zip(batch, dates):
                if date:
                    results[url] = date
        return results

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

        # Fetch publish dates from detail pages
        if listings:
            urls = [l.url for l in listings]
            dates = await self._fetch_dates_batch(urls)
            for listing in listings:
                listing.published_at = dates.get(listing.url)

        return listings
