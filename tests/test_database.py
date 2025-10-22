"""
Integration tests for database operations
"""
import pytest
import asyncpg
from uuid import uuid4
from datetime import datetime


@pytest.mark.asyncio
async def test_database_connection(db_pool: asyncpg.Pool):
    """Test database connectivity"""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1


@pytest.mark.asyncio
async def test_create_and_retrieve_user(db_pool: asyncpg.Pool, clean_test_data):
    """Test creating and retrieving a user"""
    user_id = str(uuid4())
    email = "test@integration.db.com"
    
    async with db_pool.acquire() as conn:
        # Create user
        await conn.execute(
            """
            INSERT INTO users (id, email, created_at, subscription_plan)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, email, datetime.utcnow(), 'free'
        )
        
        # Retrieve user
        user = await conn.fetchrow(
            "SELECT id, email, subscription_plan FROM users WHERE id = $1",
            user_id
        )
        
        assert user is not None
        assert str(user['id']) == user_id
        assert user['email'] == email
        assert user['subscription_plan'] == 'free'


@pytest.mark.asyncio
async def test_create_and_retrieve_thought(db_pool: asyncpg.Pool, clean_test_data):
    """Test creating and retrieving a thought"""
    # First create a user
    user_id = str(uuid4())
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email, created_at, subscription_plan)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, "test@integration.thought.com", datetime.utcnow(), 'free'
        )
        
        # Create thought
        thought_id = await conn.fetchval(
            """
            INSERT INTO thoughts (user_id, text, status, created_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            user_id, "TEST_DB: Integration test thought", "pending", datetime.utcnow()
        )
        
        assert thought_id is not None
        
        # Retrieve thought
        thought = await conn.fetchrow(
            "SELECT id, user_id, text, status FROM thoughts WHERE id = $1",
            thought_id
        )
        
        assert thought is not None
        assert str(thought['user_id']) == user_id
        assert thought['text'] == "TEST_DB: Integration test thought"
        assert thought['status'] == "pending"


@pytest.mark.asyncio
async def test_anonymous_session_creation(db_pool: asyncpg.Pool, clean_test_data):
    """Test creating anonymous session"""
    session_token = f"test_session_{uuid4()}"
    
    async with db_pool.acquire() as conn:
        # Create anonymous session
        session_id = await conn.fetchval(
            """
            INSERT INTO anonymous_sessions (session_token, ip_address, user_agent, created_at, thought_count)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            session_token, "127.0.0.1", "test-agent", datetime.utcnow(), 0
        )
        
        assert session_id is not None
        
        # Retrieve session
        session = await conn.fetchrow(
            "SELECT session_token, thought_count FROM anonymous_sessions WHERE id = $1",
            session_id
        )
        
        assert session is not None
        assert session['session_token'] == session_token
        assert session['thought_count'] == 0
