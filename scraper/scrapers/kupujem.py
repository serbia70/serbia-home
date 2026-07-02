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
        try:
            await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)

            # Wait for SPA to load listings - wait for any link containing /oglasi/
            try:
                await page.wait_for_function(
                    "() => document.querySelector('a[href*=\"/oglasi/\"]') !== null",
                    timeout=20000,
                )
            except:
                pass

            # Give SPA extra time to render
            await asyncio.sleep(3)

            # Extract all listing links and their context from the page
            items = await page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();
                    const links = document.querySelectorAll('a[href*="/oglasi/"]');

                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        if (!href || seen.has(href)) return;
                        seen.add(href);

                        // Walk up to find the card container
                        let card = link;
                        for (let i = 0; i < 5; i++) {
                            if (card.parentElement) card = card.parentElement;
                        }

                        const text = card.innerText || link.innerText || '';
                        const priceMatch = text.match(/(\\d{1,3}(?:\\.?\\d{3})*)\\s*(€|EUR)/i);
                        const sqmMatch = text.match(/(\\d+)\\s*m²/);
                        const img = card.querySelector('img');

                        results.push({
                            url: href.startsWith('http') ? href : window.location.origin + (href.startsWith('/') ? '' : '/') + href,
                            price_text: priceMatch ? priceMatch[0] : '',
                            area_text: sqmMatch ? sqmMatch[0] : '',
                            full_text: text.substr(0, 500),
                            image: img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '',
                        });
                    });
                    return results;
                }
            """)

            for item in items:
                try:
                    # Handle various price formats: "25.000 €", "25000 EUR"
                    price_clean = item["price_text"].replace(".", "").replace(",", "")
                    price_str = re.sub(r'[^\d]', '', price_clean)
                    if not price_str:
                        continue
                    price = float(price_str)
                except (ValueError, AttributeError):
                    continue
                if price > 100000 or price == 0:
                    continue

                area = None
                if item["area_text"]:
                    try:
                        area = float(re.sub(r'[^\d.]', '', item["area_text"]))
                    except ValueError:
                        pass

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
