# AI Thought Processor with RAG

A Docker-based AI Agent system that processes personal thoughts asynchronously using a 5-agent pipeline with Retrieval Augmented Generation (RAG) and semantic caching.

## Features

- **5-Agent Processing Pipeline**: Comprehensive thought analysis through specialized AI agents
- **RAG System**: Semantic caching with pgvector for intelligent result reuse
- **Dual-Layer Caching**:
  - Anthropic Prompt Caching (90% cost savings on context)
  - Semantic Caching (avoid duplicate processing)
- **Batch Processing**: Efficient nightly processing via cron or GitHub Actions
- **Fully Dockerized**: Complete system runs in containers
- **REST API**: FastAPI backend for thought management
- **Weekly Synthesis**: Automated weekly insights generation

## Architecture

```
┌─────────────────┐
│   User Input    │ (Web/iOS App)
│  (Text/Voice)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI       │ (REST API)
│   API Server    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │ (pgvector enabled)
│   Database      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Batch         │ (5-Agent Pipeline)
│   Processor     │ (Nightly cron)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI Models     │
│   Claude + RAG  │
└─────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- API Keys:
  - Anthropic API key (Claude)
  - OpenAI API key (embeddings)
  - Supabase account (or use local PostgreSQL)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd RAGMultiAgent

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Start the System

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify services
curl http://localhost:8000/health
```

### 3. Initialize Database

The database will be automatically initialized with the schema when the containers start.

To add sample data:
```bash
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql
```

### 4. Test the API

```bash
# Create a thought
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Should I learn Rust to advance my career?",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }'

# Get thoughts for user
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11

# Run batch processor manually
docker-compose exec batch-processor python processor.py
```

## Project Structure

```
RAGMultiAgent/
├── api/                          # FastAPI backend
│   ├── Dockerfile
│   ├── main.py                   # API endpoints
│   ├── models.py                 # Pydantic models
│   └── database.py               # DB connection
│
├── batch_processor/              # 5-Agent pipeline
│   ├── Dockerfile
│   ├── processor.py              # Main batch processor
│   ├── agents.py                 # 5 AI agents
│   ├── semantic_cache.py         # RAG caching
│   └── config.py                 # Configuration
│
├── database/                     # Database files
│   ├── migrations/
│   │   └── 001_initial_schema.sql
│   ├── seeds/
│   │   └── 001_sample_user.sql
│   └── init.sh
│
├── .github/workflows/            # CI/CD
│   └── batch-process.yml         # Nightly cron job
│
├── config/
│   └── batch-cron                # Cron schedule
│
├── docker-compose.yml            # Docker orchestration
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── README.md                     # This file
```

## API Endpoints

### Health
- `GET /` - Root endpoint
- `GET /health` - Health check with DB status

### Thoughts
- `POST /thoughts` - Create new thought
- `GET /thoughts/{user_id}` - List user's thoughts
- `GET /thoughts/{user_id}/{thought_id}` - Get specific thought
- `DELETE /thoughts/{user_id}/{thought_id}` - Delete thought

### Users
- `GET /users/{user_id}` - Get user info
- `PUT /users/{user_id}/context` - Update user context

### Synthesis
- `GET /synthesis/{user_id}/latest` - Get latest weekly synthesis
- `GET /synthesis/{user_id}` - Get all syntheses

**API Documentation**: http://localhost:8000/docs

## The 5-Agent Pipeline

### Agent 1: Classification & Extraction
Extracts structured information:
- Type, urgency, entities
- Emotional tone
- Implied needs

### Agent 2: Contextual Analysis
Deep analysis using user context:
- Goal alignment/conflicts
- Underlying needs
- Pattern connections
- Realistic assessment

### Agent 3: Value Impact Assessment
Evaluates across 5 dimensions:
- Economic value
- Relational value
- Legacy value
- Health value
- Growth value

### Agent 4: Action Planning
Creates actionable steps:
- Quick wins (<30 min)
- Main actions with timing
- Delegation opportunities
- Success metrics

### Agent 5: Prioritization
Determines priority and timeline:
- Critical/High/Medium/Low/Defer
- Urgency reasoning
- Strategic fit
- Risk assessment

## Caching Strategy

### Layer 1: Anthropic Prompt Caching
- Caches user context (2K tokens)
- 90% cost reduction on repeated context
- 5-minute cache window

### Layer 2: Semantic Caching
- Stores embeddings of processed thoughts
- Finds similar thoughts (>92% similarity)
- Reuses analysis results
- 7-day TTL

**Combined savings**: ~92% cost reduction

## Configuration

### Environment Variables

See [.env.example](.env.example) for all configuration options.

Key variables:
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase API key
- `CLAUDE_MODEL` - Claude model (default: claude-sonnet-4-20250514)
- `SEMANTIC_CACHE_THRESHOLD` - Similarity threshold (default: 0.92)

### User Context

Users must have a context profile in the database:

```json
{
  "demographics": {
    "age": 35,
    "role": "Senior Engineer",
    "family": "Married, 2 kids (5, 8)",
    "location": "SF Bay Area"
  },
  "goals": {
    "career": "VP Engineering in 3 years",
    "family": "Quality time with kids",
    "health": "Run half-marathon",
    "financial": "Save $50k/year"
  },
  "constraints": {
    "time": "50hr work weeks",
    "energy": "Morning person, depleted after 8pm"
  },
  "values_ranking": {
    "family": 10,
    "health": 9,
    "career": 8
  }
}
```

## Deployment Options

### Option 1: Docker (Local/Self-hosted)
```bash
docker-compose up -d
```

### Option 2: GitHub Actions (Serverless Cron)
- Push to GitHub
- Add secrets in repository settings
- Workflow runs automatically at 2 AM

### Option 3: Cloud Platforms
- **Render**: Use `render.yaml` for deployment
- **Fly.io**: Deploy with `flyctl`
- **Railway**: Connect GitHub repo

## Cost Estimates

### Infrastructure (Docker Self-hosted)
- **$0/month** - Run on your own server

### Infrastructure (Cloud)
- **Supabase**: Free tier or $25/month
- **Render/Railway**: $7-10/month
- **GitHub Actions**: Free (2000 mins/month)

### AI API Costs (20 thoughts/day)
- **Without caching**: ~$40/month
- **With prompt caching**: ~$24/month (-40%)
- **With both caching layers**: ~$17/month (-58%)

## Monitoring & Logs

### View Logs
```bash
# API logs
docker-compose logs -f api

# Batch processor logs
docker-compose logs -f batch-processor

# All logs
docker-compose logs -f
```

### Database Management
```bash
# Start pgAdmin (optional)
docker-compose --profile tools up pgadmin

# Access at: http://localhost:5050
# Email: admin@example.com
# Password: admin
```

### Cache Statistics
```bash
# Check cache hit rate
docker-compose exec batch-processor python -c "
from processor import BatchThoughtProcessor
import asyncio

async def stats():
    processor = BatchThoughtProcessor()
    stats = await processor.semantic_cache.get_cache_stats('user-id')
    print(stats)

asyncio.run(stats())
"
```

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run API locally
cd api
uvicorn main:app --reload

# Run batch processor locally
cd batch_processor
python processor.py
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

## Troubleshooting

### Issue: Database connection failed
```bash
# Check database is running
docker-compose ps

# Restart database
docker-compose restart db

# Check logs
docker-compose logs db
```

### Issue: API not responding
```bash
# Check health
curl http://localhost:8000/health

# Restart API
docker-compose restart api

# Check logs
docker-compose logs api
```

### Issue: High API costs
- Verify prompt caching is enabled (check logs)
- Check semantic cache hit rate
- Adjust `SEMANTIC_CACHE_THRESHOLD` (lower = more hits)
- Consider using Claude Haiku for simple tasks

### Issue: Batch processor not running
```bash
# Run manually
docker-compose exec batch-processor python processor.py

# Check cron status
docker-compose exec batch-processor crontab -l

# View cron logs
docker-compose exec batch-processor tail -f /var/log/cron.log
```

## Security Considerations

- Store API keys in `.env` (never commit)
- Use Supabase Row Level Security (RLS)
- Enable CORS only for trusted domains
- Use HTTPS in production
- Regularly update dependencies
- Monitor API usage and costs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

- **Issues**: GitHub Issues
- **Documentation**: See architecture.md
- **API Docs**: http://localhost:8000/docs

## Acknowledgments

- Built with [Claude](https://anthropic.com) by Anthropic
- Embeddings by [OpenAI](https://openai.com)
- Database by [Supabase](https://supabase.com)
- Vector search by [pgvector](https://github.com/pgvector/pgvector)

---

**Version**: 1.0.0
**Last Updated**: 2024-01-15

Built with ❤️ using AI
