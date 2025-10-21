"""
Base interface for AI providers using Adapter Pattern
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class AIMessage:
    """Standardized AI message format"""
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class AIResponse:
    """Standardized AI response format"""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "content": self.content,
            "usage": self.usage,
            "model": self.model,
            "finish_reason": self.finish_reason
        }


class AIProvider(ABC):
    """
    Abstract base class for AI providers

    This interface allows switching between different AI providers
    (Anthropic, OpenAI, Google) while maintaining the same API.
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize provider with API key

        Args:
            api_key: API key for the provider
            **kwargs: Provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        Generate AI response

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            AIResponse with generated content
        """
        pass

    @abstractmethod
    async def generate_with_cache(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        cacheable_context: Optional[str] = None,
        max_tokens: int = 1000,
        **kwargs
    ) -> AIResponse:
        """
        Generate with prompt caching support

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            cacheable_context: Context to cache (user profile, etc.)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            AIResponse with generated content
        """
        pass

    @abstractmethod
    def supports_caching(self) -> bool:
        """Check if provider supports prompt caching"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current model name"""
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for token usage

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pass
