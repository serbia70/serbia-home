import asyncio
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
            await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
            await asyncio.sleep(3)

            # Extract all listing data from the DOM
            items = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll('a[href*="/prodaja-stanova/"]');
                    const results = [];
                    const seen = new Set();

                    cards.forEach(card => {
                        const href = card.getAttribute('href');
                        if (!href || seen.has(href)) return;

                        // Filter: only listing detail pages (have a hex ID at the end)
                        if (!href.match(/[a-f0-9]{20,}$/)) return;
                        seen.add(href);

                        const text = card.innerText || '';
                        const priceMatch = text.match(/[\\d,.]+\\s*€/);
                        const sqmMatch = text.match(/(\\d+)\\s*m²/);
                        const roomsMatch = text.match(/(\\d+(?:\\.5)?)\\s*soba/);

                        results.push({
                            url: href.startsWith('http') ? href : 'https://www.4zida.rs' + href,
                            title: text.split('\\n')[0] || '',
                            price_text: priceMatch ? priceMatch[0] : '',
                            area_text: sqmMatch ? sqmMatch[0] : '',
                            rooms_text: roomsMatch ? roomsMatch[0] : '',
                            full_text: text,
                        });
                    });
                    return results;
                }
            """)

            for item in items:
                price = float(re.sub(r'[^\d.]', '', item["price_text"].replace(",", "")))
                if price > 100000:
                    continue  # filter > 100k

                area = None
                if item["area_text"]:
                    area = float(re.sub(r'[^\d.]', '', item["area_text"]))

                listings.append(Listing(
                    id=listing_id(item["url"]),
                    title=item["title"].strip() or f"Stan Beograd - {item['rooms_text']}",
                    price_eur=price,
                    area_sqm=area,
                    rooms=item["rooms_text"],
                    url=item["url"],
                    source="4zida",
                ))
        finally:
            await page.close()
        return listings
