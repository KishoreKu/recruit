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
from gemini_client import chat_completion
import re

settings = get_settings()

class SourcingAgent(BaseAgent):
    name = "sourcing-agent"

    async def run_task(self, task_id: str, payload: dict) -> None:
        """Not used by SourcingAgent; it only pushes tasks, doesn't consume them."""
        pass

    async def run_polling_loop(self) -> None:
        """
        Periodic sourcing loop — pulls candidates every 24 hours from multiple sources.
        """
        # Sourcing cycle every 24 hours (86400 seconds)
        interval = 86400 
        logger.info(f"[Sourcing Agent] Starting daily sourcing loop (every {interval}s).")
        
        while True:
            # 1. GitHub Sourcing
            try:
                await self.pull_github_candidates(max_candidates=5)
            except Exception as e:
                logger.error(f"[Sourcing Agent] Error during GitHub sourcing: {e}")
            
            # 2. Stack Overflow Sourcing
            try:
                await self.pull_stackoverflow_candidates(max_candidates=5)
            except Exception as e:
                logger.error(f"[Sourcing Agent] Error during Stack Overflow sourcing: {e}")
                
            # 3. Hacker News Sourcing
            try:
                await self.pull_hackernews_candidates(max_candidates=5)
            except Exception as e:
                logger.error(f"[Sourcing Agent] Error during Hacker News sourcing: {e}")
            
            await asyncio.sleep(interval)

    async def get_github_commit_email(self, username: str, headers: dict) -> str | None:
        """
        Scrapes the GitHub events log for public PushEvents and retrieves the author's real email.
        """
        try:
            url = f"https://api.github.com/users/{username}/events/public"
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                events = res.json()
                for event in events:
                    if event.get("type") == "PushEvent":
                        commits = event.get("payload", {}).get("commits", [])
                        for commit in commits:
                            email = commit.get("author", {}).get("email")
                            if email and "noreply" not in email and "@" in email:
                                return email
        except Exception as e:
            logger.error(f"[Sourcing Agent] Error scraping commit email for {username}: {e}")
        return None

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
            email = user_details.get("email")
            if not email:
                email = await self.get_github_commit_email(username, headers)
                if email:
                    logger.info(f"[Sourcing Agent] 📧 Found email in public commits for {username}: {email}")
                else:
                    email = f"{username}@github.candidate.local"
            
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

    async def pull_stackoverflow_candidates(self, max_candidates=5):
        logger.info("[Sourcing Agent] 🔍 Searching Stack Overflow for top developers...")
        headers = {"Accept": "application/json"}
        
        # Fetch top users from Stack Overflow
        url = "https://api.stackexchange.com/2.3/users?order=desc&sort=reputation&site=stackoverflow&per_page=10"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"[Sourcing Agent] ❌ Failed to query Stack Overflow: {response.text}")
            return
            
        users = response.json().get("items", [])
        count = 0
        pool = await get_pool()
        
        for user in users:
            if count >= max_candidates:
                break
                
            user_id = user["user_id"]
            display_name = user["display_name"]
            username = user.get("user_id") or display_name.replace(" ", "").lower()
            email = f"{username}@stackoverflow.candidate.local"
            
            # Check duplicates
            async with pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                if existing:
                    continue
            
            # Get user tags to find their skills
            tags_url = f"https://api.stackexchange.com/2.3/users/{user_id}/tags?site=stackoverflow&pagesize=5"
            tags_res = requests.get(tags_url, headers=headers)
            skills = []
            if tags_res.status_code == 200:
                skills = [t["name"] for t in tags_res.json().get("items", [])]
            
            location = user.get("location") or "Remote"
            website = user.get("website_url") or "Not provided"
            reputation = user.get("reputation", 0)
            
            resume_text = f"""STACK OVERFLOW PROFILE RESUME:
Name: {display_name}
Location: {location}
Website: {website}
Stack Overflow Reputation: {reputation}
Stack Overflow Link: {user.get('link')}

TOP STACK OVERFLOW SKILLS:
{', '.join(skills) if skills else "General Software Engineering"}

Bio details sourced from Stack Overflow public user ID {user_id}.
"""
            
            logger.info(f"[Sourcing Agent] Enqueuing Stack Overflow candidate: {display_name}...")
            await self.enqueue_task("ingest_resume", {
                "full_name": display_name,
                "email": email,
                "phone": "555-019-8372",
                "resume_text": resume_text
            })
            count += 1
            await asyncio.sleep(1)

    async def parse_hn_comment_with_gemini(self, text: str) -> dict:
        prompt = f"""
        You are a technical recruiting system. Analyze the following Hacker News job seeker posting.
        Extract the following fields in JSON format:
        - full_name: The candidate's name (guess from email/text if not explicit, default to "Unknown")
        - email: The candidate's email address (MUST extract if present)
        - phone: The candidate's phone number if present, else null
        - skills: A list of technical skills/languages/frameworks mentioned (e.g. ["Python", "React"])
        - location: The location/remote preferences
        - experience_years: Estimated years of experience as an integer, if not mentioned guess or set null
        - current_title: Standardized job title (e.g. "Senior Software Engineer")

        Output ONLY valid JSON, do not wrap in markdown ```json blocks.
        
        HN Posting text:
        \"\"\"{text}\"\"\"
        """
        try:
            res_text = await chat_completion(prompt, system="You are a JSON parser. Output only valid JSON.")
            # Clean possible markdown formatting
            res_text = res_text.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(res_text)
        except Exception as e:
            logger.error(f"Failed parsing HN comment with Gemini: {e}")
            return {}

    async def pull_hackernews_candidates(self, max_candidates=5):
        logger.info("[Sourcing Agent] 🔍 Searching Hacker News 'Who Wants to be Hired' monthly threads...")
        
        # 1. Search for the latest "Who wants to be hired" story
        search_url = "https://hn.algolia.com/api/v1/search?query=%22Who%20wants%20to%20be%20hired%22&tags=story&hitsPerPage=3"
        response = requests.get(search_url)
        if response.status_code != 200:
            logger.error(f"[Sourcing Agent] ❌ Failed to search Hacker News: {response.text}")
            return
            
        stories = response.json().get("hits", [])
        if not stories:
            logger.warning("[Sourcing Agent] No HN 'Who wants to be hired' threads found.")
            return
            
        # Get the latest story ID
        latest_story = stories[0]
        story_id = latest_story["objectID"]
        logger.info(f"[Sourcing Agent] Sourcing comments from thread: '{latest_story['title']}' (ID: {story_id})")
        
        # 2. Fetch the comments for this story
        thread_url = f"https://hn.algolia.com/api/v1/items/{story_id}"
        thread_response = requests.get(thread_url)
        if thread_response.status_code != 200:
            logger.error(f"[Sourcing Agent] ❌ Failed to fetch HN thread details: {thread_response.text}")
            return
            
        comments = thread_response.json().get("children", [])
        logger.info(f"[Sourcing Agent] Found {len(comments)} postings in this monthly thread.")
        
        count = 0
        pool = await get_pool()
        
        import html as html_lib
        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '\n', raw_html)
            return html_lib.unescape(cleantext)
            
        for comment in comments:
            if count >= max_candidates:
                break
                
            author = comment.get("author")
            if not author:
                continue
                
            raw_text = comment.get("text", "")
            if not raw_text or len(raw_text) < 100:
                continue
                
            clean_text = clean_html(raw_text)
            
            # 3. Ask Gemini to extract structured info
            parsed_data = await self.parse_hn_comment_with_gemini(clean_text)
            if not parsed_data:
                continue
                
            email = parsed_data.get("email")
            full_name = parsed_data.get("full_name") or author
            
            if not email:
                email = f"{author}@hn.candidate.local"
                
            # Check duplicate
            async with pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                if existing:
                    continue
                    
            resume_text = f"""HACKER NEWS CANDIDATE PROFILE:
Name: {full_name}
Username: {author}
Email: {email}
Phone: {parsed_data.get('phone') or 'Not provided'}
Location: {parsed_data.get('location') or 'Not provided'}
Standardized Title: {parsed_data.get('current_title') or 'Developer'}
Skills Sourced: {', '.join(parsed_data.get('skills', [])) if parsed_data.get('skills') else 'General Tech'}

ORIGINAL HN COMMENT POSTING:
{clean_text}
"""
            
            logger.info(f"[Sourcing Agent] Enqueuing HN candidate: {full_name} ({email})...")
            await self.enqueue_task("ingest_resume", {
                "full_name": full_name,
                "email": email,
                "phone": parsed_data.get("phone") or "555-019-8372",
                "resume_text": resume_text
            })
            count += 1
            await asyncio.sleep(2) # Throttle to respect Gemini rate limits

    async def run(self) -> None:
        """Run the daily polling loop."""
        await self.run_polling_loop()

async def main():
    agent = SourcingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
