"""
Authentication routes for user signup, login, and token management
"""
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from auth import (
    UserSignup,
    UserLogin,
    Token,
    UserResponse,
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    TokenData,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from database import get_db
from common.database.base import DatabaseAdapter

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, db: DatabaseAdapter = Depends(get_db)):
    """
    Create a new user account

    - **email**: User's email address (must be unique)
    - **password**: User's password (min 8 characters recommended)
    - **name**: Optional display name
    """
    try:
        # Check if user already exists - use the database pool directly
        async with db.pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                user_data.email
            )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create user - use the database pool directly
        user_id = str(uuid4())
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, name, created_at, subscription_plan)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id,
                user_data.email,
                hashed_password,
                user_data.name,
                datetime.utcnow(),
                'free'  # Default to free plan
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": user_id, "email": user_data.email}
        )

        logger.info(f"New user created: {user_data.email} (ID: {user_id})")

        return {
            "message": "Account created successfully",
            "user_id": user_id,
            "email": user_data.email,
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: DatabaseAdapter = Depends(get_db)):
    """
    Login with email and password

    Returns a JWT access token for authenticated requests
    """
    try:
        # Get user from database - use the database pool directly
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, password_hash, name FROM users WHERE email = $1",
                credentials.email
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token - convert UUID to string
        access_token = create_access_token(
            data={"sub": str(user['id']), "email": user['email']}
        )

        logger.info(f"User logged in: {credentials.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get current authenticated user's information

    Requires valid JWT token in Authorization header
    """
    try:
        # Get user from database - use the database pool directly
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, name, created_at FROM users WHERE id = $1",
                current_user.user_id
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(
            id=str(user['id']),
            email=user['email'],
            name=user.get('name'),
            created_at=user['created_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user information"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)):
    """
    Refresh the JWT access token

    Requires valid JWT token - returns a new token with extended expiration
    """
    access_token = create_access_token(
        data={"sub": current_user.user_id, "email": current_user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout():
    """
    Logout endpoint (client should discard the token)

    JWT tokens are stateless, so actual logout happens on client side
    """
    return {"message": "Logged out successfully"}
