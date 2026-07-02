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
            await asyncio.sleep(5)

            # Try to extract from __NEXT_DATA__ (Next.js embedded data)
            next_data = await page.evaluate("""
                () => {
                    const el = document.getElementById('__NEXT_DATA__');
                    if (!el) return null;
                    try { return JSON.parse(el.textContent); } catch(e) { return null; }
                }
            """)

            if next_data:
                # Navigate through the Next.js data structure to find ads
                try:
                    state = next_data.get("props", {}).get("pageProps", {}).get("initialReduxState", {})
                    ads = state.get("ad", {}).get("byId", {})
                    if ads:
                        for ad_id, ad_data in ads.items():
                            title = ad_data.get("name", "")
                            price = ad_data.get("price", {}).get("value", 0)
                            currency = ad_data.get("price", {}).get("currency", "EUR")
                            if currency == "RSD":
                                price = price / 117  # approximate conversion
                            if price > 100000 or price <= 0:
                                continue
                            listings.append(Listing(
                                id=listing_id(f"kp_{ad_id}"),
                                title=title,
                                price_eur=float(price),
                                url=f"https://www.kupujemprodajem.com/oglasi/{ad_id}",
                                source="kupujemprodajem",
                            ))
                except Exception:
                    pass

            # If no listings from __NEXT_DATA__, try scraping from rendered DOM
            if not listings:
                items = await page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('[class*="AdCard"], [class*="adCard"], article, [class*="oglas"], [class*="listing"]');
                        const results = [];
                        const seen = new Set();

                        cards.forEach(card => {
                            const link = card.querySelector('a[href*="/oglasi/"]') || card.querySelector('a');
                            const href = link ? link.getAttribute('href') : null;
                            if (!href || seen.has(href) || !href.includes('/oglasi/')) return;
                            seen.add(href);

                            const text = card.innerText || '';
                            const priceMatch = text.match(/[\\d,.]+\\s*(€|EUR)/i);
                            const sqmMatch = text.match(/(\\d+)\\s*m²/);
                            const img = card.querySelector('img');

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
                        source="kupujemprodajem",
                        image_url=item["image"],
                    ))
        finally:
            await page.close()
        return listings
