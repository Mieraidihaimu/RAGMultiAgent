"""
PostgreSQL adapter for direct database access
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncpg
from loguru import logger

from .base import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    """
    PostgreSQL database adapter

    Uses asyncpg for async PostgreSQL operations.
    Suitable for local Docker deployments.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "thoughtprocessor",
        user: str = "thoughtprocessor",
        password: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool: Optional[asyncpg.Pool] = None

    @staticmethod
    def _parse_json_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON string fields back to dicts"""
        import json
        
        json_fields = {'classification', 'analysis', 'value_impact', 'action_plan', 'priority', 'context', 'response'}
        
        for field in json_fields:
            if field in row and row[field] is not None and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if parsing fails
        
        return row

        logger.info(f"Initialized PostgreSQL adapter for {host}:{port}/{database}")

    async def connect(self):
        """Establish connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10
            )
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
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
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO thoughts (user_id, text, status, created_at)
                VALUES ($1, $2, 'pending', NOW())
                RETURNING id, user_id, text, status, created_at
                """,
                user_id, text
            )
            return dict(row)

    async def get_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific thought"""
        async with self.pool.acquire() as conn:
            if user_id:
                row = await conn.fetchrow(
                    "SELECT * FROM thoughts WHERE id = $1 AND user_id = $2",
                    thought_id, user_id
                )
            else:
                row = await conn.fetchrow(
                    "SELECT * FROM thoughts WHERE id = $1",
                    thought_id
                )
            return self._parse_json_fields(dict(row)) if row else None

    async def get_thoughts(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get thoughts for a user"""
        async with self.pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT * FROM thoughts
                    WHERE user_id = $1 AND status = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    user_id, status, limit, offset
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM thoughts
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    user_id, limit, offset
                )
            return [self._parse_json_fields(dict(row)) for row in rows]

    async def get_pending_thoughts(self) -> List[Dict[str, Any]]:
        """Get all pending thoughts with user context"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, u.context, u.context_version, u.email
                FROM thoughts t
                INNER JOIN users u ON t.user_id = u.id
                WHERE t.status = 'pending'
                ORDER BY t.created_at
                """
            )
            return [self._parse_json_fields(dict(row)) for row in rows]

    async def update_thought(
        self,
        thought_id: str,
        **fields
    ) -> Dict[str, Any]:
        """Update thought fields"""
        import json
        
        # JSON fields that need serialization
        json_fields = {'classification', 'analysis', 'value_impact', 'action_plan', 'priority', 'context'}
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        param_index = 1

        for key, value in fields.items():
            # Serialize dict values to JSON strings for JSONB columns
            if key in json_fields and isinstance(value, dict):
                value = json.dumps(value)
            # Handle vector embeddings - convert list to string format for pgvector
            elif key == 'embedding' and isinstance(value, list):
                value = str(value)
            
            set_clauses.append(f"{key} = ${param_index}")
            values.append(value)
            param_index += 1

        values.append(thought_id)

        query = f"""
            UPDATE thoughts
            SET {', '.join(set_clauses)}
            WHERE id = ${param_index}
            RETURNING *
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None

    async def delete_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a thought"""
        async with self.pool.acquire() as conn:
            if user_id:
                result = await conn.execute(
                    "DELETE FROM thoughts WHERE id = $1 AND user_id = $2",
                    thought_id, user_id
                )
            else:
                result = await conn.execute(
                    "DELETE FROM thoughts WHERE id = $1",
                    thought_id
                )
            return result.split()[-1] == "1"

    # User operations
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user record"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            return dict(row) if row else None

    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user context"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET context = $1, context_updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                context, user_id
            )
            return dict(row) if row else None

    # Cache operations
    async def find_similar_cached_thought(
        self,
        embedding: List[float],
        user_id: str,
        threshold: float = 0.92
    ) -> Optional[Dict[str, Any]]:
        """Find similar cached thought using vector similarity"""
        # Convert list to pgvector format string
        embedding_str = str(embedding)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, thought_text, response,
                       1 - (embedding <=> $1::vector) as similarity
                FROM thought_cache
                WHERE user_id = $2
                  AND expires_at > NOW()
                  AND 1 - (embedding <=> $1::vector) > $3
                ORDER BY embedding <=> $1::vector
                LIMIT 1
                """,
                embedding_str, user_id, threshold
            )
            return dict(row) if row else None

    async def save_to_cache(
        self,
        user_id: str,
        thought_text: str,
        embedding: List[float],
        response: Dict[str, Any],
        ttl_days: int = 7
    ) -> Dict[str, Any]:
        """Save to cache"""
        import json
        
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        # Convert list to pgvector format string
        embedding_str = str(embedding)
        # Serialize response dict to JSON string
        response_json = json.dumps(response)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO thought_cache
                (user_id, thought_text, embedding, response, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                user_id, thought_text, embedding_str, response_json, expires_at
            )
            return dict(row) if row else None

    async def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM thought_cache WHERE expires_at < NOW()"
            )
            count = int(result.split()[-1])
            logger.info(f"Cleaned up {count} expired cache entries")
            return count

    # Synthesis operations
    async def save_weekly_synthesis(
        self,
        user_id: str,
        week_start: datetime,
        week_end: datetime,
        synthesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save weekly synthesis"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO weekly_synthesis
                (user_id, week_start, week_end, synthesis, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (user_id, week_start)
                DO UPDATE SET synthesis = $4, created_at = NOW()
                RETURNING *
                """,
                user_id, week_start.date(), week_end.date(), synthesis
            )
            return dict(row) if row else None

    async def get_latest_synthesis(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest synthesis"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM weekly_synthesis
                WHERE user_id = $1
                ORDER BY week_start DESC
                LIMIT 1
                """,
                user_id
            )
            return dict(row) if row else None

    async def get_syntheses(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get all syntheses"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM weekly_synthesis
                WHERE user_id = $1
                ORDER BY week_start DESC
                LIMIT $2
                """,
                user_id, limit
            )
            return [dict(row) for row in rows]
