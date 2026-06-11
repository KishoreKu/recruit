"""
gemini_client.py — Shared LLM client: chat completions + embeddings.
Supports Azure OpenAI (preferred) and falls back to Google Gemini.
"""
import httpx
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
import google.generativeai as genai
from config import get_settings
from loguru import logger
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import google.api_core.exceptions

_client_initialized = False


async def _ensure_init():
    global _client_initialized
    if not _client_initialized:
        settings = get_settings()
        # Always configure Gemini if key is present
        if settings.GEMINI_API_KEY:
            logger.info("Configuring Gemini SDK...")
            genai.configure(api_key=settings.GEMINI_API_KEY)
        
        if settings.AZURE_OPENAI_KEY and settings.AZURE_OPENAI_ENDPOINT:
            logger.info("Azure OpenAI credentials found. Available for embeddings.")
            
        if not settings.GEMINI_API_KEY and not settings.AZURE_OPENAI_KEY:
            logger.warning("No LLM API keys found! Expected GEMINI_API_KEY or AZURE_OPENAI_KEY.")
            
        _client_initialized = True


def get_chat_model():
    """Return a Gemini chat model instance (if using Gemini fallback)."""
    # Note: This is a synchronous helper, might need adjustment if _ensure_init is awaited
    return genai.GenerativeModel(model_name=get_settings().GEMINI_CHAT_MODEL)


@retry(retry=retry_if_exception_type((google.api_core.exceptions.ResourceExhausted, httpx.HTTPStatusError, Exception)), wait=wait_exponential(multiplier=5, min=5, max=60), stop=stop_after_attempt(10))
async def chat_completion(prompt: str, system: str | None = None) -> str:
    """Generate a chat completion using Gemini or Azure OpenAI."""
    await _ensure_init()
    
    settings = get_settings()
    
    # Always prioritize Azure OpenAI for chat if configured
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
            "messages": messages
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                if response.status_code != 200:
                    logger.error(f"Azure HTTP Error: {response.status_code} - {response.text}")
                response.raise_for_status()
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.error(f"Azure OpenAI Chat error: {exc}")
                raise
                
    elif settings.GEMINI_API_KEY:
        model_name = settings.GEMINI_CHAT_MODEL
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system
        )
        response = await model.generate_content_async(prompt)
        return response.text
    else:
        raise ValueError("No API keys configured for chat completions.")


@retry(retry=retry_if_exception_type((google.api_core.exceptions.ResourceExhausted, httpx.HTTPStatusError, Exception)), wait=wait_exponential(multiplier=5, min=5, max=60), stop=stop_after_attempt(10))
async def embed_text(text: str) -> list[float]:
    """Generate a vector embedding using Azure OpenAI (prioritized) or Gemini."""
    await _ensure_init()
    
    settings = get_settings()
    
    # Always prioritize Azure OpenAI for embeddings to bypass Gemini RPM limits
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
            
    elif settings.GEMINI_API_KEY:
        # Use Gemini
        result = await genai.embed_content_async(
            model=settings.GEMINI_EMBED_MODEL,
            content=text,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=settings.GEMINI_EMBED_DIMENSIONS,
        )
        return result["embedding"]
    else:
        raise ValueError("No API keys configured for embeddings.")
