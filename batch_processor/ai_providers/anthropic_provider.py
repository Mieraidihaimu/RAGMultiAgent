"""
Anthropic Claude provider implementation
"""
import json
from typing import List, Optional, Dict, Any
from anthropic import Anthropic
from loguru import logger

from .base import AIProvider, AIMessage, AIResponse


class AnthropicProvider(AIProvider):
    """
    Anthropic Claude provider adapter

    Supports:
    - Claude Sonnet, Opus, Haiku models
    - Native prompt caching
    - Extended context (200K tokens)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.client = Anthropic(api_key=api_key)
        self.model = model

        # Pricing per 1M tokens (USD)
        self.pricing = {
            "claude-sonnet-4-20250514": {
                "input": 3.00,
                "output": 15.00,
                "cache_write": 3.75,
                "cache_read": 0.30
            },
            "claude-opus-4-20250514": {
                "input": 15.00,
                "output": 75.00,
                "cache_write": 18.75,
                "cache_read": 1.50
            },
            "claude-haiku-4-20250514": {
                "input": 0.80,
                "output": 4.00,
                "cache_write": 1.00,
                "cache_read": 0.08
            }
        }

        logger.info(f"Initialized Anthropic provider with model: {model}")

    async def generate(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """Generate response using Claude"""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
                if msg.role in ["user", "assistant"]
            ]

            # Build request
            request_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "temperature": temperature,
                **kwargs
            }

            if system_prompt:
                request_params["system"] = system_prompt

            # Make API call
            response = self.client.messages.create(**request_params)

            # Extract content
            content = response.content[0].text

            return AIResponse(
                content=content,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                model=response.model,
                finish_reason=response.stop_reason
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def generate_with_cache(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        cacheable_context: Optional[str] = None,
        max_tokens: int = 1000,
        **kwargs
    ) -> AIResponse:
        """
        Generate with prompt caching

        Uses Anthropic's native caching to cache user context
        """
        try:
            # Convert messages
            anthropic_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
                if msg.role in ["user", "assistant"]
            ]

            # Build system prompt with cache control
            system_content = []

            if system_prompt:
                system_content.append({
                    "type": "text",
                    "text": system_prompt
                })

            if cacheable_context:
                system_content.append({
                    "type": "text",
                    "text": cacheable_context,
                    "cache_control": {"type": "ephemeral"}
                })

            # Make API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_content if system_content else None,
                messages=anthropic_messages,
                **kwargs
            )

            # Extract content
            content = response.content[0].text

            # Build usage dict with cache info
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }

            # Add cache metrics if available
            if hasattr(response.usage, 'cache_creation_input_tokens'):
                usage["cache_creation_tokens"] = response.usage.cache_creation_input_tokens
            if hasattr(response.usage, 'cache_read_input_tokens'):
                usage["cache_read_tokens"] = response.usage.cache_read_input_tokens

            return AIResponse(
                content=content,
                usage=usage,
                model=response.model,
                finish_reason=response.stop_reason
            )

        except Exception as e:
            logger.error(f"Anthropic API error with caching: {e}")
            raise

    def supports_caching(self) -> bool:
        """Anthropic supports native prompt caching"""
        return True

    def get_model_name(self) -> str:
        """Get current model"""
        return self.model

    def estimate_cost(self, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0) -> float:
        """
        Estimate cost for Anthropic usage

        Args:
            input_tokens: Regular input tokens
            output_tokens: Output tokens
            cache_read_tokens: Cache hit tokens (90% cheaper)
        """
        pricing = self.pricing.get(self.model, self.pricing["claude-sonnet-4-20250514"])

        # Calculate costs per million tokens
        regular_input = input_tokens - cache_read_tokens
        input_cost = (regular_input / 1_000_000) * pricing["input"]
        cache_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total = input_cost + cache_cost + output_cost

        logger.debug(
            f"Cost estimate: ${total:.4f} "
            f"(input: ${input_cost:.4f}, cache: ${cache_cost:.4f}, output: ${output_cost:.4f})"
        )

        return total
