# Shared Schemas

**Enforced contracts between services using Pydantic schemas.**

## Purpose

These schemas define the **exact data structures** that services must use when communicating. They are:
- ✅ **Validated** at runtime (Pydantic)
- ✅ **Type-checked** during development (Python type hints)
- ✅ **Versioned** (schema_version field in events)
- ✅ **Documented** with inline docstrings

## Schemas

### 1. API Schemas (`api_schemas.py`)

**Contract between**: Frontend ⟷ API Service

**Request Schemas**:
```python
from common.schemas import ThoughtCreateRequest

# Frontend sends this
request = ThoughtCreateRequest(
    text="Should I learn Rust?",
    user_id="550e8400-e29b-41d4-a716-446655440000",
    processing_mode="single"
)
```

**Response Schemas**:
```python
from common.schemas import ThoughtResponse

# API returns this
response = ThoughtResponse(
    id="thought-uuid",
    status="pending",
    message="Thought saved!",
    created_at=datetime.utcnow(),
    session_id="sess_123"
)
```

### 2. Event Schemas (`event_schemas.py`)

**Contract between**: API Service → Kafka → Kafka Workers

**Publishing Events** (API Service):
```python
from common.schemas import ThoughtCreatedEvent

event = ThoughtCreatedEvent(
    user_id=str(user_id),
    thought_id=str(thought_id),
    text=thought.text,
    user_context=user.context,
    processing_mode="single"
)

# Serialize to JSON for Kafka
kafka_message = event.json()
producer.send('thought-events', value=kafka_message)
```

**Consuming Events** (Kafka Workers):
```python
from common.schemas import ThoughtCreatedEvent

# Deserialize from Kafka message
event_data = json.loads(kafka_message.value)
event = ThoughtCreatedEvent(**event_data)

# Now you have validated data
process_thought(event.thought_id, event.text, event.user_context)
```

### 3. AI Schemas (`ai_schemas.py`)

**Contract between**: Kafka Workers → Database (AI analysis outputs)

**AI Agent Output**:
```python
from common.schemas import ClassificationOutput, AnalysisOutput

# Agent 1 output (validated)
classification = ClassificationOutput(
    type="question",
    urgency="soon",
    entities=EntityExtraction(topics=["programming", "Rust"]),
    emotional_tone="curious",
    implied_needs=["skill development"]
)

# Save to database as JSONB
db.execute(
    "UPDATE thoughts SET classification = %s WHERE id = %s",
    (classification.dict(), thought_id)
)
```

**Frontend Reading Output**:
```python
# Frontend receives this from API
thought = {
    "id": "uuid",
    "classification": {
        "type": "question",
        "urgency": "soon",
        "entities": {...},
        ...
    }
}

# Can validate against schema
classification = ClassificationOutput(**thought["classification"])
```

## Usage Examples

### API Service

```python
from fastapi import FastAPI, HTTPException
from common.schemas import ThoughtCreateRequest, ThoughtResponse

app = FastAPI()

@app.post("/thoughts", response_model=ThoughtResponse)
async def create_thought(request: ThoughtCreateRequest):
    # Pydantic automatically validates the request
    # If invalid, returns 422 with validation errors
    
    thought = save_to_db(request)
    publish_to_kafka(thought)
    
    return ThoughtResponse(
        id=thought.id,
        status="pending",
        message="Thought saved!",
        created_at=thought.created_at
    )
```

### Kafka Workers

```python
from common.schemas import ThoughtCreatedEvent, ClassificationOutput

def process_thought(message):
    # Deserialize and validate event
    event = ThoughtCreatedEvent(**json.loads(message.value))
    
    # Run AI agent
    ai_output = run_classification_agent(event.text, event.user_context)
    
    # Validate AI output against schema
    classification = ClassificationOutput(**ai_output)
    
    # Save to database
    save_classification(event.thought_id, classification.dict())
```

### Frontend (TypeScript equivalent)

```typescript
// Generate TypeScript interfaces from Pydantic schemas
// Using tools like: pydantic-to-typescript

interface ThoughtCreateRequest {
    text: string;
    user_id: string;
    processing_mode: 'single' | 'group';
    group_id?: string;
}

interface ThoughtResponse {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    message: string;
    created_at: string;
    session_id?: string;
}

// Frontend sends validated request
const response = await fetch('/thoughts', {
    method: 'POST',
    body: JSON.stringify({
        text: "Should I learn Rust?",
        user_id: userId,
        processing_mode: "single"
    })
});

const thought: ThoughtResponse = await response.json();
```

## Breaking Changes

### What is a breaking change?

❌ **Breaking** (avoid these):
- Removing a required field
- Renaming a field
- Changing a field type
- Changing enum values (removing options)

✅ **Non-breaking** (safe):
- Adding optional fields
- Adding new enum values
- Adding new event types

### Handling Schema Changes

Since the service is not deployed yet, you can modify schemas freely. Once deployed:

1. **Add new optional fields** - Safe, won't break existing code
2. **Add new schemas** - Safe, existing services ignore them
3. **Breaking changes** - Update all services simultaneously before deploying

## Testing Schemas

```python
import pytest
from common.schemas import ThoughtCreateRequest, ClassificationOutput

def test_thought_create_request_validation():
    # Valid request
    request = ThoughtCreateRequest(
        text="Test thought",
        user_id="550e8400-e29b-41d4-a716-446655440000",
        processing_mode="single"
    )
    assert request.text == "Test thought"
    
    # Invalid request (missing required field)
    with pytest.raises(ValidationError):
        ThoughtCreateRequest(text="Test")  # Missing user_id

def test_classification_output_schema():
    # Valid output
    output = ClassificationOutput(
        type="task",
        urgency="immediate",
        entities=EntityExtraction(),
        emotional_tone="neutral",
        implied_needs=[]
    )
    
    # Serialize/deserialize
    json_data = output.json()
    restored = ClassificationOutput.parse_raw(json_data)
    assert restored.type == "task"
```

## Best Practices

1. **Always import from common.schemas** - Never duplicate schema definitions
2. **Validate at boundaries** - Validate when data enters/exits your service
3. **Use .dict() for JSON** - Convert Pydantic models to dict for JSON storage
4. **Parse with .parse_obj()** - Convert dict back to Pydantic model
5. **Handle validation errors** - Catch ValidationError and return user-friendly messages
6. **Document contracts** - Use docstrings to explain field requirements

## Schema Validation Flow

```
Frontend                 API Service              Kafka Workers
   |                        |                         |
   | POST /thoughts         |                         |
   | (JSON)                 |                         |
   |----------------------->|                         |
   |                        |                         |
   |              ThoughtCreateRequest                |
   |                  (validates)                     |
   |                        |                         |
   |                        | Kafka Event             |
   |                        | ThoughtCreatedEvent     |
   |                        | (validates)             |
   |                        |------------------------>|
   |                        |                         |
   |                        |              ThoughtCreatedEvent
   |                        |                  (validates)
   |                        |                         |
   |                        |                  ClassificationOutput
   |                        |                  (validates AI output)
   |                        |                         |
   |                        |<------------------------|
   |                        |    Update DB (JSONB)    |
   |                        |                         |
   |<-----------------------|                         |
   |   ThoughtResponse      |                         |
   |    (validates)         |                         |
```

## Generating TypeScript Interfaces

```bash
# Install pydantic-to-typescript
pip install pydantic-to-typescript

# Generate TypeScript interfaces
pydantic2ts --module common.schemas --output frontend/src/types/schemas.ts
```

## Summary

These schemas are **enforced contracts** that:
- Prevent runtime errors from mismatched data structures
- Enable multiple teams to work independently
- Provide automatic validation and documentation
- Support versioning and backward compatibility
- Make breaking changes explicit and manageable

**Import and use them everywhere data crosses service boundaries!**
