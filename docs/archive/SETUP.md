# Setup Guide

Complete setup instructions for the AI Thought Processor system.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Getting API Keys](#getting-api-keys)
3. [Local Development Setup](#local-development-setup)
4. [Docker Setup](#docker-setup)
5. [GitHub Actions Setup](#github-actions-setup)
6. [Production Deployment](#production-deployment)

---

## Prerequisites

### Required
- Docker Desktop (v20.10+)
- Docker Compose (v2.0+)
- Git
- Text editor

### For Development
- Python 3.11+
- pip
- Virtual environment tool

---

## Getting API Keys

### 1. Anthropic API Key (Claude)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-ant-`)

**Cost**: Pay-as-you-go, ~$3/MTok input, ~$15/MTok output

### 2. OpenAI API Key (Embeddings)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-`)

**Cost**: $0.02/MTok for text-embedding-3-small

### 3. Supabase Setup

#### Option A: Use Supabase (Recommended for Production)

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Wait for database provisioning (~2 minutes)
4. Go to Project Settings → API
5. Copy:
   - Project URL (`SUPABASE_URL`)
   - `anon` public key (`SUPABASE_KEY`)
6. Go to SQL Editor
7. Run the migration script from `database/migrations/001_initial_schema.sql`

**Cost**: Free tier (500MB DB, 2GB bandwidth) or $25/month Pro

#### Option B: Use Local PostgreSQL (Development)

Use the Docker setup - it includes PostgreSQL with pgvector.

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd RAGMultiAgent
```

### 2. Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with your keys
nano .env
```

Required variables:
```bash
# For local PostgreSQL (Docker)
POSTGRES_USER=thoughtprocessor
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=thoughtprocessor

# OR for Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx...

# AI APIs
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
```

### 5. Test Locally

```bash
# Terminal 1: Start API
cd api
uvicorn main:app --reload

# Terminal 2: Test batch processor
cd batch_processor
python processor.py
```

---

## Docker Setup

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

Expected output:
```
NAME                        STATUS              PORTS
thoughtprocessor-api        running             0.0.0.0:8000->8000/tcp
thoughtprocessor-batch      running
thoughtprocessor-db         running (healthy)   0.0.0.0:5432->5432/tcp
```

### 3. Verify Database

```bash
# Check database
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor -c "\dt"

# Should show tables:
# users, thoughts, thought_tags, thought_cache, weekly_synthesis
```

### 4. Load Sample Data

```bash
docker-compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/seeds/001_sample_user.sql
```

### 5. Test API

```bash
# Health check
curl http://localhost:8000/health

# Create thought
curl -X POST http://localhost:8000/thoughts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Should I learn Rust?",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
  }'

# Get thoughts
curl http://localhost:8000/thoughts/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
```

### 6. Run Batch Processor

```bash
# Manual run
docker-compose exec batch-processor python processor.py

# Or enable cron mode (edit docker-compose.yml)
# Uncomment: command: cron -f
docker-compose restart batch-processor
```

### 7. Access API Documentation

Open browser: http://localhost:8000/docs

---

## GitHub Actions Setup

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2. Add Secrets

Go to: Repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Value |
|------------|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase anon key |
| `ANTHROPIC_API_KEY` | Your Claude API key |
| `OPENAI_API_KEY` | Your OpenAI API key |

### 3. Configure Variables (Optional)

Go to: Repository → Settings → Secrets and variables → Actions → Variables

| Variable Name | Default | Description |
|--------------|---------|-------------|
| `CLAUDE_MODEL` | claude-sonnet-4-20250514 | Claude model |
| `SEMANTIC_CACHE_THRESHOLD` | 0.92 | Similarity threshold |
| `LOG_LEVEL` | INFO | Logging level |

### 4. Enable Workflows

Go to: Repository → Actions → Enable workflows

### 5. Test Manual Run

1. Go to Actions tab
2. Select "Nightly Thought Processing"
3. Click "Run workflow"
4. Select branch (main)
5. Click "Run workflow"

### 6. Verify Scheduled Runs

The workflow will run automatically at 2 AM UTC daily.

Check: Actions tab → Nightly Thought Processing

---

## Production Deployment

### Option 1: Cloud Platform (Render)

#### 1. Create `render.yaml`

```yaml
services:
  - type: web
    name: thought-api
    env: docker
    dockerfilePath: ./api/Dockerfile
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false

  - type: cron
    name: batch-processor
    env: docker
    dockerfilePath: ./batch_processor/Dockerfile
    schedule: "0 2 * * *"
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
```

#### 2. Deploy to Render

```bash
# Install Render CLI
npm install -g render

# Deploy
render deploy
```

### Option 2: Self-Hosted Server

#### 1. Provision Server

- Ubuntu 22.04+
- 2GB+ RAM
- 20GB+ storage

#### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

#### 3. Deploy Application

```bash
# Clone repo
git clone <your-repo-url>
cd RAGMultiAgent

# Configure environment
cp .env.example .env
nano .env

# Start services
docker-compose up -d

# Enable auto-restart
docker-compose restart --restart=always
```

#### 4. Setup Nginx (Optional)

```bash
# Install Nginx
sudo apt-get install nginx

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/thought-api
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/thought-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 5. Setup SSL (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Verification Checklist

- [ ] Database initialized with schema
- [ ] Sample user created
- [ ] API health check passes
- [ ] Can create thoughts via API
- [ ] Batch processor runs successfully
- [ ] Thoughts marked as "completed" after processing
- [ ] API documentation accessible
- [ ] Logs being written correctly
- [ ] Cache hit rate being tracked
- [ ] Weekly synthesis generates (if Sunday)

---

## Common Issues

### Database Connection Failed

```bash
# Check database is running
docker-compose ps db

# View logs
docker-compose logs db

# Restart
docker-compose restart db
```

### API Returns 500 Errors

```bash
# Check API logs
docker-compose logs api

# Verify environment variables
docker-compose exec api env | grep SUPABASE

# Restart API
docker-compose restart api
```

### Batch Processor Fails

```bash
# Check API keys are valid
docker-compose exec batch-processor python -c "
import os
print('Anthropic:', os.getenv('ANTHROPIC_API_KEY')[:10])
print('OpenAI:', os.getenv('OPENAI_API_KEY')[:10])
"

# View detailed logs
docker-compose logs batch-processor

# Run with debug logging
docker-compose exec batch-processor \
  LOG_LEVEL=DEBUG python processor.py
```

### High Costs

1. Check cache is enabled:
   ```bash
   # Should see cache hits in logs
   docker-compose logs batch-processor | grep "Cache HIT"
   ```

2. Verify prompt caching:
   ```bash
   # Check Anthropic dashboard for cache usage
   ```

3. Adjust settings:
   - Lower `SEMANTIC_CACHE_THRESHOLD` (more cache hits)
   - Use Claude Haiku for simple tasks
   - Reduce `CLAUDE_MAX_TOKENS`

---

## Next Steps

1. ✅ Setup complete - system running
2. 📝 Create your user context in database
3. 💭 Start adding thoughts via API
4. 🤖 Run batch processor manually to test
5. 📊 Monitor logs and cache statistics
6. 🚀 Deploy to production
7. 📱 Build frontend application (web/mobile)

---

## Support

- **Documentation**: README.md, architecture.md
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Logs**: `docker-compose logs -f`

Happy thought processing! 🧠✨
