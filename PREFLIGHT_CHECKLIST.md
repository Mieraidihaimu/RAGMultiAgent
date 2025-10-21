# ✈️ Pre-Flight Checklist

Before launching your AI Thought Processor with Google Gemini + PostgreSQL:

## ✅ Configuration Checklist

### 1. Environment File (.env)

- [x] `.env` file exists
- [x] `AI_PROVIDER=google` ✅
- [x] `GOOGLE_API_KEY` is set ✅
- [ ] **`OPENAI_API_KEY` needs to be set** ⚠️
  - Required for embeddings (semantic caching)
  - Get one at: https://platform.openai.com/api-keys
- [x] `SUPABASE_URL` is commented out ✅ (using local PostgreSQL)
- [x] PostgreSQL settings look good ✅

### Current .env Status:

```bash
✅ AI_PROVIDER=google
✅ GOOGLE_API_KEY=AIzaSy... (set)
⚠️  OPENAI_API_KEY=sk-your-openai-key-here (NEEDS UPDATE)
✅ #SUPABASE_URL=... (commented - using local PostgreSQL)
✅ POSTGRES_HOST=db
✅ POSTGRES_DB=thoughtprocessor
```

## 🔧 Fix Required

**Add your OpenAI API key to `.env`:**

```bash
# Open .env
nano .env

# Find this line:
OPENAI_API_KEY=sk-your-openai-key-here

# Replace with your actual key:
OPENAI_API_KEY=sk-proj-...your-actual-key
```

Get an OpenAI key: https://platform.openai.com/api-keys

**Note**: OpenAI is only used for embeddings (semantic search). It costs ~$0.002 per 1000 embeddings.

## 🚀 Ready to Launch!

Once you've added your OpenAI key:

```bash
# Option 1: Automated startup (recommended)
./scripts/start_local_gemini.sh

# Option 2: Manual startup
docker-compose up -d
sleep 10
./scripts/test_gemini.sh
```

## 📊 What Will Happen

1. **Docker Compose** starts 3 containers:
   - PostgreSQL database
   - FastAPI API server
   - Batch processor

2. **Database** initializes with schema + sample data

3. **API** starts on http://localhost:8000

4. **You can**:
   - Create thoughts via API
   - Process them with Google Gemini
   - See AI analysis across 5 dimensions

## 💰 Cost Estimate

With Google Gemini:
- **This test session**: <$0.01
- **100 thoughts**: ~$0.50
- **Monthly (20/day)**: ~$3-5

Plus OpenAI embeddings: ~$0.10/month

**Total: ~$3-5/month** (vs $17-24 with Claude!)

## 🆘 Troubleshooting

### "OpenAI API key not set"
→ Edit `.env` and add your OpenAI key

### "Google API key not set"
→ Already set! ✅

### "Database connection failed"
→ Wait 10-15 seconds for PostgreSQL to start
→ Check: `docker-compose logs db`

### "API not responding"
→ Check: `docker-compose logs api`
→ Restart: `docker-compose restart api`

## 🎯 Next Steps

After adding OpenAI key:

1. **Start system**: `./scripts/start_local_gemini.sh`
2. **Test Gemini**: `./scripts/test_gemini.sh`
3. **View docs**: http://localhost:8000/docs
4. **Process thoughts**: Start adding your own!

---

**Almost there! Just add your OpenAI API key and you're ready to go! 🚀**
