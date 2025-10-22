"""
Kafka integration package for event-driven thought processing
Provides producer, consumer, and event schemas for streaming architecture
"""

from kafka.events import (
    ThoughtEvent,
    ThoughtCreatedEvent,
    ThoughtProcessingEvent,
    ThoughtAgentCompletedEvent,
    ThoughtCompletedEvent,
    ThoughtFailedEvent,
    EventType
)
from kafka.producer import KafkaThoughtProducer
from kafka.consumer import KafkaThoughtConsumer
from kafka.config import KafkaConfig

__all__ = [
    "ThoughtEvent",
    "ThoughtCreatedEvent",
    "ThoughtProcessingEvent",
    "ThoughtAgentCompletedEvent",
    "ThoughtCompletedEvent",
    "ThoughtFailedEvent",
    "EventType",
    "KafkaThoughtProducer",
    "KafkaThoughtConsumer",
    "KafkaConfig",
]
