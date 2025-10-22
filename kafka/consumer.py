"""
Kafka consumer for processing thought events
Handles consuming messages from multiple partitions with error handling
"""
import asyncio
from typing import Callable, Awaitable, Optional
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from loguru import logger

from kafka.config import kafka_config
from kafka.events import ThoughtEvent, deserialize_event, EventType


class KafkaThoughtConsumer:
    """
    Async Kafka consumer for thought processing events
    Handles multi-partition consumption with error handling and DLQ
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        consumer_group: Optional[str] = None
    ):
        """
        Initialize Kafka consumer

        Args:
            bootstrap_servers: Comma-separated list of Kafka brokers
            consumer_group: Consumer group ID for coordinated consumption
        """
        self.bootstrap_servers = bootstrap_servers or kafka_config.bootstrap_servers
        self.topic = kafka_config.topic_name
        self.consumer_group = consumer_group or kafka_config.consumer_group
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._started = False
        self._stop_signal = False

    async def start(self):
        """Start the Kafka consumer connection"""
        if self._started:
            logger.warning("Consumer already started")
            return

        try:
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset=kafka_config.auto_offset_reset,
                enable_auto_commit=kafka_config.enable_auto_commit,
                auto_commit_interval_ms=kafka_config.auto_commit_interval_ms,
                session_timeout_ms=kafka_config.session_timeout_ms,
                max_poll_records=kafka_config.max_poll_records,
            )

            await self.consumer.start()
            self._started = True

            # Get assigned partitions
            partitions = self.consumer.assignment()
            logger.info(
                f"Kafka consumer started: {self.bootstrap_servers} "
                f"| group={self.consumer_group} "
                f"| topic={self.topic} "
                f"| partitions={[p.partition for p in partitions]}"
            )

        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def stop(self):
        """Stop the Kafka consumer connection"""
        self._stop_signal = True

        if self.consumer and self._started:
            try:
                await self.consumer.stop()
                self._started = False
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")

    async def consume(
        self,
        message_handler: Callable[[ThoughtEvent], Awaitable[bool]]
    ):
        """
        Consume messages from Kafka and process them

        Args:
            message_handler: Async function that processes a ThoughtEvent
                           Should return True if successful, False otherwise

        Example:
            async def process_thought(event: ThoughtEvent) -> bool:
                # Process the event
                return True

            consumer = KafkaThoughtConsumer()
            await consumer.start()
            await consumer.consume(process_thought)
        """
        if not self._started or not self.consumer:
            logger.error("Consumer not started. Call start() first.")
            return

        logger.info("Starting message consumption loop...")
        retry_counts = {}  # Track retry counts per thought_id

        try:
            async for msg in self.consumer:
                if self._stop_signal:
                    logger.info("Stop signal received, exiting consumption loop")
                    break

                try:
                    # Deserialize message
                    event = deserialize_event(msg.value.decode('utf-8'))

                    logger.info(
                        f"Received event: {event.event_type.value} "
                        f"| thought_id={event.thought_id} "
                        f"| partition={msg.partition} "
                        f"| offset={msg.offset}"
                    )

                    # Process message with handler
                    success = await message_handler(event)

                    if success:
                        # Successfully processed
                        if event.thought_id in retry_counts:
                            del retry_counts[event.thought_id]

                        logger.info(f"Successfully processed: {event.thought_id}")

                    else:
                        # Processing failed
                        retry_count = retry_counts.get(event.thought_id, 0) + 1
                        retry_counts[event.thought_id] = retry_count

                        if retry_count >= kafka_config.max_retries:
                            logger.error(
                                f"Max retries reached for thought_id={event.thought_id}. "
                                f"Moving to DLQ."
                            )
                            await self._send_to_dlq(msg, event, retry_count)
                            del retry_counts[event.thought_id]
                        else:
                            logger.warning(
                                f"Processing failed for thought_id={event.thought_id}. "
                                f"Retry {retry_count}/{kafka_config.max_retries}"
                            )

                            # Wait before retrying (exponential backoff)
                            wait_time = kafka_config.retry_backoff_ms / 1000 * (2 ** (retry_count - 1))
                            await asyncio.sleep(wait_time)

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

                    # Try to extract thought_id for error tracking
                    try:
                        event = deserialize_event(msg.value.decode('utf-8'))
                        await self._send_to_dlq(msg, event, 0, str(e))
                    except:
                        logger.error("Could not deserialize message for DLQ")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in consumption loop: {e}", exc_info=True)
        finally:
            await self.stop()

    async def _send_to_dlq(
        self,
        original_msg,
        event: ThoughtEvent,
        retry_count: int,
        error_message: str = "Max retries exceeded"
    ):
        """
        Send failed message to Dead Letter Queue

        Args:
            original_msg: Original Kafka message
            event: Deserialized event
            retry_count: Number of retry attempts
            error_message: Error description
        """
        try:
            # Import here to avoid circular dependency
            from kafka.producer import KafkaThoughtProducer

            # Create DLQ producer
            dlq_producer = KafkaThoughtProducer(self.bootstrap_servers)
            await dlq_producer.start()

            # Create failed event
            from kafka.events import ThoughtFailedEvent

            failed_event = ThoughtFailedEvent(
                user_id=event.user_id,
                thought_id=event.thought_id,
                error_message=error_message,
                retry_count=retry_count
            )

            # Send to DLQ topic
            dlq_topic = kafka_config.dead_letter_topic
            await dlq_producer.producer.send(
                dlq_topic,
                value=failed_event.to_json().encode('utf-8'),
                key=event.user_id.encode('utf-8')
            )

            logger.info(f"Sent to DLQ: thought_id={event.thought_id}")

            await dlq_producer.stop()

        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")

    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()


async def consume_thoughts(
    message_handler: Callable[[ThoughtEvent], Awaitable[bool]],
    bootstrap_servers: Optional[str] = None,
    consumer_group: Optional[str] = None
):
    """
    Convenience function to start consuming thoughts

    Args:
        message_handler: Async function to process events
        bootstrap_servers: Kafka brokers
        consumer_group: Consumer group ID

    Example:
        async def process(event: ThoughtEvent) -> bool:
            print(f"Processing {event.thought_id}")
            return True

        await consume_thoughts(process)
    """
    consumer = KafkaThoughtConsumer(bootstrap_servers, consumer_group)
    await consumer.start()

    try:
        await consumer.consume(message_handler)
    except KeyboardInterrupt:
        logger.info("Consumption interrupted")
    finally:
        await consumer.stop()
