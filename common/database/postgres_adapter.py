"""
PostgreSQL adapter for direct database access with field-level encryption
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncpg
from loguru import logger

from .base import DatabaseAdapter
from common.security import get_encryption_service


class PostgreSQLAdapter(DatabaseAdapter):
    """
    PostgreSQL database adapter with field-level encryption

    Uses asyncpg for async PostgreSQL operations.
    Implements transparent encryption/decryption for sensitive fields:
    - users.context (JSONB)
    - thoughts.text (TEXT)
    - thoughts.classification, analysis, value_impact, action_plan, priority (JSONB)
    - thought_cache.response (JSONB)

    Encryption is transparent to application code - data is encrypted
    on write and decrypted on read automatically.
    """

    # Fields that require encryption
    ENCRYPTED_FIELDS = {
        'context',          # User context (JSONB)
        'text',            # Thought text (TEXT)
        'classification',  # AI classification (JSONB)
        'analysis',        # AI analysis (JSONB)
        'value_impact',    # Value impact (JSONB)
        'action_plan',     # Action plan (JSONB)
        'priority',        # Priority (JSONB)
        'response'         # Cached response (JSONB)
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "thoughtprocessor",
        user: str = "thoughtprocessor",
        password: str = "",
        enable_encryption: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool: Optional[asyncpg.Pool] = None
        self.enable_encryption = enable_encryption

        # Initialize encryption service if enabled
        if self.enable_encryption:
            try:
                self.encryption = get_encryption_service()
                logger.info("Encryption enabled for PostgreSQL adapter")
            except Exception as e:
                logger.warning(f"Failed to initialize encryption: {e}. Running without encryption.")
                self.enable_encryption = False
                self.encryption = None
        else:
            self.encryption = None
            logger.warning("Encryption is DISABLED - data will be stored in plaintext")

    def _encrypt_field(self, field_name: str, value: Any) -> Any:
        """
        Encrypt a field value if encryption is enabled and field is in ENCRYPTED_FIELDS

        Args:
            field_name: Name of the field
            value: Value to encrypt

        Returns:
            Encrypted value if encryption enabled, otherwise original value
        """
        if not self.enable_encryption or not self.encryption:
            return value

        if field_name not in self.ENCRYPTED_FIELDS or value is None:
            return value

        try:
            # Determine if field should be encrypted as JSON or text
            if field_name == 'text':
                # Encrypt as text
                return self.encryption.encrypt_text(value)
            else:
                # Encrypt as JSON (context, analysis fields, response, etc.)
                return self.encryption.encrypt_json(value)
        except Exception as e:
            logger.error(f"Failed to encrypt field {field_name}: {e}")
            raise

    def _decrypt_field(self, field_name: str, encrypted_value: Any) -> Any:
        """
        Decrypt a field value if encryption is enabled and field is in ENCRYPTED_FIELDS

        Args:
            field_name: Name of the field
            encrypted_value: Encrypted value

        Returns:
            Decrypted value if encryption enabled, otherwise original value
        """
        if not self.enable_encryption or not self.encryption:
            return encrypted_value

        if field_name not in self.ENCRYPTED_FIELDS or encrypted_value is None:
            return encrypted_value

        try:
            # Determine if field should be decrypted as JSON or text
            if field_name == 'text':
                # Decrypt as text
                return self.encryption.decrypt_text(encrypted_value)
            else:
                # Decrypt as JSON
                return self.encryption.decrypt_json(encrypted_value)
        except Exception as e:
            logger.error(f"Failed to decrypt field {field_name}: {e}")
            # Return as-is if decryption fails (for migration/backward compatibility)
            return encrypted_value

    def _encrypt_row_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt all encrypted fields in a dictionary (for INSERT/UPDATE)

        Args:
            fields: Dictionary of field names to values

        Returns:
            Dictionary with encrypted values
        """
        if not self.enable_encryption:
            return fields

        encrypted_fields = {}
        for key, value in fields.items():
            encrypted_fields[key] = self._encrypt_field(key, value)
        return encrypted_fields

    def _decrypt_row_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt all encrypted fields in a row (for SELECT results)

        Args:
            row: Database row as dictionary

        Returns:
            Dictionary with decrypted values
        """
        if not self.enable_encryption:
            return row

        decrypted_row = dict(row)
        for field_name in self.ENCRYPTED_FIELDS:
            if field_name in decrypted_row:
                decrypted_row[field_name] = self._decrypt_field(field_name, decrypted_row[field_name])
        return decrypted_row

    @staticmethod
    def _parse_json_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON string fields back to dicts (for non-encrypted JSONB fields)
        Note: This is only used for fields that are NOT encrypted, as encrypted
        fields are already returned as dicts from decryption.
        """
        import json

        json_fields = {'classification', 'analysis', 'value_impact', 'action_plan', 'priority', 'context', 'response', 'consolidated_output'}

        for field in json_fields:
            if field in row and row[field] is not None and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if parsing fails

        return row

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
        processing_mode: str = 'single',
        group_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new thought with encrypted text

        Args:
            user_id: User ID
            text: Thought text (will be encrypted if encryption enabled)
            processing_mode: 'single' or 'group'
            group_id: Persona group ID (required if processing_mode='group')
            **kwargs: Additional fields (e.g., anonymous_session_id)

        Returns:
            Created thought record (with text decrypted)
        """
        # Encrypt the thought text before storing
        encrypted_text = self._encrypt_field('text', text)
        
        # Extract anonymous_session_id if present
        anonymous_session_id = kwargs.get('anonymous_session_id')

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO thoughts (user_id, text, status, processing_mode, group_id, anonymous_session_id, created_at)
                VALUES ($1, $2, 'pending', $3, $4, $5, NOW())
                RETURNING id, user_id, text, status, processing_mode, group_id, created_at
                """,
                user_id, encrypted_text, processing_mode, group_id, anonymous_session_id
            )
            result = dict(row)

            # Decrypt the text before returning
            return self._decrypt_row_fields(result)

    async def get_thought(
        self,
        thought_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific thought (decrypts sensitive fields)

        Args:
            thought_id: Thought ID
            user_id: Optional user ID for ownership check

        Returns:
            Thought record with decrypted fields
        """
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

            if not row:
                return None

            # Decrypt encrypted fields
            result = self._decrypt_row_fields(dict(row))
            # Parse any remaining JSON fields
            return self._parse_json_fields(result)

    async def get_thoughts(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get thoughts for a user (decrypts sensitive fields)

        Args:
            user_id: User ID
            status: Optional status filter
            limit: Max number of results
            offset: Offset for pagination

        Returns:
            List of thought records with decrypted fields
        """
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

            # Decrypt each row
            results = []
            for row in rows:
                decrypted = self._decrypt_row_fields(dict(row))
                results.append(self._parse_json_fields(decrypted))
            return results

    async def get_pending_thoughts(self) -> List[Dict[str, Any]]:
        """
        Get all pending thoughts with user context (decrypts all sensitive fields)

        Returns:
            List of thoughts with decrypted text, context, and analysis fields
        """
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

            # Decrypt each row
            results = []
            for row in rows:
                decrypted = self._decrypt_row_fields(dict(row))
                results.append(self._parse_json_fields(decrypted))
            return results

    async def update_thought(
        self,
        thought_id: str,
        **fields
    ) -> Dict[str, Any]:
        """
        Update thought fields (encrypts sensitive fields before storing)

        Args:
            thought_id: Thought ID
            **fields: Fields to update (will encrypt sensitive fields)

        Returns:
            Updated thought record with decrypted fields
        """
        import json

        # JSON fields that need serialization (for non-encrypted fields)
        json_fields = {'classification', 'analysis', 'value_impact', 'action_plan', 'priority', 'context', 'consolidated_output'}

        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        param_index = 1

        for key, value in fields.items():
            # Encrypt sensitive fields before storing
            if key in self.ENCRYPTED_FIELDS:
                value = self._encrypt_field(key, value)
                # Encrypted fields return strings, but if encryption is disabled,
                # we need to ensure dict values are converted to JSON
                if key in json_fields and isinstance(value, dict):
                    value = json.dumps(value)
            # Convert dict values to JSON strings for JSONB columns
            # asyncpg will automatically convert JSON strings to JSONB
            elif key in json_fields and isinstance(value, dict):
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
            if not row:
                return None

            # Decrypt fields before returning
            result = self._decrypt_row_fields(dict(row))
            return self._parse_json_fields(result)

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
        """
        Get user record (decrypts context field)

        Args:
            user_id: User ID

        Returns:
            User record with decrypted context
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            if not row:
                return None

            # Decrypt context field
            return self._decrypt_row_fields(dict(row))

    async def update_user_context(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user context (encrypts before storing)

        Args:
            user_id: User ID
            context: Context dictionary (will be encrypted)

        Returns:
            Updated user record with decrypted context
        """
        # Encrypt context before storing
        encrypted_context = self._encrypt_field('context', context)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET context = $1, context_updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                encrypted_context, user_id
            )
            if not row:
                return None

            # Decrypt context before returning
            return self._decrypt_row_fields(dict(row))

    # Cache operations
    async def find_similar_cached_thought(
        self,
        embedding: List[float],
        user_id: str,
        threshold: float = 0.92
    ) -> Optional[Dict[str, Any]]:
        """
        Find similar cached thought using vector similarity (decrypts response)

        Args:
            embedding: Embedding vector
            user_id: User ID
            threshold: Similarity threshold

        Returns:
            Cached thought with decrypted response
        """
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
            if not row:
                return None

            # Decrypt response field
            return self._decrypt_row_fields(dict(row))

    async def save_to_cache(
        self,
        user_id: str,
        thought_text: str,
        embedding: List[float],
        response: Dict[str, Any],
        ttl_days: int = 7
    ) -> Dict[str, Any]:
        """
        Save to cache (encrypts response before storing)

        Args:
            user_id: User ID
            thought_text: Thought text
            embedding: Embedding vector
            response: Response dictionary (will be encrypted)
            ttl_days: Cache TTL in days

        Returns:
            Cached entry with decrypted response
        """
        import json

        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        # Convert list to pgvector format string
        embedding_str = str(embedding)
        # Encrypt response before storing
        encrypted_response = self._encrypt_field('response', response)
        # Ensure response is JSON string if encryption returned a dict (when disabled)
        if isinstance(encrypted_response, dict):
            encrypted_response = json.dumps(encrypted_response)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO thought_cache
                (user_id, thought_text, embedding, response, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                user_id, thought_text, embedding_str, encrypted_response, expires_at
            )
            if not row:
                return None

            # Decrypt response before returning
            return self._decrypt_row_fields(dict(row))

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

    # ========================================================================
    # Persona Group Methods
    # ========================================================================

    async def create_persona_group(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new persona group"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO persona_groups (user_id, name, description)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, name, description, created_at, updated_at
                """,
                user_id, name, description
            )
            return dict(row)

    async def get_persona_group(
        self,
        group_id: str,
        include_personas: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get a persona group by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, name, description, created_at, updated_at
                FROM persona_groups
                WHERE id = $1
                """,
                group_id
            )
            
            if not row:
                return None
            
            group = dict(row)
            
            if include_personas:
                personas = await conn.fetch(
                    """
                    SELECT id, group_id, name, prompt, sort_order, created_at, updated_at
                    FROM personas
                    WHERE group_id = $1
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    group_id
                )
                group['personas'] = [dict(p) for p in personas]
            else:
                group['personas'] = []
            
            return group

    async def get_persona_groups(
        self,
        user_id: str,
        include_personas: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all persona groups for a user"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, name, description, created_at, updated_at
                FROM persona_groups
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user_id
            )
            
            groups = [dict(row) for row in rows]
            
            if include_personas and groups:
                # Fetch all personas for these groups in one query
                group_ids = [g['id'] for g in groups]
                personas = await conn.fetch(
                    """
                    SELECT id, group_id, name, prompt, sort_order, created_at, updated_at
                    FROM personas
                    WHERE group_id = ANY($1)
                    ORDER BY sort_order ASC, created_at ASC
                    """,
                    group_ids
                )
                
                # Group personas by group_id
                personas_by_group = {}
                for p in personas:
                    persona_dict = dict(p)
                    group_id = persona_dict['group_id']
                    if group_id not in personas_by_group:
                        personas_by_group[group_id] = []
                    personas_by_group[group_id].append(persona_dict)
                
                # Attach personas to groups
                for group in groups:
                    group['personas'] = personas_by_group.get(group['id'], [])
            else:
                for group in groups:
                    group['personas'] = []
            
            return groups

    async def update_persona_group(
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a persona group"""
        updates = []
        values = []
        param_idx = 1
        
        if name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(name)
            param_idx += 1
        
        if description is not None:
            updates.append(f"description = ${param_idx}")
            values.append(description)
            param_idx += 1
        
        if not updates:
            return await self.get_persona_group(group_id, include_personas=False)
        
        values.append(group_id)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE persona_groups
                SET {', '.join(updates)}
                WHERE id = ${param_idx}
                RETURNING id, user_id, name, description, created_at, updated_at
                """,
                *values
            )
            
            if not row:
                return None
            
            return dict(row)

    async def delete_persona_group(self, group_id: str) -> bool:
        """Delete a persona group (cascades to personas and thought_persona_runs)"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM persona_groups WHERE id = $1",
                group_id
            )
            return result == "DELETE 1"

    # ========================================================================
    # Persona Methods
    # ========================================================================

    async def create_persona(
        self,
        group_id: str,
        name: str,
        prompt: str,
        sort_order: int = 0
    ) -> Dict[str, Any]:
        """Create a new persona"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO personas (group_id, name, prompt, sort_order)
                VALUES ($1, $2, $3, $4)
                RETURNING id, group_id, name, prompt, sort_order, created_at, updated_at
                """,
                group_id, name, prompt, sort_order
            )
            return dict(row)

    async def get_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get a persona by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, group_id, name, prompt, sort_order, created_at, updated_at
                FROM personas
                WHERE id = $1
                """,
                persona_id
            )
            return dict(row) if row else None

    async def update_persona(
        self,
        persona_id: str,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a persona"""
        updates = []
        values = []
        param_idx = 1
        
        if name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(name)
            param_idx += 1
        
        if prompt is not None:
            updates.append(f"prompt = ${param_idx}")
            values.append(prompt)
            param_idx += 1
        
        if sort_order is not None:
            updates.append(f"sort_order = ${param_idx}")
            values.append(sort_order)
            param_idx += 1
        
        if not updates:
            return await self.get_persona(persona_id)
        
        values.append(persona_id)
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE personas
                SET {', '.join(updates)}
                WHERE id = ${param_idx}
                RETURNING id, group_id, name, prompt, sort_order, created_at, updated_at
                """,
                *values
            )
            
            if not row:
                return None
            
            return dict(row)

    async def delete_persona(self, persona_id: str) -> bool:
        """Delete a persona"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM personas WHERE id = $1",
                persona_id
            )
            return result == "DELETE 1"

    # ========================================================================
    # Thought Persona Run Methods
    # ========================================================================

    async def create_thought_persona_run(
        self,
        thought_id: str,
        persona_id: Optional[str],
        group_id: Optional[str],
        persona_name: str,
        persona_output: Dict[str, Any],
        processing_time_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record a persona's processing of a thought"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO thought_persona_runs 
                (thought_id, persona_id, group_id, persona_name, persona_output, processing_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, thought_id, persona_id, group_id, persona_name, 
                          persona_output, processing_time_ms, created_at
                """,
                thought_id, persona_id, group_id, persona_name, persona_output, processing_time_ms
            )
            return dict(row)

    async def get_thought_persona_runs(
        self,
        thought_id: str
    ) -> List[Dict[str, Any]]:
        """Get all persona runs for a thought"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, thought_id, persona_id, group_id, persona_name,
                       persona_output, processing_time_ms, created_at
                FROM thought_persona_runs
                WHERE thought_id = $1
                ORDER BY created_at ASC
                """,
                thought_id
            )
            return [dict(row) for row in rows]
