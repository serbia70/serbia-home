from abc import ABC, abstractmethod
from typing import List
from playwright.async_api import async_playwright, Browser, Page
from scraper.models import Listing


class BaseScraper(ABC):
    BASE_URL = ""

    def __init__(self):
        self.browser: Browser | None = None
        self._playwright_cm = None

    async def __aenter__(self):
        self._playwright_cm = async_playwright()
        playwright = await self._playwright_cm.__aenter__()
        self.browser = await playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()
        if self._playwright_cm:
            await self._playwright_cm.__aexit__(*args)

    async def new_page(self) -> Page:
        context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        return await context.new_page()

    @abstractmethod
    async def scrape(self) -> List[Listing]:
        ...
