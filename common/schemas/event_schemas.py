"""
Kafka Event Schemas
These schemas define the contract between API Service and Kafka Workers.

IMPORTANT: These are used for message serialization/deserialization.
Breaking changes require version bumping and backward compatibility handling.
"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event schema that all Kafka events inherit from."""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "1.0.0"


class ThoughtCreatedEvent(BaseEvent):
    """
    Published by: API Service
    Consumed by: Kafka Workers
    
    Contract:
    - Triggers thought processing pipeline
    - user_id and thought_id required for processing
    - group_id required only if processing_mode='group'
    """
    event_type: Literal['thought_created'] = 'thought_created'
    user_id: str
    thought_id: str
    text: str
    user_context: Optional[Dict[str, Any]] = None
    processing_mode: Literal['single', 'group'] = 'single'
    group_id: Optional[str] = None


class ThoughtProcessingEvent(BaseEvent):
    """Worker → Redis (SSE): Processing started."""
    event_type: Literal['thought_processing'] = 'thought_processing'
    user_id: str
    thought_id: str
    status: Literal['processing'] = 'processing'
    message: str = "Starting AI analysis..."


class ThoughtAgentCompletedEvent(BaseEvent):
    """Worker → Redis (SSE): Agent completed."""
    event_type: Literal['thought_agent_completed'] = 'thought_agent_completed'
    user_id: str
    thought_id: str
    agent_name: str
    agent_number: int = Field(..., ge=1, le=5)
    progress: str  # e.g., "1/5"


class ThoughtCompletedEvent(BaseEvent):
    """Worker → Redis (SSE): Processing completed."""
    event_type: Literal['thought_completed'] = 'thought_completed'
    user_id: str
    thought_id: str
    status: Literal['completed'] = 'completed'
    message: str = "Analysis complete!"
    processing_time_seconds: Optional[float] = None


class ThoughtFailedEvent(BaseEvent):
    """Worker → Redis (SSE): Processing failed."""
    event_type: Literal['thought_failed'] = 'thought_failed'
    user_id: str
    thought_id: str
    status: Literal['failed'] = 'failed'
    error_message: str
    retry_count: int = 0


# Event schema mapping for deserialization
EVENT_SCHEMA_MAP = {
    'thought_created': ThoughtCreatedEvent,
    'thought_processing': ThoughtProcessingEvent,
    'thought_agent_completed': ThoughtAgentCompletedEvent,
    'thought_completed': ThoughtCompletedEvent,
    'thought_failed': ThoughtFailedEvent,
}
