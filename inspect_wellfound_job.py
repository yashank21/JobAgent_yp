import asyncio

from playwright.async_api import async_playwright


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        url = "https://wellfound.com/jobs"

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        await page.wait_for_timeout(5000)

        print("TITLE:", await page.title())

        # ---------------------------------------------------------
        # Find elements that may contain posting date/time.
        # ---------------------------------------------------------

        print("\n========== DATE/TIME ELEMENTS ==========\n")

        elements = await page.locator(
            "time, [datetime], "
            "[data-testid*='date'], "
            "[data-testid*='time']"
        ).all()

        print(
            "DATE/TIME ELEMENT COUNT:",
            len(elements),
        )

        for i, element in enumerate(elements[:30]):

            try:

                print(
                    f"[{i}] "
                    f"text={repr(await element.inner_text())} "
                    f"datetime={repr(await element.get_attribute('datetime'))} "
                    f"data-testid={repr(await element.get_attribute('data-testid'))}"
                )

            except Exception as exc:

                print(
                    f"[{i}] ERROR: {exc!r}"
                )

        # ---------------------------------------------------------
        # Search visible text containing "Posted".
        # ---------------------------------------------------------

        print("\n========== POSTED TEXT ==========\n")

        posted_matches = await page.locator(
            "text=/Posted:/i"
        ).all_inner_texts()

        for item in posted_matches:

            print(
                repr(item)
            )

        # ---------------------------------------------------------
        # Inspect HTML around the "Posted:" text.
        # ---------------------------------------------------------

        print("\n========== POSTED HTML ==========\n")

        posted_elements = await page.locator(
            "text=/Posted:/i"
        ).all()

        for i, element in enumerate(
            posted_elements[:10]
        ):

            try:

                html = await element.evaluate(
                    """
                    el => {
                        let node = el;

                        for (let i = 0; i < 4 && node; i++) {
                            if (
                                (node.innerText || "")
                                    .includes("Posted:")
                            ) {
                                return node.outerHTML;
                            }

                            node = node.parentElement;
                        }

                        return el.outerHTML;
                    }
                    """
                )

                print(
                    f"\n--- MATCH {i} ---\n"
                )

                print(
                    html[:5000]
                )

            except Exception as exc:

                print(
                    f"MATCH {i} ERROR: {exc!r}"
                )

        # ---------------------------------------------------------
        # Full page text
        # ---------------------------------------------------------

        print("\n========== PAGE TEXT ==========\n")

        text = await page.locator(
            "body"
        ).inner_text()

        print(
            text[:10000]
        )

        await browser.close()


asyncio.run(main())