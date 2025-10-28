# Service Contracts & Responsibilities

This document defines the responsibilities, input/output protocols, and contracts for each service in the RAG Multi-Agent system. Following these contracts ensures backward compatibility and enables multiple developers to work in parallel without breaking changes.

**Version**: 1.0.0  
**Last Updated**: 2025-10-28

---

## Table of Contents

- [Service Overview](#service-overview)
- [1. API Service](#1-api-service)
- [2. Kafka Workers Service](#2-kafka-workers-service)
- [3. Database Service](#3-database-service)
- [4. Kafka Broker Service](#4-kafka-broker-service)
- [5. Redis Service](#5-redis-service)
- [6. Search Service](#6-search-service)
- [7. Frontend Service](#7-frontend-service)
- [Contract Versioning](#contract-versioning)
- [Breaking Change Policy](#breaking-change-policy)

---

## Service Overview

```
┌─────────────┐
│  Frontend   │ HTTP/SSE
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         API Service (FastAPI)       │
│  - REST endpoints                   │
│  - Authentication/Authorization     │
│  - SSE real-time updates           │
│  - Payment integration             │
└─────┬────────────────┬──────────────┘
      │                │
      │ Kafka Events   │ Redis Pub/Sub
      ▼                ▼
┌──────────────┐  ┌──────────┐
│    Kafka     │  │  Redis   │
│   Broker     │  │  Cache   │
└──────┬───────┘  └────┬─────┘
       │               │
       │ Consume       │ Subscribe
       ▼               ▼
┌────────────────────────────────────┐
│   Kafka Workers (Batch Processor)  │
│  - 5-Agent AI Pipeline             │
│  - Semantic Caching                │
│  - Multi-provider AI               │
└────────┬───────────────────────────┘
         │
         ▼ Read/Write
┌────────────────────────────────────┐
│  Database (PostgreSQL + pgvector)  │
│  - Data persistence                │
│  - Vector search                   │
└────────────────────────────────────┘
```

---

## 1. API Service

**Location**: `api/`  
**Language**: Python (FastAPI)  
**Port**: 8000  
**Responsibilities**:

### Core Responsibilities

1. **HTTP API Gateway** - Expose REST endpoints for all client interactions
2. **Authentication & Authorization** - Manage user sessions, JWT tokens, OAuth
3. **Request Validation** - Validate and sanitize all incoming requests using Pydantic
4. **Event Publishing** - Publish events to Kafka for async processing
5. **Real-time Updates** - Provide SSE endpoints for streaming progress updates
6. **Payment Integration** - Handle Stripe subscription webhooks
7. **Rate Limiting** - Enforce anonymous and authenticated user limits

### Input Contracts

#### REST API Endpoints

All endpoints documented at `http://localhost:8000/docs` (OpenAPI/Swagger)

##### Thought Management

```http
POST /thoughts
Content-Type: application/json
Authorization: Bearer <token>

{
  "text": "string (1-10000 chars)",
  "user_id": "uuid",
  "processing_mode": "single" | "group",
  "group_id": "uuid?" // required if processing_mode='group'
}

Response: 201 Created
{
  "id": "uuid",
  "status": "pending",
  "message": "string",
  "created_at": "ISO-8601 datetime"
}
```

```http
POST /anonymous/thoughts
Content-Type: application/json

{
  "text": "string (1-10000 chars)",
  "session_token": "string?" // optional
}

Response: 201 Created
{
  "id": "uuid",
  "status": "pending",
  "message": "string",
  "created_at": "ISO-8601 datetime",
  "session_info": {
    "session_token": "string",
    "thoughts_remaining": "integer",
    "thoughts_used": "integer",
    "limit_reached": "boolean"
  }
}
```

```http
GET /thoughts/{user_id}?status=completed&limit=50&offset=0
Authorization: Bearer <token>

Response: 200 OK
{
  "thoughts": [ThoughtDetail],
  "count": "integer",
  "status_filter": "string?"
}
```

##### User Management

```http
POST /signup
Content-Type: application/json

{
  "email": "email",
  "password": "string (min 8 chars)"
}

Response: 201 Created
{
  "user_id": "uuid",
  "email": "email",
  "access_token": "jwt",
  "token_type": "bearer"
}
```

```http
POST /login
Content-Type: application/json

{
  "email": "email",
  "password": "string"
}

Response: 200 OK
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

##### Persona Groups

```http
POST /persona-groups
Authorization: Bearer <token>

{
  "name": "string (1-100 chars)",
  "description": "string (max 500 chars)?"
}

Response: 201 Created
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "string",
  "description": "string?",
  "personas": [],
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

```http
POST /persona-groups/{group_id}/personas
Authorization: Bearer <token>

{
  "name": "string (1-100 chars)",
  "prompt": "string (10-2000 chars)",
  "sort_order": "integer (>=0)"
}

Response: 201 Created
{
  "id": "uuid",
  "group_id": "uuid",
  "name": "string",
  "prompt": "string",
  "sort_order": "integer",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

##### Real-time Updates

```http
GET /events/{session_id}
Accept: text/event-stream

Response: 200 OK (SSE Stream)
event: thought_processing
data: {"thought_id": "uuid", "status": "processing"}

event: thought_agent_completed
data: {"thought_id": "uuid", "agent_name": "string", "progress": "1/5"}

event: thought_completed
data: {"thought_id": "uuid", "status": "completed"}
```

### Output Contracts

#### Kafka Events Published

```python
# Defined in kafka/events.py

ThoughtCreatedEvent {
  event_id: "uuid",
  event_type: "thought_created",
  timestamp: "ISO-8601",
  user_id: "string (uuid)",
  thought_id: "string (uuid)",
  text: "string",
  user_context: "dict?",
  processing_mode: "single" | "group",
  group_id: "string (uuid)?"
}
```

#### Redis Pub/Sub Channels

**Channel Pattern**: `thought_events:{session_id}`

```json
{
  "event": "thought_processing" | "thought_agent_completed" | "thought_completed" | "thought_failed",
  "data": {
    "thought_id": "uuid",
    "status": "string",
    "message": "string?",
    "progress": "string?",
    "timestamp": "ISO-8601"
  }
}
```

### Dependencies

- **Database**: Read/Write to PostgreSQL (user auth, thought storage)
- **Kafka**: Publish events to `thought-events` topic
- **Redis**: Subscribe to SSE channels, session management
- **Stripe API**: Payment webhooks and subscription management

### Error Handling

All errors follow consistent format:

```json
{
  "error": "Brief error message",
  "detail": "Detailed error description",
  "timestamp": "ISO-8601"
}
```

**Status Codes**:
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized
- 403: Forbidden (rate limit, subscription)
- 404: Not Found
- 500: Internal Server Error

---

## 2. Kafka Workers Service

**Location**: `batch_processor/`  
**Language**: Python  
**Responsibilities**:

### Core Responsibilities

1. **Event Consumption** - Consume events from Kafka `thought-events` topic
2. **AI Processing** - Execute 5-agent AI pipeline on thoughts
3. **Semantic Caching** - Check cache before AI processing to avoid duplicates
4. **Multi-Provider AI** - Support Google Gemini, Anthropic Claude, OpenAI GPT
5. **Persona Processing** - Process thoughts through multiple custom personas
6. **Progress Publishing** - Publish real-time progress to Redis
7. **Result Persistence** - Save AI analysis results to database

### Input Contracts

#### Kafka Events Consumed

**Topic**: `thought-events` (3 partitions)  
**Consumer Group**: `thought-processor-workers`

```python
# Event types consumed (from kafka/events.py)

ThoughtCreatedEvent {
  event_id: "uuid",
  event_type: "thought_created",
  timestamp: "ISO-8601",
  user_id: "string (uuid)",
  thought_id: "string (uuid)",
  text: "string",
  user_context: "dict?",
  processing_mode: "single" | "group",
  group_id: "string (uuid)?"
}
```

#### Database Reads

```sql
-- Fetch thought for processing
SELECT id, user_id, text, processing_mode, group_id, status
FROM thoughts
WHERE id = $1 AND status = 'pending';

-- Fetch user context
SELECT id, context
FROM users
WHERE id = $1;

-- Fetch personas for group processing
SELECT id, name, prompt, sort_order
FROM personas
WHERE group_id = $1
ORDER BY sort_order ASC;

-- Semantic cache lookup
SELECT id, thought_text, response, similarity
FROM match_similar_thoughts($1, $2, $3, $4);
-- Parameters: embedding, threshold (0.92), count (1), user_id
```

### Output Contracts

#### Database Writes

```sql
-- Update thought with processing results
UPDATE thoughts SET
  status = 'completed',
  processed_at = NOW(),
  classification = $1::jsonb,
  analysis = $2::jsonb,
  value_impact = $3::jsonb,
  action_plan = $4::jsonb,
  priority = $5::jsonb,
  consolidated_output = $6::jsonb, -- For group mode
  embedding = $7::vector(1536)
WHERE id = $8;

-- Insert persona run record (for group mode)
INSERT INTO thought_persona_runs (
  thought_id, persona_id, group_id, persona_name,
  persona_output, processing_time_ms
) VALUES ($1, $2, $3, $4, $5, $6);

-- Insert/update semantic cache
INSERT INTO thought_cache (
  user_id, thought_text, embedding, response, hit_count
) VALUES ($1, $2, $3, $4, 1)
ON CONFLICT (user_id, thought_text) DO UPDATE
SET hit_count = thought_cache.hit_count + 1,
    last_hit_at = NOW();
```

#### Redis Pub/Sub Published

**Channel Pattern**: `thought_events:{session_id}`

```json
// Processing started
{
  "event": "thought_processing",
  "data": {
    "thought_id": "uuid",
    "status": "processing",
    "message": "Starting AI analysis...",
    "timestamp": "ISO-8601"
  }
}

// Agent completed (5 times for 5-agent pipeline)
{
  "event": "thought_agent_completed",
  "data": {
    "thought_id": "uuid",
    "agent_name": "Classifier" | "Analyzer" | "Value Assessor" | "Action Planner" | "Prioritizer",
    "agent_number": 1-5,
    "progress": "1/5",
    "timestamp": "ISO-8601"
  }
}

// Group processing events
{
  "event": "group_processing_started",
  "data": {
    "thought_id": "uuid",
    "group_name": "string",
    "persona_count": "integer"
  }
}

{
  "event": "persona_completed",
  "data": {
    "thought_id": "uuid",
    "persona_name": "string",
    "progress": "2/5"
  }
}

// Processing completed
{
  "event": "thought_completed",
  "data": {
    "thought_id": "uuid",
    "status": "completed",
    "message": "Analysis complete!",
    "processing_time_seconds": "float",
    "timestamp": "ISO-8601"
  }
}

// Processing failed
{
  "event": "thought_failed",
  "data": {
    "thought_id": "uuid",
    "status": "failed",
    "error_message": "string",
    "timestamp": "ISO-8601"
  }
}
```

#### AI Analysis Output Schema

All AI outputs are stored as JSONB in database. Schema defined below:

##### Classification (Agent 1)

```json
{
  "type": "task" | "problem" | "idea" | "question" | "observation" | "emotion",
  "urgency": "immediate" | "soon" | "eventually" | "never",
  "entities": {
    "people": ["string"],
    "dates": ["string"],
    "places": ["string"],
    "topics": ["string"]
  },
  "emotional_tone": "string",
  "implied_needs": ["string"]
}
```

##### Analysis (Agent 2)

```json
{
  "goal_alignment": {
    "aligned_goals": ["string"],
    "conflicting_goals": ["string"],
    "reasoning": "string"
  },
  "underlying_needs": ["string"],
  "pattern_connections": ["string"],
  "realistic_assessment": {
    "feasibility": "string",
    "constraints": ["string"]
  },
  "unspoken_factors": ["string"]
}
```

##### Value Impact (Agent 3)

```json
{
  "economic_value": {
    "score": 0-10,
    "reasoning": "string"
  },
  "relational_value": {
    "score": 0-10,
    "reasoning": "string"
  },
  "legacy_value": {
    "score": 0-10,
    "reasoning": "string"
  },
  "health_value": {
    "score": 0-10,
    "reasoning": "string"
  },
  "growth_value": {
    "score": 0-10,
    "reasoning": "string"
  },
  "weighted_total": "float",
  "overall_assessment": "string"
}
```

##### Action Plan (Agent 4)

```json
{
  "quick_wins": [
    {
      "action": "string",
      "duration": "string",
      "timing": "string"
    }
  ],
  "main_actions": [
    {
      "action": "string",
      "duration": "string",
      "prerequisites": ["string"],
      "obstacles": ["string"],
      "mitigation": "string",
      "timing": "string"
    }
  ],
  "delegation_opportunities": ["string"],
  "success_metrics": ["string"]
}
```

##### Priority (Agent 5)

```json
{
  "priority_level": "Critical" | "High" | "Medium" | "Low" | "Defer",
  "urgency_reasoning": "string",
  "strategic_fit": "string",
  "recommended_timeline": {
    "start": "string",
    "duration": "string",
    "checkpoints": ["string"]
  },
  "final_recommendation": "string"
}
```

##### Consolidated Output (Group Mode Only)

```json
{
  "summary": "string",
  "key_insights": ["string"],
  "consensus_points": ["string"],
  "divergent_views": [
    {
      "persona": "string",
      "viewpoint": "string"
    }
  ],
  "recommended_action": "string",
  "personas_processed": "integer"
}
```

### Dependencies

- **Kafka**: Consume from `thought-events` topic
- **Database**: Read/Write thoughts, users, personas
- **Redis**: Publish SSE events
- **AI Providers**: Google Gemini, Anthropic Claude, OpenAI GPT
- **OpenAI Embeddings**: Generate embeddings for semantic cache

### Configuration

```env
# AI Provider Selection
AI_PROVIDER=google | anthropic | openai
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_CONSUMER_GROUP=thought-processor-workers

# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://...

# Semantic Cache
SEMANTIC_CACHE_THRESHOLD=0.92
SEMANTIC_CACHE_TTL_DAYS=7
```

---

## 3. Database Service

**Technology**: PostgreSQL 15 + pgvector  
**Port**: 5432  
**Responsibilities**:

### Core Responsibilities

1. **Data Persistence** - Store all application data
2. **Vector Search** - Enable semantic similarity search via pgvector
3. **Transactional Integrity** - Ensure ACID compliance
4. **Schema Management** - Version-controlled migrations
5. **Query Optimization** - Indexed queries for performance

### Schema Contracts

#### Tables

##### `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT, -- bcrypt hash
    is_anonymous BOOLEAN DEFAULT false,
    anonymous_session_token TEXT UNIQUE,
    subscription_tier TEXT DEFAULT 'free', -- free | pro | enterprise
    created_at TIMESTAMPTZ DEFAULT NOW(),
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    context_version INTEGER DEFAULT 1,
    context_updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_anonymous_token ON users(anonymous_session_token);
```

**Context JSONB Schema** (user profile for AI personalization):

```json
{
  "demographics": {
    "age": "integer?",
    "role": "string?",
    "location": "string?"
  },
  "goals": ["string"],
  "values": ["string"],
  "constraints": {
    "time": "string?",
    "financial": "string?",
    "health": "string?"
  },
  "challenges": ["string"],
  "patterns": ["string"]
}
```

##### `thoughts`

```sql
CREATE TABLE thoughts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Processing
    status TEXT DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processing_mode TEXT DEFAULT 'single'
        CHECK (processing_mode IN ('single', 'group')),
    group_id UUID REFERENCES persona_groups(id) ON DELETE SET NULL,
    processed_at TIMESTAMPTZ,
    processing_attempts INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- AI Results
    classification JSONB,
    analysis JSONB,
    value_impact JSONB,
    action_plan JSONB,
    priority JSONB,
    consolidated_output JSONB, -- For group mode
    
    -- Metadata
    context_version INTEGER,
    embedding VECTOR(1536)
);

-- Indexes
CREATE INDEX idx_thoughts_user_status ON thoughts(user_id, status);
CREATE INDEX idx_thoughts_created_at ON thoughts(created_at DESC);
CREATE INDEX idx_thoughts_status_pending ON thoughts(status) WHERE status = 'pending';
CREATE INDEX idx_thoughts_embedding ON thoughts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_thoughts_processing_mode ON thoughts(processing_mode);
CREATE INDEX idx_thoughts_group_id ON thoughts(group_id);
```

##### `persona_groups`

```sql
CREATE TABLE persona_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_group_name UNIQUE(user_id, name),
    CONSTRAINT group_name_length CHECK (LENGTH(TRIM(name)) >= 1 AND LENGTH(name) <= 100)
);

CREATE INDEX idx_persona_groups_user_id ON persona_groups(user_id);
```

##### `personas`

```sql
CREATE TABLE personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES persona_groups(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL, -- User-defined persona context
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT persona_name_length CHECK (LENGTH(TRIM(name)) >= 1 AND LENGTH(name) <= 100),
    CONSTRAINT persona_prompt_length CHECK (LENGTH(TRIM(prompt)) >= 10 AND LENGTH(prompt) <= 2000)
);

CREATE INDEX idx_personas_group_id ON personas(group_id);
CREATE INDEX idx_personas_sort_order ON personas(group_id, sort_order);
```

##### `thought_persona_runs`

```sql
CREATE TABLE thought_persona_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thought_id UUID NOT NULL REFERENCES thoughts(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,
    group_id UUID REFERENCES persona_groups(id) ON DELETE SET NULL,
    persona_name TEXT NOT NULL,
    persona_output JSONB, -- Full 5-agent result for this persona
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT reasonable_processing_time CHECK (processing_time_ms >= 0 AND processing_time_ms <= 300000)
);

CREATE INDEX idx_thought_persona_runs_thought_id ON thought_persona_runs(thought_id);
```

##### `thought_cache`

```sql
CREATE TABLE thought_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thought_text TEXT NOT NULL,
    embedding VECTOR(1536),
    response JSONB NOT NULL, -- Cached AI result
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

CREATE INDEX idx_cache_user_embedding ON thought_cache USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_cache_expires ON thought_cache(expires_at) WHERE expires_at > NOW();
```

##### `weekly_synthesis`

```sql
CREATE TABLE weekly_synthesis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    synthesis JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, week_start)
);

CREATE INDEX idx_weekly_synthesis_user_week ON weekly_synthesis(user_id, week_start DESC);
```

#### Functions

##### `match_similar_thoughts`

```sql
CREATE OR REPLACE FUNCTION match_similar_thoughts(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    user_id_param uuid
)
RETURNS TABLE (
    id uuid,
    thought_text text,
    response jsonb,
    similarity float
)
LANGUAGE plpgsql;
```

**Usage**:
```sql
SELECT * FROM match_similar_thoughts(
    $1::vector(1536), -- query embedding
    0.92,             -- threshold
    1,                -- limit
    $2::uuid          -- user_id
);
```

### Migration Strategy

**Location**: `database/migrations/`  
**Naming Convention**: `XXX_description.sql` (e.g., `001_initial_schema.sql`)  
**Applied**: Automatically on container startup via docker-entrypoint-initdb.d

### Dependencies

None (foundational service)

---

## 4. Kafka Broker Service

**Technology**: Apache Kafka (KRaft mode)  
**Port**: 9092 (internal), 9093 (external)  
**Responsibilities**:

### Core Responsibilities

1. **Message Queuing** - Queue thought processing events
2. **Event Streaming** - Provide durable event log
3. **Partitioning** - Enable parallel processing (3 partitions)
4. **Consumer Groups** - Support multiple worker instances
5. **Message Retention** - Keep events for debugging (7 days)

### Topics

#### `thought-events`

**Partitions**: 3  
**Replication Factor**: 1 (increase in production)  
**Retention**: 7 days  
**Compression**: snappy

**Message Format**:
```json
{
  "key": "thought_id (uuid)", // For partition routing
  "value": "ThoughtEvent JSON" // See kafka/events.py
}
```

**Event Types** (see [Kafka Events Schema](#kafka-events-published)):
- `thought_created`
- `thought_processing`
- `thought_agent_completed`
- `thought_completed`
- `thought_failed`
- `group_processing_started`
- `persona_completed`
- `consolidation_started`

### Producer Contract

**Producer ID**: `api-service`

```python
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8') if k else None
)

# Publish event
producer.send(
    topic='thought-events',
    key=thought_id,  # Ensures ordering per thought
    value=event.to_json()
)
```

### Consumer Contract

**Consumer Group**: `thought-processor-workers`  
**Auto-commit**: False (manual commit after successful processing)

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'thought-events',
    bootstrap_servers=['kafka:9092'],
    group_id='thought-processor-workers',
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    event = deserialize_event(message.value)
    process_event(event)
    consumer.commit()  # Manual commit
```

### Dependencies

None (foundational service)

---

## 5. Redis Service

**Technology**: Redis 7  
**Port**: 6379  
**Responsibilities**:

### Core Responsibilities

1. **Pub/Sub** - Real-time event distribution for SSE
2. **Session Storage** - Anonymous user session tracking
3. **Rate Limiting** - Track API request counts
4. **Cache** - Temporary data caching (future)

### Pub/Sub Channels

#### Pattern: `thought_events:{session_id}`

**Publishers**: Kafka Workers  
**Subscribers**: API Service (SSE endpoints)

**Message Format**:
```json
{
  "event": "thought_processing" | "thought_agent_completed" | "thought_completed" | "thought_failed",
  "data": {
    "thought_id": "uuid",
    "status": "string",
    "message": "string",
    "timestamp": "ISO-8601"
  }
}
```

**Publishing** (from workers):
```python
import redis
r = redis.Redis(host='redis', port=6379)
r.publish(f'thought_events:{session_id}', json.dumps(message))
```

**Subscribing** (from API):
```python
import redis
r = redis.Redis(host='redis', port=6379)
pubsub = r.pubsub()
pubsub.subscribe(f'thought_events:{session_id}')
for message in pubsub.listen():
    yield message['data']
```

### Key Patterns

#### Anonymous Sessions

**Key**: `anon_session:{token}`  
**Type**: Hash  
**TTL**: 24 hours

```redis
HSET anon_session:{token} thoughts_used 1
HSET anon_session:{token} created_at {timestamp}
EXPIRE anon_session:{token} 86400
```

#### Rate Limiting

**Key**: `rate_limit:{user_id}:{endpoint}:{window}`  
**Type**: String (counter)  
**TTL**: Window duration

```redis
INCR rate_limit:{user_id}:/thoughts:60
EXPIRE rate_limit:{user_id}:/thoughts:60 60
```

### Dependencies

None (foundational service)

---

## 6. Search Service

**Location**: `search_comparison/`  
**Technology**: Elasticsearch (optional)  
**Port**: 9200  
**Responsibilities**:

### Core Responsibilities

1. **Full-Text Search** - Search thoughts by text content
2. **Hybrid Search** - Combine semantic and keyword search
3. **Aggregations** - Analytics on thought patterns
4. **Faceted Search** - Filter by tags, dates, categories

### Index Contract

#### `thoughts` Index

```json
{
  "mappings": {
    "properties": {
      "thought_id": { "type": "keyword" },
      "user_id": { "type": "keyword" },
      "text": { 
        "type": "text",
        "analyzer": "english"
      },
      "classification_type": { "type": "keyword" },
      "created_at": { "type": "date" },
      "tags": { "type": "keyword" },
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

### Search API Contract

#### Hybrid Search

```http
POST /search/hybrid
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "string",
  "user_id": "uuid",
  "filters": {
    "type": ["task", "idea"],
    "date_from": "ISO-8601",
    "date_to": "ISO-8601"
  },
  "limit": 10,
  "offset": 0
}

Response: 200 OK
{
  "results": [
    {
      "thought_id": "uuid",
      "text": "string",
      "score": "float",
      "highlight": "string",
      "created_at": "ISO-8601"
    }
  ],
  "total": "integer",
  "took_ms": "integer"
}
```

### Dependencies

- **Database**: Read thought data for indexing
- **API Service**: Expose search endpoints

---

## 7. Frontend Service

**Location**: `frontend/`  
**Technology**: HTML/JS, nginx  
**Port**: 3000  
**Responsibilities**:

### Core Responsibilities

1. **User Interface** - Provide web UI for thought submission
2. **SSE Client** - Listen for real-time processing updates
3. **Authentication UI** - Login/signup forms
4. **Dashboard** - Display thought analysis results
5. **Persona Management** - Create/edit persona groups

### API Integration Contract

**Base URL**: `http://localhost:8000` (configurable)

#### Authentication

```javascript
// Signup
const response = await fetch('/signup', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});
const { access_token } = await response.json();
localStorage.setItem('token', access_token);
```

#### Thought Submission

```javascript
// Submit thought
const response = await fetch('/thoughts', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({ text, user_id, processing_mode, group_id })
});
const { id, session_id } = await response.json();

// Listen for updates via SSE
const eventSource = new EventSource(`/events/${session_id}`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateProgress(data);
};
```

### Dependencies

- **API Service**: All backend operations
- **SSE**: Real-time updates

---

## Contract Versioning

### Versioning Strategy

We follow **Semantic Versioning** for all contracts:

**Format**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (requires migration)
- **MINOR**: Backward-compatible additions
- **PATCH**: Bug fixes, clarifications

**Current Version**: 1.0.0

### API Versioning

APIs will be versioned via URL prefix when breaking changes occur:

```
/v1/thoughts      # Current
/v2/thoughts      # Future breaking change
```

**Deprecation Policy**:
- Announce deprecation 3 months before removal
- Support old version for 6 months minimum
- Provide migration guide

### Event Schema Versioning

Kafka events include schema version in event:

```json
{
  "schema_version": "1.0.0",
  "event_type": "thought_created",
  ...
}
```

**Backward Compatibility**:
- Consumers must handle old schema versions
- New fields are optional
- Never remove or rename fields (add new ones instead)

### Database Schema Versioning

Use numbered migrations:

```
001_initial_schema.sql
002_add_subscriptions.sql
003_add_auth_fields.sql
...
```

**Migration Rules**:
- Never modify existing migrations
- Always create new migration for changes
- Test rollback capability
- Include data migration scripts

---

## Breaking Change Policy

### What Constitutes a Breaking Change?

1. **API**: Removing/renaming endpoint, changing required fields
2. **Events**: Removing/renaming event fields
3. **Database**: Removing columns, changing types
4. **Behavior**: Changing default behavior that clients depend on

### Non-Breaking Changes

1. **API**: Adding new optional fields, new endpoints
2. **Events**: Adding new optional fields, new event types
3. **Database**: Adding new columns with defaults
4. **Behavior**: Adding new features behind feature flags

### Process for Breaking Changes

1. **Proposal**: Document proposed change and impact
2. **Review**: Team review and approval
3. **Deprecation**: Announce and mark as deprecated
4. **Migration Guide**: Provide clear upgrade path
5. **Support Period**: Support old version for 6 months
6. **Removal**: Remove after support period

### Example Migration Path

```
# Version 1.0.0 (Current)
POST /thoughts
{
  "text": "string",
  "user_id": "uuid"
}

# Version 1.1.0 (Add optional field - NON-BREAKING)
POST /thoughts
{
  "text": "string",
  "user_id": "uuid",
  "processing_mode": "single" (optional, defaults to "single")
}

# Version 2.0.0 (Remove user_id from body - BREAKING)
# Would require new endpoint: POST /v2/thoughts
# Extract user_id from JWT token instead
```

---

## Service Communication Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Communication Flows                      │
└─────────────────────────────────────────────────────────────────┘

1. Thought Submission Flow:
   Frontend → API (HTTP POST /thoughts)
   API → Database (INSERT thought)
   API → Kafka (PUBLISH ThoughtCreatedEvent)
   API → Frontend (HTTP 201 + session_id)

2. Processing Flow:
   Kafka → Worker (CONSUME ThoughtCreatedEvent)
   Worker → Database (SELECT user context, personas)
   Worker → AI Provider (5-agent pipeline)
   Worker → Redis (PUBLISH progress events)
   Worker → Database (UPDATE thought with results)

3. Real-time Update Flow:
   Frontend → API (SSE /events/{session_id})
   Worker → Redis (PUBLISH to thought_events channel)
   Redis → API (SUBSCRIBE to channel)
   API → Frontend (SSE stream)

4. Search Flow:
   Frontend → API (HTTP POST /search/hybrid)
   API → Search Service (Query Elasticsearch)
   API → Database (Fetch full thought details)
   API → Frontend (HTTP 200 + results)
```

---

## Testing Contracts

All contracts should have integration tests:

### API Contract Tests

```python
# tests/test_api_contracts.py
def test_thought_creation_contract():
    response = client.post('/thoughts', json={
        'text': 'test thought',
        'user_id': str(user_id)
    })
    assert response.status_code == 201
    assert 'id' in response.json()
    assert 'status' in response.json()
    assert response.json()['status'] == 'pending'
```

### Event Contract Tests

```python
# tests/test_event_contracts.py
def test_thought_created_event_schema():
    event = ThoughtCreatedEvent(
        user_id=str(user_id),
        thought_id=str(thought_id),
        text='test'
    )
    serialized = event.to_json()
    deserialized = ThoughtCreatedEvent.from_json(serialized)
    assert deserialized.event_type == EventType.THOUGHT_CREATED
```

### Database Contract Tests

```python
# tests/test_database_contracts.py
def test_thought_table_schema():
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'thoughts'
    """)
    columns = {row[0]: row[1] for row in cursor.fetchall()}
    assert columns['id'] == 'uuid'
    assert columns['status'] == 'text'
    assert columns['classification'] == 'jsonb'
```

---

## Summary Checklist

When making changes, ensure:

- [ ] Contract changes are documented in this file
- [ ] Breaking changes follow the breaking change policy
- [ ] API changes are reflected in OpenAPI schema
- [ ] Event schema changes bump schema_version
- [ ] Database changes have migration scripts
- [ ] Integration tests cover new contracts
- [ ] Dependent services are notified
- [ ] Documentation is updated

---

**Maintained by**: Development Team  
**Questions?**: Create an issue or contact the maintainers
