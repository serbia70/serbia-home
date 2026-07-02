import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class KupujemScraper(BaseScraper):
    BASE_URL = "https://www.kupujemprodajem.com"
    SEARCH_URL = "https://www.kupujemprodajem.com/pretraga?pretraga=stan+beograd&cena_max=100000&kategorija_id=10"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []
        try:
            await page.goto(self.SEARCH_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            items = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll('[class*="ad"], [class*="oglas"], [class*="card"], [class*="listing"], article');
                    const results = [];
                    const seen = new Set();

                    cards.forEach(card => {
                        const link = card.querySelector('a[href*="/oglasi/"]') || card.querySelector('a[href*="/nekretnine/"]') || card.querySelector('a[href*="-stan-"]');
                        const href = link ? link.getAttribute('href') : null;
                        if (!href || seen.has(href)) return;
                        seen.add(href);

                        const text = card.innerText || '';
                        const priceMatch = text.match(/[\\d,.]+\\s*(€|EUR|din)/i);
                        const sqmMatch = text.match(/(\\d+)\\s*m²/);
                        const img = card.querySelector('img');

                        results.push({
                            url: href.startsWith('http') ? href : 'https://www.kupujemprodajem.com' + (href.startsWith('/') ? '' : '/') + href,
                            price_text: priceMatch ? priceMatch[0] : '',
                            area_text: sqmMatch ? sqmMatch[0] : '',
                            full_text: text,
                            image: img ? img.getAttribute('src') : null,
                        });
                    });
                    return results;
                }
            """)

            # Try alternative selectors if no results
            if not items:
                items = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href*="/oglasi/"]');
                        const results = [];
                        const seen = new Set();

                        links.forEach(link => {
                            const href = link.getAttribute('href');
                            if (!href || seen.has(href)) return;
                            seen.add(href);

                            const parent = link.closest('div, article, li') || link;
                            const text = parent.innerText || link.innerText || '';
                            const priceMatch = text.match(/[\\d,.]+\\s*(€|EUR|din)/i);
                            const sqmMatch = text.match(/(\\d+)\\s*m²/);
                            const img = parent.querySelector('img');

                            results.push({
                                url: href.startsWith('http') ? href : 'https://www.kupujemprodajem.com' + href,
                                price_text: priceMatch ? priceMatch[0] : '',
                                area_text: sqmMatch ? sqmMatch[0] : '',
                                full_text: text,
                                image: img ? img.getAttribute('src') : null,
                            });
                        });
                        return results;
                    }
                """)

            for item in items:
                price = float(re.sub(r'[^\d.]', '', item["price_text"].replace(",", "")))
                if price > 100000 or price == 0:
                    continue

                area = None
                if item["area_text"]:
                    area = float(re.sub(r'[^\d.]', '', item["area_text"]))

                listings.append(Listing(
                    id=listing_id(item["url"]),
                    title=item["full_text"].split("\\n")[0].strip()[:100],
                    price_eur=price,
                    area_sqm=area,
                    url=item["url"],
                    source="kupujemprodajem",
                    image_url=item["image"],
                ))
        finally:
            await page.close()
        return listings
