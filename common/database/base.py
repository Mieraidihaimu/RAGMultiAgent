"""
Base interface for database adapters using Adapter Pattern
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class DatabaseAdapter(ABC):
    """
    Abstract base class for database adapters

    This interface allows switching between different databases
    (PostgreSQL, Supabase, MongoDB, etc.) while maintaining the same API.
    """

    def __init__(self, **kwargs):
        """
        Initialize database connection

        Args:
            **kwargs: Database-specific connection parameters
        """
        self.config = kwargs

    @abstractmethod
    async def connect(self):
        """Establish database connection"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Close database connection"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check database connectivity

        Returns:
            True if database is accessible, False otherwise
        """
        pass

    # Thought operations
    @abstractmethod
    async def create_thought(
        self,
        user_id: str,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new thought

        Args:
            user_id: User ID
            text: Thought text
            **kwargs: Additional fields

        Returns:
            Created thought record
        """
        pass

    @abstractmethod
    async def get_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific thought

        Args:
            thought_id: Thought ID
            user_id: Optional user ID for authorization

        Returns:
            Thought record or None
        """
        pass

    @abstractmethod
    async def get_thoughts(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get thoughts for a user

        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum number of thoughts
            offset: Pagination offset

        Returns:
            List of thought records
        """
        pass

    @abstractmethod
    async def get_pending_thoughts(self) -> List[Dict[str, Any]]:
        """
        Get all pending thoughts for batch processing

        Returns:
            List of pending thought records with user context
        """
        pass

    @abstractmethod
    async def update_thought(
        self,
        thought_id: str,
        **fields
    ) -> Dict[str, Any]:
        """
        Update thought fields

        Args:
            thought_id: Thought ID
            **fields: Fields to update

        Returns:
            Updated thought record
        """
        pass

    @abstractmethod
    async def delete_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a thought

        Args:
            thought_id: Thought ID
            user_id: Optional user ID for authorization

        Returns:
            True if deleted, False otherwise
        """
        pass

    # User operations
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user record

        Args:
            user_id: User ID

        Returns:
            User record or None
        """
        pass

    @abstractmethod
    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user context

        Args:
            user_id: User ID
            context: New context data

        Returns:
            Updated user record
        """
        pass

    # Cache operations
    @abstractmethod
    async def find_similar_cached_thought(
        self,
        embedding: List[float],
        user_id: str,
        threshold: float = 0.92
    ) -> Optional[Dict[str, Any]]:
        """
        Find similar cached thought using vector similarity

        Args:
            embedding: Query embedding vector
            user_id: User ID
            threshold: Similarity threshold

        Returns:
            Cached thought record or None
        """
        pass

    @abstractmethod
    async def save_to_cache(
        self,
        user_id: str,
        thought_text: str,
        embedding: List[float],
        response: Dict[str, Any],
        ttl_days: int = 7
    ) -> Dict[str, Any]:
        """
        Save thought processing result to cache

        Args:
            user_id: User ID
            thought_text: Original thought text
            embedding: Embedding vector
            response: Processing result
            ttl_days: Time-to-live in days

        Returns:
            Cache record
        """
        pass

    @abstractmethod
    async def cleanup_expired_cache(self) -> int:
        """
        Remove expired cache entries

        Returns:
            Number of entries removed
        """
        pass

    # Synthesis operations
    @abstractmethod
    async def save_weekly_synthesis(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        synthesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save weekly synthesis

        Args:
            user_id: User ID
            week_start: Week start date
            week_end: Week end date
            synthesis: Synthesis data

        Returns:
            Synthesis record
        """
        pass

    @abstractmethod
    async def get_latest_synthesis(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest weekly synthesis for user

        Args:
            user_id: User ID

        Returns:
            Synthesis record or None
        """
        pass

    @abstractmethod
    async def get_syntheses(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all syntheses for user

        Args:
            user_id: User ID
            limit: Maximum number of syntheses

        Returns:
            List of synthesis records
        """
        pass
