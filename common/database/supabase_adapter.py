"""
Supabase adapter for managed PostgreSQL access
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client
from loguru import logger

from .base import DatabaseAdapter


class SupabaseAdapter(DatabaseAdapter):
    """
    Supabase database adapter

    Uses Supabase SDK for managed PostgreSQL access.
    Suitable for cloud deployments.
    """

    def __init__(
        self,
        url: str,
        key: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.url = url
        self.key = key
        self.client: Optional[Client] = None

        logger.info(f"Initialized Supabase adapter for {url}")

    async def connect(self):
        """Establish Supabase client"""
        try:
            self.client = create_client(self.url, self.key)
            logger.info("Supabase client created")
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            raise

    async def disconnect(self):
        """Close Supabase client"""
        # Supabase client doesn't need explicit disconnection
        self.client = None
        logger.info("Supabase client closed")

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            result = self.client.table("users").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # Thought operations
    async def create_thought(
        self,
        user_id: str,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new thought"""
        result = self.client.table("thoughts").insert({
            "user_id": user_id,
            "text": text,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        return result.data[0] if result.data else None

    async def get_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific thought"""
        query = self.client.table("thoughts").select("*").eq("id", thought_id)

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()
        return result.data[0] if result.data else None

    async def get_thoughts(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get thoughts for a user"""
        query = self.client.table("thoughts").select("*").eq("user_id", user_id)

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data

    async def get_pending_thoughts(self) -> List[Dict[str, Any]]:
        """Get all pending thoughts with user context"""
        result = self.client.table("thoughts")\
            .select("*, users!inner(context, context_version, email)")\
            .eq("status", "pending")\
            .order("created_at")\
            .execute()

        return result.data

    async def update_thought(
        self,
        thought_id: str,
        **fields
    ) -> Dict[str, Any]:
        """Update thought fields"""
        result = self.client.table("thoughts")\
            .update(fields)\
            .eq("id", thought_id)\
            .execute()

        return result.data[0] if result.data else None

    async def delete_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a thought"""
        query = self.client.table("thoughts").delete().eq("id", thought_id)

        if user_id:
            query = query.eq("user_id", user_id)

        result = query.execute()
        return len(result.data) > 0

    # User operations
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user record"""
        result = self.client.table("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None

    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user context"""
        result = self.client.table("users")\
            .update({"context": context})\
            .eq("id", user_id)\
            .execute()

        return result.data[0] if result.data else None

    # Cache operations
    async def find_similar_cached_thought(
        self,
        embedding: List[float],
        user_id: str,
        threshold: float = 0.92
    ) -> Optional[Dict[str, Any]]:
        """Find similar cached thought using vector similarity"""
        result = self.client.rpc(
            "match_similar_thoughts",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": 1,
                "user_id_param": user_id
            }
        ).execute()

        if result.data and len(result.data) > 0:
            # Update hit count
            cache_id = result.data[0]["id"]
            self.client.table("thought_cache")\
                .update({
                    "hit_count": result.data[0].get("hit_count", 0) + 1,
                    "last_hit_at": datetime.utcnow().isoformat()
                })\
                .eq("id", cache_id)\
                .execute()

            return result.data[0]

        return None

    async def save_to_cache(
        self,
        user_id: str,
        thought_text: str,
        embedding: List[float],
        response: Dict[str, Any],
        ttl_days: int = 7
    ) -> Dict[str, Any]:
        """Save to cache"""
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        result = self.client.table("thought_cache").insert({
            "user_id": user_id,
            "thought_text": thought_text,
            "embedding": embedding,
            "response": response,
            "hit_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat()
        }).execute()

        return result.data[0] if result.data else None

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries"""
        result = self.client.rpc("cleanup_expired_cache").execute()
        logger.info("Cache cleanup completed")
        return 0  # Function returns void

    # Synthesis operations
    async def save_weekly_synthesis(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        synthesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save weekly synthesis"""
        result = self.client.table("weekly_synthesis").insert({
            "user_id": user_id,
            "week_start": week_start.date().isoformat(),
            "week_end": week_end.date().isoformat(),
            "synthesis": synthesis,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        return result.data[0] if result.data else None

    async def get_latest_synthesis(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest synthesis"""
        result = self.client.table("weekly_synthesis")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("week_start", desc=True)\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None

    async def get_syntheses(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get all syntheses"""
        result = self.client.table("weekly_synthesis")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("week_start", desc=True)\
            .limit(limit)\
            .execute()

        return result.data
