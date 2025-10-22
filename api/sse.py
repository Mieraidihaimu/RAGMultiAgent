"""
Server-Sent Events (SSE) connection manager with Redis pub/sub
Enables real-time updates to clients across multiple API instances
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional
from uuid import uuid4
import redis.asyncio as aioredis
from loguru import logger


class SSEConnectionManager:
    """
    Manages SSE connections and Redis pub/sub for real-time updates
    Supports multiple API instances via Redis pub/sub
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize SSE connection manager

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None

        # Track active connections per user (for connection limits)
        self.active_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.max_connections_per_user = 5

        self._started = False

    async def start(self):
        """Initialize Redis connection"""
        if self._started:
            return

        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            self._started = True

            logger.info(f"SSE Manager started with Redis: {self.redis_url}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def stop(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self._started = False
            logger.info("SSE Manager stopped")

    def _get_channel_name(self, user_id: str) -> str:
        """Get Redis channel name for a user"""
        return f"thought_updates:{user_id}"

    async def subscribe(self, user_id: str, connection_id: Optional[str] = None) -> aioredis.client.PubSub:
        """
        Subscribe to Redis pub/sub channel for a user

        Args:
            user_id: User ID to subscribe to
            connection_id: Optional connection identifier

        Returns:
            Redis PubSub instance
        """
        if not self._started or not self.redis_client:
            raise RuntimeError("SSE Manager not started. Call start() first.")

        # Track connection
        conn_id = connection_id or str(uuid4())
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        if len(self.active_connections[user_id]) >= self.max_connections_per_user:
            logger.warning(f"Max connections reached for user {user_id}")

        self.active_connections[user_id].add(conn_id)

        # Subscribe to channel
        channel = self._get_channel_name(user_id)
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)

        logger.info(f"SSE subscription created: user={user_id}, channel={channel}, conn={conn_id}")

        return pubsub

    async def unsubscribe(self, user_id: str, pubsub: aioredis.client.PubSub, connection_id: Optional[str] = None):
        """
        Unsubscribe from Redis pub/sub channel

        Args:
            user_id: User ID
            pubsub: PubSub instance to close
            connection_id: Optional connection identifier
        """
        try:
            await pubsub.unsubscribe()
            await pubsub.close()

            # Remove from active connections
            if connection_id and user_id in self.active_connections:
                self.active_connections[user_id].discard(connection_id)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            logger.info(f"SSE subscription closed: user={user_id}")

        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")

    async def broadcast(
        self,
        user_id: str,
        event_type: str,
        data: Dict,
        event_id: Optional[str] = None
    ):
        """
        Broadcast an event to all SSE clients subscribed to a user

        Args:
            user_id: User ID to broadcast to
            event_type: SSE event type (e.g., 'thought_created', 'thought_completed')
            data: Event data (will be JSON-serialized)
            event_id: Optional event ID for client-side tracking
        """
        if not self._started or not self.redis_client:
            logger.warning("SSE Manager not started, cannot broadcast")
            return

        try:
            channel = self._get_channel_name(user_id)

            # Create event payload
            payload = {
                "event": event_type,
                "event_id": event_id or str(uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            # Publish to Redis channel
            await self.redis_client.publish(channel, json.dumps(payload))

            logger.debug(f"Broadcast event: {event_type} to {channel}")

        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")

    async def broadcast_thought_created(self, user_id: str, thought_id: str):
        """Convenience method: broadcast thought created event"""
        await self.broadcast(
            user_id=user_id,
            event_type="thought_created",
            data={"thought_id": thought_id, "status": "pending"}
        )

    async def broadcast_thought_processing(self, user_id: str, thought_id: str):
        """Convenience method: broadcast thought processing event"""
        await self.broadcast(
            user_id=user_id,
            event_type="thought_processing",
            data={"thought_id": thought_id, "status": "processing", "message": "Starting AI analysis..."}
        )

    async def broadcast_agent_completed(
        self,
        user_id: str,
        thought_id: str,
        agent_name: str,
        agent_number: int,
        total_agents: int = 5
    ):
        """Convenience method: broadcast agent completed event"""
        await self.broadcast(
            user_id=user_id,
            event_type="thought_agent_completed",
            data={
                "thought_id": thought_id,
                "agent": agent_name,
                "progress": f"{agent_number}/{total_agents}",
                "agent_number": agent_number,
                "total_agents": total_agents
            }
        )

    async def broadcast_thought_completed(self, user_id: str, thought_id: str):
        """Convenience method: broadcast thought completed event"""
        await self.broadcast(
            user_id=user_id,
            event_type="thought_completed",
            data={"thought_id": thought_id, "status": "completed", "message": "Analysis complete!"}
        )

    async def broadcast_thought_failed(self, user_id: str, thought_id: str, error: str):
        """Convenience method: broadcast thought failed event"""
        await self.broadcast(
            user_id=user_id,
            event_type="thought_failed",
            data={"thought_id": thought_id, "status": "failed", "error": error}
        )

    def get_connection_count(self, user_id: Optional[str] = None) -> int:
        """
        Get number of active connections

        Args:
            user_id: Optional user ID to get count for specific user

        Returns:
            Number of active connections
        """
        if user_id:
            return len(self.active_connections.get(user_id, set()))
        else:
            return sum(len(conns) for conns in self.active_connections.values())


# Global SSE manager instance
_global_sse_manager: Optional[SSEConnectionManager] = None


async def get_sse_manager(redis_url: str = "redis://localhost:6379") -> SSEConnectionManager:
    """
    Get or create global SSE manager instance

    Args:
        redis_url: Redis connection URL

    Returns:
        SSEConnectionManager instance
    """
    global _global_sse_manager

    if _global_sse_manager is None:
        _global_sse_manager = SSEConnectionManager(redis_url)
        await _global_sse_manager.start()

    return _global_sse_manager


async def close_sse_manager():
    """Close the global SSE manager instance"""
    global _global_sse_manager

    if _global_sse_manager:
        await _global_sse_manager.stop()
        _global_sse_manager = None
