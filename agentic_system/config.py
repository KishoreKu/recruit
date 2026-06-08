# ============================================================
#  Shared Configuration — reads from .env
# ============================================================
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../server/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Database ────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://localhost:5432/westleyresource"

    # ─── Gemini ──────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBED_MODEL: str = "models/text-embedding-004"
    GEMINI_EMBED_DIMENSIONS: int = 768

    # ─── Azure OpenAI ────────────────────────────────────────
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-5-mini"
    AZURE_OPENAI_EMBED_DEPLOYMENT: str = "text-embedding-3-small"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # ─── Microsoft Graph (email) ─────────────────────────────
    MS_TENANT_ID: str = ""
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_SENDER: str = "support@westleyresource.com"

    # ─── MCP Server ports ────────────────────────────────────
    ATS_MCP_PORT: int = 8100
    VMS_MCP_PORT: int = 8101
    COMM_MCP_PORT: int = 8102
    ORCHESTRATOR_PORT: int = 8200

    # ─── Agent behaviour ─────────────────────────────────────
    MAX_TASK_ATTEMPTS: int = 3          # circuit breaker threshold
    VMS_POLL_INTERVAL_SECONDS: int = 300  # 5 minutes
    MATCH_TOP_K: int = 5                # top K candidates per job
    OUTREACH_WAIT_HOURS: int = 48       # wait for RTR reply

    # ─── Job Scrapers ─────────────────────────────────────────────────────────
    ADZUNA_APP_ID: str = ""           # https://developer.adzuna.com/
    ADZUNA_APP_KEY: str = ""
    RAPIDAPI_KEY: str = ""            # https://rapidapi.com → JSearch
    USAJOBS_API_KEY: str = ""         # https://developer.usajobs.gov/
    USAJOBS_EMAIL: str = "recruiter@westleyresource.com"

    # ─── Twilio (SMS fallback) ────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
