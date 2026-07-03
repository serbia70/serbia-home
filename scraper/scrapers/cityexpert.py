import re
from typing import List
from urllib.request import Request, urlopen

from scraper.models import Listing
from scraper.utils import listing_id


class CityexpertScraper:
    SEARCH_URL = "https://www.cityexpert.rs/prodaja-nekretnina/beograd"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def scrape(self) -> List[Listing]:
        import html as html_mod

        req = Request(self.SEARCH_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        page = urlopen(req, timeout=30).read().decode("utf-8")

        # Split page into card chunks
        cards = re.split(r'<div _ngcontent[^>]+class="tw-relative" style="height: 150px;">', page)[1:]

        seen = set()
        listings = []

        for card in cards:
            # Find listing link within this card
            link_m = re.search(r'href="(/prodaja-nekretnina/beograd/\d+[^"]*)"', card)
            if not link_m:
                continue
            href = link_m.group(1)
            if href in seen:
                continue
            seen.add(href)

            # Find price within this card (first occurrence is total price)
            price_m = re.search(r'([\d.]+)\s*€', card)
            if not price_m:
                continue
            try:
                price = float(price_m.group(1).replace(".", ""))
            except ValueError:
                continue
            if price > 100000 or price == 0:
                continue

            # Find area
            area_m = re.search(r'(\d+)\s*m²', card)
            area = float(area_m.group(1)) if area_m else None

            # Extract place info (when available)
            place_m = re.search(r'class="property-card__place[^"]*"[^>]*>([^<]+)', card)

            # Extract title from URL slug (e.g., "dvosoban-stan-stanoja-glavasa-palilula")
            title = href.split("/")[-1].replace("-", " ").strip() if "/" in href else ""

            listings.append(Listing(
                id=listing_id(f"https://www.cityexpert.rs{href}"),
                title=html_mod.unescape(place_m.group(1).strip()) if place_m else title[:100],
                price_eur=price,
                area_sqm=area,
                url=f"https://www.cityexpert.rs{href}",
                source="cityexpert",
                image_url=img_m.group(1) if img_m else None,
            ))

        return listings
