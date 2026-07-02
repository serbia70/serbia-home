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
        api_responses = []

        async def on_response(response):
            url = response.url
            if "ad" in url and response.ok:
                try:
                    body = await response.json()
                    api_responses.append(("json", url, body))
                except:
                    try:
                        text = await response.text()
                        if "price" in text:
                            api_responses.append(("text", url, text[:2000]))
                    except:
                        pass

        page.on("response", on_response)
        await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
        await asyncio.sleep(10)

        # Check what API responses we captured
        if api_responses:
            for rtype, url, data in api_responses[:5]:
                print(f"  KP API: {rtype} {url[:80]}")
                if rtype == "json" and isinstance(data, dict):
                    ads = data.get("ads") or data.get("items") or data.get("results") or data
                    if isinstance(ads, list):
                        for ad in ads:
                            try:
                                ad_id = ad.get("id", "") or ad.get("adId", "")
                                price = float(ad.get("price", {}).get("value", 0) or
                                              ad.get("priceValue", 0) or
                                              ad.get("cena", 0))
                                if price > 100000 or price <= 0:
                                    continue
                                listings.append(Listing(
                                    id=listing_id(str(ad_id)),
                                    title=ad.get("name", ad.get("title", ""))[:100],
                                    price_eur=price,
                                    url=f"https://www.kupujemprodajem.com/oglasi/{ad_id}",
                                    source="kupujemprodajem",
                                ))
                            except (ValueError, AttributeError):
                                continue

        # Try to extract from rendered DOM
        if not listings:
            items = await page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();
                    const cards = document.querySelectorAll('[class*="ad"]');

                    cards.forEach(card => {
                        const text = card.innerText || '';
                        const link = card.querySelector('a');
                        const href = link ? link.getAttribute('href') : '';
                        if (!href || seen.has(href) || !href.includes('/oglasi/')) return;
                        seen.add(href);

                        const m = text.match(/([\\d.]+)\\s*(€|EUR)/i);
                        const sqm = text.match(/(\\d+)\\s*m²/);
                        const img = card.querySelector('img');

                        results.push({
                            url: href.startsWith('http') ? href : window.location.origin + href,
                            price_text: m ? m[0] : '',
                            area_text: sqm ? sqm[0] : '',
                            full_text: text.substr(0, 500),
                            image: img ? (img.getAttribute('src') || '') : '',
                        });
                    });
                    return results;
                }
            """)

            for item in items:
                try:
                    p = item["price_text"].replace(".", "").replace("€", "").replace("EUR", "").strip()
                    price = float(p) if p else 0
                except ValueError:
                    continue
                if price > 100000 or price <= 0:
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

        await page.close()
        return listings
