import re
from typing import List
from urllib.request import Request, urlopen

from scraper.models import Listing
from scraper.utils import listing_id


class CityexpertScraper:
    """SSR site - no Playwright needed, use direct HTTP requests."""
    SEARCH_URL = "https://www.cityexpert.rs/prodaja-nekretnina/beograd"

    async def scrape(self) -> List[Listing]:
        listings = []
        req = Request(self.SEARCH_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        html = urlopen(req, timeout=30).read().decode("utf-8")

        # Parse listing cards from HTML
        pattern = r'href="(/prodaja-nekretnina/beograd/(\d+)[^"]*)"[^>]*>.*?'
        cards = re.findall(
            r'<a[^>]*href="(/prodaja-nekretnina/beograd/\d+[^"]*)"[^>]*>'
            r'.*?(\d[\d.]*)\s*€.*?'
            r'(\d+)\s*m²',
            html, re.DOTALL,
        )

        if not cards:
            # Broader fallback
            links = re.findall(r'href="(/prodaja-nekretnina/beograd/\d+[^"]*)"', html)
            seen = set()
            for href in links:
                if href in seen:
                    continue
                seen.add(href)
                full_url = f"https://www.cityexpert.rs{href}"
                # Find price near this link
                idx = html.index(href)
                chunk = html[idx:idx+2000]
                price_m = re.search(r'(\d[\d.]*)\s*€', chunk)
                area_m = re.search(r'(\d+)\s*m²', chunk)
                title_m = re.search(r'alt="([^"]*)"', chunk)

                try:
                    price_str = price_m.group(1).replace(".", "")
                    price = float(price_str)
                except (AttributeError, ValueError):
                    continue
                if price > 100000 or price == 0:
                    continue

                area = None
                if area_m:
                    try:
                        area = float(area_m.group(1))
                    except ValueError:
                        pass

                listings.append(Listing(
                    id=listing_id(full_url),
                    title=(title_m.group(1) if title_m else "")[:100],
                    price_eur=price,
                    area_sqm=area,
                    url=full_url,
                    source="cityexpert",
                ))

        else:
            seen = set()
            for href, _, price_str in cards:
                if href in seen:
                    continue
                seen.add(href)
                try:
                    price = float(price_str.replace(".", ""))
                except ValueError:
                    continue
                if price > 100000 or price == 0:
                    continue

                listings.append(Listing(
                    id=listing_id(f"https://www.cityexpert.rs{href}"),
                    title="",
                    price_eur=price,
                    url=f"https://www.cityexpert.rs{href}",
                    source="cityexpert",
                ))

        return listings
