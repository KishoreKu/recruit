"""
gemini_client.py — Shared LLM client: chat completions + embeddings.
Supports Azure OpenAI (preferred) and falls back to Google Gemini.
"""
import httpx
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
import google.generativeai as genai
from config import get_settings
from loguru import logger

_initialised = False


def _ensure_init():
    global _initialised
    if not _initialised:
        settings = get_settings()
        # Initialize Gemini SDK only if no Azure OpenAI credentials are set
        if not (settings.AZURE_OPENAI_KEY and settings.AZURE_OPENAI_ENDPOINT):
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                logger.info("Configured Gemini SDK client.")
            else:
                logger.warning("No LLM keys configured (neither Azure OpenAI nor Gemini).")
        else:
            logger.info("Azure OpenAI credentials found. Bypassing Gemini SDK configuration.")
        _initialised = True


def get_chat_model():
    """Return a Gemini chat model instance (if using Gemini fallback)."""
    _ensure_init()
    settings = get_settings()
    return genai.GenerativeModel(model_name=settings.GEMINI_CHAT_MODEL)


async def embed_text(text: str) -> list[float]:
    """
    Generate a 768-dimensional embedding for the given text.
    Uses Azure OpenAI text-embedding-3-small (requesting 768 dimensions),
    or falls back to Google's text-embedding-004.
    """
    _ensure_init()
    settings = get_settings()

    if settings.AZURE_OPENAI_KEY and settings.AZURE_OPENAI_ENDPOINT:
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        url = f"{endpoint}/openai/deployments/{settings.AZURE_OPENAI_EMBED_DEPLOYMENT}/embeddings?api-version={settings.AZURE_OPENAI_API_VERSION}"
        headers = {
            "api-key": settings.AZURE_OPENAI_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "input": text,
            "dimensions": 768,
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                res_data = response.json()
                return res_data["data"][0]["embedding"]
            except Exception as exc:
                logger.error(f"Azure OpenAI Embeddings error: {exc}")
                raise
    else:
        # Fallback to Gemini
        result = genai.embed_content(
            model=settings.GEMINI_EMBED_MODEL,
            content=text,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=settings.GEMINI_EMBED_DIMENSIONS,
        )
        return result["embedding"]


async def chat_completion(prompt: str, system: str | None = None) -> str:
    """Single-turn chat completion via Azure OpenAI or Gemini Flash."""
    _ensure_init()
    settings = get_settings()

    if settings.AZURE_OPENAI_KEY and settings.AZURE_OPENAI_ENDPOINT:
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        url = f"{endpoint}/openai/deployments/{settings.AZURE_OPENAI_CHAT_DEPLOYMENT}/chat/completions?api-version={settings.AZURE_OPENAI_API_VERSION}"
        headers = {
            "api-key": settings.AZURE_OPENAI_KEY,
            "Content-Type": "application/json",
        }
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.error(f"Azure OpenAI Chat error: {exc}")
                raise
    else:
        # Fallback to Gemini
        model = get_chat_model()
        messages = []
        if system:
            messages.append({"role": "user", "parts": [f"[SYSTEM] {system}"]})
            messages.append({"role": "model", "parts": ["Understood."]})
        messages.append({"role": "user", "parts": [prompt]})

        try:
            response = model.generate_content(messages)
            return response.text
        except Exception as exc:
            logger.error(f"Gemini error: {exc}")
            raise
