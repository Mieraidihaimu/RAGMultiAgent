"""
Configuration settings for batch processor with provider support
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ===================================
    # Database Configuration
    # ===================================
    # Supabase (Option 1)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    # PostgreSQL (Option 2)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "thoughtprocessor"
    postgres_user: str = "thoughtprocessor"
    postgres_password: str = ""
    database_url: Optional[str] = None

    # ===================================
    # AI Provider Configuration
    # ===================================
    ai_provider: str = "anthropic"  # anthropic, openai, or google

    # Anthropic (Claude)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    # OpenAI (GPT)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"

    # Google (Gemini)
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.5-flash-lite"

    # ===================================
    # Processing Configuration
    # ===================================
    max_tokens: int = 4000

    # OpenAI Embeddings (for semantic caching)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Caching
    semantic_cache_threshold: float = 0.92
    semantic_cache_ttl_days: int = 7
    prompt_cache_enabled: bool = True

    # Processing
    rate_limit_delay: float = 0.5
    max_retries: int = 3
    batch_size: int = 10

    # Logging
    log_level: str = "INFO"

    # ===================================
    # Kafka Configuration
    # ===================================
    kafka_enabled: bool = False
    kafka_mode: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "thought-processing"
    kafka_consumer_group: str = "thought-workers"
    kafka_partitions: int = 3

    # ===================================
    # Redis Configuration (for SSE)
    # ===================================
    redis_url: str = "redis://localhost:6379"
    redis_sse_prefix: str = "thought_updates"

    # ===================================
    # SSE Configuration
    # ===================================
    sse_heartbeat_interval: int = 30
    sse_max_connections: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_ai_api_key(self) -> str:
        """Get API key for configured AI provider"""
        if self.ai_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY must be set")
            return self.anthropic_api_key
        elif self.ai_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set")
            return self.openai_api_key
        elif self.ai_provider == "google":
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY must be set")
            return self.google_api_key
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")

    def get_ai_model(self) -> str:
        """Get model for configured AI provider"""
        if self.ai_provider == "anthropic":
            return self.anthropic_model
        elif self.ai_provider == "openai":
            return self.openai_model
        elif self.ai_provider == "google":
            return self.google_model
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")

    def use_supabase(self) -> bool:
        """Check if Supabase should be used"""
        return bool(self.supabase_url and self.supabase_key)


# Global settings instance
settings = Settings()
