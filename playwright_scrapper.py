import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def load_all_items(page):

    load_more_xpath = '//*[@id="facet-browse"]/section/div[3]/div[2]/div[1]/div/div'

    while True:
        try:
            # Scroll to the bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)  # give time for lazy loading

            load_more = page.locator(f'xpath={load_more_xpath}')

            if await load_more.is_visible():
                print("Clicking 'Load More'...")
                await load_more.click()
                await asyncio.sleep(3)  # wait for new items to load
            else:
                print("No more 'Load More' button. All items loaded.")
                break
        except Exception as e:
            print(f"Error during load more process: {e}")
            break


async def scrape_link(context, href, max_retries=3):
    page = await context.new_page()
    attempt = 0
    while attempt < max_retries:
        try:
            await page.goto("https://shop.alphacomm.com/Shop-by-Handset/Apple/Apple-iPhone-16-Pro", timeout=60000, wait_until="load")
            # await page.goto(href, timeout=60000, wait_until="load")  # longer timeout
            await asyncio.sleep(1.5)
            await load_all_items(page)  # load all products

            outer_base_xpath = '//*[@id="facet-browse"]/section/div[3]/div[1]/div[5]'
            await page.wait_for_selector(f'xpath={outer_base_xpath}/div', timeout=60000)
            outer_container = page.locator(f'xpath={outer_base_xpath}')
            outer_divs = outer_container.locator(":scope > div")
            outer_count = await outer_divs.count()

            print(f"Found {outer_count} outer divs")

            item_data = []

            for i in range(1, outer_count + 1):

                inner_path = f'{outer_base_xpath}/div[{i}]'
                await page.wait_for_selector(f'xpath={inner_path}/div', timeout=60000)
                inner_container = page.locator(f'xpath={outer_base_xpath}')
                inner_divs = inner_container.locator(":scope > div")
                inner_count = await inner_divs.count()

                print(f"Outer div {i} has {inner_count} inner divs (items)")

                # for j in range(1, inner_count + 1):
                #     try:
                #         item_name_xpath = f'{outer_base_xpath}/div[{i}]/div[{j}]/div/div[2]/span[2]/a/h4'
                #         await page.wait_for_selector(f'xpath={item_name_xpath}', timeout=60000)
                    
                #         item_name = await page.locator(f'xpath={item_name_xpath}').inner_text()
                #         item_data.append({"group": i, "index": j, "name": item_name})
                    
                #     except Exception as e:
                #         print(f"    Failed to get phone at outer {i}, inner {j}: {e}")
                #         continue

            return {
                "href": href,
                "title": f"{len(item_data)} phones found",
                "phones": item_data
            }

        except Exception as e:
            attempt += 1
            print(f"Attempt {attempt} failed for {href}: {e}")
            await asyncio.sleep(5)
        finally:
            await page.close()
    return {"href": href, "title": "Error after retries", "phones": []}


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Go to the website
        await page.goto("https://shop.alphacomm.com/",wait_until="load")

        # Login
        await page.locator('xpath=//*[@id="login-email"]').fill("Somaan@xclusivetradinginc.com")
        await page.locator('xpath=//*[@id="login-password"]').fill("Metro57398XTI$")
        await page.locator('xpath=//*[@id="LoginRegister.View"]/section/div[2]/div/div/form/fieldset/div[6]/button').click()

        href_links = []

        # Loop through top navigation menus
        for l in range(1, 4):
            top_nav_xpath = f'//*[@id="site-header"]/div[4]/div/div[2]/div/nav/ul/li[{l}]/a'
            await page.locator(f'xpath={top_nav_xpath}').hover()
            
            # Wait for dropdown to appear
            mid_ul_xpath = f'//*[@id="site-header"]/div[4]/div/div[2]/div/nav/ul/li[{l}]/ul/li/ul'
            try:
                await page.locator(f'xpath={mid_ul_xpath}').wait_for(state='visible', timeout=10000)
            except:
                print(f"No dropdown menu for top nav li[{l}]")
                continue

            # Get all middle li elements
            middle_lis_xpath = f'//*[@id="site-header"]/div[4]/div/div[2]/div/nav/ul/li[{l}]/ul/li/ul/li'
            middle_items = await page.locator(f'xpath={middle_lis_xpath}').all()

            for i in range(1, len(middle_items) + 1):
                final_ul_xpath = f'//*[@id="site-header"]/div[4]/div/div[2]/div/nav/ul/li[{l}]/ul/li/ul/li[{i}]/ul'

                try:
                    await page.locator(f'xpath={final_ul_xpath}').wait_for(state='attached', timeout=3000)
                    final_links = await page.locator(f'xpath={final_ul_xpath}/li/a').all()

                    for link in final_links:

                        base_url = "https://shop.alphacomm.com"
                        # Inside your for loop where you collect hrefs:
                        href = await link.get_attribute('href')
                        if href:
                            if href.startswith("/"):
                                href = base_url + href
                            href_links.append(href)

                        print(href)
                except:
                    print(f"No final links in li[{i}] of main menu li[{l}]")

        print(f"Total links collected: {len(href_links)}")

        results = []
        batch_size = 5

        for i in range(0, 5, batch_size):
            batch = href_links[i:i+batch_size]
            tasks = [scrape_link(context, href) for href in batch]
            batch_results = await asyncio.gather(*tasks)
            for result in batch_results:
                for phone in result["phones"]:
                    phone["source_url"] = result["href"]  # add the page URL for reference
                    results.append(phone)

        df = pd.DataFrame(results)
        df.to_csv("item_data.csv", index=False)
        print("Saved to item_data.csv")

asyncio.run(run())
