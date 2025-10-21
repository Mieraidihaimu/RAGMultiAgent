"""
Database connection using Adapter Pattern
Supports multiple database backends (PostgreSQL, Supabase)
"""
import os
import sys
from typing import Optional
from loguru import logger

# Add common directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.database import DatabaseAdapter, DatabaseFactory


class DatabaseClient:
    """
    Singleton database client wrapper using Adapter Pattern

    Automatically selects database type based on environment variables:
    - If SUPABASE_URL is set: Use Supabase
    - Otherwise: Use local PostgreSQL
    """
    _instance: Optional[DatabaseAdapter] = None
    _initialized: bool = False

    @classmethod
    async def get_client(cls) -> DatabaseAdapter:
        """Get or create database adapter"""
        if cls._instance is None:
            await cls._initialize()
        return cls._instance

    @classmethod
    async def _initialize(cls):
        """Initialize database adapter based on environment"""
        if cls._initialized:
            return

        # Determine which database to use
        supabase_url = os.getenv("SUPABASE_URL")
        use_supabase = bool(supabase_url)

        try:
            logger.info(
                f"Initializing database adapter "
                f"(type: {'Supabase' if use_supabase else 'PostgreSQL'})"
            )

            cls._instance = await DatabaseFactory.create_from_env(
                use_supabase=use_supabase
            )

            # Test connection
            if await cls._instance.health_check():
                logger.info("Database connection successful")
            else:
                logger.warning("Database health check failed")

            cls._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @classmethod
    async def close(cls):
        """Close the database connection"""
        if cls._instance is not None:
            await cls._instance.disconnect()
            cls._instance = None
            cls._initialized = False
            logger.info("Database connection closed")


async def get_db() -> DatabaseAdapter:
    """FastAPI dependency for database access"""
    return await DatabaseClient.get_client()
