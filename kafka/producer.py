"""
Kafka producer for publishing thought events
Handles async message publishing with retry logic
"""
import asyncio
import hashlib
from typing import Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError, KafkaTimeoutError
from loguru import logger

from kafka.config import kafka_config
from kafka.events import ThoughtEvent


class KafkaThoughtProducer:
    """
    Async Kafka producer for thought processing events
    Handles connection management, message publishing, and retries
    """

    def __init__(self, bootstrap_servers: Optional[str] = None):
        """
        Initialize Kafka producer

        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
                             Defaults to kafka_config.bootstrap_servers
        """
        self.bootstrap_servers = bootstrap_servers or kafka_config.bootstrap_servers
        self.topic = kafka_config.topic_name
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False

    async def start(self):
        """Start the Kafka producer connection"""
        if self._started:
            logger.warning("Producer already started")
            return

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                acks=kafka_config.acks,
                retries=kafka_config.retries,
                max_in_flight_requests_per_connection=kafka_config.max_in_flight_requests_per_connection,
                compression_type=kafka_config.compression_type,
                batch_size=kafka_config.batch_size,
                linger_ms=kafka_config.linger_ms,
                buffer_memory=kafka_config.buffer_memory,
            )

            await self.producer.start()
            self._started = True
            logger.info(f"Kafka producer started: {self.bootstrap_servers}")

        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop(self):
        """Stop the Kafka producer connection"""
        if self.producer and self._started:
            try:
                await self.producer.stop()
                self._started = False
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")

    def _get_partition_key(self, user_id: str) -> bytes:
        """
        Generate partition key from user_id
        Ensures all thoughts from same user go to same partition (ordered processing)

        Args:
            user_id: User identifier

        Returns:
            Partition key as bytes
        """
        # Use hash of user_id for consistent partitioning
        return user_id.encode('utf-8')

    async def send_event(
        self,
        event: ThoughtEvent,
        retry_count: int = 0
    ) -> bool:
        """
        Send an event to Kafka topic

        Args:
            event: ThoughtEvent instance to send
            retry_count: Current retry attempt (for internal use)

        Returns:
            True if successful, False otherwise
        """
        if not self._started or not self.producer:
            logger.error("Producer not started. Call start() first.")
            return False

        try:
            # Serialize event to JSON
            message_value = event.to_json().encode('utf-8')

            # Get partition key (ensures ordered processing per user)
            partition_key = self._get_partition_key(event.user_id)

            # Send message
            future = await self.producer.send(
                self.topic,
                value=message_value,
                key=partition_key
            )

            # Wait for acknowledgment
            record_metadata = await future

            logger.info(
                f"Event sent successfully: {event.event_type.value} "
                f"| thought_id={event.thought_id} "
                f"| partition={record_metadata.partition} "
                f"| offset={record_metadata.offset}"
            )

            return True

        except KafkaTimeoutError as e:
            logger.error(f"Kafka timeout sending event: {e}")

            # Retry logic
            if retry_count < kafka_config.max_retries:
                wait_time = kafka_config.retry_backoff_ms / 1000 * (2 ** retry_count)
                logger.info(f"Retrying in {wait_time}s... (attempt {retry_count + 1}/{kafka_config.max_retries})")
                await asyncio.sleep(wait_time)
                return await self.send_event(event, retry_count + 1)
            else:
                logger.error(f"Max retries reached for event: {event.event_id}")
                return False

        except KafkaError as e:
            logger.error(f"Kafka error sending event: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending event: {e}")
            return False

    async def send_thought_created(
        self,
        user_id: str,
        thought_id: str,
        text: str,
        user_context: Optional[dict] = None
    ) -> bool:
        """
        Convenience method to send a ThoughtCreatedEvent

        Args:
            user_id: User ID
            thought_id: Thought ID
            text: Thought text
            user_context: Optional user context

        Returns:
            True if successful, False otherwise
        """
        from kafka.events import ThoughtCreatedEvent

        event = ThoughtCreatedEvent(
            user_id=user_id,
            thought_id=thought_id,
            text=text,
            user_context=user_context or {}
        )

        return await self.send_event(event)

    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()


# Global producer instance (can be reused across requests)
_global_producer: Optional[KafkaThoughtProducer] = None


async def get_kafka_producer() -> KafkaThoughtProducer:
    """
    Get or create global Kafka producer instance
    Safe for concurrent use across FastAPI requests

    Returns:
        KafkaThoughtProducer instance
    """
    global _global_producer

    if _global_producer is None:
        _global_producer = KafkaThoughtProducer()
        await _global_producer.start()

    return _global_producer


async def close_kafka_producer():
    """Close the global Kafka producer instance"""
    global _global_producer

    if _global_producer:
        await _global_producer.stop()
        _global_producer = None
