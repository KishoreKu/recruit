import asyncio
import httpx
from dotenv import load_dotenv
import os

load_dotenv("server/.env")

async def test():
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT").rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_KEY")
    url = f"{endpoint}/openai/deployments/gpt-5-mini/chat/completions?api-version=2024-08-01-preview"
    
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.7,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        print("Status:", resp.status_code)
        print("Body:", resp.text)

asyncio.run(test())
