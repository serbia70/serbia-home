import re
from typing import List
from urllib.request import Request, urlopen

from scraper.models import Listing
from scraper.utils import listing_id


class CityexpertScraper:
    """Angular SSR site - extract all prices and match with nearby links."""
    SEARCH_URL = "https://www.cityexpert.rs/prodaja-nekretnina/beograd"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def scrape(self) -> List[Listing]:
        req = Request(self.SEARCH_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        html = urlopen(req, timeout=30).read().decode("utf-8")

        # Find all listing URLs with their positions
        link_positions = []
        for m in re.finditer(r'href="(/prodaja-nekretnina/beograd/\d+[^"]*)"', html):
            link_positions.append((m.start(), m.group(1)))

        # Find all prices with their positions
        price_positions = []
        for m in re.finditer(r'>([\d.]+)\s*€<', html):
            try:
                price = float(m.group(1).replace(".", ""))
            except ValueError:
                continue
            if 10000 < price <= 100000:
                price_positions.append((m.start(), price))

        # Match each price to its nearest link
        listings = []
        seen = set()

        for ppos, price in price_positions:
            # Find closest link before the price (within 1000 chars)
            best_link = None
            best_dist = 999999

            for lpos, href in link_positions:
                dist = abs(ppos - lpos)
                if dist < best_dist:
                    best_dist = dist
                    best_link = href

            if not best_link or best_link in seen or best_dist > 1000:
                continue
            seen.add(best_link)

            full_url = f"https://www.cityexpert.rs{best_link}"

            # Get context around the price for area/title
            chunk = html[max(0, ppos - 800):ppos + 500]
            title_m = re.search(r'alt="([^"]*)"', chunk)
            area_m = re.search(r'(\d+)\s*m²', chunk)

            listings.append(Listing(
                id=listing_id(full_url),
                title=(title_m.group(1) if title_m else "")[:100],
                price_eur=price,
                area_sqm=float(area_m.group(1)) if area_m else None,
                url=full_url,
                source="cityexpert",
            ))

        return listings
