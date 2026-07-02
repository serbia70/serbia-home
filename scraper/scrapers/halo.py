import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class HaloScraper(BaseScraper):
    BASE_URL = "https://www.halooglasi.com"
    SEARCH_URL = "https://www.halooglasi.com/nekretnine/prodaja-stanova/beograd"

    async def scrape(self) -> List[Listing]:
        # Simple retry: sometimes Cloudflare passes, sometimes not
        for attempt in range(2):
            listings = await self._try_scrape()
            if listings:
                return listings
            if attempt == 0:
                print("  Halo Oglasi: retrying...")
        return []

    async def _try_scrape(self) -> List[Listing] | None:
        page = await self.new_page()
        listings = []
        try:
            await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
            await asyncio.sleep(5)

            # Accept cookies
            try:
                for text in ["Prihvati", "U redu", "Saglasan", "Accept"]:
                    btn = await page.query_selector(f"button:has-text('{text}')")
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        break
            except:
                pass

            items = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll('[class*="oglas"], [class*="listing"], [class*="card"], [class*="product"], article, [class*="result"], li[class*="ad"], [id*="oglas"]');
                    const results = [];
                    const seen = new Set();
                    cards.forEach(card => {
                        const link = card.querySelector('a[href*="halooglasi"]') || card.querySelector('a[href*="/nekretnine"]') || card.closest('a');
                        const href = link ? link.getAttribute('href') : null;
                        if (!href || seen.has(href)) return;
                        seen.add(href);
                        const text = card.innerText || '';
                        const priceMatch = text.match(/[\\d.,]+\\s*€/);
                        const sqmMatch = text.match(/(\\d+)\\s*m²/);
                        const img = card.querySelector('img');
                        results.push({
                            url: href.startsWith('http') ? href : 'https://www.halooglasi.com' + (href.startsWith('/') ? '' : '/') + href,
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
                try:
                    price_str = item["price_text"].replace(".", "").replace(",", "")
                    price_str = re.sub(r'[^\d]', '', price_str)
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
                    source="halo_oglasi",
                    image_url=item["image"],
                ))

            return listings if listings else None
        finally:
            await page.close()
