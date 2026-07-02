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
        api_data = []

        async def capture_response(response):
            url = response.url
            if "/api/" in url and response.ok:
                try:
                    body = await response.json()
                    api_data.append({"url": url, "data": body})
                except:
                    pass

        try:
            page.on("response", lambda resp: asyncio.ensure_future(capture_response(resp)))
            await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)

            # Wait for SPA data to load
            await asyncio.sleep(8)

            # If we captured API data with ads, extract from there
            for capture in api_data:
                data = capture["data"]
                if isinstance(data, dict):
                    ads = data.get("ads") or data.get("items") or data.get("results") or data.get("data", {})
                    if isinstance(ads, list):
                        for ad in ads:
                            try:
                                price = float(ad.get("price", {}).get("value", 0) or ad.get("price_value", 0))
                                if price > 100000 or price == 0:
                                    continue
                                ad_id = ad.get("id", "")
                                listings.append(Listing(
                                    id=listing_id(str(ad_id)),
                                    title=ad.get("name", ad.get("title", ""))[:100],
                                    price_eur=price,
                                    area_sqm=float(ad.get("area", 0) or 0) or None,
                                    url=f"https://www.kupujemprodajem.com/oglasi/{ad_id}",
                                    source="kupujemprodajem",
                                ))
                            except (ValueError, AttributeError):
                                continue

            # Fallback: try DOM extraction
            if not listings:
                # Try to extract from the initial Redux state in __NEXT_DATA__
                items = await page.evaluate("""
                    () => {
                        const el = document.getElementById('__NEXT_DATA__');
                        if (!el) return [];
                        try {
                            const data = JSON.parse(el.textContent);
                            const state = data.props?.pageProps?.initialReduxState || {};
                            const nav = state.adNavigation || {};
                            const byId = state.ad?.byId || {};
                            const total = nav.total || 0;
                            if (total === 0) return [];

                            // Get ad IDs from navigation
                            const ids = nav.adsIds || [];
                            const results = [];
                            ids.forEach(id => {
                                const ad = byId[id];
                                if (!ad) return;
                                const priceVal = ad.price?.value || 0;
                                const currency = ad.price?.currency || 'EUR';
                                let price = priceVal;
                                if (currency === 'RSD') price = priceVal / 117;
                                results.push({
                                    id: String(id),
                                    title: ad.name || '',
                                    price: price,
                                    area: ad.area || null,
                                    image: ad.image || (ad.images && ad.images[0]) || null,
                                });
                            });
                            return results;
                        } catch(e) { return []; }
                    }
                """)

                for item in items:
                    try:
                        price = float(item["price"])
                    except (ValueError, TypeError):
                        continue
                    if price > 100000 or price <= 0:
                        continue

                    area = float(item["area"]) if item.get("area") else None
                    listings.append(Listing(
                        id=listing_id(item["id"]),
                        title=item.get("title", "")[:100] or "Stan Beograd",
                        price_eur=price,
                        area_sqm=area,
                        url=f"https://www.kupujemprodajem.com/oglasi/{item['id']}",
                        source="kupujemprodajem",
                        image_url=item.get("image"),
                    ))

            # Final fallback: scroll to trigger lazy loading
            if not listings:
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)

                items = await page.evaluate("""
                    () => {
                        const results = [];
                        const seen = new Set();
                        document.querySelectorAll('a[href*="/oglasi/"]').forEach(a => {
                            const href = a.getAttribute('href');
                            if (!href || seen.has(href)) return;
                            seen.add(href);
                            const text = a.innerText || '';
                            const m = text.match(/([\\d.]+)\\s*(€|EUR)/i);
                            results.push({
                                url: href.startsWith('http') ? href : window.location.origin + href,
                                price_text: m ? m[0] : '',
                                full_text: text.substr(0, 300),
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

        finally:
            await page.close()
        return listings
