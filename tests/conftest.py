"""
Pytest configuration and fixtures for integration tests
"""
import asyncio
import os
from typing import AsyncGenerator

import httpx
import pytest
import asyncpg
import pytest_asyncio


# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
DB_URL = os.getenv("DATABASE_URL", "postgresql://thoughtprocessor:changeme@db:5432/thoughtprocessor")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client for API requests"""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Database connection pool"""
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=5)
    yield pool
    await pool.close()


@pytest_asyncio.fixture
async def clean_test_data(db_pool):
    """Clean up test data before and after tests - optional fixture"""
    # Skip cleanup if there's bad data that would cause constraint violations
    try:
        async with db_pool.acquire() as conn:
            # Delete in order: thoughts first (has FKs), then sessions, then users  
            await conn.execute("DELETE FROM thoughts WHERE text LIKE '%TEST_%' OR text LIKE '%TEST_ANON%'")
            await conn.execute("DELETE FROM thoughts WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%test@integration%')")
            await conn.execute("DELETE FROM users WHERE email LIKE '%test@integration%'")
    except Exception as e:
        print(f"Warning: Could not clean test data before test: {e}")
    
    yield
    
    # Clean after test
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM thoughts WHERE text LIKE '%TEST_%' OR text LIKE '%TEST_ANON%'")
            await conn.execute("DELETE FROM thoughts WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%test@integration%')")
            await conn.execute("DELETE FROM users WHERE email LIKE '%test@integration%'")
    except Exception as e:
        print(f"Warning: Could not clean test data after test: {e}")
