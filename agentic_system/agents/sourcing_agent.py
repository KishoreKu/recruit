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
            await self._safe_source("GitHub", self.pull_github_candidates, max_candidates=5)
            
            # 2. Stack Overflow Sourcing
            await self._safe_source("Stack Overflow", self.pull_stackoverflow_candidates, max_candidates=5)
                
            # 3. Hacker News Sourcing
            await self._safe_source("Hacker News", self.pull_hackernews_candidates, max_candidates=5)
            
            # 4. Reddit Sourcing
            await self._safe_source("Reddit", self.pull_reddit_candidates, max_candidates=3)
            
            # 5. GitLab Sourcing
            await self._safe_source("GitLab", self.pull_gitlab_candidates, max_candidates=3)
            
            # 6. Bitbucket Sourcing
            await self._safe_source("Bitbucket", self.pull_bitbucket_candidates, max_candidates=3)
            
            # 7. LinkedIn Sourcing
            await self._safe_source("LinkedIn", self.pull_linkedin_candidates, max_candidates=3)
            
            # 8. USAJobs Sourcing
            await self._safe_source("USAJobs", self.pull_usajobs_candidates, max_candidates=3)
            
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

    async def _safe_source(self, name: str, method, **kwargs):
        """Helper to run a candidate sync source safely without crashing the main loop."""
        try:
            logger.info(f"[Sourcing Agent] 🚀 Starting candidate sync from {name}...")
            await method(**kwargs)
            logger.success(f"[Sourcing Agent] Completed candidate sync from {name}")
        except Exception as e:
            logger.error(f"[Sourcing Agent] Error during {name} candidate sync: {e}")

    async def pull_reddit_candidates(self, max_candidates=3):
        logger.info("[Sourcing Agent] 🔍 Searching Reddit r/forhire and r/jobbit...")
        # Reddit requires a custom User-Agent to prevent 429 Too Many Requests errors
        headers = {"User-Agent": "Mozilla/5.0 WestleyRecruiterAgent/1.0 (contact: support@westleyresource.com)"}
        
        for sub in ["forhire", "jobbit"]:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=15"
            try:
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    logger.warning(f"[Sourcing Agent] Reddit r/{sub} returned HTTP {response.status_code}")
                    continue
                    
                posts = response.json().get("data", {}).get("children", [])
                count = 0
                pool = await get_pool()
                
                for post in posts:
                    if count >= max_candidates:
                        break
                        
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    author = post_data.get("author", "")
                    
                    # Look for job seekers (titles containing "[for hire]")
                    if not any(k in title.lower() for k in ["[for hire]", "for hire", "seeking"]):
                        continue
                        
                    if len(selftext) < 150 or not author:
                        continue
                        
                    # Parse using Gemini (reusing HN comment parsing schema)
                    parsed_data = await self.parse_hn_comment_with_gemini(selftext)
                    if not parsed_data:
                        continue
                        
                    email = parsed_data.get("email") or f"{author}@reddit.candidate.local"
                    full_name = parsed_data.get("full_name") or author
                    
                    # Check duplicates
                    async with pool.acquire() as conn:
                        existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                        if existing:
                            continue
                            
                    resume_text = f"""REDDIT CANDIDATE PROFILE (r/{sub}):
Name: {full_name}
Reddit Author: u/{author}
Email: {email}
Phone: {parsed_data.get('phone') or 'Not provided'}
Location: {parsed_data.get('location') or 'Not provided'}
Title: {parsed_data.get('current_title') or 'Developer'}
Skills Sourced: {', '.join(parsed_data.get('skills', [])) if parsed_data.get('skills') else 'General Tech'}

ORIGINAL REDDIT POST:
{selftext}
"""
                    
                    logger.info(f"[Sourcing Agent] Enqueuing Reddit candidate: {full_name} ({email})...")
                    await self.enqueue_task("ingest_resume", {
                        "full_name": full_name,
                        "email": email,
                        "phone": parsed_data.get("phone") or "555-019-8372",
                        "resume_text": resume_text
                    })
                    count += 1
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[Sourcing Agent] Error parsing Reddit r/{sub}: {e}")

    async def pull_gitlab_candidates(self, max_candidates=3):
        logger.info("[Sourcing Agent] 🔍 Searching GitLab public user directory...")
        headers = {"Accept": "application/json"}
        url = "https://gitlab.com/api/v4/users?active=true&per_page=10"
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"[Sourcing Agent] ❌ GitLab API failed: {response.text}")
            return
            
        users = response.json()
        count = 0
        pool = await get_pool()
        
        for user in users:
            if count >= max_candidates:
                break
                
            username = user.get("username")
            full_name = user.get("name") or username
            email = user.get("public_email") or f"{username}@gitlab.candidate.local"
            
            # Check duplicates
            async with pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                if existing:
                    continue
            
            resume_text = f"""GITLAB PROFILE RESUME:
Name: {full_name}
Username: {username}
GitLab Profile: {user.get('web_url')}
Avatar Link: {user.get('avatar_url')}

Profile sourced from GitLab public search index.
"""
            
            logger.info(f"[Sourcing Agent] Enqueuing GitLab candidate: {full_name}...")
            await self.enqueue_task("ingest_resume", {
                "full_name": full_name,
                "email": email,
                "phone": "555-019-8372",
                "resume_text": resume_text
            })
            count += 1
            await asyncio.sleep(1)

    async def pull_bitbucket_candidates(self, max_candidates=3):
        logger.info("[Sourcing Agent] 🔍 Searching Bitbucket public repository commit activity...")
        pool = await get_pool()
        count = 0
        
        # Sourcing contributors from recent commits in public workspaces
        url = "https://api.bitbucket.org/2.0/repositories?role=member&pagelen=3"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                repos = response.json().get("values", [])
                for repo in repos:
                    if count >= max_candidates:
                        break
                    slug = repo.get("full_name")
                    commit_url = f"https://api.bitbucket.org/2.0/repositories/{slug}/commits?pagelen=5"
                    commit_res = requests.get(commit_url)
                    if commit_res.status_code == 200:
                        commits = commit_res.json().get("values", [])
                        for commit in commits:
                            author = commit.get("author", {})
                            raw_author = author.get("raw", "")
                            # Standard format: "Name <email@address.com>"
                            if "<" in raw_author and ">" in raw_author:
                                full_name, email = raw_author.split("<", 1)
                                full_name = full_name.strip()
                                email = email.replace(">", "").strip()
                                
                                if "noreply" in email or not email:
                                    continue
                                    
                                # Check duplicates
                                async with pool.acquire() as conn:
                                    existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                                    if existing:
                                        continue
                                
                                resume_text = f"""BITBUCKET CONTRIBUTOR RESUME:
Name: {full_name}
Email: {email}
Contributing to Bitbucket Repository: https://bitbucket.org/{slug}
Commit Message Sample: {commit.get('message', '').strip()}

Profile compiled from public Bitbucket VCS commit activity.
"""
                                
                                logger.info(f"[Sourcing Agent] Enqueuing Bitbucket candidate: {full_name} ({email})...")
                                await self.enqueue_task("ingest_resume", {
                                    "full_name": full_name,
                                    "email": email,
                                    "phone": "555-019-8372",
                                    "resume_text": resume_text
                                })
                                count += 1
                                break
        except Exception as e:
            logger.error(f"[Sourcing Agent] Bitbucket API error: {e}")

    async def pull_linkedin_candidates(self, max_candidates=3):
        logger.info("[Sourcing Agent] 🔍 Searching LinkedIn profiles...")
        pool = await get_pool()
        
        if settings.RAPIDAPI_KEY:
            url = "https://linkedin-data-api.p.rapidapi.com/search-profiles"
            headers = {
                "x-rapidapi-key": settings.RAPIDAPI_KEY,
                "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com"
            }
            params = {"query": "Software Engineer Open To Work", "limit": "10"}
            try:
                res = requests.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    profiles = res.json().get("items", [])
                    count = 0
                    for prof in profiles:
                        if count >= max_candidates:
                            break
                        full_name = prof.get("fullName") or (prof.get("firstName", "") + " " + prof.get("lastName", ""))
                        username = prof.get("username") or full_name.replace(" ", "").lower()
                        email = prof.get("email") or f"{username}@linkedin.candidate.local"
                        
                        async with pool.acquire() as conn:
                            existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", email)
                            if existing:
                                continue
                                
                        resume_text = f"""LINKEDIN PROFILE RESUME:
Name: {full_name}
Headline: {prof.get('headline', 'Software Engineer')}
Location: {prof.get('location', 'United States')}
Email: {email}
LinkedIn URL: https://linkedin.com/in/{username}

Summary:
{prof.get('summary', 'Not provided')}

Work History Sourced from LinkedIn Profile.
"""
                        logger.info(f"[Sourcing Agent] Enqueuing LinkedIn candidate: {full_name}...")
                        await self.enqueue_task("ingest_resume", {
                            "full_name": full_name,
                            "email": email,
                            "phone": "555-019-8372",
                            "resume_text": resume_text
                        })
                        count += 1
                    return
            except Exception as e:
                logger.error(f"[Sourcing Agent] RapidAPI LinkedIn search failed: {e}")
                
        # Fallback simulation if no API Key is set
        logger.warning("[Sourcing Agent] RAPIDAPI_KEY not configured. Simulating LinkedIn candidate ingestion...")
        mock_candidates = [
            {"name": "Alex Mercer", "title": "Senior Cloud Infrastructure Architect", "skills": "AWS, Terraform, Kubernetes, Go", "email": "alex.mercer@linkedin.candidate.local"},
            {"name": "Elena Rostova", "title": "Lead React & Frontend Engineer", "skills": "React, TypeScript, Redux, TailwindCSS", "email": "elena.rostova@linkedin.candidate.local"}
        ]
        
        count = 0
        for cand in mock_candidates:
            if count >= max_candidates:
                break
            async with pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", cand["email"])
                if existing:
                    continue
            
            resume_text = f"""LINKEDIN PROFILE RESUME (SIMULATED):
Name: {cand['name']}
Headline: {cand['title']}
Skills: {cand['skills']}
Email: {cand['email']}
LinkedIn URL: https://linkedin.com/in/{cand['name'].replace(' ', '').lower()}

Summary:
Experienced tech leader seeking new opportunities. Proven track record in scaling cloud architectures.
"""
            logger.info(f"[Sourcing Agent] Enqueuing simulated LinkedIn candidate: {cand['name']}...")
            await self.enqueue_task("ingest_resume", {
                "full_name": cand["name"],
                "email": cand["email"],
                "phone": "555-019-8372",
                "resume_text": resume_text
            })
            count += 1

    async def pull_usajobs_candidates(self, max_candidates=3):
        logger.info("[Sourcing Agent] 🔍 Sourcing USAJobs federal profiles...")
        pool = await get_pool()
        
        if settings.USAJOBS_API_KEY:
            # Query federal public search endpoint if available
            pass
            
        # Fallback simulation
        logger.warning("[Sourcing Agent] USAJOBS_API_KEY not configured. Simulating Federal Candidate ingestion...")
        mock_usajobs = [
            {"name": "Command Sgt. Frank Castle", "title": "Senior Cybersecurity Specialist (GS-14)", "skills": "NIST, SIEM, Incident Response, Splunk, CISSP", "clearance": "Top Secret / SCI", "email": "frank.castle@usajobs.candidate.local"},
            {"name": "Major Samantha Carter", "title": "Lead Software Engineer (GS-13)", "skills": "C++, Python, Aerospace Systems, Embedded C", "clearance": "Secret", "email": "samantha.carter@usajobs.candidate.local"}
        ]
        
        count = 0
        for cand in mock_usajobs:
            if count >= max_candidates:
                break
            async with pool.acquire() as conn:
                existing = await conn.fetchrow("SELECT id FROM candidates WHERE email = $1", cand["email"])
                if existing:
                    continue
            
            resume_text = f"""USAJOBS FEDERAL RESUME (SIMULATED):
Name: {cand['name']}
Current Grade: {cand['title']}
Security Clearance: {cand['clearance']}
Key Tech Skills: {cand['skills']}
Email: {cand['email']}

Professional History:
10+ years serving federal agencies in advanced computing roles.
Expertise in secure systems integration and defense networks compliance.
"""
            logger.info(f"[Sourcing Agent] Enqueuing simulated USAJobs candidate: {cand['name']}...")
            await self.enqueue_task("ingest_resume", {
                "full_name": cand["name"],
                "email": cand["email"],
                "phone": "555-019-8372",
                "resume_text": resume_text
            })
            count += 1

    async def run(self) -> None:
        """Run the daily polling loop."""
        await self.run_polling_loop()

async def main():
    agent = SourcingAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
