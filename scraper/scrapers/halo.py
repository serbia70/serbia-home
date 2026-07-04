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
        for attempt in range(3):
            listings = await self._try_scrape()
            if listings:
                return listings
            print(f"  Halo Oglasi: retrying (attempt {attempt + 1})...")
        return []

    async def _try_scrape(self) -> List[Listing] | None:
        # Scrape page 1 with full init (cookies, etc.)
        page1_listings = await self._scrape_single_page(self.SEARCH_URL, accept_cookies=True)
        if page1_listings is None:
            return None

        all_listings = list(page1_listings)
        print(f"  Halo page 1: {len(page1_listings)} listings (under €100k)")

        # Pages 2-5: each in a fresh context to avoid Cloudflare session detection
        for page_num in range(2, 6):
            url = f"{self.SEARCH_URL}?page={page_num}"
            page_listings = await self._scrape_single_page(url, accept_cookies=False)
            if page_listings is None:
                print(f"  Halo page {page_num}: blocked or failed")
                break
            print(f"  Halo page {page_num}: {len(page_listings)} listings (under €100k)")
            all_listings.extend(page_listings)

        return all_listings if all_listings else None

    async def _scrape_single_page(self, url: str, accept_cookies: bool) -> List[Listing] | None:
        page = await self.new_page()
        try:
            await page.goto(url, wait_until="load", timeout=60000)
            await asyncio.sleep(5)

            if accept_cookies:
                try:
                    for text in ["U redu", "Prihvati", "Saglasan", "Accept"]:
                        btn = await page.query_selector(f"button:has-text('{text}')")
                        if btn:
                            await btn.click()
                            await asyncio.sleep(1)
                            break
                except:
                    pass
                await asyncio.sleep(3)

            # Check if blocked
            page_text = await page.evaluate("document.body.innerText")
            if "Just a moment" in page_text or "Checking your browser" in page_text:
                return None
            if page_text.strip() == "":
                return None

            has_products = await page.evaluate(
                "document.querySelectorAll('.product-item.product-list-item').length"
            )
            if has_products == 0:
                return []

            items = await page.evaluate("""
                () => {
                    const products = document.querySelectorAll('.product-item.product-list-item');
                    const results = [];
                    const seen = new Set();

                    products.forEach(p => {
                        const titleLink = p.querySelector('h3.product-title a');
                        const href = titleLink ? titleLink.getAttribute('href') : null;
                        if (!href || seen.has(href)) return;
                        seen.add(href);

                        const priceSpan = p.querySelector('span[data-value]');
                        const priceText = priceSpan ? priceSpan.getAttribute('data-value') : '';

                        const img = p.querySelector('figure img');
                        const imgSrc = img ? img.getAttribute('src') : '';

                        const title = titleLink ? titleLink.innerText.trim() : '';

                        const locationLis = p.querySelectorAll('ul.subtitle-places li');
                        const locations = Array.from(locationLis).map(li => li.innerText.trim());
                        const location = locations.filter(Boolean).join(', ');

                        const features = p.querySelectorAll('.value-wrapper');
                        const areaText = features.length > 0 ? (features[0].childNodes[0]?.nodeValue || '').trim() : '';
                        const roomsText = features.length > 1 ? (features[1].childNodes[0]?.nodeValue || '').trim() : '';

                        const descEl = p.querySelector('.product-description');
                        const descText = descEl ? descEl.innerText.trim() : '';

                        const dateEl = p.querySelector('.publish-date');
                        const dateText = dateEl ? dateEl.innerText.trim() : '';

                        results.push({
                            url: href.startsWith('http') ? href : 'https://www.halooglasi.com' + href,
                            price_text: priceText,
                            area_text: areaText,
                            rooms_text: roomsText,
                            title: title,
                            location: location,
                            full_text: (title + ' ' + descText + ' ' + locations.join(' ')),
                            image: imgSrc,
                            date_text: dateText,
                        });
                    });

                    return results;
                }
            """)

            listings = []
            for item in items:
                try:
                    price = float(item["price_text"].replace(".", ""))
                except (ValueError, AttributeError):
                    continue
                if price > 100000 or price == 0:
                    continue

                area = None
                if item["area_text"]:
                    try:
                        area = float(re.sub(r'[^\d.,]', '', item["area_text"]).replace(",", "."))
                    except ValueError:
                        pass

                # Parse publish date (format: 04.07.2026.)
                published_at = None
                if item.get("date_text"):
                    try:
                        dt = item["date_text"].rstrip(".")
                        parts = dt.split(".")
                        if len(parts) == 3:
                            published_at = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    except (ValueError, IndexError):
                        pass

                listings.append(Listing(
                    id=listing_id(item["url"]),
                    title=item.get("title", "") or item["full_text"].split("\n")[0].strip()[:100],
                    price_eur=price,
                    area_sqm=area,
                    rooms=item.get("rooms_text", ""),
                    location=item.get("location", ""),
                    url=item["url"],
                    source="halo_oglasi",
                    image_url=item.get("image"),
                    published_at=published_at,
                ))

            return listings
        finally:
            await page.close()
