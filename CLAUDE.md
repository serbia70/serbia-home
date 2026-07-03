# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Belgrade property listing monitor - scrapes Serbian real estate websites for apartments/flats under €100,000 and generates a filterable static HTML site.

## Commands

```bash
pip install -r requirements.txt && python -m playwright install chromium  # setup
python scraper/main.py                    # run all scrapers → site/listings.json
python scraper/site_generator.py          # generate site/index.html from listings.json
```

## Architecture

```
scraper/
├── main.py              # Entry point: runs all scrapers sequentially
├── models.py            # Listing dataclass (id, price, area, rooms, location, source, url)
├── utils.py             # JSON persistence with SHA256-based dedup (listing_id)
├── site_generator.py    # Generates static index.html (Chinese UI, JS-based filtering)
└── scrapers/
    ├── base.py          # ABC with Playwright async context manager, anti-bot evasions
    ├── zida.py          # 4zida.rs - extracts JSON-LD structured data
    ├── halo.py          # Halo Oglasi - DOM extraction with Cloudflare retry
    ├── kupujem.py       # KupujemProdajem - SPA, waits for JS rendering
    ├── cityexpert.py    # Cityexpert - plain HTTP + regex (no Playwright needed)
    └── nekretnine.py    # Nekretnine.rs - Next.js SPA, waits for content load
```

### Key design decisions

- **All scrapers filter listings to ≤€100,000** at scrape time
- **Dedup by SHA256 URL hash** (16 chars) — `first_seen` date is preserved on re-scrape
- **Output**: `site/listings.json` (sorted by price) + `site/index.html` (Chinese-language static site with source/price/area filters)
- **CI**: GitHub Actions daily at 13:00 Belgrade time (CEST UTC+2), deploys `site/` to GitHub Pages

### Scraper patterns

- Most scrapers extend `BaseScraper` which manages a Playwright Chromium browser with anti-detection measures
- `CityexpertScraper` uses plain `urllib` + regex (no Playwright needed for that site)
- `HaloScraper` has a 2-attempt retry loop for Cloudflare challenges
- `KupujemScraper` captures XHR responses to bypass SPA rendering limitations
- All scrapers implement `async def scrape(self) -> List[Listing]`
