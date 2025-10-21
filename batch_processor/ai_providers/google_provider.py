"""
Google Gemini provider implementation
"""
from typing import List, Optional
from loguru import logger

from .base import AIProvider, AIMessage, AIResponse


class GoogleProvider(AIProvider):
    """
    Google Gemini provider adapter

    Supports:
    - Gemini Pro, Gemini Ultra models
    - Long context (up to 2M tokens with Gemini 1.5)
    - Multimodal capabilities
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model = model

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.genai = genai
        except ImportError:
            logger.error(
                "google-generativeai not installed. "
                "Install with: pip install google-generativeai"
            )
            raise

        # Pricing per 1M tokens (USD)
        self.pricing = {
            "gemini-2.5-flash-lite": {
                "input": 1.25,
                "output": 5.00,
                "cache_read": 0.3125  # Gemini has context caching
            },
            "gemini-2.5-flash-lite": {
                "input": 0.075,
                "output": 0.30,
                "cache_read": 0.01875
            },
            "gemini-2.5-flash-lite": {
                "input": 0.50,
                "output": 1.50
            }
        }

        logger.info(f"Initialized Google provider with model: {model}")

    async def generate(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """Generate response using Gemini"""
        try:
            # Build conversation history
            conversation = []

            if system_prompt:
                conversation.append({
                    "role": "user",
                    "parts": [f"System: {system_prompt}"]
                })
                conversation.append({
                    "role": "model",
                    "parts": ["Understood. I'll follow these instructions."]
                })

            # Convert messages to Gemini format
            for msg in messages:
                role = "model" if msg.role == "assistant" else "user"
                conversation.append({
                    "role": role,
                    "parts": [msg.content]
                })

            # Generation config
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }

            # Start chat with history
            chat = self.client.start_chat(history=conversation[:-1])

            # Generate response for last message
            response = chat.send_message(
                conversation[-1]["parts"][0],
                generation_config=generation_config
            )

            # Extract content
            content = response.text

            # Estimate token usage (Gemini doesn't always return this)
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }

            return AIResponse(
                content=content,
                usage=usage,
                model=self.model,
                finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None
            )

        except Exception as e:
            logger.error(f"Google API error: {e}")
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
        Generate with context caching

        Gemini 1.5 supports context caching for long contexts
        """
        try:
            # For Gemini, we can use cached_content for long contexts
            # This is a simplified version - full implementation would use cached_content API

            # Combine system prompt and cacheable context
            full_system_prompt = system_prompt or ""
            if cacheable_context:
                full_system_prompt += f"\n\nContext:\n{cacheable_context}"

            return await self.generate(
                messages=messages,
                system_prompt=full_system_prompt if full_system_prompt else None,
                max_tokens=max_tokens,
                **kwargs
            )

        except Exception as e:
            logger.error(f"Google API error with caching: {e}")
            raise

    def supports_caching(self) -> bool:
        """Gemini 1.5 supports context caching"""
        return "1.5" in self.model

    def get_model_name(self) -> str:
        """Get current model"""
        return self.model

    def estimate_cost(self, input_tokens: int, output_tokens: int, cache_read_tokens: int = 0) -> float:
        """Estimate cost for Google usage"""
        pricing = self.pricing.get(self.model, self.pricing["gemini-2.5-flash-lite"])

        regular_input = input_tokens - cache_read_tokens
        input_cost = (regular_input / 1_000_000) * pricing["input"]
        cache_cost = (cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        total = input_cost + cache_cost + output_cost

        logger.debug(
            f"Cost estimate: ${total:.4f} "
            f"(input: ${input_cost:.4f}, cache: ${cache_cost:.4f}, output: ${output_cost:.4f})"
        )

        return total
