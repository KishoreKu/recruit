import sys
import asyncio
import os
import json
import psycopg2
from pathlib import Path

# Add parent directory to path to load config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings
from playwright.async_api import async_playwright
from loguru import logger

settings = get_settings()

def save_to_db(state):
    logger.info("Connecting to database to upload session state...")
    db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    
    # Check if we should use Azure credentials fallback (same as migrate.py)
    if not os.environ.get("DATABASE_URL") and "localhost" in db_url:
        logger.info("Using default Azure Database credentials...")
        try:
            conn = psycopg2.connect(
                host="westley-db-pg.postgres.database.azure.com",
                database="postgres",
                user="westleyadmin",
                password="P@ssw0rd_Westley_2026_Recruit",
                sslmode="require"
            )
        except Exception as azure_err:
            logger.error(f"Failed to connect to Azure Database: {azure_err}")
            logger.info("Falling back to DATABASE_URL...")
            conn = psycopg2.connect(db_url)
    else:
        conn = psycopg2.connect(db_url)
        
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Save session state to agent_settings
        cursor.execute(
            "INSERT INTO agent_settings (key, value) VALUES ('indeed_session_state', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
            (json.dumps(state),)
        )
        logger.success("Session state successfully saved and synced to the database!")
        cursor.close()
    except Exception as db_err:
        logger.error(f"Failed to write session state to database: {db_err}")
        raise db_err
    finally:
        conn.close()

async def main():
    logger.info("Launching visible Chromium browser...")
    
    async with async_playwright() as p:
        # We launch a clean, non-persistent context so you can log in fresh,
        # and we capture the cookies at the end.
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        page = await context.new_page()
        
        logger.info("Navigating to Indeed...")
        await page.goto("https://employers.indeed.com")
        
        print("\n=======================================================")
        print("INSTRUCTIONS:")
        print("1. Log in on the browser window that just opened.")
        print("2. Complete any email verification / MFA codes.")
        print("3. Once you see the Indeed Dashboard, come back here")
        print("   and press ENTER to save the session, or close the browser.")
        print("=======================================================\n")
        
        # Wait for user input or browser window close
        loop = asyncio.get_event_loop()
        input_task = loop.run_in_executor(None, input, "Press Enter here once you are logged in to save: ")

        
        try:
            while not input_task.done() and len(context.pages) > 0:
                await asyncio.sleep(0.5)
        except Exception:
            pass
            
        # Extract storage state (cookies + localStorage)
        logger.info("Extracting session storage state...")
        state = await context.storage_state()
        
        # Upload to DB
        save_to_db(state)
        
        logger.info("Closing browser...")
        await context.close()
        await browser.close()
        
    logger.success("Done!")

if __name__ == "__main__":
    asyncio.run(main())
