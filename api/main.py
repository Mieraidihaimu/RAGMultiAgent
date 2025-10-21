"""
FastAPI backend for AI Thought Processor
Main API server with endpoints for thought management
"""
import os
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from models import (
    ThoughtInput,
    ThoughtResponse,
    ThoughtsListResponse,
    ThoughtDetail,
    UserResponse,
    UserContextUpdate,
    WeeklySynthesisResponse,
    HealthResponse,
    ErrorResponse
)
from database import get_db
from common.database.base import DatabaseAdapter

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    "/thoughts",
    response_model=ThoughtResponse,
    status_code=201,
    tags=["Thoughts"]
)
async def create_thought(
    thought: ThoughtInput,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a new thought for processing

    The thought will be saved with 'pending' status and processed
    during the next nightly batch run.
    """
    try:
        # Verify user exists
        user = await db.get_user(str(thought.user_id))
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f"User {thought.user_id} not found"
            )

        # Insert thought
        thought_data = await db.create_thought(
            user_id=str(thought.user_id),
            text=thought.text,
        )

        if not thought_data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create thought"
            )

        logger.info(f"Created thought {thought_data['id']} for user {thought.user_id}")

        return ThoughtResponse(
            id=thought_data["id"],
            status="pending",
            message="Thought saved! It will be analyzed tonight.",
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
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed"),
    limit: int = Query(50, ge=1, le=100, description="Number of thoughts to return"),
    offset: int = Query(0, ge=0, description="Number of thoughts to skip"),
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Get thoughts for a specific user with optional filtering
    """
    try:
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
    db: DatabaseAdapter = Depends(get_db)
):
    """Get a specific thought by ID"""
    try:
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