import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class NekretnineScraper(BaseScraper):
    BASE_URL = "https://www.nekretnine.rs"
    SEARCH_URL = "https://www.nekretnine.rs/"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []

        await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)
        await asyncio.sleep(3)

        # Find and click search link for "stanovi prodaja Beograd"
        # The site is a Next.js SPA - navigate to search page via app routing
        await page.goto("https://www.nekretnine.rs/prodaja-stanova-beograd/",
                        wait_until="load", timeout=30000)

        # Wait for SPA to render
        for i in range(6):
            await asyncio.sleep(5)
            # Check if any listing content appeared
            has_content = await page.evaluate(
                "document.body.innerText.length"
            )
            if has_content and has_content > 5000:
                break

        # Extract listing data from rendered page
        items = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();

                // Try broader approach - find any links with price patterns
                const allLinks = document.querySelectorAll('a');
                allLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href || seen.has(href)) return;
                    const parent = link.closest('div,li,article') || link;
                    const text = parent.innerText || '';
                    if (!text.match(/\\d+\\s*€/)) return;

                    results.push({
                        url: href.startsWith('http') ? href : 'https://www.nekretnine.rs' + (href.startsWith('/') ? '' : '/') + href,
                        full_text: text.substr(0, 500),
                    });
                    seen.add(href);
                });

                return results;
            }
        """)

        for item in items:
            try:
                price_m = re.search(r'([\d.]+)\s*€', item["full_text"])
                if not price_m:
                    continue
                price = float(price_m.group(1).replace(".", ""))
            except (ValueError, AttributeError):
                continue
            if price > 100000 or price == 0:
                continue

            area_m = re.search(r'(\d+)\s*m²', item["full_text"])

            listings.append(Listing(
                id=listing_id(item["url"]),
                title=item["full_text"].split("\n")[0].strip()[:100],
                price_eur=price,
                area_sqm=float(area_m.group(1)) if area_m else None,
                url=item["url"],
                source="nekretnine",
            ))

        await page.close()
        return listings
