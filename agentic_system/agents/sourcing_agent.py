"""
agents/sourcing_agent.py
─────────────────────────────────────────────────────────────────────────────
Sourcing Agent — "The Talent Scout"
Handles: Periodic fetching of candidates from external sources (e.g., GitHub).
  1. Runs daily.
  2. Fetches candidates, avoiding duplicates.
  3. Enqueues ingest_resume tasks for ATS Agent.
─────────────────────────────────────────────────────────────────────────────
"""
import sys
import asyncio
import json
import base64
import requests
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from agents.base_agent import BaseAgent
from config import get_settings
from db import get_pool

settings = get_settings()

class SourcingAgent(BaseAgent):
    name = "sourcing-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """Not used by SourcingAgent; it only pushes tasks, doesn't consume them."""
        pass

    async def run_polling_loop(self) -> None:
        """
        Periodic sourcing loop — pulls candidates every 24 hours.
        """
        # Pull 10 candidates every 24 hours (86400 seconds)
        interval = 86400 
        logger.info(f"[Sourcing Agent] Starting daily sourcing loop (every {interval}s).")
        
        while True:
            try:
                await self.pull_github_candidates(max_candidates=10)
            except Exception as e:
                logger.error(f"[Sourcing Agent] Error during sourcing: {e}")
            
            await asyncio.sleep(interval)

    async def pull_github_candidates(self, max_candidates=10):
        logger.info("[Sourcing Agent] 🔍 Searching GitHub for developers 'open to work'...")
        
        # Pick a random page between 1 and 50 to avoid getting the same candidates every day
        page = random.randint(1, 50)
        search_url = f"https://api.github.com/search/users?q=%22open%20to%20work%22%20in:readme%20type:user&per_page=10&page={page}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"[Sourcing Agent] ❌ Failed to query GitHub: {response.text}")
            return

        users = response.json().get("items", [])
        count = 0
        
        for user in users:
            if count >= max_candidates:
                break
                
            username = user["login"]
            logger.info(f"[Sourcing Agent] 👤 Analyzing user: {username}...")
            
            # 1. Fetch user details to get name and email
            user_details = requests.get(f"https://api.github.com/users/{username}", headers=headers).json()
            full_name = user_details.get("name") or username
            email = user_details.get("email") or f"{username}@github.candidate.local"
            
            # 2. Check if candidate already exists in DB to prevent duplicates
            pool = await get_pool()
            async with pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                if existing:
                    logger.info(f"[Sourcing Agent] Skipping {full_name} - already exists in system.")
                    continue
            
            # 3. Fetch their README
            readme_url = f"https://api.github.com/repos/{username}/{username}/readme"
            readme_res = requests.get(readme_url, headers=headers)
            
            resume_text = f"GitHub Profile: {user['html_url']}\n\n"
            if readme_res.status_code == 200:
                try:
                    content_b64 = readme_res.json().get("content", "")
                    readme_text = base64.b64decode(content_b64).decode("utf-8")
                    resume_text += readme_text
                except Exception:
                    resume_text += "Error decoding README."
            else:
                resume_text += "No detailed README found, but marked as open to work."
                
            # 4. Enqueue ingest task (just like submitting through the web form)
            logger.info(f"[Sourcing Agent] Enqueuing ATS ingest for {full_name}...")
            await self.enqueue_task("ingest_resume", {
                "full_name": full_name,
                "email": email,
                "phone": "555-019-8372", # Mock phone
                "resume_text": resume_text
            })
            
            count += 1
            await asyncio.sleep(1) # Prevent rate limiting

    async def run(self) -> None:
        """Run the daily polling loop."""
        await self.run_polling_loop()

async def main():
    agent = SourcingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
