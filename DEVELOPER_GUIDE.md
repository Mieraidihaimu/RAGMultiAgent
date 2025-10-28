# Developer Onboarding Guide

Quick guide for developers joining the RAG Multi-Agent project. Read this first!

---

## 📚 Documentation Map

Start here based on what you need:

| I want to... | Read this document |
|--------------|-------------------|
| Understand the project | [README.md](README.md) |
| Get the project running | [QUICK_START.md](QUICK_START.md) |
| Understand system architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Know service responsibilities and APIs** | **[SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md)** ⭐ |
| Quick contract reference | [SERVICE_CONTRACTS_QUICK_REFERENCE.md](SERVICE_CONTRACTS_QUICK_REFERENCE.md) |
| See service communication flow | [SERVICE_ARCHITECTURE_DIAGRAM.md](SERVICE_ARCHITECTURE_DIAGRAM.md) |
| Set up monitoring | [MONITORING.md](MONITORING.md) |
| Run tests | [tests/README.md](tests/README.md) |
| Deploy to production | [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) |

---

## 🎯 Project Overview

**What it does**: AI-powered thought analysis system using a 5-agent pipeline with real-time updates.

**Key Features**:
- Submit thoughts (text input)
- 5-agent AI analysis pipeline
- Real-time progress updates via SSE
- Custom persona groups (multi-perspective analysis)
- Semantic caching to reduce costs
- Anonymous + authenticated users

**Tech Stack**:
- Backend: Python, FastAPI
- Database: PostgreSQL + pgvector
- Message Broker: Apache Kafka
- Cache: Redis
- AI: Google Gemini / Anthropic Claude / OpenAI GPT
- Frontend: HTML/JS, nginx

---

## 🏗️ System Architecture (Simplified)

```
Frontend (Port 3000)
    │
    ▼ HTTP/SSE
API Service (Port 8000)
    │
    ├─> Database (5432)      - Read/Write user data
    ├─> Kafka (9092)         - Publish events
    └─> Redis (6379)         - SSE pub/sub
         │
         ▼ Consume events
    Kafka Workers
         │
         ├─> Database         - Save results
         ├─> Redis            - Publish progress
         └─> AI Providers     - Run 5-agent pipeline
```

---

## 🔑 Service Responsibilities

### 1. API Service (`api/`)
**What it does**: HTTP gateway, authentication, event publishing, SSE streaming

**Key files**:
- `main.py` - Main routes, SSE endpoints
- `auth_routes.py` - Signup/login
- `models.py` - Pydantic request/response models
- `sse.py` - Server-Sent Events handling

**You modify this when**:
- Adding new API endpoints
- Changing authentication logic
- Modifying request/response formats

### 2. Kafka Workers (`batch_processor/`)
**What it does**: Consume Kafka events, run AI analysis, save results

**Key files**:
- `processor.py` - Main event consumer, orchestration
- `agents.py` - 5-agent AI pipeline
- `semantic_cache.py` - Vector similarity caching
- `ai_providers/` - Multi-provider AI integration

**You modify this when**:
- Changing AI analysis logic
- Adding new AI providers
- Modifying agent prompts or outputs

### 3. Database (`database/`)
**What it does**: Data persistence, vector search

**Key files**:
- `migrations/*.sql` - Schema definitions
- `seeds/*.sql` - Sample data

**You modify this when**:
- Adding new tables or columns
- Changing database schema

### 4. Kafka (`kafka/`)
**What it does**: Event streaming and queuing

**Key files**:
- `producer.py` - Publish events
- `consumer.py` - Consume events
- `events.py` - Event schema definitions

**You modify this when**:
- Adding new event types
- Changing event schemas

### 5. Frontend (`frontend/`)
**What it does**: User interface, SSE client

**You modify this when**:
- Changing UI/UX
- Adding new features to web interface

---

## 🔄 Data Flow

### Submitting a Thought

```
1. User enters thought in UI
   └─> Frontend sends POST /thoughts

2. API validates and saves
   └─> Saves to database with status='pending'
   └─> Publishes ThoughtCreatedEvent to Kafka
   └─> Returns 201 + session_id to frontend

3. Frontend connects to SSE
   └─> GET /events/{session_id}

4. Worker consumes event
   └─> Fetches user context from database
   └─> Runs 5-agent AI pipeline
   └─> Publishes progress to Redis (SSE)
   └─> Saves results to database
   └─> Publishes completion to Redis

5. Frontend receives updates
   └─> SSE events show progress
   └─> UI updates in real-time
```

### 5-Agent Pipeline

Each thought goes through 5 AI agents sequentially:

1. **Classifier** - Type, urgency, entities, emotional tone
2. **Analyzer** - Goal alignment, needs, patterns
3. **Value Assessor** - Economic, relational, legacy, health, growth scores
4. **Action Planner** - Quick wins, main actions, success metrics
5. **Prioritizer** - Priority level, timeline, recommendation

**Group Mode**: Process through multiple custom personas, then consolidate outputs.

---

## 📝 Making Changes

### Before You Start

1. Read [SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md) - **Critical!**
2. Understand which service you're modifying
3. Check if your change is breaking or non-breaking

### Adding a New API Endpoint

```python
# 1. Define request/response models in api/models.py
class MyRequest(BaseModel):
    field: str

class MyResponse(BaseModel):
    result: str

# 2. Add route in api/main.py
@app.post("/my-endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    # Your logic
    return MyResponse(result="success")

# 3. Document in SERVICE_CONTRACTS.md
# 4. Add integration test
# 5. OpenAPI docs auto-generate at /docs
```

### Adding a New Event Type

```python
# 1. Add to kafka/events.py
class MyNewEvent(ThoughtEvent):
    event_type: Literal[EventType.MY_NEW_EVENT] = EventType.MY_NEW_EVENT
    custom_field: str

# 2. Update EventType enum
class EventType(str, Enum):
    ...
    MY_NEW_EVENT = "my_new_event"

# 3. Update EVENT_TYPE_MAP
EVENT_TYPE_MAP = {
    ...
    EventType.MY_NEW_EVENT: MyNewEvent,
}

# 4. Document in SERVICE_CONTRACTS.md
# 5. Add test for serialization/deserialization
```

### Adding a Database Table

```sql
-- 1. Create migration: database/migrations/008_my_new_table.sql
CREATE TABLE my_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_my_table_user ON my_table(user_id);

-- 2. Document in SERVICE_CONTRACTS.md
-- 3. Add test for schema
-- 4. Restart database container to apply migration
```

### Modifying AI Agent Output

```python
# 1. Update agent in batch_processor/agents.py
# 2. Update output schema documentation in SERVICE_CONTRACTS.md
# 3. Test with sample data
# 4. Consider backward compatibility (add fields, don't remove)
```

---

## ⚠️ Breaking vs Non-Breaking Changes

### ❌ Breaking Changes (Require Version Bump)

- Removing/renaming API endpoints
- Removing/renaming fields from requests/responses
- Changing required fields
- Removing database columns
- Changing event schemas (removing fields)

**Process**:
1. Propose change and get approval
2. Announce deprecation (3 months notice)
3. Create new version (e.g., `/v2/endpoint`)
4. Support old version for 6 months
5. Document migration path

### ✅ Non-Breaking Changes (Safe)

- Adding new optional fields
- Adding new endpoints
- Adding database columns with defaults
- Adding new event types
- Adding new event fields (optional)

**Process**:
1. Make the change
2. Update documentation
3. Add tests
4. Deploy

---

## 🧪 Testing

### Run All Tests

```bash
docker-compose --profile test run --rm integration-tests pytest -v
```

### Test Specific Service

```bash
# API tests
docker-compose --profile test run --rm integration-tests pytest tests/test_api_contracts.py -v

# Kafka tests
docker-compose --profile test run --rm integration-tests pytest tests/test_kafka_direct.py -v

# Database tests
docker-compose --profile test run --rm integration-tests pytest tests/test_database.py -v
```

### Test Your Changes

Before committing:
1. Run relevant tests locally
2. Add new tests for your changes
3. Ensure all tests pass
4. Check code follows existing style

---

## 🚀 Common Development Tasks

### Start the System

```bash
# Start all services
docker compose up -d

# Check logs
docker compose logs -f api
docker compose logs -f kafka-worker

# Check health
curl http://localhost:8000/health
```

### Stop the System

```bash
docker compose down
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker compose up -d --build
```

### Access Database Console

```bash
docker compose exec db psql -U thoughtprocessor
```

### View Kafka Topics

```bash
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic thought-events \
  --from-beginning
```

### Monitor Redis Pub/Sub

```bash
docker compose exec redis redis-cli PSUBSCRIBE 'thought_events:*'
```

### Test SSE Endpoint

```bash
curl -N http://localhost:8000/events/test-session-id
```

---

## 🐛 Troubleshooting

### API not responding
```bash
# Check API logs
docker compose logs api

# Check API health
curl http://localhost:8000/health

# Restart API
docker compose restart api
```

### Workers not processing
```bash
# Check worker logs
docker compose logs kafka-worker

# Check Kafka topics
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check consumer group lag
docker compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group thought-processor-workers \
  --describe
```

### Database connection issues
```bash
# Check database logs
docker compose logs db

# Verify database is healthy
docker compose exec db pg_isready -U thoughtprocessor

# Check connections
docker compose exec db psql -U thoughtprocessor -c "SELECT count(*) FROM pg_stat_activity;"
```

### SSE not streaming
```bash
# Check Redis
docker compose logs redis

# Verify Redis is running
docker compose exec redis redis-cli ping

# Monitor pub/sub
docker compose exec redis redis-cli PSUBSCRIBE 'thought_events:*'
```

---

## 📊 Monitoring

Start monitoring stack:

```bash
./start_monitoring.sh
# OR
docker-compose --profile monitoring up -d
```

Access dashboards:
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API Metrics**: http://localhost:8000/metrics

See [MONITORING.md](MONITORING.md) for details.

---

## 🔐 Environment Variables

Key environment variables (see `.env.example`):

```bash
# AI Provider (choose one)
AI_PROVIDER=google           # google | anthropic | openai
GOOGLE_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Database
DATABASE_URL=postgresql://user:pass@db:5432/thoughtprocessor

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ENABLED=true

# Redis
REDIS_URL=redis://redis:6379

# Stripe (optional)
STRIPE_SECRET_KEY=sk_test_...
```

---

## 📞 Getting Help

1. **Check documentation**: Start with this guide, then dive into specific docs
2. **Search existing issues**: Someone may have had the same problem
3. **Check logs**: `docker compose logs <service>`
4. **Ask the team**: Create an issue or reach out on Slack
5. **Read the contracts**: [SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md) is your friend

---

## ✅ Pull Request Checklist

Before submitting a PR:

- [ ] Code follows existing patterns and style
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] Documentation updated (if needed)
- [ ] SERVICE_CONTRACTS.md updated (if API/schema changes)
- [ ] No breaking changes (or properly versioned if necessary)
- [ ] Commit messages are clear and descriptive
- [ ] PR description explains what and why

---

## 🎓 Learning Resources

### Understanding the Codebase

1. Start with [README.md](README.md) - High-level overview
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) - System design
3. Study [SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md) - API contracts
4. Explore [SERVICE_ARCHITECTURE_DIAGRAM.md](SERVICE_ARCHITECTURE_DIAGRAM.md) - Visual flows
5. Run the system and trace a request through logs

### Key Concepts

- **Kafka**: Event streaming for async processing
- **SSE**: Server-Sent Events for real-time updates
- **pgvector**: Vector similarity search for semantic caching
- **5-Agent Pipeline**: Sequential AI analysis agents
- **Persona Groups**: Multi-perspective thought analysis

### Recommended Reading Order

```
Day 1: README.md → QUICK_START.md → Get system running
Day 2: ARCHITECTURE.md → SERVICE_ARCHITECTURE_DIAGRAM.md
Day 3: SERVICE_CONTRACTS.md → Start with a small task
Day 4+: Deep dive into specific services as needed
```

---

**Welcome to the team! Happy coding! 🚀**

For questions or feedback on this guide, create an issue or contact the maintainers.
