import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.scrapers.zida import ZidaScraper
from scraper.scrapers.halo import HaloScraper
from scraper.scrapers.kupujem import KupujemScraper
from scraper.utils import save_listings


async def main():
    all_listings = []
    scrapers = [ZidaScraper, HaloScraper, KupujemScraper]

    for scraper_cls in scrapers:
        name = scraper_cls.__name__.replace("Scraper", "")
        print(f"Scraping {name}...")
        try:
            async with scraper_cls() as scraper:
                listings = await scraper.scrape()
                print(f"  Found {len(listings)} listings")
                all_listings.extend(listings)
        except Exception as e:
            print(f"  Error scraping {name}: {e}")

    result = save_listings(all_listings)
    print(f"\nTotal: {result['total']} listings saved")
    return result


if __name__ == "__main__":
    asyncio.run(main())
