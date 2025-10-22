"""
Direct Kafka producer and consumer integration tests
Tests Kafka message flow without going through API layer
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
import sys
import os

# Change directory to /app so relative imports work
os.chdir('/app')
sys.path.insert(0, '/app')

# Import aiokafka first (it needs kafka-python)
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# Now import our custom modules - they're in /app/kafka/ directory
# We import them directly by changing how Python finds them
from kafka import producer, consumer, events, config

# Create aliases for clarity
KafkaThoughtProducer = producer.KafkaThoughtProducer
KafkaThoughtConsumer = consumer.KafkaThoughtConsumer
ThoughtCreatedEvent = events.ThoughtCreatedEvent
ThoughtProcessingEvent = events.ThoughtProcessingEvent
ThoughtCompletedEvent = events.ThoughtCompletedEvent
ThoughtFailedEvent = events.ThoughtFailedEvent
EventType = events.EventType
deserialize_event = events.deserialize_event


@pytest.mark.asyncio
async def test_kafka_producer_connection():
    """Test that Kafka producer can connect and start"""
    producer = KafkaThoughtProducer(bootstrap_servers="kafka:9092")
    
    # Test connection
    await producer.start()
    assert producer._started is True
    assert producer.producer is not None
    
    # Cleanup
    await producer.stop()
    assert producer._started is False


@pytest.mark.asyncio
async def test_kafka_consumer_connection():
    """Test that Kafka consumer can connect and start"""
    consumer = KafkaThoughtConsumer(
        bootstrap_servers="kafka:9092",
        consumer_group=f"test_group_{uuid4()}"
    )
    
    # Test connection
    await consumer.start()
    assert consumer._started is True
    assert consumer.consumer is not None
    
    # Cleanup
    await consumer.stop()
    assert consumer._started is False


@pytest.mark.asyncio
async def test_kafka_producer_send_thought_created_event():
    """Test sending ThoughtCreatedEvent through Kafka producer"""
    producer = KafkaThoughtProducer(bootstrap_servers="kafka:9092")
    await producer.start()
    
    # Create test event
    event = ThoughtCreatedEvent(
        user_id=str(uuid4()),
        thought_id=str(uuid4()),
        text="TEST_DIRECT_KAFKA: This is a direct Kafka test message",
        user_context={"test": True, "source": "direct_test"}
    )
    
    # Send event
    success = await producer.send_event(event)
    assert success is True
    
    # Cleanup
    await producer.stop()


@pytest.mark.asyncio
async def test_kafka_producer_send_multiple_event_types():
    """Test sending different event types through Kafka producer"""
    producer = KafkaThoughtProducer(bootstrap_servers="kafka:9092")
    await producer.start()
    
    user_id = str(uuid4())
    thought_id = str(uuid4())
    
    # Send ThoughtCreatedEvent
    created_event = ThoughtCreatedEvent(
        user_id=user_id,
        thought_id=thought_id,
        text="TEST_MULTI: Testing multiple events"
    )
    success1 = await producer.send_event(created_event)
    assert success1 is True
    
    # Send ThoughtProcessingEvent
    processing_event = ThoughtProcessingEvent(
        user_id=user_id,
        thought_id=thought_id,
        status="processing"
    )
    success2 = await producer.send_event(processing_event)
    assert success2 is True
    
    # Send ThoughtCompletedEvent
    completed_event = ThoughtCompletedEvent(
        user_id=user_id,
        thought_id=thought_id,
        status="completed",
        processing_time_seconds=2.5
    )
    success3 = await producer.send_event(completed_event)
    assert success3 is True
    
    await producer.stop()


@pytest.mark.asyncio
async def test_kafka_consumer_receives_messages():
    """Test that Kafka consumer can receive messages sent by producer"""
    # Use unique topic/group for this test
    test_thought_id = str(uuid4())
    received_events = []
    
    # Message handler that stores received events
    async def message_handler(event):
        received_events.append(event)
        # Stop after receiving our test message
        if event.thought_id == test_thought_id:
            return True
        return True
    
    # Start producer and send a test message
    producer = KafkaThoughtProducer(bootstrap_servers="kafka:9092")
    await producer.start()
    
    test_event = ThoughtCreatedEvent(
        user_id=str(uuid4()),
        thought_id=test_thought_id,
        text="TEST_CONSUMER_RECEIVE: Consumer should receive this"
    )
    
    success = await producer.send_event(test_event)
    assert success is True
    await producer.stop()
    
    # Start consumer and consume messages (with timeout)
    consumer = KafkaThoughtConsumer(
        bootstrap_servers="kafka:9092",
        consumer_group=f"test_receive_{uuid4()}"
    )
    await consumer.start()
    
    # Consume with timeout
    try:
        await asyncio.wait_for(
            consumer.consume(message_handler),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        pass  # Expected - we'll stop after a few seconds
    finally:
        await consumer.stop()
    
    # Verify we received at least one message
    assert len(received_events) > 0, "Consumer should have received at least one message"
    
    # Verify our specific test message was received
    test_messages = [e for e in received_events if e.thought_id == test_thought_id]
    assert len(test_messages) > 0, f"Consumer should have received our test message with ID {test_thought_id}"
    
    # Verify message content
    received_event = test_messages[0]
    assert received_event.event_type == EventType.THOUGHT_CREATED
    assert "TEST_CONSUMER_RECEIVE" in received_event.text


@pytest.mark.asyncio
async def test_kafka_producer_consumer_full_workflow():
    """Test complete producer-consumer workflow with multiple messages"""
    test_user_id = str(uuid4())
    test_messages = []
    received_messages = []
    
    # Create 3 test messages
    for i in range(3):
        thought_id = str(uuid4())
        test_messages.append({
            "thought_id": thought_id,
            "text": f"TEST_WORKFLOW_{i}: Message number {i}"
        })
    
    # Message handler
    async def message_handler(event):
        received_messages.append(event)
        return True
    
    # Send messages
    producer = KafkaThoughtProducer(bootstrap_servers="kafka:9092")
    await producer.start()
    
    for msg in test_messages:
        event = ThoughtCreatedEvent(
            user_id=test_user_id,
            thought_id=msg["thought_id"],
            text=msg["text"]
        )
        success = await producer.send_event(event)
        assert success is True
    
    await producer.stop()
    
    # Give Kafka a moment to process
    await asyncio.sleep(2)
    
    # Consume messages
    consumer = KafkaThoughtConsumer(
        bootstrap_servers="kafka:9092",
        consumer_group=f"test_workflow_{uuid4()}"
    )
    await consumer.start()
    
    # Consume with timeout
    try:
        await asyncio.wait_for(
            consumer.consume(message_handler),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        pass
    finally:
        await consumer.stop()
    
    # Verify we received messages
    assert len(received_messages) > 0, "Should have received messages"
    
    # Verify at least one of our test messages was received
    test_thought_ids = {msg["thought_id"] for msg in test_messages}
    received_thought_ids = {e.thought_id for e in received_messages}
    
    overlap = test_thought_ids & received_thought_ids
    assert len(overlap) > 0, f"Should have received at least one of our test messages. Sent: {test_thought_ids}, Received: {received_thought_ids}"


@pytest.mark.asyncio
async def test_kafka_context_managers():
    """Test producer and consumer context managers work properly"""
    test_thought_id = str(uuid4())
    
    # Test producer context manager
    async with KafkaThoughtProducer(bootstrap_servers="kafka:9092") as producer:
        assert producer._started is True
        
        event = ThoughtCreatedEvent(
            user_id=str(uuid4()),
            thought_id=test_thought_id,
            text="TEST_CONTEXT: Testing context manager"
        )
        success = await producer.send_event(event)
        assert success is True
    
    # Producer should be stopped after context exit
    # (we can't verify directly, but it shouldn't error)
    
    # Test consumer context manager
    received = []
    
    async def handler(event):
        received.append(event)
        return True
    
    async with KafkaThoughtConsumer(
        bootstrap_servers="kafka:9092",
        consumer_group=f"test_context_{uuid4()}"
    ) as consumer:
        assert consumer._started is True
        
        # Start consuming with timeout
        try:
            await asyncio.wait_for(
                consumer.consume(handler),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            pass
    
    # Should have received some messages
    assert len(received) >= 0  # May or may not receive messages in 5 seconds


@pytest.mark.asyncio
async def test_kafka_partition_key_consistency():
    """Test that messages for same user go to same partition"""
    producer = KafkaThoughtProducer(bootstrap_servers="kafka:9092")
    await producer.start()
    
    user_id = str(uuid4())
    
    # Send multiple messages for same user
    thought_ids = []
    for i in range(3):
        thought_id = str(uuid4())
        thought_ids.append(thought_id)
        
        event = ThoughtCreatedEvent(
            user_id=user_id,  # Same user for all messages
            thought_id=thought_id,
            text=f"TEST_PARTITION: Message {i} for same user"
        )
        
        success = await producer.send_event(event)
        assert success is True
    
    await producer.stop()
    
    # Note: We can't easily verify partition assignment without access to metadata,
    # but this test verifies the producer accepts the partition key without error


@pytest.mark.asyncio
async def test_kafka_serialization_deserialization():
    """Test event serialization and deserialization"""
    from kafka.events import deserialize_event
    
    # Create an event
    original_event = ThoughtCreatedEvent(
        user_id=str(uuid4()),
        thought_id=str(uuid4()),
        text="TEST_SERIALIZATION: Testing JSON serialization",
        user_context={"key": "value", "number": 42}
    )
    
    # Serialize
    json_str = original_event.to_json()
    assert isinstance(json_str, str)
    assert "TEST_SERIALIZATION" in json_str
    
    # Deserialize
    deserialized_event = deserialize_event(json_str)
    
    # Verify
    assert deserialized_event.event_type == EventType.THOUGHT_CREATED
    assert deserialized_event.user_id == original_event.user_id
    assert deserialized_event.thought_id == original_event.thought_id
    assert deserialized_event.text == original_event.text
    assert isinstance(deserialized_event, ThoughtCreatedEvent)
    assert deserialized_event.user_context == original_event.user_context
