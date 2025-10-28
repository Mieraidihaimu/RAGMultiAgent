# Service Architecture Diagram

Visual representation of service boundaries, responsibilities, and communication contracts.

---

## System Architecture with Service Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Frontend Service (Port 3000)                                             │  │
│  │  Responsibility: User Interface, SSE Client                               │  │
│  │  Technology: HTML/JS, nginx                                               │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────────────────┘
                               │
                               │ HTTP/REST + SSE
                               ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                       │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  API Service (Port 8000)                                                  │  │
│  │  ────────────────────────────────────────────────────────────────────    │  │
│  │  Responsibilities:                                                        │  │
│  │    • HTTP Gateway & Routing                                              │  │
│  │    • Authentication & Authorization                                      │  │
│  │    • Request Validation (Pydantic)                                       │  │
│  │    • Event Publishing (Kafka)                                            │  │
│  │    • Real-time Updates (SSE via Redis)                                   │  │
│  │    • Payment Integration (Stripe)                                        │  │
│  │    • Rate Limiting                                                       │  │
│  │  ────────────────────────────────────────────────────────────────────    │  │
│  │  Key Endpoints:                                                           │  │
│  │    POST   /thoughts                                                       │  │
│  │    POST   /anonymous/thoughts                                             │  │
│  │    POST   /signup, /login                                                 │  │
│  │    GET    /events/{session_id}   [SSE]                                   │  │
│  │    POST   /persona-groups                                                 │  │
│  │    GET    /health                                                         │  │
│  └──────────┬────────────────────────────┬──────────────┬────────────────────┘  │
└─────────────┼────────────────────────────┼──────────────┼─────────────────────┘
              │                            │              │
              │ Kafka Events               │ Redis        │ SQL Queries
              │ (Publish)                  │ Pub/Sub      │ (Read/Write)
              ▼                            ▼              ▼
┌──────────────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│  MESSAGE BROKER LAYER    │  │   CACHE LAYER      │  │   DATA LAYER             │
│  ─────────────────────   │  │   ─────────────    │  │   ──────────             │
│  Kafka (Port 9092)       │  │   Redis (6379)     │  │   PostgreSQL (5432)      │
│  ─────────────────────   │  │   ─────────────    │  │   ──────────             │
│  Responsibilities:       │  │   Responsibilities:│  │   Responsibilities:      │
│   • Event Streaming      │  │    • Pub/Sub       │  │    • Data Persistence    │
│   • Message Queuing      │  │    • Sessions      │  │    • Vector Search       │
│   • Partitioning (3)     │  │    • Rate Limits   │  │    • ACID Transactions   │
│   • Consumer Groups      │  │    • Cache         │  │    • Schema Mgmt         │
│  ─────────────────────   │  │   ─────────────    │  │   ──────────             │
│  Topics:                 │  │   Channels:        │  │   Tables:                │
│   • thought-events       │  │    • thought_      │  │    • users               │
│                          │  │      events:*      │  │    • thoughts            │
│                          │  │   Keys:            │  │    • persona_groups      │
│                          │  │    • anon_session  │  │    • personas            │
│                          │  │    • rate_limit    │  │    • thought_cache       │
└──────────┬───────────────┘  └────────┬───────────┘  └──────────┬───────────────┘
           │                           │                         │
           │ Consume Events            │ Publish Progress        │ Read/Write
           │                           │                         │
           └───────────────────────────┴─────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          PROCESSING LAYER                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Kafka Workers (Batch Processor)                                          │  │
│  │  ────────────────────────────────────────────────────────────────────    │  │
│  │  Responsibilities:                                                        │  │
│  │    • Event Consumption (Kafka)                                           │  │
│  │    • 5-Agent AI Pipeline Execution                                       │  │
│  │    • Semantic Caching (pgvector)                                         │  │
│  │    • Multi-Provider AI (Google/Anthropic/OpenAI)                         │  │
│  │    • Persona Group Processing                                            │  │
│  │    • Progress Publishing (Redis)                                         │  │
│  │    • Result Persistence (Database)                                       │  │
│  │  ────────────────────────────────────────────────────────────────────    │  │
│  │  5-Agent Pipeline:                                                        │  │
│  │    Agent 1: Classifier        → classification (JSONB)                   │  │
│  │    Agent 2: Analyzer          → analysis (JSONB)                         │  │
│  │    Agent 3: Value Assessor    → value_impact (JSONB)                     │  │
│  │    Agent 4: Action Planner    → action_plan (JSONB)                      │  │
│  │    Agent 5: Prioritizer       → priority (JSONB)                         │  │
│  │                                                                            │  │
│  │  Group Mode: Process through multiple personas, consolidate              │  │
│  └──────────────────────────────────┬────────────────────────────────────────┘  │
└─────────────────────────────────────┼─────────────────────────────────────────┘
                                      │
                                      ▼ AI API Calls
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Google Gemini   │  │ Anthropic Claude │  │   OpenAI GPT     │            │
│  │  (AI Provider)   │  │  (AI Provider)   │  │  (AI Provider)   │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
│  ┌──────────────────┐  ┌──────────────────┐                                  │
│  │ OpenAI Embeddings│  │  Stripe Payments │                                  │
│  │ (Semantic Cache) │  │  (Subscriptions) │                                  │
│  └──────────────────┘  └──────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Communication Contracts

### 1. Frontend ⟷ API Service

**Protocol**: HTTP/REST + Server-Sent Events (SSE)

```
┌──────────┐                                          ┌─────────┐
│ Frontend │                                          │   API   │
└────┬─────┘                                          └────┬────┘
     │                                                     │
     │  POST /thoughts                                     │
     │  { text, user_id, processing_mode, group_id }      │
     │────────────────────────────────────────────────────>│
     │                                                     │
     │  201 Created                                        │
     │  { id, status, created_at, session_id }             │
     │<────────────────────────────────────────────────────│
     │                                                     │
     │  GET /events/{session_id}  [SSE]                   │
     │────────────────────────────────────────────────────>│
     │                                                     │
     │  event: thought_processing                          │
     │  data: { thought_id, status }                       │
     │<────────────────────────────────────────────────────│
     │                                                     │
     │  event: thought_agent_completed                     │
     │  data: { agent_name, progress: "1/5" }              │
     │<────────────────────────────────────────────────────│
     │  ... (5 more agent events) ...                      │
     │                                                     │
     │  event: thought_completed                           │
     │  data: { thought_id, status: "completed" }          │
     │<────────────────────────────────────────────────────│
```

**Contract**:
- Input: HTTP JSON (validated by Pydantic models)
- Output: HTTP JSON responses OR SSE streams
- Auth: JWT Bearer token OR anonymous session token
- Rate Limiting: 3 thoughts for anonymous, tier-based for authenticated

---

### 2. API Service ⟷ Kafka

**Protocol**: Kafka Producer

```
┌─────────┐                                          ┌───────┐
│   API   │                                          │ Kafka │
└────┬────┘                                          └───┬───┘
     │                                                   │
     │  PUBLISH to 'thought-events'                      │
     │  Key: thought_id                                  │
     │  Value: ThoughtCreatedEvent JSON                  │
     │──────────────────────────────────────────────────>│
     │                                                   │
     │  ACK (message stored)                             │
     │<──────────────────────────────────────────────────│
```

**Contract**:
- Topic: `thought-events` (3 partitions)
- Key: `thought_id` (ensures ordering per thought)
- Value: JSON serialized event (see kafka/events.py)
- Schema Version: Included in event payload

**Event Schema**:
```json
{
  "event_id": "uuid",
  "event_type": "thought_created",
  "timestamp": "ISO-8601",
  "user_id": "uuid",
  "thought_id": "uuid",
  "text": "string",
  "user_context": { ... },
  "processing_mode": "single" | "group",
  "group_id": "uuid?"
}
```

---

### 3. Kafka ⟷ Kafka Workers

**Protocol**: Kafka Consumer

```
┌───────┐                                          ┌──────────────┐
│ Kafka │                                          │ Kafka Workers│
└───┬───┘                                          └──────┬───────┘
    │                                                     │
    │  CONSUME from 'thought-events'                      │
    │  Consumer Group: thought-processor-workers          │
    │<────────────────────────────────────────────────────│
    │                                                     │
    │  Message: ThoughtCreatedEvent                       │
    │────────────────────────────────────────────────────>│
    │                                                     │
    │  COMMIT offset (manual)                             │
    │<────────────────────────────────────────────────────│
```

**Contract**:
- Consumer Group: `thought-processor-workers`
- Auto-commit: False (manual commit after processing)
- Partitions: 3 (enables parallel processing)
- Error Handling: Retry with exponential backoff, DLQ for failures

---

### 4. Kafka Workers ⟷ Database

**Protocol**: SQL (PostgreSQL)

```
┌──────────────┐                                    ┌──────────┐
│Kafka Workers │                                    │ Database │
└──────┬───────┘                                    └────┬─────┘
       │                                                 │
       │  SELECT context FROM users WHERE id = ?         │
       │────────────────────────────────────────────────>│
       │                                                 │
       │  { demographics, goals, values, ... }           │
       │<────────────────────────────────────────────────│
       │                                                 │
       │  SELECT * FROM match_similar_thoughts(...)      │
       │  (semantic cache lookup)                        │
       │────────────────────────────────────────────────>│
       │                                                 │
       │  [] (no cache hit)                              │
       │<────────────────────────────────────────────────│
       │                                                 │
       │  ... AI Processing ...                          │
       │                                                 │
       │  UPDATE thoughts SET                            │
       │    status = 'completed',                        │
       │    classification = ?, analysis = ?, ...        │
       │  WHERE id = ?                                   │
       │────────────────────────────────────────────────>│
       │                                                 │
       │  OK (1 row updated)                             │
       │<────────────────────────────────────────────────│
```

**Contract**:
- Read Operations: User context, personas, semantic cache
- Write Operations: Thought results, persona runs, cache updates
- Transaction Isolation: Read Committed
- Connection Pooling: Max 10 connections per worker

---

### 5. Kafka Workers ⟷ Redis

**Protocol**: Redis Pub/Sub

```
┌──────────────┐                                    ┌───────┐
│Kafka Workers │                                    │ Redis │
└──────┬───────┘                                    └───┬───┘
       │                                                │
       │  PUBLISH thought_events:{session_id}           │
       │  { event: "thought_processing", data: {...} }  │
       │───────────────────────────────────────────────>│
       │                                                │
       │  Integer (# subscribers)                       │
       │<───────────────────────────────────────────────│
       │                                                │
       │  PUBLISH thought_events:{session_id}           │
       │  { event: "thought_agent_completed", ... }     │
       │───────────────────────────────────────────────>│
       │  ... (repeat for each agent) ...               │
       │                                                │
       │  PUBLISH thought_events:{session_id}           │
       │  { event: "thought_completed", ... }           │
       │───────────────────────────────────────────────>│
```

**Contract**:
- Channel Pattern: `thought_events:{session_id}`
- Message Format: JSON with event type and data
- TTL: Messages expire when SSE connection closes
- No persistence (pub/sub only)

---

### 6. Redis ⟷ API Service

**Protocol**: Redis Pub/Sub Subscribe

```
┌───────┐                                          ┌─────────┐
│ Redis │                                          │   API   │
└───┬───┘                                          └────┬────┘
    │                                                   │
    │  SUBSCRIBE thought_events:{session_id}            │
    │<──────────────────────────────────────────────────│
    │                                                   │
    │  Message: { event, data }                         │
    │──────────────────────────────────────────────────>│
    │  (from worker)                                    │
    │                                                   │
    │  ... (stream to SSE client) ...                   │
    │                                                   │
    │  UNSUBSCRIBE (when SSE connection closes)         │
    │<──────────────────────────────────────────────────│
```

**Contract**:
- Subscribe on SSE connection open
- Forward messages to SSE client
- Unsubscribe on connection close
- Heartbeat: Send comment every 30s to keep connection alive

---

### 7. Kafka Workers ⟷ AI Providers

**Protocol**: HTTP REST (Provider-specific APIs)

```
┌──────────────┐                                    ┌─────────────┐
│Kafka Workers │                                    │AI Providers │
└──────┬───────┘                                    └──────┬──────┘
       │                                                   │
       │  POST /v1/messages (Anthropic)                    │
       │  POST /v1/chat/completions (OpenAI)               │
       │  POST /v1beta/generateContent (Google)            │
       │  Body: { model, messages, temperature, ... }      │
       │──────────────────────────────────────────────────>│
       │                                                   │
       │  { content, usage, ... }                          │
       │<──────────────────────────────────────────────────│
       │                                                   │
       │  (Repeat for each of 5 agents)                    │
       │                                                   │
       │  POST /v1/embeddings (OpenAI)                     │
       │  Body: { input, model: "text-embedding-3-small" } │
       │──────────────────────────────────────────────────>│
       │                                                   │
       │  { data: [{ embedding: [...] }] }                 │
       │<──────────────────────────────────────────────────│
```

**Contract**:
- Provider Selection: ENV variable `AI_PROVIDER`
- Retry Logic: 3 retries with exponential backoff
- Rate Limiting: Respect provider limits
- Cost Tracking: Log token usage
- Prompt Caching: Use provider-specific caching (Anthropic)

---

## Data Flow Example: Complete Thought Processing

```
┌─────────┐  ┌─────┐  ┌───────┐  ┌──────┐  ┌───────┐  ┌──────────┐  ┌────────┐
│Frontend │  │ API │  │ Kafka │  │Workers│  │ Redis │  │ Database │  │AI Prov.│
└────┬────┘  └──┬──┘  └───┬───┘  └───┬───┘  └───┬───┘  └────┬─────┘  └───┬────┘
     │          │         │          │          │           │            │
     │ 1. POST  │         │          │          │           │            │
     │ /thoughts│         │          │          │           │            │
     │─────────>│         │          │          │           │            │
     │          │ 2. INSERT          │          │           │            │
     │          │ thought            │          │           │            │
     │          │────────────────────────────────────────────>           │
     │          │         │          │          │           │            │
     │          │ 3. PUBLISH         │          │           │            │
     │          │ ThoughtCreated     │          │           │            │
     │          │────────>│          │          │           │            │
     │          │         │          │          │           │            │
     │ 4. 201   │         │          │          │           │            │
     │ Created  │         │          │          │           │            │
     │<─────────│         │          │          │           │            │
     │          │         │          │          │           │            │
     │ 5. SSE   │         │          │          │           │            │
     │ Connect  │         │          │          │           │            │
     │─────────>│         │          │          │           │            │
     │          │ 6. SUBSCRIBE       │          │           │            │
     │          │────────────────────────────────>           │            │
     │          │         │          │          │           │            │
     │          │         │ 7. CONSUME         │           │            │
     │          │         │<─────────│          │           │            │
     │          │         │          │ 8. SELECT user       │            │
     │          │         │          │ context  │           │            │
     │          │         │          │──────────────────────>            │
     │          │         │          │          │ 9. PUBLISH             │
     │          │         │          │ "processing"         │            │
     │          │         │          │─────────>│           │            │
     │          │         │          │          │ 10. Forward            │
     │          │         │          │<─────────│           │            │
     │ 11. SSE  │         │          │          │           │            │
     │ event    │         │          │          │           │            │
     │<─────────│         │          │          │           │            │
     │          │         │          │ 12. Agent 1          │            │
     │          │         │          │─────────────────────────────────>│
     │          │         │          │          │           │ 13. Result │
     │          │         │          │<─────────────────────────────────│
     │          │         │          │ 14. PUBLISH          │            │
     │          │         │          │ "agent_completed"    │            │
     │          │         │          │─────────>│           │            │
     │ 15. SSE  │         │          │<─────────│           │            │
     │ event    │         │          │          │           │            │
     │<─────────┼─────────┼──────────┘          │           │            │
     │          │         │          ... (Agents 2-5) ...   │            │
     │          │         │          │          │ 16. UPDATE │            │
     │          │         │          │ thought  │           │            │
     │          │         │          │──────────────────────>            │
     │          │         │          │          │ 17. PUBLISH            │
     │          │         │          │ "completed"          │            │
     │          │         │          │─────────>│           │            │
     │ 18. SSE  │         │          │<─────────│           │            │
     │ complete │         │          │ 19. COMMIT           │            │
     │<─────────┼─────────┼──────────┤          │           │            │
     │          │         │<─────────│          │           │            │
```

---

## Service Dependency Graph

```
                    ┌─────────────┐
                    │  Frontend   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  API Service│────────┐
                    └──────┬──────┘        │
                           │               │
              ┌────────────┼───────────┐   │
              │            │           │   │
              ▼            ▼           ▼   ▼
       ┌──────────┐  ┌─────────┐  ┌──────────┐
       │  Kafka   │  │  Redis  │  │ Database │
       └────┬─────┘  └────┬────┘  └────┬─────┘
            │             │            │
            │             │            │
            └─────────────┼────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Kafka Workers  │
                 └────────┬─────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
       ┌──────────┐  ┌─────────┐  ┌──────────┐
       │ Database │  │  Redis  │  │    AI    │
       └──────────┘  └─────────┘  │ Providers│
                                  └──────────┘

Legend:
  → Direct dependency (service cannot function without it)
  ┆ Optional dependency (degrades gracefully if unavailable)
```

**Critical Dependencies**:
- API Service → Database (cannot serve requests without it)
- API Service → Kafka (async processing would fail, but read operations OK)
- Kafka Workers → Database (cannot save results)
- Kafka Workers → AI Providers (cannot process thoughts)

**Graceful Degradation**:
- If Kafka down: API can still serve read requests
- If Redis down: No real-time updates, but processing continues
- If Elasticsearch down: Search unavailable, but core features work

---

## Contract Testing Strategy

Each service boundary should have contract tests:

### 1. API Contract Tests
```python
# Verify API responses match documented schema
def test_thought_creation_response_schema():
    response = client.post('/thoughts', json=valid_payload)
    assert response.status_code == 201
    assert 'id' in response.json()
    assert 'status' in response.json()
    assert UUID(response.json()['id'])  # Valid UUID
```

### 2. Event Contract Tests
```python
# Verify Kafka events match schema
def test_thought_created_event_schema():
    event = ThoughtCreatedEvent(user_id=..., thought_id=..., text=...)
    json_str = event.to_json()
    deserialized = ThoughtCreatedEvent.from_json(json_str)
    assert deserialized.event_type == EventType.THOUGHT_CREATED
```

### 3. Database Contract Tests
```python
# Verify database schema matches documentation
def test_thoughts_table_schema():
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'thoughts'
    """)
    schema = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    assert schema['status'][0] == 'text'
    assert schema['status'][1] == 'NO'  # NOT NULL
```

---

**For detailed contract specifications, see [SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md)**
