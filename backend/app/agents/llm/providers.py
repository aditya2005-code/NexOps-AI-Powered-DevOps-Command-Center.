# LLM provider abstraction — instantiates the configured provider without making calls.
# shortcut: single model per provider, no per-task override; add when agents need different models
from app.core.config import settings

def get_llm():
    """Return configured LLM instance. Raises if API key missing."""
    if settings.LLM_DEFAULT_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set")
        return ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, google_api_key=settings.GOOGLE_API_KEY)
    elif settings.LLM_DEFAULT_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        return ChatGroq(model=settings.GROQ_MODEL, groq_api_key=settings.GROQ_API_KEY)
    raise ValueError(f"Unknown provider: {settings.LLM_DEFAULT_PROVIDER}")
