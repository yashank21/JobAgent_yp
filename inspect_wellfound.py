import asyncio

from playwright.async_api import async_playwright
from app.collectors.wellfound import WellfoundCollector


async def main():

    collector = WellfoundCollector()

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            collector.urls[0],
            wait_until="domcontentloaded",
            timeout=30000,
        )

        await page.wait_for_timeout(4000)

        links = await page.query_selector_all(
            "a[href*='/jobs/']"
        )

        print("LINKS:", len(links))

        if not links:
            await browser.close()
            return

        href = await links[0].get_attribute("href")

        print("URL:", href)

        await page.goto(
            collector._absolute_url(href),
            wait_until="domcontentloaded",
            timeout=30000,
        )

        await page.wait_for_timeout(2000)

        body = await page.locator("body").inner_text()

        print("\n========== JOB DETAIL ==========\n")
        print(body[:8000])

        await browser.close()


asyncio.run(main())
