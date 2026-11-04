import logging
from typing import Any, Dict, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from app.agents.llm.exceptions import LLMConfigurationError
from app.core.config import settings

logger = logging.getLogger("nexops.agents.llm")


class LLMProviderFactory:
    """Factory creating configured LangChain chat model instances with lazy initialization."""

    @staticmethod
    def get_effective_provider_name(provider: Optional[str] = None) -> str:
        """Resolve requested or default provider name."""
        return (provider or settings.effective_llm_provider).lower().strip()

    @classmethod
    def create_llm(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BaseChatModel:
        """Instantiate and return a configured LangChain BaseChatModel."""
        resolved_provider = cls.get_effective_provider_name(provider)
        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        if resolved_provider == "gemini":
            api_key = settings.effective_gemini_api_key
            if not api_key:
                raise LLMConfigurationError(
                    "Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in the backend environment."
                )
            selected_model = model or settings.LLM_MODEL or settings.GEMINI_MODEL
            logger.info("Initializing Gemini Chat Model: %s (temp=%.2f)", selected_model, temp)
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=selected_model,
                google_api_key=api_key,
                temperature=temp,
                max_output_tokens=tokens,
            )

        if resolved_provider == "groq":
            api_key = settings.effective_groq_api_key
            if not api_key:
                raise LLMConfigurationError(
                    "Groq API key is not configured. Set GROQ_API_KEY in the backend environment."
                )
            selected_model = model or settings.LLM_MODEL or settings.GROQ_MODEL
            logger.info("Initializing Groq Chat Model: %s (temp=%.2f)", selected_model, temp)
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=selected_model,
                groq_api_key=api_key,
                temperature=temp,
                max_tokens=tokens,
            )

        raise LLMConfigurationError(
            f"Unsupported LLM provider '{resolved_provider}'. Supported providers are: 'gemini', 'groq'."
        )

    @classmethod
    def get_provider_info(cls, provider: Optional[str] = None) -> Dict[str, Any]:
        """Return safe, sanitized metadata for the requested or default provider without exposing keys."""
        resolved_provider = cls.get_effective_provider_name(provider)
        if resolved_provider == "gemini":
            return {
                "provider": "gemini",
                "model": settings.LLM_MODEL or settings.GEMINI_MODEL,
                "configured": bool(settings.effective_gemini_api_key),
            }
        if resolved_provider == "groq":
            return {
                "provider": "groq",
                "model": settings.LLM_MODEL or settings.GROQ_MODEL,
                "configured": bool(settings.effective_groq_api_key),
            }
        return {
            "provider": resolved_provider,
            "model": "unknown",
            "configured": False,
        }

