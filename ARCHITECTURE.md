# System Architecture

Detailed technical architecture of the AI Thought Processor with RAG.

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Web App    │  │   iOS App    │  │   API Client │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                            │ HTTP/REST
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Endpoints: /thoughts, /users, /synthesis, /health          │ │
│  │ Authentication, Validation, Error Handling                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Data Layer (PostgreSQL + pgvector)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Users     │  │   Thoughts   │  │ Thought_Cache│          │
│  │   Context    │  │   Analysis   │  │  (Vectors)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                Batch Processing Layer (Nightly Cron)              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  5-Agent Pipeline                          │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │ │
│  │  │ Agent 1   │→ │ Agent 2   │→ │ Agent 3   │            │ │
│  │  │ Classify  │  │ Analyze   │  │ Value     │            │ │
│  │  └───────────┘  └───────────┘  └─────┬─────┘            │ │
│  │                                       ↓                    │ │
│  │  ┌───────────┐  ┌───────────┐                            │ │
│  │  │ Agent 5   │← │ Agent 4   │                            │ │
│  │  │Prioritize │  │ Plan      │                            │ │
│  │  └───────────┘  └───────────┘                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Semantic Caching (RAG)                        │ │
│  │  • Vector embeddings (OpenAI)                             │ │
│  │  • Similarity search (pgvector)                           │ │
│  │  • 92% similarity threshold                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      AI Services Layer                            │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  Anthropic Claude    │  │  OpenAI Embeddings   │            │
│  │  • Prompt Caching    │  │  • text-embed-3-sm   │            │
│  │  • 5-agent analysis  │  │  • 1536 dimensions   │            │
│  └──────────────────────┘  └──────────────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Layer (FastAPI)

**Location**: [`api/`](api/)

**Components**:
- `main.py` - API server with endpoints
- `models.py` - Pydantic models for validation
- `database.py` - Database connection management

**Endpoints**:
```
POST   /thoughts                    Create new thought
GET    /thoughts/{user_id}          List user thoughts
GET    /thoughts/{user_id}/{id}     Get specific thought
DELETE /thoughts/{user_id}/{id}     Delete thought
GET    /users/{user_id}             Get user info
PUT    /users/{user_id}/context     Update user context
GET    /synthesis/{user_id}/latest  Latest synthesis
GET    /synthesis/{user_id}         All syntheses
GET    /health                      Health check
```

**Features**:
- Request validation with Pydantic
- Error handling and logging
- CORS middleware
- Auto-generated OpenAPI docs
- Health checks

### 2. Database Layer (PostgreSQL + pgvector)

**Location**: [`database/`](database/)

**Tables**:

```sql
users
├── id (UUID, PK)
├── email (TEXT, UNIQUE)
├── context (JSONB)           -- User profile
├── context_version (INTEGER)
└── timestamps

thoughts
├── id (UUID, PK)
├── user_id (UUID, FK)
├── text (TEXT)
├── status (ENUM)            -- pending/processing/completed/failed
├── classification (JSONB)   -- Agent 1 output
├── analysis (JSONB)         -- Agent 2 output
├── value_impact (JSONB)     -- Agent 3 output
├── action_plan (JSONB)      -- Agent 4 output
├── priority (JSONB)         -- Agent 5 output
├── embedding (VECTOR(1536)) -- For semantic search
└── timestamps

thought_cache
├── id (UUID, PK)
├── user_id (UUID, FK)
├── thought_text (TEXT)
├── embedding (VECTOR(1536)) -- For similarity search
├── response (JSONB)         -- Cached AI results
├── hit_count (INTEGER)
└── expires_at (TIMESTAMPTZ)

weekly_synthesis
├── id (UUID, PK)
├── user_id (UUID, FK)
├── week_start (DATE)
├── week_end (DATE)
├── synthesis (JSONB)
└── created_at (TIMESTAMPTZ)
```

**Vector Operations**:
- Cosine similarity search
- IVFFlat indexing for performance
- Automatic cache expiration

### 3. Batch Processor (5-Agent Pipeline)

**Location**: [`batch_processor/`](batch_processor/)

**Components**:

#### `processor.py` - Main Orchestrator
- Fetches pending thoughts
- Coordinates agent pipeline
- Manages caching
- Handles errors and retries
- Generates weekly synthesis

#### `agents.py` - 5-Agent Pipeline

**Agent 1: Classification & Extraction**
```python
Input:  Thought text + User context
Output: {
  "type": "task|problem|idea|question|observation|emotion",
  "urgency": "immediate|soon|eventually|never",
  "entities": {
    "people": [],
    "dates": [],
    "places": [],
    "topics": []
  },
  "emotional_tone": str,
  "implied_needs": []
}
```

**Agent 2: Contextual Analysis**
```python
Input:  Thought + Classification + User context
Output: {
  "goal_alignment": {
    "aligned_goals": [],
    "conflicting_goals": [],
    "reasoning": str
  },
  "underlying_needs": [],
  "pattern_connections": [],
  "realistic_assessment": {},
  "unspoken_factors": []
}
```

**Agent 3: Value Impact Assessment**
```python
Input:  Thought + Classification + Analysis + User context
Output: {
  "economic_value": {"score": 0-10, "reasoning": str},
  "relational_value": {"score": 0-10, "reasoning": str},
  "legacy_value": {"score": 0-10, "reasoning": str},
  "health_value": {"score": 0-10, "reasoning": str},
  "growth_value": {"score": 0-10, "reasoning": str},
  "weighted_total": float,
  "overall_assessment": str
}
```

**Agent 4: Action Planning**
```python
Input:  Thought + Analysis + Value Impact
Output: {
  "quick_wins": [
    {"action": str, "duration": str, "timing": str}
  ],
  "main_actions": [
    {
      "action": str,
      "duration": str,
      "prerequisites": [],
      "obstacles": [],
      "mitigation": str,
      "timing": str
    }
  ],
  "delegation_opportunities": [],
  "success_metrics": []
}
```

**Agent 5: Prioritization**
```python
Input:  Thought + Action Plan + Value Impact
Output: {
  "priority_level": "Critical|High|Medium|Low|Defer",
  "urgency_reasoning": str,
  "strategic_fit": str,
  "recommended_timeline": {
    "start": str,
    "duration": str,
    "checkpoints": []
  },
  "final_recommendation": str
}
```

#### `semantic_cache.py` - RAG System

**Caching Flow**:
```
1. New thought arrives
2. Generate embedding (OpenAI)
3. Vector similarity search (pgvector)
4. If similarity > 0.92:
   → Return cached result
5. Else:
   → Process with AI agents
   → Save result to cache
```

**Benefits**:
- ~30% cache hit rate (typical)
- 90% cost savings on cache hits
- Automatic expiration (7 days)
- Hit count tracking

### 4. AI Services

#### Anthropic Claude (Sonnet 4)

**Usage**:
- All 5 agents use Claude
- Prompt caching enabled
- Structured JSON output
- Context window: 200K tokens

**Prompt Caching**:
```python
system_prompt = [
    {
        "type": "text",
        "text": "You are an AI thought analyzer..."
    },
    {
        "type": "text",
        "text": f"USER CONTEXT:\n{user_context}",
        "cache_control": {"type": "ephemeral"}  # ← Cached
    }
]
```

**Cost Savings**:
- Cache write: $3.75/MTok (one-time)
- Cache read: $0.30/MTok (90% cheaper)
- 5 agents × 20 thoughts = massive savings

#### OpenAI Embeddings

**Usage**:
- Semantic caching
- Model: text-embedding-3-small
- Dimensions: 1536
- Cost: $0.02/MTok

**Embedding Generation**:
```python
response = openai.embeddings.create(
    input=thought_text,
    model="text-embedding-3-small"
)
embedding = response.data[0].embedding
```

## Data Flow

### Thought Submission Flow

```
1. Client → POST /thoughts
   {
     "text": "Should I learn Rust?",
     "user_id": "uuid"
   }

2. API validates request
3. API inserts to DB with status="pending"
4. API returns 201 Created
   {
     "id": "thought-uuid",
     "status": "pending",
     "message": "Will be analyzed tonight"
   }

5. User sees: "Thought saved!"
```

### Batch Processing Flow

```
1. Cron triggers at 2 AM UTC (or manual run)

2. Processor fetches pending thoughts:
   SELECT * FROM thoughts
   WHERE status = 'pending'
   ORDER BY created_at

3. For each thought:
   a. Mark status = 'processing'

   b. Check semantic cache:
      - Generate embedding
      - Vector similarity search
      - If match > 0.92 → use cached result

   c. If no cache hit:
      - Run 5-agent pipeline
      - Each agent receives user context (cached)
      - Agents process sequentially
      - Results stored as JSONB

   d. Save results:
      - Update thought record
      - Store embedding
      - Cache result
      - Mark status = 'completed'

   e. Rate limiting (0.5s delay)

4. Weekly synthesis (Sundays):
   - Aggregate week's thoughts
   - Generate summary with AI
   - Store in weekly_synthesis table

5. Cache cleanup:
   - Delete expired entries

6. Log statistics:
   - Total processed
   - Cache hit rate
   - Failed thoughts
   - Duration
```

### Retrieval Flow

```
1. Client → GET /thoughts/{user_id}?status=completed

2. API queries database:
   SELECT * FROM thoughts
   WHERE user_id = ?
   AND status = 'completed'
   ORDER BY created_at DESC

3. API returns thoughts with all analysis:
   [
     {
       "id": "uuid",
       "text": "Should I learn Rust?",
       "status": "completed",
       "classification": {...},
       "analysis": {...},
       "value_impact": {...},
       "action_plan": {...},
       "priority": {...}
     }
   ]

4. Client displays insights to user
```

## Caching Architecture

### Two-Layer Caching Strategy

```
┌─────────────────────────────────────────────┐
│          Layer 1: Prompt Caching            │
│         (Anthropic API Native)              │
│                                             │
│  User Context (2K tokens)                   │
│  ┌───────────────────────────────────────┐ │
│  │ Demographics, Goals, Constraints,     │ │
│  │ Values, Challenges, Patterns          │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  • Cached for 5 minutes                     │
│  • 90% cost reduction on reads              │
│  • Automatic by Anthropic                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│        Layer 2: Semantic Caching            │
│          (Application Level)                │
│                                             │
│  Vector Similarity Search                   │
│  ┌───────────────────────────────────────┐ │
│  │ 1. Generate embedding (OpenAI)        │ │
│  │ 2. Search cached thoughts (pgvector)  │ │
│  │ 3. Cosine similarity > 0.92?          │ │
│  │    Yes → Return cached result         │ │
│  │    No  → Process with AI              │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  • 7-day TTL                                │
│  • ~30% hit rate                            │
│  • Saves full AI processing                │
└─────────────────────────────────────────────┘

Combined Effect: ~92% cost reduction
```

## Scaling Considerations

### Current Capacity
- **Single instance**: 100-1000 thoughts/day
- **Database**: 500MB Supabase free tier
- **Rate limiting**: 0.5s between API calls

### Horizontal Scaling

```
Multiple API instances (load balanced):
┌─────────┐  ┌─────────┐  ┌─────────┐
│ API #1  │  │ API #2  │  │ API #3  │
└────┬────┘  └────┬────┘  └────┬────┘
     └────────────┼────────────┘
                  ↓
         Load Balancer (Nginx)
                  ↓
         Shared Database
```

### Batch Processing Scaling

```
Parallel processing (by user):
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Processor #1 │  │ Processor #2 │  │ Processor #3 │
│ Users 1-100  │  │ Users 101-200│  │ Users 201-300│
└──────────────┘  └──────────────┘  └──────────────┘
```

### Database Scaling

- **Read replicas** for GET requests
- **Partitioning** thoughts table by date
- **Archive** old thoughts to cold storage
- **Index optimization** for common queries

## Security

### API Security
- API key authentication (future)
- Rate limiting per user
- Input validation (Pydantic)
- SQL injection prevention (parameterized queries)
- CORS configuration

### Data Security
- Environment variables for secrets
- No API keys in code
- Encrypted database connections
- Row-level security (Supabase RLS)
- User data isolation

### AI Security
- Prompt injection prevention
- Output validation
- Error message sanitization
- Usage monitoring
- Cost limits

## Monitoring & Observability

### Metrics Tracked
- API request rate
- API error rate
- Batch processing duration
- Cache hit rate
- AI API costs
- Database query performance

### Logs
- API access logs
- Batch processor logs
- Error logs with stack traces
- AI API usage logs

### Health Checks
- API health endpoint
- Database connectivity
- AI API availability
- Disk space
- Memory usage

## Deployment Architecture

### Docker Compose (Development/Self-hosted)

```
docker-compose.yml
├── db (PostgreSQL + pgvector)
├── api (FastAPI)
└── batch-processor (Cron)

Volumes:
├── postgres_data (persistent)
├── api_logs
└── batch_logs

Network:
└── thoughtprocessor-network (bridge)
```

### GitHub Actions (Serverless Cron)

```
.github/workflows/batch-process.yml
├── Scheduled: 2 AM UTC daily
├── Manual trigger available
├── Secrets: API keys
└── Artifacts: Logs (30 days)
```

### Cloud Deployment (Production)

```
Render/Fly.io/Railway:
├── Web Service (API)
│   ├── Auto-scaling
│   ├── HTTPS
│   └── Custom domain
│
├── Cron Job (Batch)
│   └── Scheduled runs
│
└── Supabase (Database)
    ├── Managed PostgreSQL
    ├── Auto backups
    └── Global CDN
```

## Cost Optimization

### Infrastructure
- Use free tiers when possible
- GitHub Actions for cron (free)
- Supabase free tier (500MB)
- Fly.io/Railway free tier

### AI API
- Prompt caching (90% savings)
- Semantic caching (avoid duplicate work)
- Batch processing (lower latency costs)
- Use Haiku for simple tasks (future)

### Database
- Efficient indexing
- Query optimization
- Archive old data
- Compression for JSONB

## Future Enhancements

1. **Real-time Processing**: WebSocket for instant analysis
2. **Multi-modal**: Support voice and images
3. **Collaborative**: Share insights with others
4. **Mobile Apps**: Native iOS/Android
5. **Analytics Dashboard**: Visualize patterns
6. **Custom Agents**: User-defined analysis
7. **Integrations**: Calendar, email, notes
8. **ML Improvements**: Fine-tuned models

---

**Version**: 1.0.0
**Last Updated**: 2024-01-15
