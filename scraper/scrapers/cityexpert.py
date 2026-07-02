import asyncio
import re
from typing import List

from scraper.models import Listing
from scraper.utils import listing_id
from scraper.scrapers.base import BaseScraper


class CityexpertScraper(BaseScraper):
    BASE_URL = "https://www.cityexpert.rs"
    SEARCH_URL = "https://www.cityexpert.rs/prodaja-nekretnina/beograd"

    async def scrape(self) -> List[Listing]:
        page = await self.new_page()
        listings = []
        try:
            await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            items = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="/prodaja-nekretnina/beograd/"]');
                    const results = [];
                    const seen = new Set();

                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        if (!href || seen.has(href)) return;
                        if (!href.match(/\\/prodaja-nekretnina\\/beograd\\/\\d+/)) return;
                        seen.add(href);

                        const card = link.closest('div, article, li') || link;
                        const text = card.innerText || link.innerText || '';
                        const priceMatch = text.match(/([\\d.]+)\\s*€/);
                        const sqmMatch = text.match(/(\\d+)\\s*m²/);
                        const img = card.querySelector('img');

                        let title = '';
                        const parts = text.split('\\n').filter(s => s.trim());
                        if (parts.length > 0) title = parts[0].trim();
                        if (!title || title.length > 100) title = text.substr(0, 80).trim();

                        results.push({
                            url: href.startsWith('http') ? href : 'https://www.cityexpert.rs' + href,
                            title: title,
                            price_text: priceMatch ? priceMatch[0] : '',
                            area_text: sqmMatch ? sqmMatch[0] : '',
                            full_text: text.substr(0, 400),
                            image: img ? (img.getAttribute('src') || '') : '',
                        });
                    });
                    return results;
                }
            """)

            for item in items:
                try:
                    price_str = item["price_text"].replace(".", "")
                    price = float(re.sub(r'[^\d]', '', price_str))
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
                    title=item.get("title", "")[:100] or "Stan Beograd",
                    price_eur=price,
                    area_sqm=area,
                    url=item["url"],
                    source="cityexpert",
                    image_url=item.get("image"),
                ))
        finally:
            await page.close()
        return listings
