import re
from typing import List
from urllib.request import Request, urlopen

from scraper.models import Listing
from scraper.utils import listing_id


class CityexpertScraper:
    """SSR site - no Playwright needed, use direct HTTP requests."""
    SEARCH_URL = "https://www.cityexpert.rs/prodaja-nekretnina/beograd"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def scrape(self) -> List[Listing]:
        listings = []
        req = Request(self.SEARCH_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        html = urlopen(req, timeout=30).read().decode("utf-8")

        # Find all listing links
        links = re.finditer(r'href="(/prodaja-nekretnina/beograd/\d+[^"]*)"', html)
        seen = set()

        for match in links:
            href = match.group(1)
            if href in seen:
                continue
            seen.add(href)

            full_url = f"https://www.cityexpert.rs{href}"

            # Extract the chunk around this link to find the price
            start = max(0, match.start() - 500)
            end = min(len(html), match.end() + 1500)
            chunk = html[start:end]

            # Find price: look for "d+.d+ €" or "d+ €" patterns (European format)
            price_m = re.search(r'>(\d{2,}\.\d{3})\s*€', chunk)
            if not price_m:
                price_m = re.search(r'>(\d{4,})\s*€', chunk)

            if not price_m:
                continue

            try:
                price = float(price_m.group(1).replace(".", ""))
            except ValueError:
                continue

            if price > 100000 or price == 0:
                continue

            # Find area
            area_m = re.search(r'(\d+)\s*m²', chunk)
            area = float(area_m.group(1)) if area_m else None

            # Find title/image
            title_m = re.search(r'alt="([^"]*)"', chunk)
            img_m = re.search(r'<img[^>]*src="([^"]*)"', chunk)

            listings.append(Listing(
                id=listing_id(full_url),
                title=(title_m.group(1) if title_m else "")[:100],
                price_eur=price,
                area_sqm=area,
                url=full_url,
                source="cityexpert",
                image_url=img_m.group(1) if img_m else None,
            ))

        return listings
