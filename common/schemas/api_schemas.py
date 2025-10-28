"""
API Request/Response Schemas
These schemas define the contract between Frontend and API Service.

IMPORTANT: Changes to these schemas may break frontend/backend compatibility.
Follow semantic versioning when modifying.
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator


# ============================================================================
# REQUEST SCHEMAS (Frontend → API)
# ============================================================================

class ThoughtCreateRequest(BaseModel):
    """
    Schema for creating a new thought.
    
    Contract:
    - text: Required, 1-10000 characters
    - user_id: Required UUID
    - processing_mode: Optional, defaults to 'single'
    - group_id: Required only if processing_mode='group'
    """
    text: str = Field(..., min_length=1, max_length=10000)
    user_id: UUID
    processing_mode: Literal['single', 'group'] = 'single'
    group_id: Optional[UUID] = None
    
    @validator('group_id')
    def validate_group_id(cls, v, values):
        if values.get('processing_mode') == 'group' and v is None:
            raise ValueError('group_id is required when processing_mode is "group"')
        return v


class AnonymousThoughtRequest(BaseModel):
    """Schema for anonymous thought submission (rate-limited to 3)."""
    text: str = Field(..., min_length=1, max_length=10000)
    session_token: Optional[str] = None


class UserContextSchema(BaseModel):
    """
    User context schema for AI personalization.
    
    Contract:
    - All fields are optional
    - This schema is passed to AI agents
    """
    demographics: Optional[Dict[str, Any]] = None
    goals: Optional[List[str]] = None
    values: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    challenges: Optional[List[str]] = None
    patterns: Optional[List[str]] = None


class ThoughtResponse(BaseModel):
    """Schema for thought creation response."""
    id: UUID
    status: Literal['pending', 'processing', 'completed', 'failed']
    message: str
    created_at: datetime
    session_id: Optional[str] = None
