class LLMError(Exception):
    """Base exception for all AI agent and LLM operations."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when an LLM provider is misconfigured or missing credentials."""
    pass


class LLMAuthenticationError(LLMConfigurationError):
    """Raised when provider authentication fails due to invalid API keys."""
    pass


class LLMProviderError(LLMError):
    """Raised when an LLM provider fails during invocation or returns an error."""
    pass

