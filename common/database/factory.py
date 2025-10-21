"""
Factory for creating database adapter instances
"""
from typing import Optional
from loguru import logger

from .base import DatabaseAdapter
from .postgres_adapter import PostgreSQLAdapter
# from .supabase_adapter import SupabaseAdapter  # Commented out - not using Supabase


class DatabaseFactory:
    """
    Factory for creating database adapter instances

    Usage:
        # PostgreSQL (local Docker)
        db = await DatabaseFactory.create(
            db_type="postgresql",
            host="localhost",
            database="thoughtprocessor",
            user="thoughtprocessor",
            password="password"
        )

        # Supabase (cloud)
        db = await DatabaseFactory.create(
            db_type="supabase",
            url="https://xxx.supabase.co",
            key="eyJxxx..."
        )
    """

    @staticmethod
    async def create(
        db_type: str,
        **kwargs
    ) -> DatabaseAdapter:
        """
        Create a database adapter instance

        Args:
            db_type: Type of database ("postgresql", "supabase")
            **kwargs: Database-specific connection parameters

        Returns:
            DatabaseAdapter instance

        Raises:
            ValueError: If db_type is not supported
        """
        db_type = db_type.lower()

        if db_type == "postgresql":
            logger.info("Creating PostgreSQL adapter")
            adapter = PostgreSQLAdapter(**kwargs)
            await adapter.connect()
            return adapter

        # elif db_type == "supabase":
        #     logger.info("Creating Supabase adapter")
        #     adapter = SupabaseAdapter(**kwargs)
        #     await adapter.connect()
        #     return adapter

        else:
            raise ValueError(
                f"Unsupported database type: {db_type}. "
                f"Supported types: postgresql"
            )

    @staticmethod
    def get_supported_databases() -> list:
        """Get list of supported database types"""
        return ["postgresql"]  # Supabase removed

    @staticmethod
    async def create_from_env(
        use_supabase: bool = False,
        **kwargs
    ) -> DatabaseAdapter:
        """
        Create database adapter based on environment

        Args:
            use_supabase: If True, use Supabase; otherwise PostgreSQL
            **kwargs: Additional connection parameters

        Returns:
            DatabaseAdapter instance
        """
        import os

        if use_supabase:
            raise ValueError("Supabase support is disabled. Use PostgreSQL only.")
            # url = os.getenv("SUPABASE_URL", kwargs.get("url"))
            # key = os.getenv("SUPABASE_KEY", kwargs.get("key"))
            # if not url or not key:
            #     raise ValueError(
            #         "SUPABASE_URL and SUPABASE_KEY must be set in environment"
            #     )
            # return await DatabaseFactory.create(
            #     db_type="supabase",
            #     url=url,
            #     key=key
            # )
        else:
            # PostgreSQL from DATABASE_URL or individual params
            database_url = os.getenv("DATABASE_URL")

            if database_url:
                # Parse DATABASE_URL
                # postgresql://user:password@host:port/database
                import re
                pattern = r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)"
                match = re.match(pattern, database_url)

                if match:
                    user, password, host, port, database = match.groups()
                    return await DatabaseFactory.create(
                        db_type="postgresql",
                        host=host,
                        port=int(port),
                        database=database,
                        user=user,
                        password=password
                    )

            # Use individual environment variables
            return await DatabaseFactory.create(
                db_type="postgresql",
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                database=os.getenv("POSTGRES_DB", "thoughtprocessor"),
                user=os.getenv("POSTGRES_USER", "thoughtprocessor"),
                password=os.getenv("POSTGRES_PASSWORD", "")
            )
