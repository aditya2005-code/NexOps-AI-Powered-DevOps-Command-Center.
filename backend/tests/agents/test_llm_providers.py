import pytest
from unittest.mock import patch

from app.agents.llm.exceptions import LLMConfigurationError
from app.agents.llm.provider_factory import LLMProviderFactory
from app.core.config import settings


def test_gemini_provider_initialization_with_credentials() -> None:
    """Verify ChatGoogleGenerativeAI instantiates with valid credentials."""
    with patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"):
        llm = LLMProviderFactory.create_llm(provider="gemini")
        assert llm is not None
        assert getattr(llm, "model", None) == "gemini-1.5-flash"


def test_groq_provider_initialization_with_credentials() -> None:
    """Verify ChatGroq instantiates with valid credentials."""
    with patch.object(settings, "GROQ_API_KEY", "test-groq-key"):
        llm = LLMProviderFactory.create_llm(provider="groq")
        assert llm is not None
        assert getattr(llm, "model_name", None) == "llama-3.1-8b-instant"


def test_missing_gemini_credentials_raises_error() -> None:
    """Verify LLMConfigurationError is raised when Gemini API key is missing."""
    with patch.object(settings, "GEMINI_API_KEY", None), \
         patch.object(settings, "GOOGLE_API_KEY", ""):
        with pytest.raises(LLMConfigurationError) as exc_info:
            LLMProviderFactory.create_llm(provider="gemini")
        assert "Gemini API key is not configured" in str(exc_info.value)


def test_missing_groq_credentials_raises_error() -> None:
    """Verify LLMConfigurationError is raised when Groq API key is missing."""
    with patch.object(settings, "GROQ_API_KEY", ""):
        with pytest.raises(LLMConfigurationError) as exc_info:
            LLMProviderFactory.create_llm(provider="groq")
        assert "Groq API key is not configured" in str(exc_info.value)


def test_unsupported_provider_raises_error() -> None:
    """Verify LLMConfigurationError is raised for invalid/unknown provider."""
    with pytest.raises(LLMConfigurationError) as exc_info:
        LLMProviderFactory.create_llm(provider="unsupported-provider-xyz")
    assert "Unsupported LLM provider" in str(exc_info.value)


def test_model_and_temperature_overrides() -> None:
    """Verify custom model, temperature, and token overrides are passed through."""
    with patch.object(settings, "GEMINI_API_KEY", "test-key"):
        llm = LLMProviderFactory.create_llm(
            provider="gemini",
            model="gemini-1.5-pro",
            temperature=0.7,
            max_tokens=4096,
        )
        assert getattr(llm, "model", None) == "gemini-1.5-pro"
        assert getattr(llm, "temperature", None) == 0.7


def test_provider_info_redacts_secrets() -> None:
    """Verify get_provider_info returns sanitized configuration metadata without secrets."""
    with patch.object(settings, "GEMINI_API_KEY", "secret-super-key"):
        info = LLMProviderFactory.get_provider_info(provider="gemini")
        assert info["provider"] == "gemini"
        assert info["configured"] is True
        assert "secret-super-key" not in str(info)
        assert "key" not in info

