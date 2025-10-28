# Service Contracts - Quick Reference

A condensed reference for the RAG Multi-Agent service contracts. For detailed documentation, see [SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md).

---

## Service Responsibilities Matrix

| Service | Primary Responsibility | Input | Output | Port |
|---------|----------------------|-------|--------|------|
| **API** | HTTP Gateway, Auth, SSE | HTTP Requests | HTTP Responses, Kafka Events, SSE Streams | 8000 |
| **Kafka Workers** | AI Processing Pipeline | Kafka Events | Database Updates, Redis Events | - |
| **Database** | Data Persistence | SQL Queries | Query Results | 5432 |
| **Kafka** | Event Streaming | Events from Producers | Events to Consumers | 9092 |
| **Redis** | Pub/Sub, Sessions | Pub/Sub Messages | Pub/Sub Distribution | 6379 |
| **Search** | Full-text & Semantic Search | Search Queries | Search Results | 9200 |
| **Frontend** | User Interface | User Actions | HTTP Requests, SSE Listeners | 3000 |

---

## Key API Endpoints

```
# Thoughts
POST   /thoughts                        # Create thought (authenticated)
POST   /anonymous/thoughts              # Create thought (anonymous, rate-limited)
GET    /thoughts/{user_id}              # List user thoughts
GET    /thoughts/{user_id}/{id}         # Get specific thought

# Auth
POST   /signup                          # Create account
POST   /login                           # Authenticate

# Persona Groups
GET    /persona-groups                  # List groups
POST   /persona-groups                  # Create group
POST   /persona-groups/{id}/personas    # Add persona to group

# Real-time
GET    /events/{session_id}             # SSE stream for updates

# Health
GET    /health                          # Service health check
```

---

## Kafka Event Types

| Event Type | Published By | Consumed By | Purpose |
|------------|-------------|-------------|---------|
| `thought_created` | API | Workers | Trigger processing |
| `thought_processing` | Workers | (None) | Status update |
| `thought_agent_completed` | Workers | (None) | Progress update |
| `thought_completed` | Workers | (None) | Processing complete |
| `thought_failed` | Workers | (None) | Processing failed |
| `group_processing_started` | Workers | (None) | Group mode started |
| `persona_completed` | Workers | (None) | Persona finished |
| `consolidation_started` | Workers | (None) | Consolidating outputs |

**Note**: Most events are published to Redis for SSE, not consumed from Kafka.

---

## Database Tables

```
users                   # User accounts and context
thoughts                # User thoughts and AI analysis
persona_groups          # Custom persona collections
personas                # Individual personas with prompts
thought_persona_runs    # Audit log of persona processing
thought_cache           # Semantic cache (pgvector)
weekly_synthesis        # Weekly summaries
```

---

## Data Flow Sequence

```
1. User submits thought via Frontend
   └─> Frontend: POST /thoughts

2. API validates and saves
   └─> Database: INSERT INTO thoughts
   └─> Kafka: PUBLISH ThoughtCreatedEvent
   └─> Frontend: 201 Created + session_id

3. Worker consumes event
   └─> Kafka: CONSUME ThoughtCreatedEvent
   └─> Database: SELECT user context, personas
   └─> Redis: PUBLISH "processing" event
   └─> AI Provider: Run 5-agent pipeline
   └─> Redis: PUBLISH progress events (5x)
   └─> Database: UPDATE thought with results
   └─> Redis: PUBLISH "completed" event

4. Frontend receives updates
   └─> API: SSE /events/{session_id}
   └─> Redis: SUBSCRIBE to channel
   └─> Frontend: Receive SSE events
   └─> UI: Update progress bar
```

---

## AI Analysis Output Structure

Each thought is processed through a 5-agent pipeline:

```
Agent 1: Classifier
├─ type: task | problem | idea | question | observation | emotion
├─ urgency: immediate | soon | eventually | never
├─ entities: { people, dates, places, topics }
└─ emotional_tone, implied_needs

Agent 2: Analyzer
├─ goal_alignment: { aligned_goals, conflicting_goals, reasoning }
├─ underlying_needs: [...]
├─ pattern_connections: [...]
└─ realistic_assessment, unspoken_factors

Agent 3: Value Assessor
├─ economic_value: { score: 0-10, reasoning }
├─ relational_value: { score: 0-10, reasoning }
├─ legacy_value: { score: 0-10, reasoning }
├─ health_value: { score: 0-10, reasoning }
├─ growth_value: { score: 0-10, reasoning }
└─ weighted_total, overall_assessment

Agent 4: Action Planner
├─ quick_wins: [{ action, duration, timing }]
├─ main_actions: [{ action, duration, prerequisites, obstacles, mitigation, timing }]
├─ delegation_opportunities: [...]
└─ success_metrics: [...]

Agent 5: Prioritizer
├─ priority_level: Critical | High | Medium | Low | Defer
├─ urgency_reasoning, strategic_fit
├─ recommended_timeline: { start, duration, checkpoints }
└─ final_recommendation
```

**Group Mode Adds**:
```
Consolidated Output (synthesized from multiple personas)
├─ summary
├─ key_insights: [...]
├─ consensus_points: [...]
├─ divergent_views: [{ persona, viewpoint }]
├─ recommended_action
└─ personas_processed: integer
```

---

## Redis Pub/Sub Channels

**Pattern**: `thought_events:{session_id}`

Messages published:
```json
{
  "event": "thought_processing | thought_agent_completed | thought_completed | thought_failed",
  "data": {
    "thought_id": "uuid",
    "status": "string",
    "message": "string",
    "progress": "1/5",
    "timestamp": "ISO-8601"
  }
}
```

---

## Environment Variables

### API Service
```bash
DATABASE_URL=postgresql://...
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ENABLED=true
REDIS_URL=redis://redis:6379
STRIPE_SECRET_KEY=sk_...
```

### Kafka Workers
```bash
AI_PROVIDER=google | anthropic | openai
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
DATABASE_URL=postgresql://...
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379
SEMANTIC_CACHE_THRESHOLD=0.92
```

---

## Versioning Rules

### Semantic Versioning
- **MAJOR**: Breaking changes
- **MINOR**: Backward-compatible additions
- **PATCH**: Bug fixes

### Breaking Changes Require:
1. 3-month deprecation notice
2. 6-month support for old version
3. Migration guide
4. New API version (e.g., /v2/thoughts)

### Non-Breaking Changes:
- Adding optional fields ✓
- Adding new endpoints ✓
- Adding new event types ✓
- Adding database columns with defaults ✓

---

## Testing Contracts

```bash
# Run all integration tests
docker-compose --profile test run --rm integration-tests pytest -v

# Test specific contract
docker-compose --profile test run --rm integration-tests pytest tests/test_api_contracts.py -v
```

---

## Common Development Scenarios

### Adding a New API Endpoint
1. Define Pydantic models in `api/models.py`
2. Add route in `api/main.py` or relevant route file
3. Update `SERVICE_CONTRACTS.md` with endpoint specification
4. Add integration test
5. Update OpenAPI docs automatically generated

### Adding a New Event Type
1. Add event class to `kafka/events.py`
2. Update `EventType` enum
3. Update `EVENT_TYPE_MAP`
4. Document in `SERVICE_CONTRACTS.md`
5. Add test for serialization/deserialization

### Adding a Database Table
1. Create migration in `database/migrations/XXX_description.sql`
2. Define schema with constraints and indexes
3. Document in `SERVICE_CONTRACTS.md`
4. Add test for schema validation
5. Update dependent services

### Modifying AI Output Schema
1. Update agent code in `batch_processor/agents.py`
2. Update schema documentation in `SERVICE_CONTRACTS.md`
3. Test with sample data
4. Consider backward compatibility (add, don't remove)

---

## Service Dependencies

```
Frontend
  ↓ (depends on)
API Service
  ↓
Database, Kafka, Redis
  ↓
Kafka Workers
  ↓
Database, Redis, AI Providers
```

**Critical Path**: API → Kafka → Workers → Database  
**Real-time Path**: Workers → Redis → API → Frontend (SSE)

---

## Contact

For questions or clarifications:
- Review full [SERVICE_CONTRACTS.md](SERVICE_CONTRACTS.md)
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Create an issue in the repository
- Contact the development team

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-28
