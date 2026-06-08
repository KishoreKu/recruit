"""
job_scrapers.py
─────────────────────────────────────────────────────────────────────────────
Multi-source IT job scraper.

Sources:
  1. Adzuna API        — https://developer.adzuna.com/
  2. JSearch (RapidAPI) — https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
  3. USAJobs.gov       — https://developer.usajobs.gov/ (no key needed)

All results are normalised into a common JobListing dict so the VMS MCP
server can insert them into the requisitions table without caring about
source format differences.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Optional
import httpx
from loguru import logger


# ── Normalised output format ──────────────────────────────────────────────────

@dataclass
class JobListing:
    title: str
    client_company: str
    description: str
    location: str
    skills_required: list[str]
    job_type: str = "Contract"
    bill_rate_max: Optional[float] = None
    vms_platform: str = "scraped"
    external_id: str = ""          # source-specific ID for deduplication
    source: str = ""


# ── Skill extraction from free-text ──────────────────────────────────────────

IT_SKILLS = [
    # Cloud
    "AWS","Azure","GCP","Google Cloud","Terraform","CloudFormation","Ansible",
    "Kubernetes","Docker","Helm","Istio","Pulumi","CDK",
    # Languages
    "Python","Java","Go","Golang","Rust","C#","C++","TypeScript","JavaScript",
    "Scala","Kotlin","R","Ruby","PHP","Swift","Bash","PowerShell","SQL",
    # Data
    "Spark","PySpark","Databricks","Kafka","Airflow","dbt","Snowflake",
    "Redshift","BigQuery","Delta Lake","Hadoop","Hive","Flink",
    "Pandas","NumPy","Tableau","Power BI","Looker",
    # ML/AI
    "Machine Learning","Deep Learning","NLP","TensorFlow","PyTorch","scikit-learn",
    "MLflow","SageMaker","Vertex AI","LangChain","OpenAI","Gemini",
    # DevOps / Platform
    "CI/CD","Jenkins","GitHub Actions","GitLab CI","ArgoCD","Spinnaker",
    "Prometheus","Grafana","Datadog","Splunk","ELK","New Relic",
    # Web / Backend
    "React","Angular","Vue","Next.js","FastAPI","Django","Flask","Spring Boot",
    "Node.js","Express","GraphQL","REST API","gRPC","PostgreSQL","MySQL",
    "MongoDB","Redis","Elasticsearch","Cassandra","DynamoDB",
    # Security / Compliance
    "Cybersecurity","SIEM","Zero Trust","SOC","IAM","OAuth","SAML","FedRAMP",
    "NIST","ISO 27001","PCI-DSS","HIPAA",
    # Other IT
    "Agile","Scrum","JIRA","Confluence","Git","Linux","Windows Server",
    "Active Directory","ServiceNow","SAP","Salesforce","VMware",
]

_SKILL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in IT_SKILLS) + r")\b",
    re.IGNORECASE,
)

def extract_skills(text: str) -> list[str]:
    found = {m.group(0).title() for m in _SKILL_PATTERN.finditer(text)}
    return sorted(found)


def parse_rate(text: str) -> Optional[float]:
    """Try to extract an hourly bill rate from salary/rate text."""
    if not text:
        return None
    # Look for patterns like "$80/hr", "$75-$95/hr", "80 per hour"
    m = re.search(r"\$?(\d{2,3}(?:\.\d+)?)\s*(?:[-–]\s*\$?(\d{2,3}(?:\.\d+)?))?\s*(?:/hr|per hour|hourly)", text, re.IGNORECASE)
    if m:
        low = float(m.group(1))
        high = float(m.group(2)) if m.group(2) else low
        return round((low + high) / 2, 2)
    return None


def infer_job_type(text: str) -> str:
    t = text.lower()
    if "contract to hire" in t or "contract-to-hire" in t or "c2h" in t:
        return "Contract-to-Hire"
    if "contract" in t or "1099" in t or "c2c" in t or "corp to corp" in t:
        return "Contract"
    if "full time" in t or "full-time" in t or "permanent" in t:
        return "Full-Time"
    if "part time" in t or "part-time" in t:
        return "Part-Time"
    return "Contract"


# ── Search keywords for IT recruiting ────────────────────────────────────────

IT_QUERIES = [
    "software engineer contract",
    "cloud engineer AWS contract",
    "data engineer contract",
    "devops engineer contract",
    "full stack developer contract",
    "python developer contract",
    "cybersecurity analyst contract",
    "machine learning engineer contract",
]


# ── 1. Adzuna ─────────────────────────────────────────────────────────────────

async def scrape_adzuna(
    app_id: str,
    app_key: str,
    country: str = "us",
    results_per_query: int = 10,
) -> list[JobListing]:
    """Fetch IT contract jobs from the Adzuna API."""
    listings: list[JobListing] = []
    base = f"https://api.adzuna.com/v1/api/jobs/{country}/search"

    async with httpx.AsyncClient(timeout=20) as client:
        for query in IT_QUERIES[:4]:   # limit to 4 queries to stay under free quota
            try:
                resp = await client.get(
                    f"{base}/1",
                    params={
                        "app_id": app_id,
                        "app_key": app_key,
                        "what": query,
                        "content-type": "application/json",
                        "results_per_page": results_per_query,
                        "sort_by": "date",
                        "full_time": 0,  # include all types
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for job in data.get("results", []):
                    desc = job.get("description", "")
                    title = job.get("title", "")
                    company = job.get("company", {}).get("display_name", "Unknown")
                    location = job.get("location", {}).get("display_name", "")
                    salary_text = f"${job.get('salary_min','')}-${job.get('salary_max','')}/yr" if job.get("salary_min") else ""
                    
                    # Convert annual salary to rough hourly if available
                    bill_rate = None
                    if job.get("salary_max"):
                        annual = float(job["salary_max"])
                        if annual > 1000:  # it's annual, not hourly
                            bill_rate = round(annual / 2080, 2)

                    listings.append(JobListing(
                        title=title,
                        client_company=company,
                        description=desc,
                        location=location,
                        skills_required=extract_skills(f"{title} {desc}"),
                        job_type=infer_job_type(f"{title} {desc}"),
                        bill_rate_max=bill_rate,
                        vms_platform="Adzuna",
                        external_id=str(job.get("id", "")),
                        source="adzuna",
                    ))

                await asyncio.sleep(0.5)  # be polite to the API

            except Exception as e:
                logger.warning(f"[Adzuna] Query '{query}' failed: {e}")

    logger.info(f"[Adzuna] Scraped {len(listings)} listings.")
    return listings


# ── 2. JSearch (RapidAPI) ─────────────────────────────────────────────────────

async def scrape_jsearch(
    rapid_api_key: str,
    results_per_query: int = 5,
) -> list[JobListing]:
    """Fetch IT contract jobs from JSearch (powered by Google Jobs + Indeed)."""
    listings: list[JobListing] = []
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        for query in IT_QUERIES[:4]:
            try:
                resp = await client.get(
                    url,
                    headers=headers,
                    params={
                        "query": query,
                        "page": "1",
                        "num_pages": "1",
                        "employment_types": "CONTRACTOR",
                        "date_posted": "week",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for job in data.get("data", [])[:results_per_query]:
                    desc = job.get("job_description", "")
                    title = job.get("job_title", "")
                    company = job.get("employer_name", "Unknown")
                    city = job.get("job_city", "")
                    state = job.get("job_state", "")
                    location = f"{city}, {state}".strip(", ") or job.get("job_country", "")
                    if job.get("job_is_remote"):
                        location = "Remote" if not location else f"{location} (Remote)"

                    salary_text = ""
                    if job.get("job_min_salary"):
                        salary_text = f"${job['job_min_salary']}-${job.get('job_max_salary','')}"
                    bill_rate = parse_rate(salary_text) or (
                        round(float(job["job_max_salary"]) / 2080, 2)
                        if job.get("job_max_salary") and float(job.get("job_max_salary", 0)) > 500
                        else None
                    )

                    listings.append(JobListing(
                        title=title,
                        client_company=company,
                        description=desc[:2000],   # truncate very long descriptions
                        location=location,
                        skills_required=extract_skills(f"{title} {desc}") or extract_skills(
                            " ".join(job.get("job_required_skills", []) or [])
                        ),
                        job_type=infer_job_type(job.get("job_employment_type", "") + " " + title),
                        bill_rate_max=bill_rate,
                        vms_platform="JSearch",
                        external_id=job.get("job_id", ""),
                        source="jsearch",
                    ))

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"[JSearch] Query '{query}' failed: {e}")

    logger.info(f"[JSearch] Scraped {len(listings)} listings.")
    return listings


# ── 3. USAJobs.gov ────────────────────────────────────────────────────────────

async def scrape_usajobs(
    api_key: str = "",
    user_agent_email: str = "recruiter@westleyresource.com",
    results_per_query: int = 10,
) -> list[JobListing]:
    """
    Fetch IT jobs from USAJobs.gov.
    Requires a free API key from https://developer.usajobs.gov/
    Sign up takes ~1 minute — key is emailed instantly.
    """
    if not api_key:
        logger.info("[USAJobs] Skipped — USAJOBS_API_KEY not set. Get a free key at https://developer.usajobs.gov/")
        return []

    listings: list[JobListing] = []
    url = "https://data.usajobs.gov/api/search"
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": user_agent_email,
        "Authorization-Key": api_key,
    }

    usa_queries = [
        "Information Technology",
        "Software Engineer",
        "Cloud Engineer",
        "Data Engineer",
        "Cybersecurity",
    ]


    async with httpx.AsyncClient(timeout=20) as client:
        for query in usa_queries[:3]:
            try:
                resp = await client.get(
                    url,
                    headers=headers,
                    params={
                        "Keyword": query,
                        "ResultsPerPage": results_per_query,
                        "SortField": "OpenDate",
                        "SortDirection": "Desc",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("SearchResult", {}).get("SearchResultItems", [])
                for item in items:
                    pos = item.get("MatchedObjectDescriptor", {})
                    title = pos.get("PositionTitle", "")
                    company = pos.get("DepartmentName", "") or pos.get("OrganizationName", "Unknown")
                    desc = pos.get("UserArea", {}).get("Details", {}).get("JobSummary", "")
                    location_list = pos.get("PositionLocation", [{}])
                    location = location_list[0].get("LocationName", "") if location_list else ""
                    
                    # Salary
                    salary_range = pos.get("PositionRemuneration", [{}])
                    bill_rate = None
                    if salary_range:
                        max_range = salary_range[0].get("MaximumRange", "")
                        rate_interval = salary_range[0].get("RateIntervalCode", "")
                        if max_range:
                            val = float(max_range)
                            if rate_interval == "PA":  # Per Annum
                                bill_rate = round(val / 2080, 2)
                            elif rate_interval == "PH":  # Per Hour
                                bill_rate = round(val, 2)

                    listings.append(JobListing(
                        title=title,
                        client_company=company,
                        description=desc[:2000],
                        location=location,
                        skills_required=extract_skills(f"{title} {desc}"),
                        job_type="Contract",
                        bill_rate_max=bill_rate,
                        vms_platform="USAJobs",
                        external_id=pos.get("PositionID", ""),
                        source="usajobs",
                    ))

                await asyncio.sleep(0.3)

            except Exception as e:
                logger.warning(f"[USAJobs] Query '{query}' failed: {e}")

    logger.info(f"[USAJobs] Scraped {len(listings)} listings.")
    return listings


# ── Orchestrator: run all scrapers ────────────────────────────────────────────

async def scrape_all_sources() -> list[JobListing]:
    """
    Run all enabled scrapers concurrently and deduplicate by external_id.
    Reads API keys from environment variables.
    """
    tasks = []

    adzuna_id  = os.getenv("ADZUNA_APP_ID", "")
    adzuna_key = os.getenv("ADZUNA_APP_KEY", "")
    rapid_key  = os.getenv("RAPIDAPI_KEY", "")
    usajobs_key   = os.getenv("USAJOBS_API_KEY", "")
    usajobs_email = os.getenv("USAJOBS_EMAIL", "recruiter@westleyresource.com")

    if adzuna_id and adzuna_key:
        tasks.append(scrape_adzuna(adzuna_id, adzuna_key))
        logger.info("[Scrapers] Adzuna enabled.")
    else:
        logger.info("[Scrapers] Adzuna skipped — ADZUNA_APP_ID / ADZUNA_APP_KEY not set.")

    if rapid_key:
        tasks.append(scrape_jsearch(rapid_key))
        logger.info("[Scrapers] JSearch enabled.")
    else:
        logger.info("[Scrapers] JSearch skipped — RAPIDAPI_KEY not set.")

    if usajobs_key:
        tasks.append(scrape_usajobs(api_key=usajobs_key, user_agent_email=usajobs_email))
        logger.info("[Scrapers] USAJobs enabled.")
    else:
        logger.info("[Scrapers] USAJobs skipped — USAJOBS_API_KEY not set. Get free key at https://developer.usajobs.gov/")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_listings: list[JobListing] = []
    seen_ids: set[str] = set()

    for batch in results:
        if isinstance(batch, Exception):
            logger.error(f"[Scrapers] A scraper failed: {batch}")
            continue
        for listing in batch:
            key = f"{listing.source}:{listing.external_id}" if listing.external_id else f"{listing.title}:{listing.client_company}"
            if key not in seen_ids:
                seen_ids.add(key)
                all_listings.append(listing)

    logger.info(f"[Scrapers] Total unique listings: {len(all_listings)}")
    return all_listings
