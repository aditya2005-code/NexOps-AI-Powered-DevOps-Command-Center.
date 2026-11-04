from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from app.agents.llm.provider_factory import LLMProviderFactory


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> BaseChatModel:
    """Return configured LLM instance. Raises LLMConfigurationError if missing credentials."""
    return LLMProviderFactory.create_llm(
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
