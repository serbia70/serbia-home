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
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
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
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="sr-RS",
            timezone_id="Europe/Belgrade",
            permissions=["geolocation"],
            extra_http_headers={
                "Accept-Language": "sr-RS,en-US;q=0.9,sr;q=0.8",
            },
        )
        page = await context.new_page()

        # Comprehensive anti-detection script
        await page.add_init_script("""
            // Override webdriver flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1,2,3,4,5],
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['sr-RS', 'en-US', 'en'],
            });

            // Override Chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {},
            };

            // Override permissions
            if (navigator.permissions) {
                const origQuery = navigator.permissions.query;
                navigator.permissions.query = function(p) {
                    if (p.name === 'notifications') {
                        return Promise.resolve({state: 'denied'});
                    }
                    return origQuery.call(this, p);
                };
            }

            // Hide headless by overriding connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    downlink: 10,
                    effectiveType: '4g',
                    rtt: 50,
                }),
            });

            // Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
            });

            // Override deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
            });
        """)

        return page

    @abstractmethod
    async def scrape(self) -> List[Listing]:
        ...
