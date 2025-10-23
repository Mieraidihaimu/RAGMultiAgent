"""
Pydantic models for API request/response validation
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class ThoughtInput(BaseModel):
    """Input model for creating a new thought"""
    text: str = Field(..., min_length=1, max_length=10000, description="The thought text")
    user_id: UUID = Field(..., description="User ID")
    processing_mode: Optional[str] = Field("single", description="Processing mode: 'single' or 'group'")
    group_id: Optional[UUID] = Field(None, description="Persona group ID (required if processing_mode='group')")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Should I start learning Rust to stay relevant in my career?",
                "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
                "processing_mode": "single",
                "group_id": None
            }
        }


class AnonymousThoughtInput(BaseModel):
    """Input model for creating a new thought as anonymous user"""
    text: str = Field(..., min_length=1, max_length=10000, description="The thought text")
    session_token: Optional[str] = Field(None, description="Anonymous session token")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Should I start learning Rust to stay relevant in my career?",
                "session_token": "anon_abc123xyz"
            }
        }


class AnonymousSessionResponse(BaseModel):
    """Response model for anonymous session info"""
    session_token: str
    thoughts_remaining: int
    thoughts_used: int
    limit_reached: bool

    class Config:
        json_schema_extra = {
            "example": {
                "session_token": "anon_abc123xyz",
                "thoughts_remaining": 2,
                "thoughts_used": 1,
                "limit_reached": False
            }
        }


class ThoughtResponse(BaseModel):
    """Response model for thought creation"""
    id: UUID
    status: str
    message: str
    created_at: datetime
    session_info: Optional['AnonymousSessionResponse'] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "b1ffbc99-9c0b-4ef8-bb6d-6bb9bd380a12",
                "status": "pending",
                "message": "Thought saved! It will be analyzed tonight.",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class ThoughtDetail(BaseModel):
    """Detailed thought with analysis results"""
    id: UUID
    user_id: UUID
    text: str
    status: str
    processing_mode: Optional[str] = "single"
    group_id: Optional[UUID] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    classification: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    value_impact: Optional[Dict[str, Any]] = None
    action_plan: Optional[Dict[str, Any]] = None
    priority: Optional[Dict[str, Any]] = None
    consolidated_output: Optional[Dict[str, Any]] = None
    persona_runs: Optional[List['ThoughtPersonaRunResponse']] = None


class ThoughtsListResponse(BaseModel):
    """Response model for listing thoughts"""
    thoughts: List[ThoughtDetail]
    count: int
    status_filter: Optional[str] = None


class UserContextUpdate(BaseModel):
    """Model for updating user context"""
    context: Dict[str, Any] = Field(..., description="Complete user context JSON")


class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    email: EmailStr
    created_at: datetime
    context_version: int
    context_updated_at: datetime


class WeeklySynthesisResponse(BaseModel):
    """Weekly synthesis response"""
    id: UUID
    user_id: UUID
    week_start: str
    week_end: str
    synthesis: Dict[str, Any]
    created_at: datetime


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    database: str


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Thought not found",
                "detail": "No thought exists with the given ID",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class SSEEvent(BaseModel):
    """Server-Sent Event model"""
    event: str = Field(..., description="Event type")
    id: Optional[str] = Field(None, description="Event ID for client tracking")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "event": "thought_processing",
                "id": "evt_123",
                "data": {"thought_id": "uuid", "status": "processing"},
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


# ============================================================================
# Persona Group Models
# ============================================================================

class PersonaInput(BaseModel):
    """Input model for creating/updating a persona"""
    name: str = Field(..., min_length=1, max_length=100, description="Persona name (e.g., 'Tech Lead', 'Life Coach')")
    prompt: str = Field(..., min_length=10, max_length=2000, description="Simple text describing persona's context/role")
    sort_order: Optional[int] = Field(0, ge=0, description="Order in which persona processes thoughts")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Pragmatic Tech Lead",
                "prompt": "You are a senior technical leader focused on scalability, maintainability, and team efficiency. You consider technical debt and long-term consequences.",
                "sort_order": 0
            }
        }


class PersonaResponse(BaseModel):
    """Response model for persona details"""
    id: UUID
    group_id: UUID
    name: str
    prompt: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "c1ffbc99-9c0b-4ef8-bb6d-6bb9bd380a13",
                "group_id": "d2ffbc99-9c0b-4ef8-bb6d-6bb9bd380a14",
                "name": "Pragmatic Tech Lead",
                "prompt": "You are a senior technical leader...",
                "sort_order": 0,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class PersonaGroupInput(BaseModel):
    """Input model for creating/updating a persona group"""
    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    description: Optional[str] = Field(None, max_length=500, description="Group description")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Career Advisory Board",
                "description": "Professional advisors for career decisions"
            }
        }


class PersonaGroupResponse(BaseModel):
    """Response model for persona group details"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    personas: List[PersonaResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "d2ffbc99-9c0b-4ef8-bb6d-6bb9bd380a14",
                "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
                "name": "Career Advisory Board",
                "description": "Professional advisors for career decisions",
                "personas": [],
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class PersonaGroupListResponse(BaseModel):
    """Response model for listing persona groups"""
    groups: List[PersonaGroupResponse]
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "groups": [],
                "count": 0
            }
        }


class ThoughtPersonaRunResponse(BaseModel):
    """Response model for a single persona's processing result"""
    id: UUID
    thought_id: UUID
    persona_id: Optional[UUID]
    persona_name: str
    persona_output: Dict[str, Any]
    processing_time_ms: Optional[int]
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "e3ffbc99-9c0b-4ef8-bb6d-6bb9bd380a15",
                "thought_id": "b1ffbc99-9c0b-4ef8-bb6d-6bb9bd380a12",
                "persona_id": "c1ffbc99-9c0b-4ef8-bb6d-6bb9bd380a13",
                "persona_name": "Pragmatic Tech Lead",
                "persona_output": {},
                "processing_time_ms": 15234,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


# Resolve forward references
ThoughtDetail.model_rebuild()
ThoughtResponse.model_rebuild()
