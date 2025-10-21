# AI Thought Processor

> **⚡ Built with AI Vibes** - This project was thoroughly vibe-coded with AI assistance, iterating through ideas and implementations to create a functional multi-agent thought processing system.

A Docker-based AI system that analyzes personal thoughts using a 5-agent pipeline with semantic caching. Supports multiple AI providers (Anthropic Claude, OpenAI, Google Gemini).

## Features

- **5-Agent Pipeline**: Classification → Analysis → Value Assessment → Action Planning → Prioritization
- **Multi-Provider Support**: Use Anthropic Claude, OpenAI GPT, or Google Gemini
- **Semantic Caching**: Avoid processing similar thoughts twice (pgvector)
- **Docker Everything**: API + Database + Batch Processor all containerized
- **REST API**: FastAPI backend with automatic documentation

## Quick Start

### Prerequisites

- Docker & Docker Compose
- API key for your chosen provider:
  - **Google Gemini** (recommended, cheapest): Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
  - **Anthropic Claude**: From [Anthropic Console](https://console.anthropic.com/)
  - **OpenAI**: From [OpenAI Platform](https://platform.openai.com/)

### Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/Mieraidihaimu/RAGMultiAgent.git
cd RAGMultiAgent

# 2. Create .env file
cp .env.example .env

# 3. Edit .env and add your API key
# For Google Gemini (recommended):
AI_PROVIDER=google
GOOGLE_API_KEY=your-key-here

# 4. Start everything
docker compose up -d

# 5. Open the web UI
open http://localhost:3000

# Or check the API is working
curl http://localhost:8000/health
```

### Using the Frontend

1. Open http://localhost:3000 in your browser
2. Enter a thought (e.g., "Should I learn Rust or Go?")
3. Click "Submit Thought"
4. Wait ~10 seconds or click "Process Pending Thoughts"
5. Click "🔄 Refresh" to see your analyzed thought with AI insights

### Using the API

```bash
# Create a thought
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Should I switch careers to AI/ML? I have 5 years of web dev experience.",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }'

# Process it through the AI pipeline
docker compose exec batch-processor python processor.py

# View the analysis
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11 | python -m json.tool
```

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Web UI<br/>Port 3000]
    end
    
    subgraph "API Layer"
        API[FastAPI Server<br/>Port 8000]
    end
    
    subgraph "Processing Layer"
        BP[Batch Processor<br/>Continuous Mode]
        CACHE[Semantic Cache<br/>pgvector]
    end
    
    subgraph "AI Providers"
        GEMINI[Google Gemini]
        CLAUDE[Anthropic Claude]
        GPT[OpenAI GPT]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL<br/>+ pgvector)]
    end
    
    UI -->|REST API| API
    API -->|CRUD| DB
    BP -->|Read/Write| DB
    BP -->|Check Cache| CACHE
    CACHE -->|Vector Search| DB
    BP -->|Generate| GEMINI
    BP -->|Generate| CLAUDE
    BP -->|Generate| GPT
    
    style UI fill:#667eea,color:#fff
    style API fill:#764ba2,color:#fff
    style BP fill:#f093fb,color:#fff
    style DB fill:#4facfe,color:#fff
    style GEMINI fill:#34a853,color:#fff
    style CLAUDE fill:#f97316,color:#fff
    style GPT fill:#10b981,color:#fff
```

### Data Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant DB
    participant BatchProcessor
    participant Cache
    participant AI
    
    User->>Frontend: Submit thought
    Frontend->>API: POST /thoughts
    API->>DB: INSERT thought (status: pending)
    API-->>Frontend: 201 Created
    Frontend-->>User: Thought saved!
    
    Note over BatchProcessor: Runs every 10s
    
    BatchProcessor->>DB: Get pending thoughts
    DB-->>BatchProcessor: List of thoughts
    
    BatchProcessor->>Cache: Check semantic similarity
    alt Cache Hit
        Cache-->>BatchProcessor: Cached result
    else Cache Miss
        BatchProcessor->>AI: Process through 5-agent pipeline
        AI-->>BatchProcessor: Analysis result
        BatchProcessor->>Cache: Save to cache
    end
    
    BatchProcessor->>DB: UPDATE thought (status: completed)
    
    User->>Frontend: View results
    Frontend->>API: GET /thoughts/{user_id}
    API->>DB: SELECT thoughts
    DB-->>API: Thought with analysis
    API-->>Frontend: JSON response
    Frontend-->>User: Display analysis
```

### 5-Agent Processing Pipeline

```mermaid
graph LR
    START([Thought Input]) --> A1
    
    subgraph "5-Agent Pipeline"
        A1[Agent 1<br/>Classifier]
        A2[Agent 2<br/>Analyzer]
        A3[Agent 3<br/>Value Assessor]
        A4[Agent 4<br/>Action Planner]
        A5[Agent 5<br/>Prioritizer]
        
        A1 -->|Type, Urgency<br/>Emotional Tone| A2
        A2 -->|Core Issue<br/>Context Analysis| A3
        A3 -->|Value Scores<br/>6 Dimensions| A4
        A4 -->|Action Steps<br/>Quick Wins| A5
        A5 -->|Priority Level<br/>Reasoning| END
    end
    
    END([Complete Analysis])
    
    style A1 fill:#667eea,color:#fff
    style A2 fill:#764ba2,color:#fff
    style A3 fill:#f093fb,color:#fff
    style A4 fill:#4facfe,color:#fff
    style A5 fill:#00f2fe,color:#fff
    style START fill:#34a853,color:#fff
    style END fill:#f97316,color:#fff
```

### Database Schema

```mermaid
erDiagram
    USERS ||--o{ THOUGHTS : creates
    USERS ||--o{ THOUGHT_CACHE : owns
    USERS ||--o{ WEEKLY_SYNTHESIS : receives
    
    USERS {
        uuid id PK
        string email
        jsonb context
        int context_version
        timestamp created_at
    }
    
    THOUGHTS {
        uuid id PK
        uuid user_id FK
        string text
        string status
        timestamp created_at
        timestamp processed_at
        jsonb classification
        jsonb analysis
        jsonb value_impact
        jsonb action_plan
        jsonb priority
        vector embedding
    }
    
    THOUGHT_CACHE {
        uuid id PK
        uuid user_id FK
        string thought_text
        vector embedding
        jsonb response
        int hit_count
        timestamp expires_at
    }
    
    WEEKLY_SYNTHESIS {
        uuid id PK
        uuid user_id FK
        date week_start
        date week_end
        jsonb synthesis
        timestamp created_at
    }
```

## How It Works

### The 5-Agent Pipeline

Your thought goes through 5 specialized AI agents:

1. **Classifier** - Extracts type, urgency, emotional tone, entities
2. **Analyzer** - Provides deep context based on your goals and constraints
3. **Value Assessor** - Rates impact across 5 life dimensions (career, health, family, etc.)
4. **Action Planner** - Creates concrete, actionable steps with timing
5. **Prioritizer** - Determines priority level (Critical/High/Medium/Low)

**Processing time**: ~18 seconds per thought (with Google Gemini)

### API Endpoints

**Interactive docs**: http://localhost:8000/docs

- `POST /thoughts` - Create a thought
- `GET /thoughts/{user_id}` - List thoughts
- `GET /thoughts/{user_id}/{thought_id}` - Get specific thought
- `GET /health` - Check system status

## Configuration

## Configuration

### Switch AI Providers

Edit `.env`:

```bash
# Google Gemini (cheapest, fast)
AI_PROVIDER=google
GOOGLE_API_KEY=your-key-here
GOOGLE_MODEL=gemini-2.5-flash-lite

# Anthropic Claude (best quality)
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI GPT (alternative)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### User Context

Users need a context profile for personalized analysis. See `database/seeds/001_sample_user.sql` for an example.

## Project Structure

```
RAGMultiAgent/
├── api/                      # FastAPI backend
│   ├── main.py              # API routes
│   └── database.py          # DB adapter
├── batch_processor/         # AI pipeline
│   ├── agents.py            # 5-agent logic
│   ├── processor.py         # Batch orchestration
│   ├── ai_providers/        # Multi-provider support
│   └── semantic_cache.py    # Caching layer
├── common/database/         # Shared DB adapters
├── database/                # Schema & seeds
└── docker-compose.yml       # Container setup
```

## Costs (Estimated for 20 thoughts/day)

- **Google Gemini**: ~$3/month ⭐ (recommended)
- **Anthropic Claude**: ~$17-24/month
- **OpenAI GPT-4**: ~$30-40/month

*With semantic caching enabled*

## Common Commands

```bash
# Start/stop
docker compose up -d
docker compose down

# View logs
docker compose logs -f api
docker compose logs -f batch-processor

# Rebuild after code changes
docker compose up -d --build

# Process thoughts manually
docker compose exec batch-processor python processor.py

# Database console
docker compose exec db psql -U thoughtprocessor -d thoughtprocessor
```

## Troubleshooting

## Troubleshooting

**API not responding?**
```bash
docker compose logs api
docker compose restart api
```

**Database issues?**
```bash
docker compose logs db
docker compose restart db
```

**Agent pipeline failing?**
- Check your API key is correct in `.env`
- Verify you have credits with your AI provider
- Check logs: `docker compose logs batch-processor`

## Documentation

- `QUICKSTART_GEMINI.md` - Detailed Google Gemini setup
- `ARCHITECTURE.md` - System design details
- `ADAPTER_PATTERN_GUIDE.md` - Multi-provider implementation

## Acknowledgments

Built with love and AI assistance ❤️

**AI Providers:**
- [Google Gemini](https://ai.google.dev/) - Fast & affordable
- [Anthropic Claude](https://anthropic.com) - Best reasoning
- [OpenAI GPT](https://openai.com) - Industry standard

**Tech Stack:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [PostgreSQL](https://postgresql.org) + [pgvector](https://github.com/pgvector/pgvector) - Vector database
- [Docker](https://docker.com) - Containerization

---

**License**: MIT  
**Version**: 1.0.0

*This project was vibe-coded through iterative AI collaboration* 🤖✨
