#!/usr/bin/env python3
"""
Data migration script: Encrypt existing sensitive data

This script encrypts existing data in the database using AES-256-GCM encryption.
It processes data in batches to avoid memory issues with large datasets.

Usage:
    python database/migrate_encrypt_data.py [--dry-run] [--batch-size 100]

Prerequisites:
    1. Run database migration 005_prepare_for_encryption.sql first
    2. Set ENCRYPTION_MASTER_KEY environment variable
    3. Ensure database is accessible

Fields encrypted:
    - users.context (JSONB)
    - thoughts.text (TEXT)
    - thoughts.classification, analysis, value_impact, action_plan, priority (JSONB)
    - thought_cache.response (JSONB)
"""

import os
import sys
import argparse
import asyncio
import asyncpg
from typing import Dict, Any, List, Optional
from loguru import logger
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.security import get_encryption_service, EncryptionService


class DataEncryptionMigrator:
    """Migrates existing data to encrypted format"""

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5432,
        db_name: str = "thoughtprocessor",
        db_user: str = "thoughtprocessor",
        db_password: str = "",
        batch_size: int = 100,
        dry_run: bool = False
    ):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.batch_size = batch_size
        self.dry_run = dry_run

        # Initialize encryption service
        try:
            self.encryption = get_encryption_service()
            logger.info("✓ Encryption service initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize encryption service: {e}")
            logger.error("Make sure ENCRYPTION_MASTER_KEY is set in environment")
            sys.exit(1)

        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Connect to database"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                min_size=2,
                max_size=10
            )
            logger.info(f"✓ Connected to database: {self.db_host}:{self.db_port}/{self.db_name}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to database: {e}")
            sys.exit(1)

    async def disconnect(self):
        """Disconnect from database"""
        if self.pool:
            await self.pool.close()
            logger.info("✓ Disconnected from database")

    async def get_migration_status(self) -> List[Dict[str, Any]]:
        """Get current migration status"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM encryption_migration_status
                ORDER BY table_name, field_name
            """)
            return [dict(row) for row in rows]

    async def encrypt_users_context(self) -> int:
        """
        Encrypt users.context field

        Returns:
            Number of records encrypted
        """
        logger.info("📝 Encrypting users.context...")

        async with self.pool.acquire() as conn:
            # Get users with non-encrypted context
            users = await conn.fetch("""
                SELECT id, context
                FROM users
                WHERE context IS NOT NULL
                  AND context_encrypted IS NULL
                LIMIT $1
            """, self.batch_size)

            if not users:
                logger.info("  → No users.context records to encrypt")
                return 0

            encrypted_count = 0
            for user in users:
                try:
                    # Parse context if it's a JSON string
                    context = user['context']
                    if isinstance(context, str):
                        context = json.loads(context)

                    # Encrypt context
                    encrypted_context = self.encryption.encrypt_json(context)

                    if not self.dry_run:
                        # Update with encrypted version
                        await conn.execute("""
                            UPDATE users
                            SET context_encrypted = $1
                            WHERE id = $2
                        """, encrypted_context, user['id'])

                    encrypted_count += 1

                    if encrypted_count % 10 == 0:
                        logger.info(f"  → Encrypted {encrypted_count} users.context records...")

                except Exception as e:
                    logger.error(f"  ✗ Failed to encrypt context for user {user['id']}: {e}")

            logger.info(f"✓ Encrypted {encrypted_count} users.context records")
            return encrypted_count

    async def encrypt_thoughts_text(self) -> int:
        """
        Encrypt thoughts.text field (in-place, as it's already TEXT type)

        Returns:
            Number of records encrypted
        """
        logger.info("📝 Encrypting thoughts.text...")

        async with self.pool.acquire() as conn:
            # Get thoughts with non-encrypted text
            thoughts = await conn.fetch("""
                SELECT id, text
                FROM thoughts
                WHERE text IS NOT NULL
                  AND text NOT LIKE 'enc_v1:%'
                LIMIT $1
            """, self.batch_size)

            if not thoughts:
                logger.info("  → No thoughts.text records to encrypt")
                return 0

            encrypted_count = 0
            for thought in thoughts:
                try:
                    # Encrypt text
                    encrypted_text = self.encryption.encrypt_text(thought['text'])

                    if not self.dry_run:
                        # Update with encrypted version (in-place)
                        await conn.execute("""
                            UPDATE thoughts
                            SET text = $1
                            WHERE id = $2
                        """, encrypted_text, thought['id'])

                    encrypted_count += 1

                    if encrypted_count % 10 == 0:
                        logger.info(f"  → Encrypted {encrypted_count} thoughts.text records...")

                except Exception as e:
                    logger.error(f"  ✗ Failed to encrypt text for thought {thought['id']}: {e}")

            logger.info(f"✓ Encrypted {encrypted_count} thoughts.text records")
            return encrypted_count

    async def encrypt_thoughts_analysis_fields(self) -> Dict[str, int]:
        """
        Encrypt thoughts analysis fields (classification, analysis, value_impact, action_plan, priority)

        Returns:
            Dictionary with counts per field
        """
        logger.info("📝 Encrypting thoughts analysis fields...")

        fields = ['classification', 'analysis', 'value_impact', 'action_plan', 'priority']
        counts = {}

        for field in fields:
            logger.info(f"  → Processing thoughts.{field}...")
            encrypted_field = f"{field}_encrypted"

            async with self.pool.acquire() as conn:
                # Get thoughts with non-encrypted field
                thoughts = await conn.fetch(f"""
                    SELECT id, {field}
                    FROM thoughts
                    WHERE {field} IS NOT NULL
                      AND {encrypted_field} IS NULL
                    LIMIT $1
                """, self.batch_size)

                if not thoughts:
                    logger.info(f"    → No thoughts.{field} records to encrypt")
                    counts[field] = 0
                    continue

                encrypted_count = 0
                for thought in thoughts:
                    try:
                        # Parse field if it's a JSON string
                        field_value = thought[field]
                        if isinstance(field_value, str):
                            field_value = json.loads(field_value)

                        # Encrypt field
                        encrypted_value = self.encryption.encrypt_json(field_value)

                        if not self.dry_run:
                            # Update with encrypted version
                            await conn.execute(f"""
                                UPDATE thoughts
                                SET {encrypted_field} = $1
                                WHERE id = $2
                            """, encrypted_value, thought['id'])

                        encrypted_count += 1

                        if encrypted_count % 10 == 0:
                            logger.info(f"    → Encrypted {encrypted_count} thoughts.{field} records...")

                    except Exception as e:
                        logger.error(f"    ✗ Failed to encrypt {field} for thought {thought['id']}: {e}")

                logger.info(f"  ✓ Encrypted {encrypted_count} thoughts.{field} records")
                counts[field] = encrypted_count

        return counts

    async def encrypt_cache_response(self) -> int:
        """
        Encrypt thought_cache.response field

        Returns:
            Number of records encrypted
        """
        logger.info("📝 Encrypting thought_cache.response...")

        async with self.pool.acquire() as conn:
            # Get cache entries with non-encrypted response
            cache_entries = await conn.fetch("""
                SELECT id, response
                FROM thought_cache
                WHERE response IS NOT NULL
                  AND response_encrypted IS NULL
                LIMIT $1
            """, self.batch_size)

            if not cache_entries:
                logger.info("  → No thought_cache.response records to encrypt")
                return 0

            encrypted_count = 0
            for entry in cache_entries:
                try:
                    # Parse response if it's a JSON string
                    response = entry['response']
                    if isinstance(response, str):
                        response = json.loads(response)

                    # Encrypt response
                    encrypted_response = self.encryption.encrypt_json(response)

                    if not self.dry_run:
                        # Update with encrypted version
                        await conn.execute("""
                            UPDATE thought_cache
                            SET response_encrypted = $1
                            WHERE id = $2
                        """, encrypted_response, entry['id'])

                    encrypted_count += 1

                    if encrypted_count % 10 == 0:
                        logger.info(f"  → Encrypted {encrypted_count} thought_cache.response records...")

                except Exception as e:
                    logger.error(f"  ✗ Failed to encrypt response for cache entry {entry['id']}: {e}")

            logger.info(f"✓ Encrypted {encrypted_count} thought_cache.response records")
            return encrypted_count

    async def run_migration(self):
        """Run complete migration"""
        logger.info("=" * 80)
        logger.info("DATA ENCRYPTION MIGRATION")
        logger.info("=" * 80)

        if self.dry_run:
            logger.warning("🔍 DRY RUN MODE - No data will be modified")

        # Show initial status
        logger.info("\n📊 Initial Migration Status:")
        initial_status = await self.get_migration_status()
        for row in initial_status:
            logger.info(
                f"  {row['table_name']}.{row['field_name']}: "
                f"{row['encrypted_records']}/{row['total_records']} "
                f"({row['percent_complete'] or 0}% complete)"
            )

        logger.info("\n" + "=" * 80)
        logger.info("Starting encryption...")
        logger.info("=" * 80 + "\n")

        total_encrypted = 0

        # Encrypt users.context
        count = await self.encrypt_users_context()
        total_encrypted += count

        # Encrypt thoughts.text
        count = await self.encrypt_thoughts_text()
        total_encrypted += count

        # Encrypt thoughts analysis fields
        counts = await self.encrypt_thoughts_analysis_fields()
        total_encrypted += sum(counts.values())

        # Encrypt thought_cache.response
        count = await self.encrypt_cache_response()
        total_encrypted += count

        # Show final status
        logger.info("\n" + "=" * 80)
        logger.info("📊 Final Migration Status:")
        final_status = await self.get_migration_status()
        for row in final_status:
            logger.info(
                f"  {row['table_name']}.{row['field_name']}: "
                f"{row['encrypted_records']}/{row['total_records']} "
                f"({row['percent_complete'] or 0}% complete)"
            )

        # Check if migration is complete
        pending_total = sum(row['pending_records'] or 0 for row in final_status)

        logger.info("\n" + "=" * 80)
        if pending_total == 0:
            logger.info("✓ MIGRATION COMPLETE!")
            logger.info(f"✓ Total records encrypted: {total_encrypted}")
            if not self.dry_run:
                logger.info("\n🎯 Next steps:")
                logger.info("  1. Verify encrypted data is accessible through the application")
                logger.info("  2. Run: psql -U thoughtprocessor -d thoughtprocessor -c \"SELECT finalize_encryption_migration();\"")
                logger.info("  3. Restart the application with encryption enabled")
        else:
            logger.warning(f"⚠ MIGRATION INCOMPLETE: {pending_total} records still pending")
            logger.warning("  Run this script again to continue migrating in batches")

        logger.info("=" * 80)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Encrypt existing database records")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without modifying data"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process per batch (default: 100)"
    )
    parser.add_argument(
        "--db-host",
        default=os.getenv("DB_HOST", "localhost"),
        help="Database host"
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=int(os.getenv("DB_PORT", "5432")),
        help="Database port"
    )
    parser.add_argument(
        "--db-name",
        default=os.getenv("DB_NAME", "thoughtprocessor"),
        help="Database name"
    )
    parser.add_argument(
        "--db-user",
        default=os.getenv("DB_USER", "thoughtprocessor"),
        help="Database user"
    )
    parser.add_argument(
        "--db-password",
        default=os.getenv("DB_PASSWORD", ""),
        help="Database password"
    )

    args = parser.parse_args()

    migrator = DataEncryptionMigrator(
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

    try:
        await migrator.connect()
        await migrator.run_migration()
    finally:
        await migrator.disconnect()


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    asyncio.run(main())
