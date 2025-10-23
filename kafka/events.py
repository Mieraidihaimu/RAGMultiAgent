"""
Event schemas for Kafka messages
All events related to thought processing
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from enum import Enum


class EventType(str, Enum):
    """Event types for thought processing"""
    THOUGHT_CREATED = "thought_created"
    THOUGHT_PROCESSING = "thought_processing"
    THOUGHT_AGENT_COMPLETED = "thought_agent_completed"
    THOUGHT_COMPLETED = "thought_completed"
    THOUGHT_FAILED = "thought_failed"
    # New events for group/persona processing
    GROUP_PROCESSING_STARTED = "group_processing_started"
    PERSONA_COMPLETED = "persona_completed"
    CONSOLIDATION_STARTED = "consolidation_started"


class ThoughtEvent(BaseModel):
    """Base event model for all thought-related events"""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    thought_id: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

    def to_json(self) -> str:
        """Serialize event to JSON string for Kafka"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "ThoughtEvent":
        """Deserialize event from JSON string"""
        return cls.model_validate_json(json_str)


class ThoughtCreatedEvent(ThoughtEvent):
    """Event emitted when a new thought is created"""
    event_type: Literal[EventType.THOUGHT_CREATED] = EventType.THOUGHT_CREATED
    text: str
    user_context: Optional[Dict[str, Any]] = None
    processing_mode: str = "single"  # 'single' or 'group'
    group_id: Optional[str] = None


class ThoughtProcessingEvent(ThoughtEvent):
    """Event emitted when thought processing starts"""
    event_type: Literal[EventType.THOUGHT_PROCESSING] = EventType.THOUGHT_PROCESSING
    status: str = "processing"
    message: Optional[str] = "Starting AI analysis..."


class ThoughtAgentCompletedEvent(ThoughtEvent):
    """Event emitted when an individual agent completes"""
    event_type: Literal[EventType.THOUGHT_AGENT_COMPLETED] = EventType.THOUGHT_AGENT_COMPLETED
    agent_name: str
    agent_number: int  # 1-5
    total_agents: int = 5
    progress: Optional[str] = None  # e.g., "1/5", "2/5"


class ThoughtCompletedEvent(ThoughtEvent):
    """Event emitted when thought processing completes successfully"""
    event_type: Literal[EventType.THOUGHT_COMPLETED] = EventType.THOUGHT_COMPLETED
    status: str = "completed"
    message: str = "Analysis complete!"
    processing_time_seconds: Optional[float] = None


class ThoughtFailedEvent(ThoughtEvent):
    """Event emitted when thought processing fails"""
    event_type: Literal[EventType.THOUGHT_FAILED] = EventType.THOUGHT_FAILED
    status: str = "failed"
    error_message: str
    retry_count: int = 0


class GroupProcessingStartedEvent(ThoughtEvent):
    """Event emitted when group processing starts"""
    event_type: Literal[EventType.GROUP_PROCESSING_STARTED] = EventType.GROUP_PROCESSING_STARTED
    group_id: str
    group_name: str
    persona_count: int


class PersonaCompletedEvent(ThoughtEvent):
    """Event emitted when a single persona completes processing"""
    event_type: Literal[EventType.PERSONA_COMPLETED] = EventType.PERSONA_COMPLETED
    persona_id: str
    persona_name: str
    progress: str  # e.g., "2/5"
    has_error: bool = False


class ConsolidationStartedEvent(ThoughtEvent):
    """Event emitted when consolidation of persona outputs starts"""
    event_type: Literal[EventType.CONSOLIDATION_STARTED] = EventType.CONSOLIDATION_STARTED
    message: str = "Synthesizing perspectives..."


# Event type mapping for deserialization
EVENT_TYPE_MAP = {
    EventType.THOUGHT_CREATED: ThoughtCreatedEvent,
    EventType.THOUGHT_PROCESSING: ThoughtProcessingEvent,
    EventType.THOUGHT_AGENT_COMPLETED: ThoughtAgentCompletedEvent,
    EventType.THOUGHT_COMPLETED: ThoughtCompletedEvent,
    EventType.THOUGHT_FAILED: ThoughtFailedEvent,
    EventType.GROUP_PROCESSING_STARTED: GroupProcessingStartedEvent,
    EventType.PERSONA_COMPLETED: PersonaCompletedEvent,
    EventType.CONSOLIDATION_STARTED: ConsolidationStartedEvent,
}


def deserialize_event(json_str: str) -> ThoughtEvent:
    """
    Deserialize a JSON string into the appropriate event type

    Args:
        json_str: JSON string from Kafka message

    Returns:
        Appropriate ThoughtEvent subclass instance
    """
    data = json.loads(json_str)
    event_type = EventType(data.get('event_type'))
    event_class = EVENT_TYPE_MAP.get(event_type, ThoughtEvent)
    return event_class(**data)
