# 🚀 Quick Start: Google Gemini + PostgreSQL (Docker)

Get your AI Thought Processor running in **under 5 minutes** with Google Gemini and local PostgreSQL!

## Prerequisites

✅ Docker Desktop installed and running
✅ Google API key ([Get one here](https://aistudio.google.com/app/apikey))
✅ OpenAI API key ([Get one here](https://platform.openai.com/api-keys)) - for embeddings

## Step 1: Configure API Keys

```bash
# Copy the environment file
cp .env.local.example .env

# Edit .env and add your keys
nano .env
```

**Required configuration in `.env`:**

```bash
# ===================================
# Database: PostgreSQL (Docker)
# ===================================
SUPABASE_URL=
# Leave empty to use local PostgreSQL!

POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=thoughtprocessor
POSTGRES_PASSWORD=changeme123
POSTGRES_DB=thoughtprocessor

# ===================================
# AI Provider: Google Gemini
# ===================================
AI_PROVIDER=google

# ADD YOUR GOOGLE API KEY HERE
GOOGLE_API_KEY=AIzaSy...your-key-here

# Google model (flash is fastest and cheapest!)
GOOGLE_MODEL=gemini-1.5-flash

# OpenAI for embeddings
OPENAI_API_KEY=sk-...your-key-here
```

**Important:**
- Leave `SUPABASE_URL` **empty** to use local PostgreSQL
- Set `AI_PROVIDER=google` to use Gemini
- You need both Google AND OpenAI keys (OpenAI is only for embeddings)

## Step 2: Start the System

**Option A: Use the automated script (recommended)**

```bash
./scripts/start_local_gemini.sh
```

This script will:
1. ✅ Check your configuration
2. ✅ Start all Docker containers
3. ✅ Initialize the database
4. ✅ Load sample data
5. ✅ Verify everything works

**Option B: Manual start**

```bash
# Start all services
docker-compose up -d

# Wait for database
sleep 10

# Load sample data
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor \
  -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql
```

## Step 3: Verify It's Working

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  ...
}
```

## Step 4: Test with Google Gemini! 🎉

```bash
# Run the Gemini test
./scripts/test_gemini.sh
```

This will:
1. Create a test thought
2. Process it with Google Gemini
3. Show you the AI analysis results!

**Or test manually:**

```bash
# 1. Create a thought
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Should I learn machine learning or focus on web development?",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }'

# 2. Process with Gemini
docker-compose exec batch-processor python processor.py

# 3. Get results
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11?status=completed
```

## What You'll See

When Gemini processes your thought, you'll get:

### 📊 5-Agent Analysis

1. **Classification**: Type, urgency, emotional tone
2. **Contextual Analysis**: Goal alignment, patterns
3. **Value Impact**: Scores across 5 life dimensions
4. **Action Plan**: Concrete steps with timing
5. **Prioritization**: Priority level and recommendation

### 💰 Cost

Google Gemini Flash is **~80% cheaper** than Claude!

- **This test**: <$0.01
- **100 thoughts**: ~$0.50
- **Monthly (20/day)**: ~$3-5

Compare to Claude: ~$17-24/month

## Architecture

```
┌─────────────────┐
│  Your Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI API   │ (Port 8000)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │ (Docker)
│  (pending)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Batch Processor │ (Python)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Google Gemini   │ (5-Agent Pipeline)
│  1.5 Flash      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │
│  (completed)    │
└─────────────────┘
```

## Services Running

| Service | Port | Purpose |
|---------|------|---------|
| **API** | 8000 | REST endpoints |
| **API Docs** | 8000/docs | Swagger UI |
| **PostgreSQL** | 5432 | Database |
| **Batch Processor** | - | Background worker |

## Useful Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just batch processor (see Gemini in action!)
docker-compose logs -f batch-processor

# Just database
docker-compose logs -f db
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor

# Example queries
SELECT id, text, status FROM thoughts;
SELECT * FROM users;
SELECT * FROM thought_cache;
```

### Manage Services

```bash
# Stop all
docker-compose down

# Restart
docker-compose restart

# Rebuild (after code changes)
docker-compose up -d --build

# Clean everything (including data!)
docker-compose down -v
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Create Thought
```bash
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your thought here...",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }'
```

### Get Thoughts
```bash
# All thoughts
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11

# Only completed
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11?status=completed

# Only pending
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11?status=pending
```

### Process Thoughts (manually)
```bash
docker-compose exec batch-processor python processor.py
```

## Interactive API Docs

Open in your browser:
**http://localhost:8000/docs**

You can:
- 📝 Test all endpoints interactively
- 📖 See request/response schemas
- 🧪 Try different parameters
- 📊 View API documentation

## Demo User

The system comes with a demo user pre-loaded:

```json
{
  "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "email": "demo@example.com",
  "context": {
    "demographics": {
      "age": 35,
      "role": "Senior Software Engineer",
      "family": "Married, 2 kids (5, 8)"
    },
    "goals": {
      "career": "VP Engineering in 3 years",
      "family": "Quality time with kids",
      "health": "Run half-marathon"
    },
    "values_ranking": {
      "family": 10,
      "health": 9,
      "career": 8
    }
  }
}
```

## Troubleshooting

### "Connection refused" when calling API

```bash
# Check if API is running
docker-compose ps

# Check API logs
docker-compose logs api

# Restart API
docker-compose restart api
```

### "Database connection failed"

```bash
# Check if database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### "GOOGLE_API_KEY not set"

Make sure your `.env` has:
```bash
GOOGLE_API_KEY=AIzaSy...your-actual-key
```

### Batch processor fails

```bash
# Check logs
docker-compose logs batch-processor

# Common issues:
# 1. API key missing or invalid
# 2. OpenAI key missing (needed for embeddings)
# 3. Database not ready

# Verify API keys
docker-compose exec batch-processor env | grep API_KEY
```

## Next Steps

### 1. Customize User Context

Edit the user context to match YOUR goals and values:

```bash
# Connect to database
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor

# Update context
UPDATE users
SET context = '{
  "demographics": {...},
  "goals": {...},
  "values_ranking": {
    "family": 10,
    "health": 9,
    "career": 8
  }
}'::jsonb
WHERE email = 'demo@example.com';
```

### 2. Try Different Models

Edit `.env` to try different Gemini models:

```bash
# Fastest and cheapest
GOOGLE_MODEL=gemini-1.5-flash

# More capable (2M token context!)
GOOGLE_MODEL=gemini-1.5-pro

# Experimental
GOOGLE_MODEL=gemini-2.0-flash-exp
```

### 3. Enable Nightly Processing

Edit `docker-compose.yml` to enable cron:

```yaml
batch-processor:
  # Uncomment this line:
  command: cron -f
```

Then restart:
```bash
docker-compose restart batch-processor
```

Now thoughts will be processed automatically at 2 AM!

### 4. Switch to Other Providers

Want to try Anthropic or OpenAI?

Just change in `.env`:
```bash
# Use Claude
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Or OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Restart and you're using a different AI provider!

## Performance

### Gemini 1.5 Flash

- **Speed**: ~1-3 seconds per thought
- **Context**: Up to 1M tokens
- **Cost**: ~$0.005 per thought
- **Quality**: Excellent for most tasks

### Caching

- **Semantic Cache**: Reuses results for similar thoughts
- **Hit Rate**: ~20-30% typical
- **Savings**: Avoid processing duplicates

## Cost Breakdown

**Example: 20 thoughts/day with Gemini Flash**

- Processing: 20 × $0.005 = **$0.10/day**
- Embeddings: 20 × $0.0001 = **$0.002/day**
- **Total: ~$3/month**

Compare to:
- Anthropic Claude: ~$17-24/month
- OpenAI GPT-4: ~$25-35/month

**Gemini saves you ~80% in AI costs!** 💰

## Summary

You now have:

✅ Local PostgreSQL database (no cloud dependency)
✅ Google Gemini AI (cheapest option!)
✅ Full 5-agent thought processing pipeline
✅ Semantic caching for cost optimization
✅ REST API with interactive docs
✅ Sample data to play with

**Total setup time**: <5 minutes
**Monthly cost**: ~$3 (just AI API)
**Infrastructure cost**: $0 (local Docker)

## Resources

- **API Docs**: http://localhost:8000/docs
- **Adapter Guide**: [ADAPTER_PATTERN_GUIDE.md](ADAPTER_PATTERN_GUIDE.md)
- **Full README**: [README.md](README.md)

---

**Ready to process thoughts with Google Gemini!** 🧠✨

Happy thinking! 🚀
