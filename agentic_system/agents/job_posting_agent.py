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
                # Navigate directly to target job posting page
                logger.info(f"[{self.name} - Indeed] Navigating to job posting page...")
                await page.goto("https://employers.indeed.com/post-job", wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                # Check if we need to sign in (redirected to a login/authentication screen)
                email_input = page.locator("input[type='email'], #ifl-InputTextInput-email, input[name='email']")
                sign_in_link = page.locator("a:has-text('Sign In'), a[href*='signon']")
                
                if await sign_in_link.first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Clicking Sign In button...")
                    await sign_in_link.first.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(2000)
                    
                if await email_input.first.is_visible():
                    logger.info(f"[{self.name} - Indeed] Login input detected. Typing email...")
                    if not settings.INDEED_EMAIL:
                        raise ValueError("INDEED_EMAIL setting not set. Cannot authenticate.")
                    await email_input.first.fill(settings.INDEED_EMAIL)
                    
                    # Press Continue
                    continue_btn = page.locator("button[type='submit'], button:has-text('Continue')")
                    await continue_btn.first.click()
                    await page.wait_for_timeout(3000)

                    password_input = page.locator("input[type='password'], #ifl-InputTextInput-password, input[name='password']")
                    if await password_input.first.is_visible():
                        logger.info(f"[{self.name} - Indeed] Password input visible. Typing password...")
                        if not settings.INDEED_PASSWORD:
                            raise ValueError("INDEED_PASSWORD setting not set. Cannot authenticate.")
                        await password_input.first.fill(settings.INDEED_PASSWORD)
                        await page.locator("button[type='submit'], button:has-text('Sign')").first.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(5000)
                    else:
                        logger.warning(f"[{self.name} - Indeed] Password input not visible. May be prompting for verification or MFA.")

                # Check if we are on the template selection screen first
                brand_new_post_locator = page.locator("label:has-text('Create a brand new post'), :text('Create a brand new post')")
                try:
                    logger.info(f"[{self.name} - Indeed] Checking for template selection screen...")
                    await brand_new_post_locator.first.wait_for(state="visible", timeout=4000)
                    logger.info(f"[{self.name} - Indeed] Template selection screen detected. Selecting 'Create a brand new post'...")
                    await page.locator("label:has-text('Create a brand new post')").first.click()
                    await page.wait_for_timeout(1000)
                    
                    # Click Continue/Next
                    continue_btn = page.locator("button[type='submit'], button:has-text('Continue'), button:has-text('Next')")
                    await continue_btn.first.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.info(f"[{self.name} - Indeed] Template selection screen not detected or timed out (continuing to wizard): {str(e)}")

                # Parse location information
                location_lower = location.lower() if location else ""
                is_remote = "remote" in location_lower or not location
                is_hybrid = "hybrid" in location_lower
                
                clean_location = ""
                if is_remote:
                    cleaned = location_lower.replace("remote", "").replace("usa", "").replace("us", "").replace("/", "").replace("-", "").strip()
                    if cleaned and len(cleaned) > 3:
                        clean_location = location.replace("Remote", "").replace("remote", "").replace("USA", "").replace("usa", "").replace("/", "").replace("-", "").strip(" ,")
                    else:
                        clean_location = "San Francisco, CA"
                else:
                    clean_location = location or "San Francisco, CA"
                
                target_loc_type = "Remote" if is_remote else ("Hybrid" if is_hybrid else "In person")
                logger.info(f"[{self.name} - Indeed] Requisition Location parsed: type={target_loc_type}, value={clean_location}")

                # Wizard loop
                logger.info(f"[{self.name} - Indeed] Starting wizard loop...")
                step = 0
                max_steps = 10
                title_filled = False
                loc_type_filled = False
                loc_filled = False
                timeline_filled = False
                hires_filled = False
                job_type_filled = False
                desc_filled = False
                rate_filled = False
                
                while step < max_steps:
                    step += 1
                    await page.wait_for_timeout(2000)
                    # 0. Dismiss Sponsorship Modal if visible
                    no_thanks_btn = page.locator("button:has-text('No thanks'), button:has-text('No, thanks'), button:has-text('Skip sponsorship'), [data-testid*='no-thanks']").first
                    if await no_thanks_btn.is_visible():
                        logger.info(f"[{self.name} - Indeed] Sponsorship modal detected. Clicking 'No thanks'...")
                        await no_thanks_btn.click()
                        await page.wait_for_timeout(2000)
                        continue

                    # 1. Fill Job Title
                    title_selector = "input[name='title'], #jobTitle, input[id*='job-title'], input[id*='jobtitle']"
                    title_elem = page.locator(title_selector).first
                    if not title_filled and await title_elem.is_visible():
                        logger.info(f"[{self.name} - Indeed] Filling job title: {title}")
                        await title_elem.fill(title)
                        title_filled = True

                    # 2. Select Location Type
                    loc_type_selector = "[data-testid='job-location-type-selector']"
                    loc_type_elem = page.locator(loc_type_selector).first
                    if not loc_type_filled and await loc_type_elem.is_visible():
                        current_type = await loc_type_elem.inner_text()
                        logger.info(f"[{self.name} - Indeed] Current location type: {current_type}. Target: {target_loc_type}")
                        if target_loc_type not in current_type:
                            await loc_type_elem.click()
                            await page.wait_for_timeout(1000)
                            if target_loc_type == "Remote":
                                option_selector = "[role='option'][data-testid='REMOTE_WORK_FROM_HOME']"
                            elif target_loc_type == "Hybrid":
                                option_selector = "[role='option'][data-testid='HYBRID_REMOTE']"
                            else:
                                option_selector = "[role='option'][data-testid='PRECISE_OR_GENERAL']"
                            
                            await page.locator(option_selector).first.click()
                            await page.wait_for_timeout(1000)
                        loc_type_filled = True

                    # 3. Fill Location Text
                    loc_selector = "input[id='suggestlist-id'], input[data-testid='location-input-component'], input[name='location'], #location"
                    loc_elem = page.locator(loc_selector).first
                    if not loc_filled and await loc_elem.is_visible():
                        logger.info(f"[{self.name} - Indeed] Filling location: {clean_location}")
                        await loc_elem.fill(clean_location)
                        await page.wait_for_timeout(1000)
                        # Press Enter to dismiss autocomplete dropdown if present
                        await loc_elem.press("Enter")
                        await page.wait_for_timeout(1000)
                        loc_filled = True

                    # 4. Fill Hiring Timeline
                    timeline_dropdown = page.locator("[data-testid='expect-hire-date-input']").first
                    if not timeline_filled and await timeline_dropdown.is_visible():
                        logger.info(f"[{self.name} - Indeed] Opening hiring timeline dropdown...")
                        await timeline_dropdown.click()
                        await page.wait_for_timeout(1500)
                        options = await page.locator("[role='option']").all()
                        if options:
                            logger.info(f"[{self.name} - Indeed] Selecting timeline option: {await options[0].inner_text()}")
                            await options[0].click()
                            await page.wait_for_timeout(1000)
                        timeline_filled = True

                    # 5. Fill Hires Needed
                    hires_input = page.locator("[data-testid='job-hires-needed-input']").first
                    if not hires_filled and await hires_input.is_visible():
                        logger.info(f"[{self.name} - Indeed] Filling hires needed: 1")
                        await hires_input.fill("1")
                        await page.wait_for_timeout(1000)
                        hires_filled = True

                    # 6. Select Job Type Chip
                    if job_type and not job_type_filled:
                        job_type_label = page.locator(f"label:has-text('{job_type}'), span:has-text('{job_type}')").first
                        if await job_type_label.is_visible():
                            logger.info(f"[{self.name} - Indeed] Selecting job type chip: {job_type}")
                            await job_type_label.click()
                            await page.wait_for_timeout(1000)
                            job_type_filled = True

                    # 7. Fill Description
                    desc_selector = "textarea, [contenteditable='true'], #jobDescriptionText, [role='textbox'][data-lexical-editor='true']"
                    desc_elem = page.locator(desc_selector).first
                    if not desc_filled and await desc_elem.is_visible():
                        logger.info(f"[{self.name} - Indeed] Filling description...")
                        await desc_elem.fill(description)
                        await page.wait_for_timeout(1000)
                        desc_filled = True

                    # 8. Fill Salary / Bill Rate
                    rate_selector = "input[name='salary'], input[name='rate'], #salary-input, #jobMinimumPayInput"
                    rate_elem = page.locator(rate_selector).first
                    if bill_rate and not rate_filled and await rate_elem.is_visible():
                        logger.info(f"[{self.name} - Indeed] Filling max rate: {bill_rate}")
                        await rate_elem.fill(str(bill_rate))
                        rate_filled = True

                    # 9. Check if final Publish / Submit is visible
                    publish_selector = "button:has-text('Publish'), button:has-text('Submit'), button:has-text('Post Job'), button:has-text('Post job')"
                    publish_btn = page.locator(publish_selector).first
                    if await publish_btn.is_visible():
                        logger.info(f"[{self.name} - Indeed] Publish button found! Clicking Publish...")
                        await publish_btn.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await page.wait_for_timeout(5000)
                        logger.info(f"[{self.name} - Indeed] Successfully clicked publish.")
                        break

                    # 10. Otherwise, click Continue/Next to go to next page
                    continue_selector = "button[type='submit'], button:has-text('Continue'), button:has-text('Next'), button:has-text('Save & Continue')"
                    continue_btn = page.locator(continue_selector).first
                    if await continue_btn.is_visible():
                        logger.info(f"[{self.name} - Indeed] Clicking Continue/Next...")
                        await continue_btn.click()
                        await page.wait_for_load_state("domcontentloaded")
                    else:
                        logger.warning(f"[{self.name} - Indeed] No Continue or Publish button found on page {step}. Breaking loop.")
                        break
                
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

