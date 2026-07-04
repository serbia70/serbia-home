import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class NekretnineScraper(BaseScraper):
    BASE_URL = "https://www.nekretnine.rs"
    SEARCH_URL = "https://www.nekretnine.rs/prodaja-stanova/beograd/"

    async def _fetch_publish_date(self, url: str) -> str | None:
        page = await self.new_page()
        try:
            await page.goto(url, wait_until="load", timeout=30000)
            await asyncio.sleep(1)
            try:
                btn = await page.query_selector("button:has-text('PRIHVATANJE')")
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
            except:
                pass
            date_str = await page.evaluate("""
                () => {
                    const m = document.body.innerText.match(/ažuriran[:\\s]+(\\d{1,2}\\.\\d{1,2}\\.\\d{4})/i);
                    return m ? m[1] : null;
                }
            """)
            if date_str:
                parts = date_str.split(".")
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
            return None
        except Exception:
            return None
        finally:
            await page.close()

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        all_listings = []

        for page_num in range(1, 6):
            url = self.SEARCH_URL if page_num == 1 else f"{self.SEARCH_URL}?pag={page_num}"
            listings = await self._scrape_page(page, url)
            all_listings.extend(listings)
            print(f"  Nekretnine page {page_num}: {len(listings)} listings (under €100k)")
            if len(listings) == 0:
                break

        await page.close()

        # Fetch publish dates from detail pages
        if all_listings:
            for listing in all_listings:
                date = await self._fetch_publish_date(listing.url)
                listing.published_at = date

        return all_listings

    async def _scrape_page(self, page, url: str) -> List[Listing]:
        listings = []

        await page.goto(url, wait_until="load", timeout=60000)

        try:
            btn = await page.query_selector(
                "button:has-text('PRIHVATANJE I ZATVARANJE'), button:has-text('prihvatanje')"
            )
            if btn:
                await btn.click()
                await asyncio.sleep(2)
        except:
            pass

        # Wait for SPA to render listing cards
        for i in range(6):
            await asyncio.sleep(5)
            has_cards = await page.evaluate(
                "document.querySelectorAll('[class*=\"Property_card\"], [class*=\"ListItem_item__card\"]').length"
            )
            if has_cards > 0:
                break

        # Scroll to trigger lazy loading of all cards
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)

        # Extract listing data from rendered cards
        items = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();

                // Cards use dynamic CSS module classes; find by parent container
                const cardLinks = document.querySelectorAll('a[href*="/oglasi/"]');
                cardLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href || seen.has(href)) return;
                    seen.add(href);

                    // Walk up to find the card container with all text
                    let card = link.closest('[class*="ListItem_item"], [class*="Property_card"]');
                    if (!card) card = link.closest('li, div, article');
                    if (!card) card = link;

                    const text = card.innerText || '';
                    if (!text.match(/€/)) return;

                    const priceMatch = text.match(/€[\\s]*([\\d.]+)/);
                    const sqmMatch = text.match(/(\\d+)\\s*m²/);
                    const roomMatch = text.match(/(\\d+)\\s*(sobe|soba)/i) || text.match(/(Jednosoban|Jednoiposoban|Dvosoban|Trosoban|Četvorosoban|Petosoban)/i);
                    const img = card.querySelector('img');
                    const location = text.split('\\n').filter(l => l.includes('Beograd') || l.includes('beograd') || l.includes('Novi Sad') || l.includes('Zemun') || l.includes('Novi Beograd'))[0] || '';

                    results.push({
                        url: href.startsWith('http') ? href : 'https://www.nekretnine.rs' + href,
                        price_text: priceMatch ? priceMatch[0] : '',
                        area_text: sqmMatch ? sqmMatch[0] : '',
                        rooms_text: roomMatch ? roomMatch[0] : '',
                        location: location.trim(),
                        full_text: text.substring(0, 500),
                        image: img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '',
                    });
                });

                return results;
            }
        """)

        for item in items:
            try:
                price_str = item["price_text"].replace("€", "").replace(" ", "").replace(".", "")
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
                    area = float(re.sub(r'[^\d]', '', item["area_text"]))
                except ValueError:
                    pass

            listings.append(Listing(
                id=listing_id(item["url"]),
                title=item["full_text"].split("\n")[0].strip()[:100],
                price_eur=price,
                area_sqm=area,
                rooms=item.get("rooms_text", ""),
                location=item.get("location", ""),
                url=item["url"],
                source="nekretnine",
                image_url=item["image"],
            ))

        return listings
