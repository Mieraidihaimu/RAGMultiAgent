# Service Schema Contracts

**Enforced data contracts between services using Pydantic schemas.**

## What This Is

Instead of documentation, we've created **actual Python schema files** that:
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
# In your API route
from fastapi import FastAPI
from common.schemas import ThoughtCreateRequest, ThoughtResponse

@app.post("/thoughts", response_model=ThoughtResponse)
async def create_thought(request: ThoughtCreateRequest):
    # ✅ Request automatically validated by Pydantic
    # ✅ Returns 422 if validation fails
    # ✅ Response automatically validated
    
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
# Batch processor output
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

**Who uses**: Frontend, API Service

**Key schemas**:
- `ThoughtCreateRequest` - Create thought request
- `ThoughtResponse` - Thought creation response  
- `UserContextSchema` - User profile for AI
- `AnonymousThoughtRequest` - Anonymous submission

### Event Schemas (`event_schemas.py`)

**Who uses**: API Service, Kafka Workers

**Key schemas**:
- `ThoughtCreatedEvent` - New thought to process
- `ThoughtProcessingEvent` - Processing started
- `ThoughtAgentCompletedEvent` - Agent completed
- `ThoughtCompletedEvent` - Processing done
- `ThoughtFailedEvent` - Processing failed

### AI Schemas (`ai_schemas.py`)

**Who uses**: Kafka Workers, Frontend (reading results)

**Key schemas (5-Agent Pipeline)**:
1. `ClassificationOutput` - Type, urgency, entities
2. `AnalysisOutput` - Goal alignment, needs
3. `ValueImpactOutput` - Economic, relational scores
4. `ActionPlanOutput` - Quick wins, main actions
5. `PriorityOutput` - Priority level, timeline

**Group mode**:
- `ConsolidatedOutput` - Synthesized persona outputs

## Benefits

### 1. Prevent Breaking Changes

```python
# ❌ This will fail at import time
from common.schemas import ThoughtCreateRequest

request = ThoughtCreateRequest(
    text="Test",
    # Missing required field 'user_id'
)
# ValidationError: field required
```

### 2. Type Safety

```python
from common.schemas import ClassificationOutput

# ✅ IDE autocomplete
output = ClassificationOutput(...)
print(output.type)  # IDE knows this is a Literal type
print(output.urgency)  # IDE autocomplete works
```

### 3. Auto-Validation

```python
# Frontend sends invalid data
{
    "text": "",  # Too short (min 1 char)
    "user_id": "not-a-uuid"  # Invalid UUID
}

# API automatically returns 422 with details:
{
    "detail": [
        {
            "loc": ["body", "text"],
            "msg": "ensure this value has at least 1 characters",
            "type": "value_error.any_str.min_length"
        },
        {
            "loc": ["body", "user_id"],
            "msg": "value is not a valid uuid",
            "type": "type_error.uuid"
        }
    ]
}
```

### 4. Contract Testing

```python
def test_thought_event_contract():
    """Test that event matches expected schema."""
    event = ThoughtCreatedEvent(
        user_id="user-123",
        thought_id="thought-456",
        text="Test"
    )
    
    # Serialize/deserialize
    json_str = event.json()
    restored = ThoughtCreatedEvent.parse_raw(json_str)
    
    # ✅ Contract preserved
    assert restored.event_type == "thought_created"
    assert restored.schema_version == "1.0.0"
```

## Integration Example

### Complete Flow

```python
# 1. Frontend submits thought
POST /thoughts
{
    "text": "Should I learn Rust?",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "processing_mode": "single"
}

# 2. API validates with ThoughtCreateRequest schema
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

# 7. Frontend reads from API
GET /thoughts/user-123/thought-456
# Returns ThoughtDetail with validated classification field
```

## Versioning Strategy

### Schema Version

All events include `schema_version`:

```python
class BaseEvent(BaseModel):
    schema_version: str = "1.0.0"
```

### Breaking Change Process

1. **Bump version**:
```python
class ThoughtCreatedEvent(BaseEvent):
    schema_version: str = "2.0.0"  # Was 1.0.0
    # ... new fields or changed fields
```

2. **Support multiple versions**:
```python
def deserialize_event(data: dict):
    version = data.get('schema_version', '1.0.0')
    
    if version == '1.0.0':
        return ThoughtCreatedEventV1(**data)
    elif version == '2.0.0':
        return ThoughtCreatedEventV2(**data)
    else:
        raise ValueError(f"Unsupported schema version: {version}")
```

3. **Migrate data**:
```python
def migrate_v1_to_v2(v1_event: ThoughtCreatedEventV1) -> ThoughtCreatedEventV2:
    return ThoughtCreatedEventV2(
        **v1_event.dict(),
        new_field="default_value"
    )
```

## Frontend Integration

### Generate TypeScript Interfaces

```bash
# Install tool
pip install pydantic-to-typescript

# Generate types
pydantic2ts --module common.schemas.api_schemas \
           --output frontend/src/types/api.ts
```

```typescript
// frontend/src/types/api.ts (auto-generated)
export interface ThoughtCreateRequest {
    text: string;
    user_id: string;
    processing_mode: 'single' | 'group';
    group_id?: string;
}

export interface ThoughtResponse {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    message: string;
    created_at: string;
    session_id?: string;
}
```

### Use in Frontend

```typescript
import { ThoughtCreateRequest, ThoughtResponse } from './types/api';

async function submitThought(text: string, userId: string): Promise<ThoughtResponse> {
    const request: ThoughtCreateRequest = {
        text,
        user_id: userId,
        processing_mode: 'single'
    };
    
    const response = await fetch('/thoughts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
    });
    
    return await response.json() as ThoughtResponse;
}
```

## Migration Guide

### Existing Code → Schema Validation

#### Before (No Validation)

```python
@app.post("/thoughts")
async def create_thought(data: dict):
    # ❌ No validation
    thought_text = data.get("text")  # Might be None
    user_id = data.get("user_id")    # Might be invalid
    # ... process
```

#### After (With Schema)

```python
from common.schemas import ThoughtCreateRequest, ThoughtResponse

@app.post("/thoughts", response_model=ThoughtResponse)
async def create_thought(request: ThoughtCreateRequest):
    # ✅ Guaranteed valid
    thought_text = request.text  # Never None, 1-10000 chars
    user_id = request.user_id     # Valid UUID
    # ... process
```

## Testing

```python
import pytest
from pydantic import ValidationError
from common.schemas import ThoughtCreateRequest, ClassificationOutput

def test_thought_request_validation():
    # Valid request
    request = ThoughtCreateRequest(
        text="Test thought",
        user_id="550e8400-e29b-41d4-a716-446655440000"
    )
    assert request.processing_mode == "single"  # Default value
    
    # Invalid: text too short
    with pytest.raises(ValidationError):
        ThoughtCreateRequest(
            text="",
            user_id="550e8400-e29b-41d4-a716-446655440000"
        )
    
    # Invalid: user_id not UUID
    with pytest.raises(ValidationError):
        ThoughtCreateRequest(
            text="Test",
            user_id="not-a-uuid"
        )

def test_classification_output():
    output = ClassificationOutput(
        type="task",
        urgency="immediate",
        entities=EntityExtraction(topics=["coding"]),
        emotional_tone="neutral",
        implied_needs=["learning"]
    )
    
    # Serialization
    json_data = output.json()
    restored = ClassificationOutput.parse_raw(json_data)
    
    assert restored.type == "task"
    assert restored.urgency == "immediate"
```

## Summary

### What You Get

✅ **Runtime validation** - Catch errors before they cause issues  
✅ **Type safety** - IDE autocomplete and type checking  
✅ **Version control** - Track schema changes  
✅ **Documentation** - Schemas are self-documenting  
✅ **Contract testing** - Test service boundaries  
✅ **Frontend sync** - Generate TypeScript from Python  
✅ **Break prevention** - Changes fail at import time  

### Next Steps

1. **Update existing code** to import from `common.schemas`
2. **Remove duplicate definitions** (e.g., in api/models.py, kafka/events.py)
3. **Add schema validation** to all service boundaries
4. **Generate TypeScript** interfaces for frontend
5. **Add contract tests** to your test suite
6. **Document breaking changes** in schema docstrings

### Files Location

```
/Users/mier/Documents/Projects/TrialPrototype/RAGMultiAgent/
└── common/
    └── schemas/
        ├── __init__.py           # Import all schemas
        ├── api_schemas.py        # API contracts (75 lines)
        ├── event_schemas.py      # Kafka contracts (85 lines)
        ├── ai_schemas.py         # AI output contracts (150 lines)
        └── README.md             # Detailed usage guide
```

**All schemas are ready to use! Import and validate at service boundaries.**
