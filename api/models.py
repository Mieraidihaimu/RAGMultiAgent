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

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Should I start learning Rust to stay relevant in my career?",
                "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
            }
        }


class ThoughtResponse(BaseModel):
    """Response model for thought creation"""
    id: UUID
    status: str
    message: str
    created_at: datetime

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
    created_at: datetime
    processed_at: Optional[datetime] = None
    classification: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    value_impact: Optional[Dict[str, Any]] = None
    action_plan: Optional[Dict[str, Any]] = None
    priority: Optional[Dict[str, Any]] = None


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
