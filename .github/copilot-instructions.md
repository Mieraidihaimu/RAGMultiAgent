# RAG Multi-Agent Thought Processor - AI Coding Instructions

## Project Overview

This is an **AI-powered thought analysis system** using a **5-agent pipeline** with **event-driven architecture**. The system processes user thoughts through multiple AI agents (Classification → Analysis → Value Assessment → Action Planning → Prioritization) with real-time updates, semantic caching, and multi-provider AI support.

**Tech Stack**: FastAPI, PostgreSQL+pgvector, Apache Kafka, Redis, Stripe, Docker
**AI Providers**: Google Gemini (default), Anthropic Claude, OpenAI GPT
**Key Features**: Real-time SSE, Event-driven (Kafka), Semantic caching, Anonymous users, Payment integration

---

## Architecture Principles

### 1. Event-Driven with Kafka
- **ALL thought processing goes through Kafka events** (no direct processing in API)
- API produces events → Workers consume events → Workers publish progress to Redis
- Use `ThoughtCreated`, `ThoughtProcessingStarted`, `ThoughtProcessingCompleted` events
- 3 Kafka partitions for parallel processing
- Never bypass Kafka for thought processing

### 2. Real-Time Updates via SSE
- Use Server-Sent Events (SSE) for client updates, NOT WebSockets
- Redis pub/sub for broadcasting progress across workers
- Session-based SSE streams (`/events/{session_id}`)
- Event types: `processing`, `agent_completed`, `completed`, `error`

### 3. Semantic Caching (RAG)
- Check cache BEFORE processing with AI agents
- Use pgvector cosine similarity (threshold: 0.92)
- Store embeddings for all thoughts
- Cache saves ~30% of AI costs

### 4. Multi-Provider AI Support
- Support Gemini, Claude, and GPT interchangeably
- Use provider abstraction layer (`ai_providers/`)
- All providers must implement same agent interface
- Configuration via `AI_PROVIDER` env var

---

## Code Style & Standards

### Python
```python
# Use type hints everywhere
def process_thought(thought_id: UUID, user_context: Dict[str, Any]) -> Dict[str, Any]:
    """Process a thought through the pipeline.
    
    Args:
        thought_id: UUID of the thought to process
        user_context: User's profile and preferences
        
    Returns:
        Dict containing all agent outputs
    """
    pass

# Pydantic models for all API contracts
class ThoughtInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    user_id: UUID
    
# Async/await for I/O operations
async def fetch_thought(thought_id: UUID) -> Dict[str, Any]:
    async with get_db() as conn:
        result = await conn.fetchrow(...)
        return dict(result)
```

### Database
```python
# Always use parameterized queries (SQL injection prevention)
query = "SELECT * FROM thoughts WHERE user_id = $1 AND status = $2"
await conn.fetch(query, user_id, "completed")

# Use JSONB for flexible data (agent outputs)
# Use vectors for embeddings (pgvector)
# Add indexes for common queries
```

### API Design
```python
# RESTful endpoints
POST   /thoughts              # Create thought
GET    /thoughts/{user_id}    # List thoughts
GET    /events/{session_id}   # SSE stream

# Use Pydantic models for validation
@app.post("/thoughts", response_model=ThoughtResponse)
async def create_thought(thought: ThoughtInput):
    pass

# Proper error handling
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": str(exc)})
```

### Frontend (JavaScript)
```javascript
// Use modern ES6+ syntax
const fetchThoughts = async (userId) => {
    const response = await fetch(`/api/thoughts/${userId}`);
    return await response.json();
};

// EventSource for SSE
const eventSource = new EventSource(`/events/${sessionId}`);
eventSource.addEventListener('agent_completed', (event) => {
    const data = JSON.parse(event.data);
    updateProgress(data.agent_name, data.output);
});

// CSS classes from summer-theme.css
<button class="btn btn-primary">Analyze</button>
<div class="card card-warm">...</div>
```

---

## Project Structure

```
RAGMultiAgent/
├── api/                      # FastAPI backend
│   ├── main.py              # API routes, SSE endpoints
│   ├── auth_routes.py       # Authentication (signup/login)
│   ├── payment_routes.py    # Stripe integration
│   ├── models.py            # Pydantic models (18 models)
│   ├── database.py          # DB connection pooling
│   └── sse.py               # SSE implementation
├── batch_processor/         # Kafka consumers (3 workers)
│   ├── processor.py         # Event processing logic
│   ├── agents.py            # 5-agent pipeline
│   ├── semantic_cache.py    # RAG caching
│   └── ai_providers/        # AI provider abstractions
├── kafka/                   # Event infrastructure
│   ├── producer.py          # Event publishing
│   ├── consumer.py          # Event consumption
│   └── events.py            # Event schemas
├── common/                  # Shared utilities
│   ├── schemas/             # Shared Pydantic models
│   └── database/            # DB utilities
├── frontend/                # Web UI (Perplexity-inspired)
│   ├── summer-theme.css     # Design system
│   ├── index.html           # Main app
│   └── auth-manager.js      # Auth handling
└── tests/                   # Integration tests (27 tests)
```

---

## Key Models & Schemas

### Pydantic Models (api/models.py)
- `ThoughtInput` - Thought submission
- `AnonymousThoughtInput` - Anonymous thoughts (rate-limited)
- `ThoughtResponse` - Creation response with session info
- `ThoughtDetail` - Full thought with all agent outputs
- `SSEEvent` - Real-time event structure
- `PersonaInput/PersonaResponse` - Multi-persona support
- `PersonaGroupInput/PersonaGroupResponse` - Persona groups

### Database Schema
```sql
-- Core tables
thoughts (id, user_id, text, status, embedding, classification, analysis, value_impact, action_plan, priority)
users (id, email, password_hash, subscription_tier, created_at)
thought_cache (id, thought_text, embedding, response, hit_count, expires_at)
weekly_synthesis (id, user_id, week_start, week_end, synthesis)

-- Extensions
personas (id, user_id, name, description, context, created_at)
persona_groups (id, user_id, name, persona_ids, created_at)
thought_persona_runs (id, thought_id, persona_id, output, created_at)
```

### Kafka Events (kafka/events.py)
- `ThoughtCreated` - New thought submitted
- `ThoughtProcessingStarted` - Worker picked up thought
- `ThoughtAgentCompleted` - Individual agent finished
- `ThoughtProcessingCompleted` - All agents finished
- `ThoughtProcessingFailed` - Processing error

---

## Critical Implementation Rules

### 1. Thought Processing Flow
```python
# API Layer (api/main.py)
@app.post("/thoughts")
async def create_thought(thought: ThoughtInput):
    # 1. Save to DB with status="pending"
    thought_id = await save_thought(thought.text, thought.user_id, "pending")
    
    # 2. Produce Kafka event (DON'T process directly!)
    await kafka_producer.produce(ThoughtCreated(
        thought_id=thought_id,
        user_id=thought.user_id,
        text=thought.text,
        session_id=session_id
    ))
    
    # 3. Return immediately
    return ThoughtResponse(id=thought_id, status="pending")

# Worker Layer (batch_processor/processor.py)
async def process_thought(event: ThoughtCreated):
    # 1. Update status
    await update_status(event.thought_id, "processing")
    
    # 2. Publish to Redis for SSE
    await redis.publish(f"session:{event.session_id}", {
        "type": "processing",
        "thought_id": event.thought_id
    })
    
    # 3. Check semantic cache
    cached = await check_cache(event.text, event.user_id)
    if cached:
        await save_results(event.thought_id, cached)
        return
    
    # 4. Run 5-agent pipeline
    user_context = await fetch_user_context(event.user_id)
    results = await run_agents(event.text, user_context)
    
    # 5. Save results and cache
    await save_results(event.thought_id, results)
    await cache_results(event.text, results)
```

### 2. SSE Implementation
```python
# api/sse.py
async def event_stream(session_id: str):
    """Stream SSE events from Redis"""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"session:{session_id}")
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            yield f"event: {data['type']}\ndata: {json.dumps(data)}\n\n"
```

### 3. Semantic Caching
```python
# batch_processor/semantic_cache.py
async def check_cache(text: str, user_id: UUID) -> Optional[Dict]:
    """Check if similar thought was processed before"""
    # 1. Generate embedding
    embedding = await generate_embedding(text)
    
    # 2. Vector similarity search
    query = """
        SELECT response, 1 - (embedding <=> $1) as similarity
        FROM thought_cache
        WHERE user_id = $2 AND expires_at > NOW()
        ORDER BY embedding <=> $1
        LIMIT 1
    """
    result = await conn.fetchrow(query, embedding, user_id)
    
    # 3. Check threshold
    if result and result['similarity'] > 0.92:
        await increment_hit_count(result['id'])
        return result['response']
    
    return None
```

### 4. AI Provider Abstraction
```python
# batch_processor/ai_providers/base.py
class BaseAIProvider(ABC):
    @abstractmethod
    async def classify(self, text: str, context: Dict) -> Dict:
        """Agent 1: Classification"""
        pass
    
    @abstractmethod
    async def analyze(self, text: str, classification: Dict, context: Dict) -> Dict:
        """Agent 2: Contextual Analysis"""
        pass
    
    # ... other agents

# Usage in processor.py
provider = get_ai_provider(os.getenv("AI_PROVIDER"))  # google/anthropic/openai
classification = await provider.classify(text, user_context)
```

### 5. Anonymous User Rate Limiting
```python
# api/anonymous_utils.py
async def check_rate_limit(session_token: str) -> bool:
    """Check if anonymous user exceeded limit (3 thoughts)"""
    count = await redis.get(f"anon:{session_token}:count")
    return int(count or 0) < 3

async def increment_usage(session_token: str):
    """Increment usage counter"""
    await redis.incr(f"anon:{session_token}:count")
    await redis.expire(f"anon:{session_token}:count", 86400)  # 24h
```

---

## Testing Standards

### Integration Tests (tests/)
```python
# Always use pytest fixtures
@pytest.fixture
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Test full workflows
async def test_thought_processing_workflow(test_client):
    # 1. Create thought
    response = await test_client.post("/thoughts", json=thought_data)
    assert response.status_code == 201
    thought_id = response.json()["id"]
    
    # 2. Wait for processing
    await asyncio.sleep(2)
    
    # 3. Check results
    response = await test_client.get(f"/thoughts/{user_id}/{thought_id}")
    assert response.json()["status"] == "completed"

# Test Kafka directly
async def test_kafka_event_flow():
    # Produce event
    await producer.produce(ThoughtCreated(...))
    
    # Consume event
    message = await consumer.consume(timeout=5.0)
    assert message.event_type == "ThoughtCreated"
```

### Test Coverage Requirements
- ✅ All API endpoints
- ✅ Kafka producer/consumer
- ✅ SSE event streaming
- ✅ Database operations
- ✅ Anonymous user limits
- ✅ Stripe integration
- ✅ Error handling

---

## Frontend Design System

### Use Summer Theme (frontend/summer-theme.css)
```html
<!-- Buttons -->
<button class="btn btn-primary">Analyze Thought</button>
<button class="btn btn-secondary">Cancel</button>

<!-- Cards -->
<div class="card card-warm">
    <h3 class="gradient-text">Classification</h3>
    <p>Type: Task | Urgency: Soon</p>
</div>

<!-- Forms -->
<input type="text" class="input" placeholder="Enter your thought...">
<textarea class="input" rows="4"></textarea>

<!-- Badges -->
<span class="badge badge-success">Completed</span>
<span class="badge badge-warning">Processing</span>
```

### Color Palette
- **Primary (Warm)**: Coral #FF6B6B, Yellow #FFC93C, Peach #FF8E53
- **Secondary (Cool)**: Teal #4ECDC4, Sky #5DADE2
- **Neutrals**: Dark #2C3E50, Medium #666, Light #999
- **Backgrounds**: White #FFFFFF, Light Gray #F8F9FA

### Design Principles
- ✨ Perplexity-inspired minimalism
- 🌞 Warm, cheerful summer vibes
- 📱 Mobile-first responsive
- ♿ WCAG AA accessible
- 🎨 Consistent spacing and shadows

---

## Common Patterns

### Error Handling
```python
# Always use try-except for external calls
try:
    result = await ai_provider.classify(text, context)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    await update_status(thought_id, "failed")
    await publish_error_event(session_id, str(e))
    raise
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# Structured logging
logger.info(f"Processing thought {thought_id} for user {user_id}")
logger.error(f"Failed to process: {e}", exc_info=True)
```

### Environment Variables
```python
# Always provide defaults
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/thoughtprocessor")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "true").lower() == "true"
AI_PROVIDER = os.getenv("AI_PROVIDER", "google")
```

### Database Connections
```python
# Use connection pooling
async with get_db() as conn:
    result = await conn.fetch(query, *params)
    
# Always close resources
try:
    async with conn.transaction():
        await conn.execute(query)
finally:
    await conn.close()
```

---

## Performance Optimization

### 1. Caching Strategy
- **L1**: Prompt caching (Anthropic native) - 90% cost reduction
- **L2**: Semantic caching (pgvector) - ~30% hit rate
- **L3**: Redis for session data - Instant access

### 2. Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_thoughts_user_status ON thoughts(user_id, status);
CREATE INDEX idx_thoughts_created ON thoughts(created_at DESC);

-- Use JSONB indexes
CREATE INDEX idx_classification ON thoughts USING GIN(classification);

-- Vector indexes for fast similarity search
CREATE INDEX idx_cache_embedding ON thought_cache USING ivfflat(embedding vector_cosine_ops);
```

### 3. Kafka Partitioning
- 3 partitions for parallel processing
- Partition by user_id for ordering
- 3 consumer instances (one per partition)

### 4. Rate Limiting
```python
# API rate limiting (per user)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    user_id = get_user_from_request(request)
    if await redis.get(f"ratelimit:{user_id}"):
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    await redis.setex(f"ratelimit:{user_id}", 60, "1")  # 1 req/min
    return await call_next(request)
```

---

## Deployment Checklist

### Docker Compose
```yaml
# All services orchestrated
services:
  - db (PostgreSQL + pgvector)
  - api (FastAPI)
  - kafka (KRaft mode)
  - redis (Cache + pub/sub)
  - kafka-worker-1/2/3 (3 consumers)
  - frontend (nginx)
  - prometheus/grafana (monitoring)
```

### Environment Setup
```bash
# Required environment variables
AI_PROVIDER=google
GOOGLE_API_KEY=your_key
DATABASE_URL=postgresql://...
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379
STRIPE_SECRET_KEY=sk_test_...
```

### Health Checks
```python
# api/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_db(),
        "kafka": await check_kafka(),
        "redis": await check_redis()
    }
```

---

## Documentation References

- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - System architecture details
- **[README.md](../README.md)** - Project overview and quick start
- **[QUICK_START.md](../QUICK_START.md)** - Detailed setup guide
- **[MONITORING.md](../MONITORING.md)** - Observability and monitoring
- **[tests/README.md](../tests/README.md)** - Testing documentation
- **[frontend/DESIGN_SYSTEM.md](../frontend/DESIGN_SYSTEM.md)** - UI design system

---

## When Making Changes

### Always Consider:
1. **Event-driven**: Does this need a Kafka event?
2. **Real-time**: Should users see this update via SSE?
3. **Caching**: Can this be cached to save costs?
4. **Multi-provider**: Will this work with all AI providers?
5. **Testing**: Add integration test for new functionality
6. **Documentation**: Update relevant .md files

### Before Committing:
```bash
# Run tests
docker-compose --profile test run --rm integration-tests

# Check formatting
black api/ batch_processor/ tests/

# Type checking
mypy api/ batch_processor/

# Lint
ruff check api/ batch_processor/
```

---

## Quick Reference

### Start Development
```bash
docker compose up -d
open http://localhost:3000
```

### Run Tests
```bash
docker-compose --profile test run --rm integration-tests pytest -v
```

### View Logs
```bash
docker compose logs -f api
docker compose logs -f kafka-worker-1
```

### Database Console
```bash
docker compose exec db psql -U thoughtprocessor
```

### Monitor System
```bash
./start_monitoring.sh
open http://localhost:3001  # Grafana
```

---

## AI Agent System

### 5-Agent Pipeline
Each agent receives previous outputs and user context:

1. **Classifier** (batch_processor/agents.py:classify)
   - Extracts: type, urgency, entities, emotional_tone, implied_needs
   - Output: classification (Dict)

2. **Analyzer** (batch_processor/agents.py:analyze)
   - Extracts: goal_alignment, underlying_needs, pattern_connections
   - Input: classification + user_context
   - Output: analysis (Dict)

3. **Value Assessor** (batch_processor/agents.py:assess_value)
   - Scores: economic, relational, legacy, health, growth (0-10)
   - Input: classification + analysis + user_context
   - Output: value_impact (Dict)

4. **Action Planner** (batch_processor/agents.py:plan_actions)
   - Creates: quick_wins, main_actions, delegation_opportunities
   - Input: analysis + value_impact
   - Output: action_plan (Dict)

5. **Prioritizer** (batch_processor/agents.py:prioritize)
   - Determines: priority_level, urgency_reasoning, timeline
   - Input: action_plan + value_impact
   - Output: priority (Dict)

### Agent Implementation Pattern
```python
async def agent_function(
    text: str,
    context: Dict[str, Any],
    previous_outputs: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Args:
        text: Original thought text
        context: User profile and preferences
        previous_outputs: Results from previous agents
    
    Returns:
        Structured JSON output from AI
    """
    prompt = build_prompt(text, context, previous_outputs)
    response = await ai_provider.complete(prompt)
    return parse_json_response(response)
```

---

*This file is automatically used by GitHub Copilot to understand your project and provide better code suggestions.*
