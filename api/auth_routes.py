"""
Authentication routes for user signup, login, and token management
"""
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Request
from loguru import logger
from typing import List

from auth import (
    UserSignup,
    UserLogin,
    Token,
    UserResponse,
    ConsentUpdate,
    ConsentHistoryResponse,
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    TokenData,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from database import get_db
from common.database.base import DatabaseAdapter
from anonymous_utils import convert_anonymous_to_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/convert-anonymous", status_code=status.HTTP_200_OK)
async def convert_anonymous_session(
    session_token: str,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Convert anonymous thoughts to a registered user account
    
    This should be called after signup/login to transfer any thoughts
    created during anonymous browsing to the user's account.
    
    - **session_token**: The anonymous session token from local storage
    """
    try:
        thoughts_converted = await convert_anonymous_to_user(
            db, session_token, current_user.user_id
        )
        
        logger.info(f"Converted {thoughts_converted} anonymous thoughts to user {current_user.email}")
        
        return {
            "message": f"Successfully transferred {thoughts_converted} thoughts to your account",
            "thoughts_converted": thoughts_converted
        }
        
    except Exception as e:
        logger.error(f"Error converting anonymous session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert anonymous session"
        )


@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup, request: Request, db: DatabaseAdapter = Depends(get_db)):
    """
    Create a new user account with GDPR-compliant consent tracking

    - **email**: User's email address (must be unique)
    - **password**: User's password (min 8 characters recommended)
    - **name**: Optional display name
    - **consent**: Required consent information (terms, privacy, optional marketing/analytics)
    """
    try:
        # Validate required consents (GDPR compliance)
        if not user_data.consent.terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the Terms of Service to create an account"
            )

        if not user_data.consent.privacy_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the Privacy Policy to create an account"
            )

        if not user_data.consent.data_processing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data processing consent is required for this service to function"
            )

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

        # Get client IP and user agent for consent audit trail
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")

        # Create user with consent tracking - use the database pool directly
        user_id = str(uuid4())
        current_time = datetime.utcnow()

        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (
                    id, email, password_hash, name, created_at, subscription_plan,
                    consent_terms_accepted, consent_terms_accepted_at, consent_terms_version,
                    consent_privacy_accepted, consent_privacy_accepted_at, consent_privacy_version,
                    consent_marketing, consent_marketing_at,
                    consent_analytics, consent_analytics_at,
                    consent_data_processing, consent_data_processing_at,
                    consent_ip_address, consent_user_agent,
                    data_retention_acknowledged
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                """,
                user_id,
                user_data.email,
                hashed_password,
                user_data.name,
                current_time,
                'free',  # Default to free plan
                user_data.consent.terms_accepted,
                current_time,
                user_data.consent.terms_version,
                user_data.consent.privacy_accepted,
                current_time,
                user_data.consent.privacy_version,
                user_data.consent.marketing,
                current_time if user_data.consent.marketing else None,
                user_data.consent.analytics,
                current_time if user_data.consent.analytics else None,
                user_data.consent.data_processing,
                current_time,
                client_ip,
                user_agent,
                True  # User acknowledged data retention during signup
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": user_id, "email": user_data.email}
        )

        logger.info(f"New user created with consent tracking: {user_data.email} (ID: {user_id})")

        return {
            "message": "Account created successfully",
            "user_id": user_id,
            "email": user_data.email,
            "access_token": access_token,
            "token_type": "bearer",
            "consent_recorded": {
                "terms": user_data.consent.terms_accepted,
                "privacy": user_data.consent.privacy_accepted,
                "marketing": user_data.consent.marketing,
                "analytics": user_data.consent.analytics
            }
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

# ============================================================================
# CONSENT MANAGEMENT ENDPOINTS (GDPR Compliance)
# ============================================================================

@router.get("/consent/status")
async def get_consent_status(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get current user's consent status for all consent types

    Returns detailed consent information including:
    - Required consents (terms, privacy, data processing)
    - Optional consents (marketing, analytics)
    - Timestamps and versions
    """
    try:
        async with db.pool.acquire() as conn:
            consent_data = await conn.fetchrow(
                """
                SELECT
                    consent_terms_accepted,
                    consent_terms_accepted_at,
                    consent_terms_version,
                    consent_privacy_accepted,
                    consent_privacy_accepted_at,
                    consent_privacy_version,
                    consent_marketing,
                    consent_marketing_at,
                    consent_analytics,
                    consent_analytics_at,
                    consent_data_processing,
                    consent_data_processing_at,
                    data_retention_acknowledged
                FROM users
                WHERE id = $1
                """,
                current_user.user_id
            )

        if not consent_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "required_consents": {
                "terms": {
                    "accepted": consent_data['consent_terms_accepted'],
                    "accepted_at": consent_data['consent_terms_accepted_at'],
                    "version": consent_data['consent_terms_version']
                },
                "privacy": {
                    "accepted": consent_data['consent_privacy_accepted'],
                    "accepted_at": consent_data['consent_privacy_accepted_at'],
                    "version": consent_data['consent_privacy_version']
                },
                "data_processing": {
                    "accepted": consent_data['consent_data_processing'],
                    "accepted_at": consent_data['consent_data_processing_at']
                }
            },
            "optional_consents": {
                "marketing": {
                    "accepted": consent_data['consent_marketing'],
                    "accepted_at": consent_data['consent_marketing_at']
                },
                "analytics": {
                    "accepted": consent_data['consent_analytics'],
                    "accepted_at": consent_data['consent_analytics_at']
                }
            },
            "data_retention_acknowledged": consent_data['data_retention_acknowledged']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching consent status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch consent status"
        )

@router.put("/consent/update")
async def update_consent(
    consent_update: ConsentUpdate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Update user's optional consent preferences (marketing, analytics)

    Required consents (terms, privacy, data processing) cannot be withdrawn
    while maintaining an active account. Users must delete their account
    to withdraw required consents (GDPR right to erasure).
    """
    try:
        # Get client IP and user agent for audit trail
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        current_time = datetime.utcnow()

        update_fields = []
        update_values = []
        param_counter = 1

        if consent_update.marketing is not None:
            update_fields.append(f"consent_marketing = ${param_counter}")
            update_values.append(consent_update.marketing)
            param_counter += 1

            update_fields.append(f"consent_marketing_at = ${param_counter}")
            update_values.append(current_time)
            param_counter += 1

        if consent_update.analytics is not None:
            update_fields.append(f"consent_analytics = ${param_counter}")
            update_values.append(consent_update.analytics)
            param_counter += 1

            update_fields.append(f"consent_analytics_at = ${param_counter}")
            update_values.append(current_time)
            param_counter += 1

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No consent preferences provided for update"
            )

        # Update IP and user agent for audit trail
        update_fields.append(f"consent_ip_address = ${param_counter}")
        update_values.append(client_ip)
        param_counter += 1

        update_fields.append(f"consent_user_agent = ${param_counter}")
        update_values.append(user_agent)
        param_counter += 1

        # Add user_id as the last parameter
        update_values.append(current_user.user_id)

        async with db.pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE users
                SET {', '.join(update_fields)}
                WHERE id = ${param_counter}
                """,
                *update_values
            )

        logger.info(f"Consent preferences updated for user: {current_user.email}")

        return {
            "message": "Consent preferences updated successfully",
            "updated_at": current_time
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating consent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update consent preferences"
        )

@router.get("/consent/history", response_model=List[ConsentHistoryResponse])
async def get_consent_history(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get complete history of all consent changes for the current user

    This provides an audit trail as required by GDPR Article 7.1
    (burden of proof that consent was given)
    """
    try:
        async with db.pool.acquire() as conn:
            history = await conn.fetch(
                """
                SELECT
                    id,
                    consent_type,
                    consent_given,
                    consent_version,
                    consent_timestamp,
                    action
                FROM consent_history
                WHERE user_id = $1
                ORDER BY consent_timestamp DESC
                """,
                current_user.user_id
            )

        return [
            ConsentHistoryResponse(
                id=str(record['id']),
                consent_type=record['consent_type'],
                consent_given=record['consent_given'],
                consent_version=record['consent_version'],
                consent_timestamp=record['consent_timestamp'],
                action=record['action']
            )
            for record in history
        ]

    except Exception as e:
        logger.error(f"Error fetching consent history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch consent history"
        )

@router.delete("/consent/withdraw-all")
async def withdraw_all_consents(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Withdraw all consents and deactivate account (GDPR right to withdraw consent)

    This is part of the GDPR "right to erasure" process. The account will be
    marked for deletion and the user will be logged out.

    Note: This does not immediately delete data. It initiates the deletion process
    which may take up to 30 days to complete (standard data retention period).
    """
    try:
        async with db.pool.acquire() as conn:
            # Update account status to inactive and record consent withdrawal
            await conn.execute(
                """
                UPDATE users
                SET
                    account_status = 'deleted',
                    consent_marketing = false,
                    consent_analytics = false
                WHERE id = $1
                """,
                current_user.user_id
            )

            # Log the withdrawal action
            await conn.execute(
                """
                INSERT INTO consent_history (
                    user_id, consent_type, consent_given, action, notes
                )
                VALUES
                    ($1, 'marketing', false, 'withdraw', 'User requested account deletion'),
                    ($1, 'analytics', false, 'withdraw', 'User requested account deletion')
                """,
                current_user.user_id
            )

        logger.info(f"User {current_user.email} withdrew all consents and requested account deletion")

        return {
            "message": "All consents withdrawn. Your account has been marked for deletion.",
            "deletion_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "note": "Your data will be permanently deleted within 30 days. You can contact support to cancel this request within this period."
        }

    except Exception as e:
        logger.error(f"Error withdrawing consents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process consent withdrawal"
        )
