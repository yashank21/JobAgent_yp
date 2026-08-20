import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        await page.goto(
            "https://wellfound.com/jobs/4544682-ai-engineer",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        await page.wait_for_timeout(5000)

        heading = page.get_by_text(
            "About the job",
            exact=True
        )

        print("ABOUT JOB COUNT:", await heading.count())

        if await heading.count():

            print("\n========== ABOUT JOB ELEMENT ==========")

            print(
                await heading.evaluate(
                    """
                    el => ({
                        tag: el.tagName,
                        className: el.className,
                        parentTag: el.parentElement?.tagName,
                        parentClass: el.parentElement?.className,
                        parentText: el.parentElement?.innerText
                    })
                    """
                )
            )

            print("\n========== PARENT HTML ==========")

            html = await heading.evaluate(
                """
                el => el.parentElement?.outerHTML || ""
                """
            )

            print(html[:10000])

        await browser.close()

asyncio.run(main())
