"""
Semantic caching using embeddings and vector similarity
Supports both Google (free with Gemini!) and OpenAI embeddings
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from config import settings


class SemanticCache:
    """
    Semantic cache for thought processing results
    Uses vector embeddings to find similar cached thoughts

    Supports:
    - Google Gemini embeddings (FREE with API key!)
    - OpenAI embeddings (backup option)
    """

    def __init__(self, database_client):
        self.db = database_client
        self.threshold = settings.semantic_cache_threshold
        self.ttl_days = settings.semantic_cache_ttl_days

        # Determine which embedding provider to use
        self.embedding_provider = settings.ai_provider

        # Initialize the appropriate embedding client
        if self.embedding_provider == "google":
            self._init_google_embeddings()
        else:
            # Default to OpenAI for embeddings (if available)
            self._init_openai_embeddings()

    def _init_google_embeddings(self):
        """Initialize Google Gemini embeddings (FREE!)"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self.genai = genai
            self.embedding_model = "models/text-embedding-004"  # Latest Google embedding model
            logger.info("Using Google embeddings (FREE with Gemini API key!)")
        except ImportError:
            logger.warning("google-generativeai not installed. Install with: pip install google-generativeai")
            self._init_openai_embeddings()
        except Exception as e:
            logger.warning(f"Failed to initialize Google embeddings: {e}")
            self._init_openai_embeddings()

    def _init_openai_embeddings(self):
        """Initialize OpenAI embeddings (backup option)"""
        try:
            import openai
            if settings.openai_api_key and settings.openai_api_key != "sk-your-openai-key-here":
                self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
                self.embedding_model = settings.embedding_model
                self.embedding_provider = "openai"
                logger.info("Using OpenAI embeddings")
            else:
                logger.warning("OpenAI API key not set. Semantic caching disabled.")
                self.embedding_provider = None
        except ImportError:
            logger.warning("openai not installed. Semantic caching disabled.")
            self.embedding_provider = None
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI embeddings: {e}")
            self.embedding_provider = None

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text

        Uses Google Gemini by default (FREE!), falls back to OpenAI if needed
        """
        if self.embedding_provider is None:
            logger.warning("No embedding provider available. Skipping semantic cache.")
            return None

        try:
            if self.embedding_provider == "google":
                return await self._get_google_embedding(text)
            else:
                return await self._get_openai_embedding(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def _get_google_embedding(self, text: str) -> List[float]:
        """Generate embedding using Google Gemini (FREE!)"""
        try:
            result = self.genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="semantic_similarity"
            )
            embedding = result['embedding']
            logger.debug(f"Generated Google embedding for text: {text[:50]}...")

            # Google embeddings are 768 dimensions, we need to pad to 1536 for pgvector
            # Or we can truncate our database to use 768 dimensions
            # For now, pad with zeros to match existing schema
            if len(embedding) < 1536:
                embedding = embedding + [0.0] * (1536 - len(embedding))
            elif len(embedding) > 1536:
                embedding = embedding[:1536]

            return embedding
        except Exception as e:
            logger.error(f"Google embedding failed: {e}")
            raise

    async def _get_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated OpenAI embedding for text: {text[:50]}...")
            return embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

    async def check_cache(
        self,
        thought_text: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a similar thought exists in cache
        Returns cached response if found, None otherwise
        """
        if self.embedding_provider is None:
            logger.debug("Semantic caching disabled (no embedding provider)")
            return None

        try:
            # Generate embedding for the thought
            embedding = await self.get_embedding(thought_text)
            if embedding is None:
                return None

            # Search for similar thoughts using vector similarity
            cached_thought = await self.db.find_similar_cached_thought(
                embedding=embedding,
                user_id=user_id,
                threshold=self.threshold
            )

            if cached_thought:
                similarity = cached_thought.get("similarity", 0)
                logger.info(
                    f"Cache HIT! Similarity: {similarity:.3f} "
                    f"(threshold: {self.threshold})"
                )
                return cached_thought.get("response")

            logger.info("Cache MISS - no similar thought found")
            return None

        except Exception as e:
            logger.error(f"Cache check failed: {e}")
            # Don't fail the whole pipeline on cache errors
            return None

    async def save_to_cache(
        self,
        thought_text: str,
        user_id: str,
        response: Dict[str, Any]
    ) -> bool:
        """
        Save thought and its processing result to cache
        """
        if self.embedding_provider is None:
            logger.debug("Semantic caching disabled (no embedding provider)")
            return False

        try:
            # Generate embedding
            embedding = await self.get_embedding(thought_text)
            if embedding is None:
                return False

            # Save to cache
            await self.db.save_to_cache(
                user_id=user_id,
                thought_text=thought_text,
                embedding=embedding,
                response=response,
                ttl_days=self.ttl_days
            )

            logger.info(f"Saved to cache (TTL: {self.ttl_days} days)")
            return True

        except Exception as e:
            logger.error(f"Cache save failed: {e}")
            # Don't fail the whole pipeline on cache errors
            return False

    async def cleanup_expired(self) -> int:
        """
        Remove expired cache entries
        Returns number of entries removed
        """
        try:
            count = await self.db.cleanup_expired_cache()
            logger.info(f"Cache cleanup completed: {count} entries removed")
            return count
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return 0

    async def get_cache_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get cache statistics for a user
        """
        try:
            # This would need to be implemented in the database adapter
            stats = {
                "embedding_provider": self.embedding_provider or "disabled",
                "threshold": self.threshold,
                "ttl_days": self.ttl_days,
                "model": self.embedding_model if self.embedding_provider else None
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}


class EmbeddingCache:
    """
    Simple in-memory cache for embeddings to avoid redundant API calls
    within the same batch processing run
    """

    def __init__(self):
        self._cache: Dict[str, List[float]] = {}

    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        return self._cache.get(text)

    def set(self, text: str, embedding: List[float]):
        """Cache embedding"""
        self._cache[text] = embedding

    def size(self) -> int:
        """Get cache size"""
        return len(self._cache)

    def clear(self):
        """Clear cache"""
        self._cache.clear()
        logger.debug("Embedding cache cleared")
