# Service Schema Contracts

**Enforced data contracts between services using Pydantic schemas.**

## What This Is

Actual **Python schema files** that:
- ✅ Validate data at runtime
- ✅ Type-check during development  
- ✅ Prevent breaking changes
- ✅ Can be shared between services
- ✅ Auto-generate TypeScript interfaces for frontend

## Files Created

```
common/schemas/
├── __init__.py                 # Import all schemas
├── api_schemas.py              # API request/response contracts
├── event_schemas.py            # Kafka event contracts
├── ai_schemas.py               # AI output contracts
└── README.md                   # Usage guide
```

## Quick Start

### 1. API Service (Frontend ⟷ API)

```python
from fastapi import FastAPI
from common.schemas import ThoughtCreateRequest, ThoughtResponse

@app.post("/thoughts", response_model=ThoughtResponse)
async def create_thought(request: ThoughtCreateRequest):
    # ✅ Request automatically validated by Pydantic
    # ✅ Returns 422 if validation fails
    
    thought = save_to_db(request.dict())
    return ThoughtResponse(
        id=thought.id,
        status="pending",
        message="Thought saved!",
        created_at=thought.created_at
    )
```

### 2. Kafka Events (API → Workers)

```python
# Publishing (API Service)
from common.schemas import ThoughtCreatedEvent

event = ThoughtCreatedEvent(
    user_id=str(user_id),
    thought_id=str(thought_id),
    text=thought.text,
    user_context=user.context
)

producer.send('thought-events', value=event.json())
```

```python
# Consuming (Kafka Workers)
from common.schemas import ThoughtCreatedEvent

message = consumer.poll()
event = ThoughtCreatedEvent(**json.loads(message.value))

# ✅ Event validated - safe to use
process_thought(event.thought_id, event.text)
```

### 3. AI Output (Workers → Database)

```python
from common.schemas import ClassificationOutput, EntityExtraction

# AI agent returns dict, validate it
ai_output = run_classification_agent(thought_text)

# ✅ Validate AI output matches contract
classification = ClassificationOutput(
    type=ai_output["type"],
    urgency=ai_output["urgency"],
    entities=EntityExtraction(**ai_output["entities"]),
    emotional_tone=ai_output["emotional_tone"],
    implied_needs=ai_output["implied_needs"]
)

# Save to database
db.execute(
    "UPDATE thoughts SET classification = %s WHERE id = %s",
    (classification.dict(), thought_id)
)
```

## Schema Contracts

### API Schemas (`api_schemas.py`)

**Contract**: Frontend ⟷ API Service

- `ThoughtCreateRequest` - Create thought request
- `ThoughtResponse` - Thought creation response  
- `UserContextSchema` - User profile for AI
- `AnonymousThoughtRequest` - Anonymous submission

### Event Schemas (`event_schemas.py`)

**Contract**: API Service → Kafka → Workers

- `ThoughtCreatedEvent` - New thought to process
- `ThoughtProcessingEvent` - Processing started
- `ThoughtAgentCompletedEvent` - Agent completed
- `ThoughtCompletedEvent` - Processing done
- `ThoughtFailedEvent` - Processing failed

### AI Schemas (`ai_schemas.py`)

**Contract**: Workers → Database

**5-Agent Pipeline**:
1. `ClassificationOutput` - Type, urgency, entities
2. `AnalysisOutput` - Goal alignment, needs
3. `ValueImpactOutput` - Economic, relational scores
4. `ActionPlanOutput` - Quick wins, main actions
5. `PriorityOutput` - Priority level, timeline

**Group mode**:
- `ConsolidatedOutput` - Synthesized persona outputs

## Benefits

### 1. Prevent Runtime Errors

```python
# ❌ This fails immediately
request = ThoughtCreateRequest(
    text="",  # Too short (min 1 char)
    user_id="not-a-uuid"  # Invalid UUID
)
# ValidationError: field validation errors
```

### 2. Type Safety

```python
from common.schemas import ClassificationOutput

output = ClassificationOutput(...)
print(output.type)  # IDE knows this is a Literal type
print(output.urgency)  # IDE autocomplete works
```

### 3. Auto-Validation

```python
# FastAPI automatically validates
@app.post("/thoughts", response_model=ThoughtResponse)
async def create_thought(request: ThoughtCreateRequest):
    # If request invalid, FastAPI returns 422 automatically
    ...
```

### 4. Frontend Sync

```bash
# Generate TypeScript from Python schemas
pip install pydantic-to-typescript
pydantic2ts --module common.schemas.api_schemas \
           --output frontend/src/types/api.ts
```

## Complete Example

```python
# 1. Frontend submits thought
POST /thoughts
{
    "text": "Should I learn Rust?",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "processing_mode": "single"
}

# 2. API validates with schema
from common.schemas import ThoughtCreateRequest
request = ThoughtCreateRequest(**request_data)  # ✅ Validated

# 3. API publishes Kafka event
from common.schemas import ThoughtCreatedEvent
event = ThoughtCreatedEvent(
    user_id=str(request.user_id),
    thought_id=str(thought.id),
    text=request.text
)
kafka_producer.send('thought-events', value=event.json())

# 4. Worker consumes and validates event
event = ThoughtCreatedEvent(**json.loads(message.value))  # ✅ Validated

# 5. Worker runs AI, validates output
classification = ClassificationOutput(**ai_response)  # ✅ Validated

# 6. Worker saves to DB
db.execute("UPDATE thoughts SET classification = %s", classification.dict())
```

## Schema Changes

### Safe Changes (Non-Breaking)

✅ Adding optional fields
✅ Adding new schemas/events
✅ Adding new enum values

### Breaking Changes (Avoid)

❌ Removing required fields
❌ Renaming fields
❌ Changing field types
❌ Removing enum values

### How to Modify

Since the service isn't deployed yet:
1. Modify schemas freely during development
2. Update all services that use the schema
3. Test changes with contract tests
4. Deploy together when ready

Once deployed, only add optional fields to maintain compatibility.

## Testing

```python
import pytest
from pydantic import ValidationError
from common.schemas import ThoughtCreateRequest

def test_thought_request_validation():
    # Valid request
    request = ThoughtCreateRequest(
        text="Test thought",
        user_id="550e8400-e29b-41d4-a716-446655440000"
    )
    assert request.processing_mode == "single"  # Default
    
    # Invalid: missing user_id
    with pytest.raises(ValidationError):
        ThoughtCreateRequest(text="Test")
    
    # Invalid: text too short
    with pytest.raises(ValidationError):
        ThoughtCreateRequest(
            text="",
            user_id="550e8400-e29b-41d4-a716-446655440000"
        )
```

## Migration Path

### Current State
- `api/models.py` has some Pydantic models
- `kafka/events.py` has event classes
- AI outputs validated manually

### Recommended Changes

1. **Update API Service**
```python
# BEFORE
from api.models import ThoughtInput

# AFTER
from common.schemas import ThoughtCreateRequest
```

2. **Update Kafka Events**
```python
# BEFORE
from kafka.events import ThoughtCreatedEvent

# AFTER
from common.schemas import ThoughtCreatedEvent
```

3. **Validate AI Outputs**
```python
# BEFORE
classification = ai_output  # No validation

# AFTER
from common.schemas import ClassificationOutput
classification = ClassificationOutput(**ai_output)  # ✅ Validated
```

## Summary

### What You Get

✅ Runtime validation - Catch errors immediately  
✅ Type safety - IDE autocomplete and type checking  
✅ Auto-validation - FastAPI validates automatically  
✅ Contract testing - Test service boundaries  
✅ Frontend sync - Generate TypeScript from Python  
✅ Error prevention - Breaking changes caught at import time  

### Files Location

```
/Users/mier/Documents/Projects/TrialPrototype/RAGMultiAgent/
└── common/schemas/
    ├── __init__.py           # Import all schemas
    ├── api_schemas.py        # API contracts
    ├── event_schemas.py      # Kafka contracts
    ├── ai_schemas.py         # AI output contracts
    └── README.md             # Usage guide
```

**Import and use these schemas at all service boundaries!**
