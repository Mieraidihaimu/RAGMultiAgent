"""
Factory for creating AI provider instances
"""
from typing import Optional
from loguru import logger

from .base import AIProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .google_provider import GoogleProvider


class AIProviderFactory:
    """
    Factory for creating AI provider instances

    Usage:
        provider = AIProviderFactory.create(
            provider_type="anthropic",
            api_key="sk-ant-...",
            model="claude-sonnet-4-20250514"
        )
    """

    @staticmethod
    def create(
        provider_type: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> AIProvider:
        """
        Create an AI provider instance

        Args:
            provider_type: Type of provider ("anthropic", "openai", "google")
            api_key: API key for the provider
            model: Optional model name (uses defaults if not specified)
            **kwargs: Additional provider-specific configuration

        Returns:
            AIProvider instance

        Raises:
            ValueError: If provider_type is not supported
        """
        provider_type = provider_type.lower()

        if provider_type == "anthropic":
            model = model or "claude-sonnet-4-20250514"
            logger.info(f"Creating Anthropic provider with model: {model}")
            return AnthropicProvider(api_key=api_key, model=model, **kwargs)

        elif provider_type == "openai":
            model = model or "gpt-4-turbo-preview"
            logger.info(f"Creating OpenAI provider with model: {model}")
            return OpenAIProvider(api_key=api_key, model=model, **kwargs)

        elif provider_type == "google":
            model = model or "gemini-2.5-flash-lite"
            logger.info(f"Creating Google provider with model: {model}")
            return GoogleProvider(api_key=api_key, model=model, **kwargs)

        else:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: anthropic, openai, google"
            )

    @staticmethod
    def get_supported_providers() -> list:
        """Get list of supported provider types"""
        return ["anthropic", "openai", "google"]

    @staticmethod
    def get_default_models() -> dict:
        """Get default models for each provider"""
        return {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4-turbo-preview",
            "google": "gemini-2.5-flash-lite"
        }
