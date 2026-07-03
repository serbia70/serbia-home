import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper

# Beograd municipalities and neighborhoods for location matching
BEOGRAD_KEYWORDS = [
    "beograd", "beograde", "bEOGRADA",
    "novi beograd", "zemun", "voždovac", "vozdovac",
    "čukarica", "cukarica", "palilula", "zvezdara",
    "rakovica", "grocka", "lazarevac", "mladenovac",
    "obrenovac", "sopot", "surčin", "surcin", "barajevo",
    "savski venac", "stari grad", "vrčin", "vrcin",
    "borča", "borca", "mirijevo", "kaluđerica", "kaludjerica",
    "bežanija", "bezAnija", "leštane", "lestane",
    "medaković", "medakovic", "braće jerković", "brace jerkovic",
    "konjarnik", "banovo brdo", "ban brdo",
    "cerak", "vidikovac", "labudovo brdo", "lab brdo",
    "selo rakovica",
]


def _is_belgrade(text: str) -> bool:
    """Check if listing text mentions Belgrade or its municipalities."""
    lower = text.lower()
    for kw in BEOGRAD_KEYWORDS:
        if kw in lower:
            return True
    return False


class KupujemScraper(BaseScraper):
    BASE_URL = "https://www.kupujemprodajem.com"
    SEARCH_URL = "https://www.kupujemprodajem.com/nekretnine-prodaja/stanovi/pretraga?categoryId=2821&groupId=2822&priceTo=100000&currency=eur&ignoreUserId=no"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []

        await page.goto(self.SEARCH_URL, wait_until="load", timeout=60000)

        # Wait for SPA to load data (up to 30s)
        for i in range(6):
            await asyncio.sleep(5)
            has_ads = await page.evaluate(
                "document.querySelectorAll('a[href*=\"/oglas/\"]').length"
            )
            if has_ads > 0:
                break

        items = await page.evaluate("""
            () => {
                const ads = [];
                const seen = new Set();
                const links = document.querySelectorAll('a[href*="/oglas/"]');
                links.forEach(a => {
                    const href = a.getAttribute('href');
                    if (!href || seen.has(href)) return;
                    seen.add(href);
                    const card = a.closest('div,li,article') || a;
                    const text = card.innerText || '';

                    // Extract location: find the first meaningful address line
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 3);
                    const skipWords = ['vlasnik', 'agencija', 'investitor', '€', 'm²', 'soba', 'sprat', 'www'];
                    const locationLine = lines.find(l => !skipWords.some(w => l.toLowerCase().includes(w))) || '';

                    const priceMatch = text.match(/([\\d.]+)\\s*(€|EUR)/i);
                    const sqmMatch = text.match(/(\\d+[\\.,]?\\d*)\\s*m²/);
                    const img = card.querySelector('img');
                    ads.push({
                        url: href.startsWith('http') ? href : window.location.origin + href,
                        price_text: priceMatch ? priceMatch[0] : '',
                        area_text: sqmMatch ? sqmMatch[0] : '',
                        location: locationLine,
                        full_text: text.substring(0, 400),
                        image: img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '',
                    });
                });
                return ads;
            }
        """)

        for item in items:
            # Skip if not in Belgrade
            if not _is_belgrade(item["full_text"]):
                continue

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
                    area = float(re.sub(r'[^\d.,]', '', item["area_text"]).replace(",", "."))
                except ValueError:
                    pass

            listings.append(Listing(
                id=listing_id(item["url"]),
                title=item.get("location", "") or item["full_text"].split("\n")[0].strip()[:100],
                price_eur=price,
                area_sqm=area,
                location=item.get("location", ""),
                url=item["url"],
                source="kupujemprodajem",
                image_url=item["image"],
            ))

        await page.close()
        return listings
