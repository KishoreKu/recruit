"""
agents/job_posting_agent.py
─────────────────────────────────────────────────────────────────────────────
Job Posting Agent — "The Advertiser"
Handles: Outbound job posting to job portals (LinkedIn, Indeed, etc.)
  1. Claims 'post_to_job_boards' tasks from the queue.
  2. Uses Playwright automation to securely post to job portals.
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from agents.base_agent import BaseAgent
from config import get_settings

settings = get_settings()


class JobPostingAgent(BaseAgent):
    name = "job-posting-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """Process a 'post_to_job_boards' task."""
        req_id = payload.get("requisition_id")
        title = payload.get("title", "Unknown Role")
        location = payload.get("location", "Remote")

        logger.info(f"[{self.name}] Claimed job posting task for Requisition #{req_id}: {title}")

        # Step 1: Initialize VMS session to get full job details
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from agents.base_agent import VMS_SERVER
        import os

        description = ""
        job_type = "Contract"
        bill_rate_max = None

        try:
            logger.info(f"[{self.name}] Initialising VMS session to fetch requisition details...")
            async with stdio_client(StdioServerParameters(command="python", args=[VMS_SERVER], env=dict(os.environ))) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    self._vms_session = session
                    
                    req_details = await self.call_vms("get_requisition", requisition_id=req_id)
                    if req_details and "error" not in req_details:
                        description = req_details.get("description", "")
                        job_type = req_details.get("job_type", "Contract")
                        bill_rate_max = req_details.get("bill_rate_max")
                        title = req_details.get("title", title)
                        location = req_details.get("location", location)
        except Exception as vms_err:
            logger.warning(f"[{self.name}] Could not retrieve full requisition details from VMS: {vms_err}. Using basic payload.")

        # Step 2: Post to Indeed using Playwright
        try:
            await self._post_to_indeed(req_id, title, location, description, job_type, bill_rate_max)
            
            # Mark task complete
            await self.complete_task(task_id)
            await self._log_health("succeeded", f"Posted Requisition {req_id} to Indeed.")

        except Exception as e:
            logger.error(f"[{self.name}] Playwright automation failed for task {task_id}: {str(e)}")
            raise e

    async def _post_to_indeed(self, req_id: str, title: str, location: str, description: str, job_type: str, bill_rate: float | None):
        """Playwright automation logic for Indeed Employer Portal."""
        from playwright.async_api import async_playwright
        from db import get_pool
        import json

        # Try to load session state from database
        session_state = None
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT value FROM agent_settings WHERE key = 'indeed_session_state'")
                if row:
                    session_state = json.loads(row["value"])
                    logger.info(f"[{self.name} - Indeed] Loaded session cookies from database.")
        except Exception as db_err:
            logger.warning(f"[{self.name} - Indeed] Could not read session state from DB: {db_err}")

        logger.info(f"[{self.name} - Indeed] Starting Playwright browser...")
        
        async with async_playwright() as p:
            browser = None
            if session_state:
                logger.info(f"[{self.name} - Indeed] Launching browser with database session cookies (headless={settings.INDEED_HEADLESS})")
                browser = await p.chromium.launch(headless=settings.INDEED_HEADLESS, slow_mo=100)
                context = await browser.new_context(storage_state=session_state)
                page = await context.new_page()
            elif settings.INDEED_USER_DATA_DIR:
                logger.info(f"[{self.name} - Indeed] Launching persistent browser context from {settings.INDEED_USER_DATA_DIR}")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=settings.INDEED_USER_DATA_DIR,
                    headless=settings.INDEED_HEADLESS,
                    slow_mo=100
                )
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                logger.info(f"[{self.name} - Indeed] Launching clean browser context (headless={settings.INDEED_HEADLESS})")
                browser = await p.chromium.launch(headless=settings.INDEED_HEADLESS, slow_mo=100)
                context = await browser.new_context()
                page = await context.new_page()

            try:
                # Navigate to indeed employer portal
                logger.info(f"[{self.name} - Indeed] Navigating to indeed employer signin page...")
                await page.goto("https://employers.indeed.com", wait_until="networkidle")
                
                # Check if we need to sign in
                email_input = page.locator("input[type='email'], #ifl-InputTextInput-email, input[name='email']")
                sign_in_link = page.locator("a:has-text('Sign In'), a[href*='signon']")
                
                if await sign_in_link.first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Clicking Sign In button...")
                    await sign_in_link.first.click()
                    await page.wait_for_load_state("networkidle")
                    
                if await email_input.first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Email input visible. Typing email...")
                    if not settings.INDEED_EMAIL:
                        raise ValueError("INDEED_EMAIL setting not set. Cannot authenticate.")
                    await email_input.first.fill(settings.INDEED_EMAIL)
                    
                    # Press Continue
                    continue_btn = page.locator("button[type='submit'], button:has-text('Continue')")
                    await continue_btn.first.click()
                    await page.wait_for_timeout(2000)

                    password_input = page.locator("input[type='password'], #ifl-InputTextInput-password, input[name='password']")
                    if await password_input.first.is_visible():
                        logger.info(f"[{self.name} - Indeed] Password input visible. Typing password...")
                        if not settings.INDEED_PASSWORD:
                            raise ValueError("INDEED_PASSWORD setting not set. Cannot authenticate.")
                        await password_input.first.fill(settings.INDEED_PASSWORD)
                        await page.locator("button[type='submit'], button:has-text('Sign')").first.click()
                        await page.wait_for_load_state("networkidle")
                    else:
                        logger.warning(f"[{self.name} - Indeed] Password input not visible. May be prompting for verification or MFA.")

                # Wait for session recovery / dashboard load
                logger.info(f"[{self.name} - Indeed] Checking session state...")
                await page.wait_for_timeout(3000)
                
                # Navigate directly to job posting URL
                logger.info(f"[{self.name} - Indeed] Navigating to job posting page...")
                await page.goto("https://employers.indeed.com/post-job", wait_until="networkidle")
                
                # Wait for title input
                title_selector = "input[name='title'], #jobTitle, input[id*='jobtitle']"
                await page.wait_for_selector(title_selector, timeout=15000)
                logger.info(f"[{self.name} - Indeed] Filling job title: {title}")
                await page.locator(title_selector).first.fill(title)
                
                # Fill location
                loc_selector = "input[name='location'], #location, input[id*='location']"
                if await page.locator(loc_selector).first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Filling location: {location}")
                    await page.locator(loc_selector).first.fill(location)
                
                # Click Continue/Next
                submit_btn = page.locator("button[type='submit'], button:has-text('Continue'), button:has-text('Next')")
                logger.info(f"[{self.name} - Indeed] Clicking Continue...")
                await submit_btn.first.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                # Fill description & details (Indeed step 2)
                desc_selector = "textarea, [contenteditable='true'], #jobDescriptionText"
                if await page.locator(desc_selector).first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Filling description...")
                    await page.locator(desc_selector).first.fill(description)
                
                # Select Job Type if label matches
                if job_type:
                    logger.info(f"[{self.name} - Indeed] Selecting job type: {job_type}")
                    job_type_label = page.locator(f"label:has-text('{job_type}')")
                    if await job_type_label.first.is_visible():
                        await job_type_label.first.click()
                
                if bill_rate:
                    logger.info(f"[{self.name} - Indeed] Filling max rate: {bill_rate}")
                    rate_selector = "input[name='salary'], input[name='rate'], #salary-input"
                    if await page.locator(rate_selector).first.is_visible():
                        await page.locator(rate_selector).first.fill(str(bill_rate))
                
                # Continue through steps
                logger.info(f"[{self.name} - Indeed] Clicking Continue to next steps...")
                await submit_btn.first.click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                # Click publish/submit at the end
                publish_btn = page.locator("button:has-text('Publish'), button:has-text('Submit'), button:has-text('Post Job')")
                if await publish_btn.first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Clicking Publish...")
                    await publish_btn.first.click()
                    await page.wait_for_load_state("networkidle")
                    logger.info(f"[{self.name} - Indeed] Successfully clicked publish.")
                else:
                    logger.info(f"[{self.name} - Indeed] Clicked final Continue. Job is queued.")
                
            except Exception as e:
                # Take screenshot on failure for troubleshooting
                screenshot_dir = Path("/Users/kishorekumar/.gemini/antigravity-cli/brain/4576a9e6-1714-4032-bb54-eb7770c7dc8f/scratch")
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = screenshot_dir / f"indeed_fail_{req_id}.png"
                try:
                    await page.screenshot(path=str(screenshot_path))
                    logger.error(f"[{self.name} - Indeed] Playwright task failed. Screenshot saved to {screenshot_path}")
                except Exception as screenshot_err:
                    logger.error(f"[{self.name} - Indeed] Failed to capture screenshot: {screenshot_err}")
                raise e
            finally:
                # Save updated session cookies back to DB to keep session fresh
                try:
                    new_state = await context.storage_state()
                    pool = await get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO agent_settings (key, value) VALUES ('indeed_session_state', $1) "
                            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()",
                            json.dumps(new_state)
                        )
                    logger.info(f"[{self.name} - Indeed] Updated session cookies saved back to database.")
                except Exception as db_save_err:
                    logger.warning(f"[{self.name} - Indeed] Failed to auto-save session state to DB: {db_save_err}")

                logger.info(f"[{self.name} - Indeed] Closing browser context...")
                await context.close()
                if browser:
                    await browser.close()


    async def run(self) -> None:
        """Run the task execution loop for job posting tasks."""
        logger.info(f"[{self.name}] Starting up. Polling for 'post_to_job_boards' tasks.")
        await self.run_loop(task_type="post_to_job_boards", poll_interval=15)


async def main():
    agent = JobPostingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())

