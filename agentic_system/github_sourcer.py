import requests
import json
import base64
import time

def get_github_commit_email(username: str, headers: dict) -> str | None:
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
        print(f"Error scraping commit email for {username}: {e}")
    return None

def pull_github_candidates(max_candidates=5):
    print("🔍 Searching GitHub for developers 'open to work'...")
    # Search GitHub for users with "open to work" in their READMEs
    search_url = "https://api.github.com/search/users?q=%22open%20to%20work%22%20in:readme%20type:user&per_page=10"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to query GitHub: {response.text}")
        return

    users = response.json().get("items", [])
    count = 0
    
    for user in users:
        if count >= max_candidates:
            break
            
        username = user["login"]
        print(f"\n👤 Analyzing user: {username}...")
        
        # 1. Fetch user details to get name and email
        user_details = requests.get(f"https://api.github.com/users/{username}", headers=headers).json()
        full_name = user_details.get("name") or username
        email = user_details.get("email")
        if not email:
            email = get_github_commit_email(username, headers)
            if email:
                print(f"   📧 Found email in public commits for {username}: {email}")
            else:
                email = f"{username}@github.candidate.local"
        
        # 2. Fetch their README
        readme_url = f"https://api.github.com/repos/{username}/{username}/readme"
        readme_res = requests.get(readme_url, headers=headers)
        
        resume_text = f"GitHub Profile: {user['html_url']}\n\n"
        if readme_res.status_code == 200:
            try:
                content_b64 = readme_res.json().get("content", "")
                readme_text = base64.b64decode(content_b64).decode("utf-8")
                resume_text += readme_text
            except Exception as e:
                resume_text += "Error decoding README."
        else:
            resume_text += "No detailed README found, but marked as open to work."
            
        # 3. Create a mock PDF or text file submission to the Orchestrator
        print(f"   Uploading {full_name} to Westley ATS...")
        
        upload_url = "https://westley-agents.kindtree-748f04e0.centralus.azurecontainerapps.io/ingest-resume-file"
        
        files = {
            "file": (f"{username}_resume.txt", resume_text.encode('utf-8'), "text/plain")
        }
        data = {
            "name": full_name,
            "email": email,
            "phone": "555-019-8372" # Mock phone since GitHub rarely shares them
        }
        
        upload_res = requests.post(upload_url, data=data, files=files)
        if upload_res.status_code == 200:
            print(f"   ✅ Successfully ingested {full_name} into the ATS!")
            count += 1
        else:
            print(f"   ❌ Failed to ingest: {upload_res.status_code} - {upload_res.text}")
            
        time.sleep(1) # Prevent rate limiting

if __name__ == "__main__":
    pull_github_candidates(20)
