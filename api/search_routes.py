"""
Search endpoints for thoughts using hybrid search.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from database import get_db
from common.database.base import DatabaseAdapter
from search_service import get_search_service, ThoughtSearchService

# Try to import auth
try:
    from auth import get_current_user, TokenData
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    TokenData = None


router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    """Request model for thought search"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    status: Optional[str] = Field(None, description="Filter by status")
    category: Optional[str] = Field(None, description="Filter by category")
    top_k: int = Field(10, ge=1, le=50, description="Number of results")
    search_mode: Literal["hybrid", "keyword", "semantic"] = Field(
        "hybrid",
        description="Search mode: hybrid (default), keyword (Elasticsearch), or semantic (vectors)"
    )


class SearchResult(BaseModel):
    """Individual search result"""
    thought_id: str
    title: str
    content: str
    score: float
    category: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    processing_mode: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for search"""
    query: str
    results: list
    total_hits: int
    latency_ms: float
    search_mode: str
    filters_applied: dict


@router.post("/thoughts", response_model=SearchResponse)
async def search_thoughts(
    search_req: SearchRequest,
    current_user: TokenData = Depends(get_current_user) if AUTH_AVAILABLE else None,
    search_service: ThoughtSearchService = Depends(get_search_service)
):
    """
    Search through thoughts and their processing results.
    
    Supports three search modes:
    - **hybrid** (default): Combines keyword and semantic search using RRF
    - **keyword**: Traditional Elasticsearch BM25 with fuzzy matching
    - **semantic**: Vector similarity using local embeddings
    
    Examples:
    - "career decision" - Find thoughts about career
    - "high priority urgent" - Find urgent high-priority thoughts
    - "should I learn rust" - Semantic understanding of question
    """
    try:
        # If auth is enabled and user_id is specified, verify ownership
        if AUTH_AVAILABLE and current_user and search_req.user_id:
            if str(search_req.user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot search other users' thoughts"
                )
        
        # If auth is enabled but no user_id specified, search only current user's thoughts
        if AUTH_AVAILABLE and current_user and not search_req.user_id:
            search_req.user_id = UUID(current_user.user_id)
        
        results = await search_service.search_thoughts(
            query=search_req.query,
            user_id=str(search_req.user_id) if search_req.user_id else None,
            status=search_req.status,
            category=search_req.category,
            top_k=search_req.top_k,
            search_mode=search_req.search_mode
        )
        
        return SearchResponse(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.post("/thoughts/compare")
async def compare_search_modes(
    query: str = Query(..., min_length=1, description="Search query"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    top_k: int = Query(5, ge=1, le=20, description="Results per mode"),
    current_user: TokenData = Depends(get_current_user) if AUTH_AVAILABLE else None,
    search_service: ThoughtSearchService = Depends(get_search_service)
):
    """
    Compare all three search modes side-by-side.
    
    Useful for understanding how different search strategies rank your thoughts.
    Returns results from keyword, semantic, and hybrid search.
    """
    try:
        # Verify user access
        if AUTH_AVAILABLE and current_user:
            if user_id and str(user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot search other users' thoughts"
                )
            if not user_id:
                user_id = UUID(current_user.user_id)
        
        results = await search_service.compare_search_modes(
            query=query,
            user_id=str(user_id) if user_id else None,
            top_k=top_k
        )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")


@router.post("/index/rebuild")
async def rebuild_search_index(
    user_id: UUID = Query(..., description="User ID to rebuild index for"),
    current_user: TokenData = Depends(get_current_user) if AUTH_AVAILABLE else None,
    db: DatabaseAdapter = Depends(get_db),
    search_service: ThoughtSearchService = Depends(get_search_service)
):
    """
    Rebuild search index for a user's thoughts.
    
    Use this when:
    - Adding hybrid search to existing data
    - Search results seem out of sync
    - After bulk updates to thoughts
    """
    try:
        # Verify user access
        if AUTH_AVAILABLE and current_user:
            if str(user_id) != current_user.user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot rebuild index for other users"
                )
        
        # Fetch all thoughts for user
        thoughts_data = await db.get_thoughts(
            user_id=str(user_id),
            status=None,  # Get all statuses
            limit=1000,
            offset=0
        )
        
        if not thoughts_data:
            return {
                "message": "No thoughts found to index",
                "indexed": 0
            }
        
        # Index thoughts
        result = await search_service.index_thoughts_batch(thoughts_data)
        
        return {
            "message": f"Successfully indexed {result.get('indexed', 0)} thoughts",
            "indexed": result.get('indexed', 0),
            "time_seconds": result.get('time_seconds', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Index rebuild error: {str(e)}")


@router.get("/health")
async def search_health():
    """Check if search service is available"""
    try:
        search_service = await get_search_service()
        return {
            "status": "healthy",
            "initialized": search_service._initialized,
            "elasticsearch": search_service.es_config.host,
            "embedding_model": search_service.semantic_config.local_model
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
