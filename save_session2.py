import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to login page
        await page.goto("https://metro.b2b.scp4me.com/index.php/customer/account/login")
        print("➡️ Logging in automatically...")
        
        # Fill in login credentials with xpath 

        await page.fill('#email', 'Odhaduk@xclusivetradinginc.com')
        await page.fill('#pass', 'XTI$$$7878')
        
        # Click login button
        await page.click("button[type='submit']")   
        
        # Wait for navigation to complete after login
        await page.wait_for_load_state("networkidle")
        print("✅ Login successful")
        
        # Save cookies after login
        storage = await context.storage_state()
        with open("session_data.json", "w") as f:
            json.dump(storage, f, indent=2)

        print("✅ Session saved to session_data.json")
        # await browser.close()

asyncio.run(main())
