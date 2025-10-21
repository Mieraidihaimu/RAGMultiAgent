"""
OpenAI GPT provider implementation
"""
from typing import List, Optional
import openai
from loguru import logger

from .base import AIProvider, AIMessage, AIResponse


class OpenAIProvider(AIProvider):
    """
    OpenAI GPT provider adapter

    Supports:
    - GPT-4, GPT-4 Turbo, GPT-3.5 models
    - Function calling
    - JSON mode
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

        # Pricing per 1M tokens (USD)
        self.pricing = {
            "gpt-4-turbo-preview": {
                "input": 10.00,
                "output": 30.00
            },
            "gpt-4": {
                "input": 30.00,
                "output": 60.00
            },
            "gpt-3.5-turbo": {
                "input": 0.50,
                "output": 1.50
            },
            "gpt-4o": {
                "input": 2.50,
                "output": 10.00
            },
            "gpt-4o-mini": {
                "input": 0.15,
                "output": 0.60
            }
        }

        logger.info(f"Initialized OpenAI provider with model: {model}")

    async def generate(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """Generate response using GPT"""
        try:
            # Convert messages to OpenAI format
            openai_messages = []

            if system_prompt:
                openai_messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Extract content
            content = response.choices[0].message.content

            return AIResponse(
                content=content,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
        Generate with context (OpenAI doesn't have native caching)

        Note: OpenAI doesn't support prompt caching like Anthropic,
        so this falls back to regular generation with context in system prompt
        """
        # Combine system prompt and cacheable context
        full_system_prompt = system_prompt or ""
        if cacheable_context:
            full_system_prompt += f"\n\n{cacheable_context}"

        return await self.generate(
            messages=messages,
            system_prompt=full_system_prompt if full_system_prompt else None,
            max_tokens=max_tokens,
            **kwargs
        )

    def supports_caching(self) -> bool:
        """OpenAI does not support native prompt caching"""
        return False

    def get_model_name(self) -> str:
        """Get current model"""
        return self.model

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for OpenAI usage"""
        pricing = self.pricing.get(self.model, self.pricing["gpt-4-turbo-preview"])

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total = input_cost + output_cost

        logger.debug(
            f"Cost estimate: ${total:.4f} "
            f"(input: ${input_cost:.4f}, output: ${output_cost:.4f})"
        )

        return total
