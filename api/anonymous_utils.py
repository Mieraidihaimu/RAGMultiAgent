"""
Utilities for managing anonymous user sessions and rate limiting
"""
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
from loguru import logger


def generate_session_token() -> str:
    """Generate a secure random session token for anonymous users"""
    return f"anon_{secrets.token_urlsafe(32)}"


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request, considering proxies"""
    # Check for X-Forwarded-For header (common in proxy/load balancer setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("User-Agent", "unknown")


async def create_anonymous_session(
    db,
    session_token: str,
    ip_address: str,
    user_agent: str
) -> Dict[str, Any]:
    """
    Create a new anonymous session in the database
    
    Args:
        db: Database adapter instance
        session_token: Unique session token
        ip_address: Client IP address
        user_agent: Client user agent
        
    Returns:
        Dictionary with session information
    """
    query = """
    INSERT INTO anonymous_sessions (session_token, ip_address, user_agent)
    VALUES ($1, $2, $3)
    RETURNING id, session_token, thought_count, created_at, expires_at
    """
    
    async with db.pool.acquire() as conn:
        result = await conn.fetchrow(query, session_token, ip_address, user_agent)
    
    if result:
        logger.info(f"Created anonymous session: {session_token[:20]}... from IP {ip_address}")
        return {
            "id": result["id"],
            "session_token": result["session_token"],
            "thought_count": result["thought_count"],
            "created_at": result["created_at"],
            "expires_at": result["expires_at"]
        }
    
    return None


async def get_anonymous_session(
    db,
    session_token: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an anonymous session by token
    
    Args:
        db: Database adapter instance
        session_token: Session token to lookup
        
    Returns:
        Dictionary with session information or None if not found/expired
    """
    query = """
    SELECT id, session_token, thought_count, created_at, expires_at, converted_to_user_id
    FROM anonymous_sessions
    WHERE session_token = $1
    AND expires_at > NOW()
    """
    
    async with db.pool.acquire() as conn:
        result = await conn.fetchrow(query, session_token)
    
    if result:
        return {
            "id": result["id"],
            "session_token": result["session_token"],
            "thought_count": result["thought_count"],
            "created_at": result["created_at"],
            "expires_at": result["expires_at"],
            "converted_to_user_id": result.get("converted_to_user_id")
        }
    
    return None


async def check_rate_limit(
    db,
    session_token: str,
    limit: int = 3
) -> Dict[str, Any]:
    """
    Check if anonymous session has reached rate limit
    
    Args:
        db: Database adapter instance
        session_token: Session token to check
        limit: Maximum number of thoughts allowed (default: 3)
        
    Returns:
        Dictionary with rate limit status
    """
    session = await get_anonymous_session(db, session_token)
    
    if not session:
        return {
            "valid": False,
            "limit_reached": True,
            "thoughts_remaining": 0,
            "thoughts_used": 0
        }
    
    thought_count = session["thought_count"]
    limit_reached = thought_count >= limit
    
    return {
        "valid": True,
        "limit_reached": limit_reached,
        "thoughts_remaining": max(0, limit - thought_count),
        "thoughts_used": thought_count
    }


async def increment_thought_count(
    db,
    session_token: str
) -> Dict[str, Any]:
    """
    Increment the thought count for an anonymous session
    
    Args:
        db: Database adapter instance
        session_token: Session token
        
    Returns:
        Dictionary with updated count and limit status
    """
    query = """
    SELECT * FROM increment_anonymous_thought_count($1)
    """
    
    async with db.pool.acquire() as conn:
        result = await conn.fetchrow(query, session_token)
    
    if result:
        thought_count = result["thought_count"]
        limit_reached = result["limit_reached"]
        
        logger.info(f"Incremented thought count for session {session_token[:20]}... to {thought_count}")
        
        return {
            "thought_count": thought_count,
            "limit_reached": limit_reached,
            "thoughts_remaining": max(0, 3 - thought_count)
        }
    
    return None


async def convert_anonymous_to_user(
    db,
    session_token: str,
    user_id: str
) -> int:
    """
    Convert anonymous thoughts to a registered user account
    
    Args:
        db: Database adapter instance
        session_token: Anonymous session token
        user_id: Target user ID
        
    Returns:
        Number of thoughts converted
    """
    query = """
    SELECT convert_anonymous_to_user($1, $2) as thoughts_converted
    """
    
    async with db.pool.acquire() as conn:
        result = await conn.fetchrow(query, session_token, user_id)
    
    if result:
        thoughts_converted = result["thoughts_converted"]
        logger.info(f"Converted {thoughts_converted} anonymous thoughts to user {user_id}")
        return thoughts_converted
    
    return 0


async def cleanup_expired_sessions(db):
    """
    Clean up expired anonymous sessions
    
    Args:
        db: Database adapter instance
    """
    query = "SELECT cleanup_expired_anonymous_sessions()"
    async with db.pool.acquire() as conn:
        await conn.execute(query)
    logger.info("Cleaned up expired anonymous sessions")
