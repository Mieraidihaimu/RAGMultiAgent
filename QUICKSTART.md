# Quick Start Guide

Get the AI Thought Processor running in under 5 minutes!

## Prerequisites

- Docker Desktop installed
- API keys ready:
  - Anthropic API key ([Get one](https://console.anthropic.com))
  - OpenAI API key ([Get one](https://platform.openai.com))

## 1. Setup (60 seconds)

```bash
# Clone the repository
git clone <repository-url>
cd RAGMultiAgent

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Required variables in `.env`:
```bash
# For local development (Docker PostgreSQL)
POSTGRES_PASSWORD=your-secure-password

# AI API Keys
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Use Supabase instead of local PostgreSQL
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_KEY=eyJxxx...
```

## 2. Start Services (30 seconds)

```bash
# Start everything
make setup

# Or manually:
docker-compose up -d
```

Wait for services to start (check with `docker-compose ps`).

## 3. Load Sample Data (10 seconds)

```bash
make load-sample

# Or manually:
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor \
  -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql
```

## 4. Test the System (30 seconds)

```bash
# Test API
make test-api

# Or manually create a thought:
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Should I invest more time in learning AI?",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }'
```

## 5. Run Batch Processor (2-3 minutes)

```bash
# Process thoughts
make run-batch

# Or manually:
docker-compose exec batch-processor python processor.py
```

This will:
- Find pending thoughts
- Run them through the 5-agent pipeline
- Save analysis results
- Use caching to reduce costs

## 6. View Results

```bash
# Get processed thoughts
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11?status=completed

# Or visit the API docs
open http://localhost:8000/docs
```

## That's It! 🎉

Your AI Thought Processor is now running!

## Next Steps

### View Logs
```bash
make logs              # All services
make logs-api          # API only
make logs-batch        # Batch processor only
```

### Create Your Own User Context

Edit the user context in the database:

```bash
make db-shell
```

Then:
```sql
UPDATE users
SET context = '{
  "demographics": {
    "age": 30,
    "role": "Your Role",
    "location": "Your Location"
  },
  "goals": {
    "career": "Your career goals",
    "personal": "Your personal goals"
  },
  "values_ranking": {
    "family": 10,
    "health": 9,
    "career": 8,
    "wealth": 7
  }
}'::jsonb
WHERE email = 'demo@example.com';
```

### Enable Nightly Cron

Edit `docker-compose.yml`, find the `batch-processor` service, and uncomment:

```yaml
command: cron -f
```

Then restart:
```bash
make restart
```

### Monitor Cache Performance

Check logs for cache statistics:
```bash
make logs-batch | grep "Cache"
```

You should see:
- `Cache HIT!` - Saved money by reusing results
- `Cache MISS` - New thought, processed with AI
- Cache hit rate at end of processing

### Deploy to Production

See [SETUP.md](SETUP.md) for:
- GitHub Actions setup (serverless cron)
- Cloud deployment (Render, Fly.io, Railway)
- Supabase configuration

## Common Commands

```bash
make help          # Show all commands
make up            # Start services
make down          # Stop services
make restart       # Restart services
make status        # Check service status
make clean         # Remove everything (dangerous!)
```

## Troubleshooting

### API not responding
```bash
docker-compose logs api
docker-compose restart api
```

### Database connection failed
```bash
docker-compose logs db
docker-compose restart db
```

### Batch processor errors
```bash
docker-compose logs batch-processor
# Check your API keys in .env
```

### High costs
- Verify cache is working (check logs)
- Lower `SEMANTIC_CACHE_THRESHOLD` in .env (0.85-0.90)
- Use fewer agents for testing

## Resources

- **Full Documentation**: [README.md](README.md)
- **Setup Guide**: [SETUP.md](SETUP.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Docs**: http://localhost:8000/docs
- **Original Design**: [ai-thought-processor-architecture.md](ai-thought-processor-architecture.md)

## Example Workflow

1. **Morning**: Add thoughts via API as they occur
2. **Night (2 AM)**: Batch processor analyzes all pending thoughts
3. **Next Morning**: Review insights and action plans
4. **Weekly (Sunday)**: Get comprehensive weekly synthesis

## Demo User Credentials

The sample data includes:
- **User ID**: `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`
- **Email**: `demo@example.com`
- **Sample thoughts**: 5 pre-loaded thoughts

## System Requirements

- **Docker**: 4GB RAM minimum
- **Disk**: 2GB free space
- **Network**: Internet access for AI APIs

## Support

Having issues? Check:
1. Docker is running: `docker ps`
2. Environment variables set: `cat .env`
3. API keys are valid
4. Logs for errors: `make logs`

---

**Ready to cook?** 🧑‍🍳

Start by running: `make setup`

Then explore the API at: http://localhost:8000/docs
