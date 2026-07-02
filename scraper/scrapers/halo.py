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
        page = await self.new_page()
        listings = []
        try:
            await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
            # Halo Oglasi may have Cloudflare - wait and retry
            await asyncio.sleep(5)

            # Accept cookies if present
            try:
                cookie_btn = await page.query_selector("button:has-text('Prihvati'), button:has-text('U redu'), button:has-text('Saglasan'), button:has-text('Accept')")
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Check if blocked by Cloudflare
            page_title = await page.title()
            if "Just a moment" in page_title:
                print("  Halo Oglasi: blocked by Cloudflare, waiting longer...")
                await asyncio.sleep(15)

            items = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll('[class*="oglas"], [class*="listing"], [class*="card"], [class*="product"], article, [class*="result"], li[class*="ad"]');
                    const results = [];
                    const seen = new Set();

                    cards.forEach(card => {
                        const link = card.querySelector('a[href*="halooglasi"]') || card.querySelector('a[href*="/nekretnine"]') || card.closest('a');
                        const href = link ? link.getAttribute('href') : null;
                        if (!href || seen.has(href)) return;
                        seen.add(href);

                        const text = card.innerText || '';
                        const priceMatch = text.match(/[\\d,.]+\\s*€/);
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
                    price_str = re.sub(r'[^\d.]', '', item["price_text"].replace(",", ""))
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
        finally:
            await page.close()
        return listings
