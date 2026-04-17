#!/usr/bin/env python3
"""
LinkedIn Easy Apply automation (use responsibly).
Requires: python3, playwright, python-dotenv

Environment variables (or put in .env):
  LINKEDIN_EMAIL, LINKEDIN_PASSWORD, RESUME_PATH

Usage:
  python scripts/linkedin_apply.py --keywords "software engineer" --location "San Francisco, CA"
"""

import os
import time
import argparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
RESUME = os.getenv("RESUME_PATH")
HEADLESS = os.getenv("HEADLESS", "1") == "1"


def login(page):
    page.goto("https://www.linkedin.com/login")
    page.fill("input#username", EMAIL)
    page.fill("input#password", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def search_jobs(page, keywords, location):
    q = keywords.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}&f_LF=f_AL"
    page.goto(url)
    page.wait_for_load_state("networkidle")


def apply_to_visible_jobs(page):
    # Basic attempt: iterate visible job cards and try Easy Apply
    cards = page.query_selector_all("ul.jobs-search__results-list li")
    for idx, card in enumerate(cards, start=1):
        try:
            print(f"Processing card {idx}/{len(cards)}")
            card.click()
            page.wait_for_timeout(1000)
            # If an Easy Apply button is visible
            btn = page.query_selector("button.jobs-apply-button")
            if not btn:
                print("No Easy Apply button — skipping")
                continue
            btn.click()
            page.wait_for_timeout(1000)
            # Upload resume if an input exists
            file_input = page.query_selector("input[type='file']")
            if file_input and RESUME:
                try:
                    file_input.set_input_files(RESUME)
                    page.wait_for_timeout(500)
                except Exception as e:
                    print("Failed to upload resume:", e)
            # Attempt to find submit button
            submit = page.query_selector("button[aria-label*='Submit application']") or page.query_selector("button[aria-label*='Send']")
            if submit:
                submit.click()
                page.wait_for_timeout(1000)
                print("Application submitted (or attempted)")
            else:
                print("Complex flow detected — closing and saving for manual review")
                # Try to close modal
                close = page.query_selector("button[aria-label='Dismiss']") or page.query_selector("button[aria-label='Close']")
                if close:
                    close.click()
                page.wait_for_timeout(500)
        except Exception as e:
            print("Error processing card:", e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", default=os.getenv("KEYWORDS", "software engineer"))
    parser.add_argument("--location", default=os.getenv("LOCATION", "United States"))
    parser.add_argument("--headless", action="store_true", default=HEADLESS)
    args = parser.parse_args()

    if not EMAIL or not PASSWORD:
        print("Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in env or .env")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        login(page)
        search_jobs(page, args.keywords, args.location)
        page.wait_for_timeout(2000)
        apply_to_visible_jobs(page)
        browser.close()


if __name__ == "__main__":
    main()
