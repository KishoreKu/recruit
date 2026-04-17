LinkedIn automation (Playwright)

This folder contains a simple script to automate LinkedIn "Easy Apply" applications.

Setup
1. Create and activate a Python venv (recommended).
2. Install dependencies: pip install -r requirements.txt
3. Install Playwright browsers: python -m playwright install
4. Create a .env file with at least LINKEDIN_EMAIL and LINKEDIN_PASSWORD. Optionally set RESUME_PATH, KEYWORDS, LOCATION.

Usage
python scripts/linkedin_apply.py --keywords "software engineer" --location "San Francisco, CA"

Notes & safety
- Use responsibly and review each application; LinkedIn terms may restrict automation.
- This script is a best-effort starter and will not handle complex multi-step forms.
- Keep credentials out of source control (.gitignore includes .env).
