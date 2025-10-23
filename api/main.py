"""
FastAPI backend for AI Thought Processor
Main API server with endpoints for thought management
Supports Kafka streaming and SSE real-time updates
"""
import os
import asyncio
import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from models import (
    ThoughtInput,
    ThoughtResponse,
    ThoughtsListResponse,
    ThoughtDetail,
    UserResponse,
    UserContextUpdate,
    WeeklySynthesisResponse,
    HealthResponse,
    ErrorResponse,
    AnonymousThoughtInput,
    AnonymousSessionResponse,
    PersonaInput,
    PersonaResponse,
    PersonaGroupInput,
    PersonaGroupResponse,
    PersonaGroupListResponse
)
from database import get_db
from common.database.base import DatabaseAdapter
from anonymous_utils import (
    generate_session_token,
    get_client_ip,
    get_user_agent,
    create_anonymous_session,
    get_anonymous_session,
    check_rate_limit,
    increment_thought_count,
    convert_anonymous_to_user
)

# Import Kafka and SSE components
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "false").lower() == "true"

if KAFKA_ENABLED:
    try:
        from sse_starlette.sse import EventSourceResponse
        from kafka.producer import get_kafka_producer, close_kafka_producer
        from sse import get_sse_manager, close_sse_manager
        from models import SSEEvent
        KAFKA_AVAILABLE = True
        logger.info("Kafka streaming enabled")
    except ImportError as e:
        logger.warning(f"Kafka/SSE libraries not available: {e}")
        KAFKA_AVAILABLE = False
        KAFKA_ENABLED = False
else:
    KAFKA_AVAILABLE = False
    logger.info("Kafka streaming disabled")

# Import authentication
try:
    from auth_routes import router as auth_router
    from auth import get_current_user, TokenData
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logger.warning("Auth routes not available")

# Import payment routes
try:
    from payment_routes import router as payment_router
    PAYMENT_ROUTES_AVAILABLE = True
except ImportError:
    PAYMENT_ROUTES_AVAILABLE = False
    logger.warning("Payment routes not available - stripe package may not be installed")

# Import search routes
try:
    from search_routes import router as search_router
    from search_service import get_search_service, close_search_service
    SEARCH_AVAILABLE = True
except ImportError as e:
    SEARCH_AVAILABLE = False
    logger.warning(f"Search routes not available: {e}")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Configure logging
logger.add(
    "logs/api.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

# Initialize FastAPI app
app = FastAPI(
    title="AI Thought Processor API",
    description="REST API for personal thought processing with AI analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize Prometheus metrics instrumentation
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")

# Add Gzip compression middleware
# Compresses responses > 1KB for improved performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
if AUTH_AVAILABLE:
    app.include_router(auth_router)
    logger.info("Authentication routes enabled")

# Include payment routes if available
if PAYMENT_ROUTES_AVAILABLE:
    app.include_router(payment_router)
    logger.info("Payment routes enabled")

# Include search routes if available
if SEARCH_AVAILABLE:
    app.include_router(search_router)
    logger.info("Search routes enabled")


# Lifecycle events for Kafka/Redis
@app.on_event("startup")
async def startup_event():
    """Initialize Kafka producer and SSE manager on startup"""
    if KAFKA_ENABLED and KAFKA_AVAILABLE:
        try:
            # Initialize Kafka producer
            await get_kafka_producer()
            logger.info("Kafka producer initialized")

            # Initialize SSE manager
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            await get_sse_manager(redis_url)
            logger.info("SSE manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka/Redis: {e}")
            logger.warning("Continuing without Kafka/SSE support")
    
    # Initialize search service if available
    if SEARCH_AVAILABLE:
        try:
            await get_search_service()
            logger.info("Search service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize search service: {e}")
            logger.warning("Continuing without search support")


@app.on_event("shutdown")
async def shutdown_event():
    """Close Kafka producer and SSE manager on shutdown"""
    if KAFKA_ENABLED and KAFKA_AVAILABLE:
        try:
            await close_kafka_producer()
            logger.info("Kafka producer closed")

            await close_sse_manager()
            logger.info("SSE manager closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    # Close search service if available
    if SEARCH_AVAILABLE:
        try:
            await close_search_service()
            logger.info("Search service closed")
        except Exception as e:
            logger.error(f"Error closing search service: {e}")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "message": "AI Thought Processor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: DatabaseAdapter = Depends(get_db)):
    """Health check endpoint with database connectivity test"""
    try:
        # Test database connection
        is_healthy = await db.health_check()
        db_status = "connected" if is_healthy else "error"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database=db_status
    )


@app.post(
    "/anonymous/thoughts",
    response_model=ThoughtResponse,
    status_code=201,
    tags=["Anonymous"]
)
async def create_anonymous_thought(
    thought: AnonymousThoughtInput,
    request: Request,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a thought as an anonymous user (no authentication required)
    
    Anonymous users can submit up to 3 thoughts before needing to sign up.
    If no session_token is provided, a new session will be created.
    
    Returns the thought along with session info showing remaining thoughts.
    """
    try:
        # Get or create anonymous session
        session_token = thought.session_token
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        if not session_token:
            # Create new anonymous session
            session_token = generate_session_token()
            session = await create_anonymous_session(
                db, session_token, ip_address, user_agent
            )
            if not session:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create anonymous session"
                )
        else:
            # Verify existing session
            session = await get_anonymous_session(db, session_token)
            if not session:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired session token"
                )
            
            # Check if session was already converted to a user
            if session.get("converted_to_user_id"):
                raise HTTPException(
                    status_code=403,
                    detail="This session has been converted to a registered account. Please log in."
                )
        
        # Check rate limit
        rate_limit = await check_rate_limit(db, session_token)
        if rate_limit["limit_reached"]:
            raise HTTPException(
                status_code=429,
                detail="You've reached the limit of 3 free thoughts. Please sign up to continue!",
                headers={"X-Rate-Limit-Reached": "true"}
            )
        
        # Create the thought
        query = """
        INSERT INTO thoughts (anonymous_session_id, text, status)
        VALUES (
            (SELECT id FROM anonymous_sessions WHERE session_token = $1),
            $2,
            'pending'
        )
        RETURNING id, text, status, created_at
        """
        
        async with db.pool.acquire() as conn:
            thought_data = await conn.fetchrow(query, session_token, thought.text)
        
        if not thought_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create thought"
            )
        
        logger.info(f"Created anonymous thought {thought_data['id']} for session {session_token[:20]}...")
        
        # Increment thought count
        count_info = await increment_thought_count(db, session_token)
        
        # Prepare session info for response
        session_info = AnonymousSessionResponse(
            session_token=session_token,
            thoughts_remaining=count_info["thoughts_remaining"],
            thoughts_used=count_info["thought_count"],
            limit_reached=count_info["limit_reached"]
        )
        
        # If Kafka is enabled, publish event for real-time processing
        if KAFKA_ENABLED and KAFKA_AVAILABLE:
            try:
                kafka_producer = await get_kafka_producer()
                sse_manager = await get_sse_manager()

                # Publish to Kafka topic with anonymous flag
                success = await kafka_producer.send_thought_created(
                    user_id=None,  # No user ID for anonymous
                    thought_id=str(thought_data["id"]),
                    text=thought.text,
                    user_context={},  # No context for anonymous users
                    anonymous_session=session_token
                )

                if success:
                    message = "Thought saved! Processing started..."
                    logger.info(f"Published anonymous thought {thought_data['id']} to Kafka")
                else:
                    message = "Thought saved! Will be processed soon."
                    logger.warning(f"Failed to publish anonymous thought {thought_data['id']} to Kafka")

            except Exception as kafka_error:
                logger.error(f"Kafka publishing error: {kafka_error}")
                message = "Thought saved! Will be processed in next batch."
        else:
            # Batch mode message
            message = "Thought saved! It will be analyzed tonight."
        
        return ThoughtResponse(
            id=thought_data["id"],
            status="pending",
            message=message,
            created_at=thought_data["created_at"],
            session_info=session_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating anonymous thought: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/anonymous/session/{session_token}",
    response_model=AnonymousSessionResponse,
    tags=["Anonymous"]
)
async def get_anonymous_session_info(
    session_token: str,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get information about an anonymous session including remaining thoughts
    """
    try:
        session = await get_anonymous_session(db, session_token)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )
        
        rate_limit = await check_rate_limit(db, session_token)
        
        return AnonymousSessionResponse(
            session_token=session_token,
            thoughts_remaining=rate_limit["thoughts_remaining"],
            thoughts_used=rate_limit["thoughts_used"],
            limit_reached=rate_limit["limit_reached"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting anonymous session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/anonymous/thoughts/{session_token}",
    response_model=ThoughtsListResponse,
    tags=["Anonymous"]
)
async def get_anonymous_thoughts(
    session_token: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get all thoughts for an anonymous session
    """
    try:
        # Verify session exists
        session = await get_anonymous_session(db, session_token)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )
        
        # Build query with optional status filter
        async with db.pool.acquire() as conn:
            if status:
                query = """
                SELECT t.id, t.anonymous_session_id::text as user_id, t.text, t.status, 
                       t.created_at, t.processed_at, t.classification, t.analysis,
                       t.value_impact, t.action_plan, t.priority
                FROM thoughts t
                WHERE t.anonymous_session_id = (
                    SELECT id FROM anonymous_sessions WHERE session_token = $1
                )
                AND t.status = $2
                ORDER BY t.created_at DESC
                """
                result = await conn.fetch(query, session_token, status)
            else:
                query = """
                SELECT t.id, t.anonymous_session_id::text as user_id, t.text, t.status,
                       t.created_at, t.processed_at, t.classification, t.analysis,
                       t.value_impact, t.action_plan, t.priority
                FROM thoughts t
                WHERE t.anonymous_session_id = (
                    SELECT id FROM anonymous_sessions WHERE session_token = $1
                )
                ORDER BY t.created_at DESC
                """
                result = await conn.fetch(query, session_token)
        
        thoughts = [ThoughtDetail(**dict(item)) for item in result] if result else []
        
        return ThoughtsListResponse(
            thoughts=thoughts,
            count=len(thoughts),
            status_filter=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving anonymous thoughts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/thoughts",
    response_model=ThoughtResponse,
    status_code=201,
    tags=["Thoughts"]
)
async def create_thought(
    thought: ThoughtInput,
    current_user: TokenData = Depends(get_current_user) if AUTH_AVAILABLE else None,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a new thought for processing

    Supports two processing modes:
    - 'single' (default): Personal LLM feedback using the 5-agent pipeline
    - 'group': Multiple persona perspectives with AI-powered consolidation
    
    For group mode, group_id must be provided and must belong to the user.

    With Kafka enabled: Published to Kafka topic for real-time processing
    Without Kafka: Saved with 'pending' status for batch processing

    Requires authentication (if enabled).
    """
    try:
        # If auth is enabled, verify the user_id matches the authenticated user
        if AUTH_AVAILABLE and current_user:
            if str(thought.user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot create thoughts for other users"
                )

        # Verify user exists
        user = await db.get_user(str(thought.user_id))
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User {thought.user_id} not found"
            )

        # Validate group mode requirements
        processing_mode = thought.processing_mode or "single"
        group_id = thought.group_id
        
        if processing_mode not in ["single", "group"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid processing_mode. Must be 'single' or 'group'"
            )
        
        if processing_mode == "group":
            if not group_id:
                raise HTTPException(
                    status_code=400,
                    detail="group_id is required when processing_mode is 'group'"
                )
            
            # Verify group exists and belongs to user
            group = await db.get_persona_group(str(group_id), include_personas=True)
            if not group:
                raise HTTPException(
                    status_code=404,
                    detail=f"Persona group {group_id} not found"
                )
            
            if str(group['user_id']) != str(thought.user_id):
                raise HTTPException(
                    status_code=403,
                    detail="Cannot use other users' persona groups"
                )
            
            # Check if group has personas
            if not group.get('personas'):
                raise HTTPException(
                    status_code=400,
                    detail="Persona group must have at least one persona"
                )
            
            logger.info(f"Creating group thought with {len(group['personas'])} personas from group '{group['name']}'")

        # Insert thought into database
        thought_data = await db.create_thought(
            user_id=str(thought.user_id),
            text=thought.text,
            processing_mode=processing_mode,
            group_id=str(group_id) if group_id else None
        )

        if not thought_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create thought"
            )

        logger.info(f"Created thought {thought_data['id']} for user {thought.user_id} (mode: {processing_mode})")

        # If Kafka is enabled, publish event for real-time processing
        if KAFKA_ENABLED and KAFKA_AVAILABLE:
            try:
                kafka_producer = await get_kafka_producer()
                sse_manager = await get_sse_manager()

                # Get user context as dict
                user_context = user.get("context", {})
                if isinstance(user_context, str):
                    import json
                    try:
                        user_context = json.loads(user_context)
                    except:
                        user_context = {}

                # Publish to Kafka topic
                success = await kafka_producer.send_thought_created(
                    user_id=str(thought.user_id),
                    thought_id=str(thought_data["id"]),
                    text=thought.text,
                    user_context=user_context,
                    processing_mode=processing_mode,
                    group_id=str(group_id) if group_id else None
                )

                if success:
                    # Broadcast SSE event (thought created)
                    await sse_manager.broadcast_thought_created(
                        user_id=str(thought.user_id),
                        thought_id=str(thought_data["id"])
                    )

                    if processing_mode == "group":
                        message = f"Thought saved! Processing with {len(group['personas'])} personas..."
                    else:
                        message = "Thought saved! Processing started..."
                    
                    logger.info(f"Published thought {thought_data['id']} to Kafka")
                else:
                    message = "Thought saved! Will be processed soon."
                    logger.warning(f"Failed to publish thought {thought_data['id']} to Kafka")

            except Exception as kafka_error:
                logger.error(f"Kafka publishing error: {kafka_error}")
                message = "Thought saved! Will be processed in next batch."
        else:
            # Batch mode message
            message = "Thought saved! It will be analyzed tonight."

        return ThoughtResponse(
            id=thought_data["id"],
            status="pending",
            message=message,
            created_at=thought_data["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating thought: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/thoughts/{user_id}",
    response_model=ThoughtsListResponse,
    tags=["Thoughts"]
)
async def get_thoughts(
    user_id: UUID,
    current_user: TokenData = Depends(get_current_user) if AUTH_AVAILABLE else None,
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed"),
    limit: int = Query(50, ge=1, le=100, description="Number of thoughts to return"),
    offset: int = Query(0, ge=0, description="Number of thoughts to skip"),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get thoughts for a specific user with optional filtering
    
    Requires authentication - users can only access their own thoughts.
    """
    try:
        # If auth is enabled, verify the user_id matches the authenticated user
        if AUTH_AVAILABLE and current_user:
            if str(user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot access other users' thoughts"
                )
        
        if status and status not in ["pending", "processing", "completed", "failed"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be: pending, processing, completed, or failed"
            )

        thoughts_data = await db.get_thoughts(
            user_id=str(user_id),
            status=status,
            limit=limit,
            offset=offset
        )

        thoughts = [ThoughtDetail(**item) for item in thoughts_data]

        logger.info(f"Retrieved {len(thoughts)} thoughts for user {user_id}")

        return ThoughtsListResponse(
            thoughts=thoughts,
            count=len(thoughts),
            status_filter=status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving thoughts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/thoughts/{user_id}/{thought_id}",
    response_model=ThoughtDetail,
    tags=["Thoughts"]
)
async def get_thought(
    user_id: UUID,
    thought_id: UUID,
    current_user: TokenData = Depends(get_current_user) if AUTH_AVAILABLE else None,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get a specific thought by ID
    
    Requires authentication - users can only access their own thoughts.
    """
    try:
        # If auth is enabled, verify the user_id matches the authenticated user
        if AUTH_AVAILABLE and current_user:
            if str(user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot access other users' thoughts"
                )
        
        thought = await db.get_thought(
            thought_id=str(thought_id),
            user_id=str(user_id)
        )

        if not thought:
            raise HTTPException(
                status_code=404,
                detail=f"Thought {thought_id} not found for user {user_id}"
            )

        return ThoughtDetail(**thought)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving thought: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/thoughts/{user_id}/{thought_id}",
    status_code=204,
    tags=["Thoughts"]
)
async def delete_thought(
    user_id: UUID,
    thought_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """Delete a specific thought"""
    try:
        deleted = await db.delete_thought(
            thought_id=str(thought_id),
            user_id=str(user_id)
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Thought {thought_id} not found for user {user_id}"
            )

        logger.info(f"Deleted thought {thought_id} for user {user_id}")
        return

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting thought: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
    tags=["Users"]
)
async def get_user(
    user_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """Get user information"""
    try:
        user = await db.get_user(str(user_id))

        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )

        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/users/{user_id}/context",
    response_model=UserResponse,
    tags=["Users"]
)
async def update_user_context(
    user_id: UUID,
    context_update: UserContextUpdate,
    db: DatabaseAdapter = Depends(get_db)
):
    """Update user context"""
    try:
        updated_user = await db.update_user_context(
            user_id=str(user_id),
            context=context_update.context
        )

        if not updated_user:
            raise HTTPException(
                status_code=404,
                detail=f"User {user_id} not found"
            )

        logger.info(f"Updated context for user {user_id}")
        return UserResponse(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/synthesis/{user_id}/latest",
    response_model=WeeklySynthesisResponse,
    tags=["Synthesis"]
)
async def get_latest_synthesis(
    user_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """Get the most recent weekly synthesis for a user"""
    try:
        synthesis = await db.get_latest_synthesis(str(user_id))

        if not synthesis:
            raise HTTPException(
                status_code=404,
                detail="No synthesis available yet"
            )

        return WeeklySynthesisResponse(**synthesis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving synthesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/synthesis/{user_id}",
    response_model=List[WeeklySynthesisResponse],
    tags=["Synthesis"]
)
async def get_all_syntheses(
    user_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: DatabaseAdapter = Depends(get_db)
):
    """Get all weekly syntheses for a user"""
    try:
        syntheses_data = await db.get_syntheses(
            user_id=str(user_id),
            limit=limit
        )

        syntheses = [WeeklySynthesisResponse(**item) for item in syntheses_data]
        return syntheses

    except Exception as e:
        logger.error(f"Error retrieving syntheses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/process/trigger",
    tags=["Processing"],
    response_model=dict
)
async def trigger_processing():
    """
    Trigger manual batch processing
    Note: This is a simple trigger - actual processing happens in the batch-processor service
    """
    try:
        logger.info("Manual processing triggered via API")
        return {
            "status": "triggered",
            "message": "Processing will begin shortly. The batch processor runs continuously in the background.",
            "note": "Check thought status after a few seconds"
        }
    except Exception as e:
        logger.error(f"Error triggering processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/events/{user_id}",
    tags=["SSE"]
)
async def stream_events(
    user_id: UUID,
    request: Request,
    token: Optional[str] = Query(None, description="Auth token for SSE (since EventSource can't send headers)")
):
    """
    Server-Sent Events endpoint for real-time thought updates
    
    Streams events like:
    - thought_created: New thought submitted
    - thought_processing: Thought analysis started
    - thought_agent_completed: Individual agent finished
    - thought_completed: Full analysis complete
    - thought_failed: Processing error
    
    Requires authentication - users can only subscribe to their own events.
    Note: Token passed as query param since EventSource doesn't support custom headers.
    """
    if not KAFKA_ENABLED or not KAFKA_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Real-time updates not available. Kafka/SSE not enabled."
        )
    
    # Verify authentication via query param token
    if AUTH_AVAILABLE and token:
        try:
            from auth import decode_access_token
            current_user = decode_access_token(token)
            
            # Verify user can only access their own events
            if str(user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot access other users' event streams"
                )
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
    elif AUTH_AVAILABLE:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Pass token as query parameter."
        )
    
    try:
        sse_manager = await get_sse_manager()
        
        async def event_generator():
            """Generate SSE events from Redis pub/sub"""
            pubsub = None
            try:
                # Subscribe to user's Redis channel
                pubsub = await sse_manager.subscribe(str(user_id))
                
                # Send initial connection event
                yield {
                    "event": "connected",
                    "data": json.dumps({
                        "message": "SSE connection established",
                        "user_id": str(user_id),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
                
                logger.info(f"SSE stream started for user {user_id}")
                
                # Listen for messages
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            payload = json.loads(message["data"])
                            event_type = payload.get("event", "message")
                            event_data = payload.get("data", {})
                            event_id = payload.get("event_id")
                            
                            # Format as SSE
                            sse_event = {
                                "event": event_type,
                                "data": json.dumps(event_data)
                            }
                            
                            if event_id:
                                sse_event["id"] = event_id
                            
                            yield sse_event
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in Redis message: {e}")
                            continue
                    
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.info(f"Client disconnected: user {user_id}")
                        break
                        
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
            finally:
                if pubsub:
                    await sse_manager.unsubscribe(str(user_id), pubsub)
                logger.info(f"SSE stream closed for user {user_id}")
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        logger.error(f"Failed to create SSE stream: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to establish SSE connection: {str(e)}"
        )


# ============================================================================
# Persona Group Endpoints
# ============================================================================

@app.post(
    "/groups",
    response_model=PersonaGroupResponse,
    tags=["Persona Groups"],
    status_code=201
)
@limiter.limit("20/minute")
async def create_persona_group(
    request: Request,
    group_input: PersonaGroupInput,
    user_id: UUID = Query(..., description="User ID"),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a new persona group
    
    Limits: 10 groups per user
    """
    try:
        # Check existing group count
        existing_groups = await db.get_persona_groups(str(user_id), include_personas=False)
        if len(existing_groups) >= 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 persona groups allowed per user"
            )
        
        # Create group
        group = await db.create_persona_group(
            user_id=str(user_id),
            name=group_input.name,
            description=group_input.description
        )
        
        # Add empty personas list
        group['personas'] = []
        
        logger.info(f"Created persona group {group['id']} for user {user_id}")
        return PersonaGroupResponse(**group)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating persona group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/groups",
    response_model=PersonaGroupListResponse,
    tags=["Persona Groups"]
)
@limiter.limit("60/minute")
async def list_persona_groups(
    request: Request,
    user_id: UUID = Query(..., description="User ID"),
    include_personas: bool = Query(True, description="Include personas in response"),
    db: DatabaseAdapter = Depends(get_db)
):
    """Get all persona groups for a user"""
    try:
        groups = await db.get_persona_groups(str(user_id), include_personas=include_personas)
        
        return PersonaGroupListResponse(
            groups=[PersonaGroupResponse(**g) for g in groups],
            count=len(groups)
        )
        
    except Exception as e:
        logger.error(f"Error listing persona groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/groups/{group_id}",
    response_model=PersonaGroupResponse,
    tags=["Persona Groups"]
)
@limiter.limit("60/minute")
async def get_persona_group(
    request: Request,
    group_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """Get a specific persona group with its personas"""
    try:
        group = await db.get_persona_group(str(group_id), include_personas=True)
        
        if not group:
            raise HTTPException(status_code=404, detail="Persona group not found")
        
        return PersonaGroupResponse(**group)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/groups/{group_id}",
    response_model=PersonaGroupResponse,
    tags=["Persona Groups"]
)
@limiter.limit("30/minute")
async def update_persona_group(
    request: Request,
    group_id: UUID,
    group_input: PersonaGroupInput,
    db: DatabaseAdapter = Depends(get_db)
):
    """Update a persona group's name or description"""
    try:
        updated_group = await db.update_persona_group(
            group_id=str(group_id),
            name=group_input.name,
            description=group_input.description
        )
        
        if not updated_group:
            raise HTTPException(status_code=404, detail="Persona group not found")
        
        # Fetch with personas
        group = await db.get_persona_group(str(group_id), include_personas=True)
        
        logger.info(f"Updated persona group {group_id}")
        return PersonaGroupResponse(**group)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/groups/{group_id}",
    tags=["Persona Groups"],
    status_code=204
)
@limiter.limit("20/minute")
async def delete_persona_group(
    request: Request,
    group_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Delete a persona group
    
    Note: This will cascade delete all personas in the group
    """
    try:
        success = await db.delete_persona_group(str(group_id))
        
        if not success:
            raise HTTPException(status_code=404, detail="Persona group not found")
        
        logger.info(f"Deleted persona group {group_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Persona Endpoints
# ============================================================================

@app.post(
    "/groups/{group_id}/personas",
    response_model=PersonaResponse,
    tags=["Personas"],
    status_code=201
)
@limiter.limit("20/minute")
async def create_persona(
    request: Request,
    group_id: UUID,
    persona_input: PersonaInput,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a new persona in a group
    
    Limits: 10 personas per group
    """
    try:
        # Check if group exists and get persona count
        group = await db.get_persona_group(str(group_id), include_personas=True)
        
        if not group:
            raise HTTPException(status_code=404, detail="Persona group not found")
        
        if len(group.get('personas', [])) >= 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 personas allowed per group"
            )
        
        # Create persona
        persona = await db.create_persona(
            group_id=str(group_id),
            name=persona_input.name,
            prompt=persona_input.prompt,
            sort_order=persona_input.sort_order or 0
        )
        
        logger.info(f"Created persona {persona['id']} in group {group_id}")
        return PersonaResponse(**persona)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/personas/{persona_id}",
    response_model=PersonaResponse,
    tags=["Personas"]
)
@limiter.limit("60/minute")
async def get_persona(
    request: Request,
    persona_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """Get a specific persona"""
    try:
        persona = await db.get_persona(str(persona_id))
        
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        return PersonaResponse(**persona)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put(
    "/personas/{persona_id}",
    response_model=PersonaResponse,
    tags=["Personas"]
)
@limiter.limit("30/minute")
async def update_persona(
    request: Request,
    persona_id: UUID,
    persona_input: PersonaInput,
    db: DatabaseAdapter = Depends(get_db)
):
    """Update a persona's name, prompt, or sort order"""
    try:
        updated_persona = await db.update_persona(
            persona_id=str(persona_id),
            name=persona_input.name,
            prompt=persona_input.prompt,
            sort_order=persona_input.sort_order
        )
        
        if not updated_persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        logger.info(f"Updated persona {persona_id}")
        return PersonaResponse(**updated_persona)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/personas/{persona_id}",
    tags=["Personas"],
    status_code=204
)
@limiter.limit("20/minute")
async def delete_persona(
    request: Request,
    persona_id: UUID,
    db: DatabaseAdapter = Depends(get_db)
):
    """Delete a persona from its group"""
    try:
        success = await db.delete_persona(str(persona_id))
        
        if not success:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        logger.info(f"Deleted persona {persona_id}")
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.utcnow()
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "false").lower() == "true"

    logger.info(f"Starting API server on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )