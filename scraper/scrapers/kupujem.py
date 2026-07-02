import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class KupujemScraper(BaseScraper):
    BASE_URL = "https://www.kupujemprodajem.com"
    SEARCH_URL = "https://www.kupujemprodajem.com/pretraga?pretraga=stan+beograd&kategorija=23"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []

        # Collect all API JSON responses
        api_data = []

        async def on_response(resp):
            url = resp.url
            if "ingest.sentry" not in url:
                try:
                    ct = resp.headers.get("content-type", "")
                    if "json" in ct:
                        body = await resp.json()
                        api_data.append((url, body))
                except:
                    pass

        page.on("response", on_response)
        await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)

        # Wait for data to load - try multiple strategies
        for i in range(6):
            await asyncio.sleep(5)
            # Check if any ad links appeared
            has_ads = await page.evaluate("document.querySelectorAll('a[href*=\"/oglasi/\"]').length")
            if has_ads > 0:
                print(f"  KP: found {has_ads} ad links after {i+1} polls")
                break

        print(f"  KP: captured {len(api_data)} API responses")
        # Extract API data
        for url, body in api_data:
            # Look for any endpoint that returns listing data
            if isinstance(body, dict):
                results = body.get("results") or body.get("data") or {}
                if isinstance(results, dict):
                    for key in ["ads", "items", "listings", "searchResults"]:
                        items = results.get(key, [])
                        if isinstance(items, list) and len(items) > 0:
                            for ad in items:
                                try:
                                    ad_id = ad.get("id", "")
                                    price = float(ad.get("price", {}).get("value", 0) or
                                                  ad.get("priceValue", 0) or 0)
                                    if price > 100000 or price <= 0 or not ad_id:
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

        # Fallback: extract from rendered DOM
        if not listings:
            items = await page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();
                    const links = document.querySelectorAll('a[href*="/oglasi/"]');
                    links.forEach(a => {
                        const href = a.getAttribute('href');
                        if (!href || seen.has(href)) return;
                        seen.add(href);
                        const text = a.innerText || '';
                        const card = a.closest('div,li,article') || a;
                        const cardText = card.innerText || '';
                        const priceMatch = cardText.match(/([\\d.]+)\\s*(€|EUR)/i);
                        if (!priceMatch) return;
                        results.push({
                            url: href.startsWith('http') ? href : 'https://www.kupujemprodajem.com' + href,
                            price_text: priceMatch[0],
                            full_text: cardText.substr(0, 300),
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
                listings.append(Listing(
                    id=listing_id(item["url"]),
                    title=item["full_text"].split("\\n")[0].strip()[:100],
                    price_eur=price,
                    url=item["url"],
                    source="kupujemprodajem",
                ))

        await page.close()
        return listings
