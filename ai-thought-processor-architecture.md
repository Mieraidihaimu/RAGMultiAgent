# AI Thought Processing System - Complete Architecture Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Value Framework](#value-framework)
3. [Architecture Design](#architecture-design)
4. [Agentic System Design](#agentic-system-design)
5. [Caching Strategy](#caching-strategy)
6. [Database Schema](#database-schema)
7. [Implementation Code](#implementation-code)
8. [Infrastructure Setup](#infrastructure-setup)
9. [Cost Analysis](#cost-analysis)

---

## System Overview

**Concept**: A personal AI assistant that processes thoughts asynchronously, provides contextual analysis, and generates actionable insights based on user's life context.

**User Flow**:
1. User captures thoughts via text (web/iOS app)
2. Thoughts stored in database (instant response)
3. Nightly batch processing analyzes all pending thoughts
4. User reviews processed thoughts with AI insights

**Core Value**: Context-aware intelligence that evaluates thoughts across multiple life dimensions (economic, relational, health, legacy, growth).

---

## Value Framework

The system evaluates thoughts through these dimensions:

### 1. Economic Value
- Direct: Immediate income/savings impact
- Indirect: Future earning potential, skills, network
- Opportunity cost: Alternative uses of time/energy

### 2. Relational Value
- Family bonds: Quality time, presence, shared experiences
- Partnerships: Relationship strengthening
- Social capital: Professional and personal networks
- Conflict potential: Relationship strain risks

### 3. Legacy Value
- Children: Modeling behavior, memories, life lessons
- Mentorship: Impact on others' growth
- Knowledge: Lasting contributions

### 4. Health Value
- Physical: Fitness, sleep, nutrition, longevity
- Mental: Stress reduction, fulfillment, peace
- Energy: Sustainable vs. depleting activities
- Risk: Health costs and trade-offs

### 5. Growth Value
- Learning: New skills, perspectives, experiences
- Self-actualization: Alignment with authentic self
- Meaning: Sense of purpose and fulfillment

---

## Architecture Design

### Simplified Stack (No Message Queue)

```
┌─────────────────┐
│   User Input    │ (Web/iOS App)
│  (Text/Voice)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI       │ (Minimal backend)
│   API Server    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Supabase      │ (Postgres + pgvector)
│   Database      │ (Stores thoughts, status: pending)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Cron Job      │ (GitHub Actions / Render)
│   (Nightly)     │ (Runs at 2 AM daily)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Agent       │ (Claude API + Prompt Caching)
│  Processing     │ (5-agent pipeline)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Database      │ (Update status: completed)
│   (Results)     │ (Store analysis, actions)
└─────────────────┘
```

### Tech Stack (Free/Cheap)

- **Database**: Supabase (Free: 500MB DB, 2GB bandwidth)
- **Backend**: Fly.io/Railway/Render (Free tier)
- **AI**: Claude API (Anthropic) + Prompt Caching
- **Embeddings**: OpenAI text-embedding-3-small ($0.02/MTok)
- **Cron**: GitHub Actions (free) or Render Cron Jobs
- **Total Cost**: $0-5/month + AI usage (~$1-2/month for personal use)

---

## Agentic System Design

### User Context Store

The foundation of contextual intelligence:

```python
user_context = {
    "demographics": {
        "age": 35,
        "role": "Senior Engineer",
        "family": "Married, 2 kids (5, 8)",
        "location": "SF Bay Area"
    },
    
    "goals": {
        "career": "VP Engineering in 3 years, launch side project",
        "family": "Quality time with kids, strengthen marriage",
        "health": "Run half-marathon, reduce stress",
        "financial": "Save $50k/year, diversify income"
    },
    
    "constraints": {
        "time": "50hr work weeks, 2hr commute daily",
        "energy": "Morning person, depleted after 8pm",
        "commitments": "Son's soccer Saturdays, date night Fridays"
    },
    
    "values_ranking": {
        "family": 10,
        "health": 9,
        "career": 8,
        "wealth": 7,
        "legacy": 8
    },
    
    "current_challenges": [
        "Feeling burned out at work",
        "Missing kids' milestones",
        "Haven't exercised in 2 weeks"
    ],
    
    "recent_patterns": {
        "recurring_thoughts": ["career change", "work-life balance"],
        "stress_triggers": ["late meetings", "weekend work"],
        "energy_peaks": ["6-9am", "weekends"]
    }
}
```

### 5-Agent Processing Pipeline

**Agent 1: Classification & Extraction**
- Type: task/problem/idea/question/observation/emotion
- Urgency: immediate/soon/eventually/never
- Entities: people, dates, places, topics
- Emotional tone: excited/anxious/frustrated/neutral/curious
- Implied needs: what the person might need

**Agent 2: Contextual Analysis**
- Goal alignment/conflicts
- Underlying needs and desires
- Pattern connections to recent challenges
- Realistic assessment given constraints
- Unspoken factors

**Agent 3: Value Impact Assessment**
- Scores each value dimension (0-10)
- Reasoning for each score
- Timeframe: immediate/short-term/long-term
- Confidence level
- Weighted total using user's values_ranking

**Agent 4: Action Planning**
- Specific, realistic steps
- Timing based on energy patterns
- Duration estimates
- Prerequisites and obstacles
- Mitigation strategies
- Quick wins (<30 min actions)
- Delegation opportunities

**Agent 5: Prioritization**
- Urgency assessment with reasoning
- Strategic fit analysis
- Momentum considerations
- Final recommendation: Critical/High/Medium/Low/Defer
- Timeline and confidence level

---

## Caching Strategy

### Two-Layer Caching Approach

#### Layer 1: Anthropic Prompt Caching (Native API Feature)

**How it works:**
- Cache large context blocks (user profile) in API
- Cached for 5 minutes between requests
- Write: $3.75/MTok (one-time)
- Read: $0.30/MTok (90% savings)

**Implementation:**
```python
system_prompt = [
    {
        "type": "text",
        "text": "You are an AI thought analyzer."
    },
    {
        "type": "text",
        "text": f"USER CONTEXT:\n{json.dumps(user_context, indent=2)}",
        "cache_control": {"type": "ephemeral"}  # ← CACHE THIS
    }
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    system=system_prompt,
    messages=[{"role": "user", "content": prompt}]
)
```

**Cost Savings Example** (20 thoughts/day, 2K token context):
- Without caching: $0.60/day
- With caching: $0.065/day (89% savings)

#### Layer 2: Semantic Caching (Application Level)

**Purpose**: Cache responses for similar thoughts

**Tech**: 
- OpenAI embeddings (text-embedding-3-small)
- PostgreSQL pgvector extension
- Cosine similarity matching (threshold: 0.92)

**Benefits**:
- Avoid reprocessing similar thoughts
- ~30% hit rate for typical users
- Additional 30-40% cost savings

**Database Setup:**
```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Cache table
CREATE TABLE thought_cache (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    thought_text TEXT,
    embedding VECTOR(1536),
    response JSONB,
    hit_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

-- Similarity search function
CREATE OR REPLACE FUNCTION match_similar_thoughts(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    user_id_param uuid
)
RETURNS TABLE (
    id uuid,
    thought_text text,
    response jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        thought_cache.id,
        thought_cache.thought_text,
        thought_cache.response,
        1 - (thought_cache.embedding <=> query_embedding) as similarity
    FROM thought_cache
    WHERE 
        thought_cache.user_id = user_id_param
        AND thought_cache.expires_at > NOW()
        AND 1 - (thought_cache.embedding <=> query_embedding) > match_threshold
    ORDER BY thought_cache.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## Database Schema

### Complete Supabase Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    context_version INTEGER DEFAULT 1,
    context_updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Thoughts table
CREATE TABLE thoughts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Processing status
    status TEXT DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processed_at TIMESTAMPTZ,
    processing_attempts INTEGER DEFAULT 0,
    
    -- AI Analysis results
    classification JSONB,
    analysis JSONB,
    value_impact JSONB,
    action_plan JSONB,
    priority JSONB,
    
    -- Metadata
    context_version INTEGER,
    embedding VECTOR(1536),
    
    INDEX idx_user_status (user_id, status),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_status (status) WHERE status = 'pending'
);

-- Thought tags
CREATE TABLE thought_tags (
    thought_id UUID REFERENCES thoughts(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    confidence FLOAT,
    PRIMARY KEY (thought_id, tag)
);

-- Weekly synthesis
CREATE TABLE weekly_synthesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    synthesis JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, week_start)
);

-- Semantic cache
CREATE TABLE thought_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    thought_text TEXT NOT NULL,
    embedding VECTOR(1536),
    response JSONB NOT NULL,
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
    
    INDEX idx_user_embedding (user_id),
    INDEX idx_expires (expires_at)
);
```

---

## Implementation Code

### API Server (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
import os
from datetime import datetime
from pydantic import BaseModel

app = FastAPI()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class ThoughtInput(BaseModel):
    text: str
    user_id: str

@app.post("/thoughts")
async def create_thought(thought: ThoughtInput):
    """Simple insert - processing happens nightly"""
    
    result = supabase.table("thoughts").insert({
        "user_id": thought.user_id,
        "text": thought.text,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    
    return {
        "id": result.data[0]["id"],
        "status": "pending",
        "message": "Thought saved! It will be analyzed tonight."
    }

@app.get("/thoughts/{user_id}")
async def get_thoughts(user_id: str, status: str = None, limit: int = 50):
    """Get user's thoughts"""
    
    query = supabase.table("thoughts").select("*").eq("user_id", user_id)
    
    if status:
        query = query.eq("status", status)
    
    result = query.order("created_at", desc=True).limit(limit).execute()
    
    return {"thoughts": result.data, "count": len(result.data)}

@app.get("/synthesis/{user_id}/latest")
async def get_latest_synthesis(user_id: str):
    """Get most recent weekly synthesis"""
    
    result = supabase.table("weekly_synthesis")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("week_start", desc=True)\
        .limit(1)\
        .execute()
    
    if not result.data:
        return {"message": "No synthesis available yet"}
    
    return result.data[0]
```

### Batch Processor (Nightly Cron)

```python
import asyncio
from supabase import create_client
from anthropic import Anthropic
import openai
import json
from datetime import datetime, timedelta

class BatchThoughtProcessor:
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.anthropic = Anthropic()
        self.openai = openai.OpenAI()
        
    async def process_pending_thoughts(self):
        """Main batch processing"""
        
        print(f"[{datetime.utcnow()}] Starting batch...")
        
        # Get pending thoughts
        result = self.supabase.table("thoughts")\
            .select("*, users!inner(context, context_version)")\
            .eq("status", "pending")\
            .order("created_at")\
            .execute()
        
        thoughts = result.data
        print(f"Found {len(thoughts)} pending thoughts")
        
        # Group by user
        by_user = {}
        for t in thoughts:
            uid = t["user_id"]
            by_user.setdefault(uid, []).append(t)
        
        # Process each user
        for user_id, user_thoughts in by_user.items():
            await self.process_user_batch(user_id, user_thoughts)
        
        # Weekly synthesis on Sundays
        if datetime.utcnow().weekday() == 6:
            await self.generate_weekly_syntheses()
        
        print("Batch complete!")
    
    async def process_user_batch(self, user_id, thoughts):
        """Process all thoughts for one user"""
        
        user_context = thoughts[0]["users"]["context"]
        
        for thought in thoughts:
            try:
                # Mark processing
                self.supabase.table("thoughts")\
                    .update({"status": "processing"})\
                    .eq("id", thought["id"])\
                    .execute()
                
                # Check semantic cache
                cached = await self.check_semantic_cache(
                    thought["text"], 
                    user_id
                )
                
                if cached:
                    result = cached
                else:
                    # Process with AI
                    result = await self.process_single_thought(
                        thought["text"],
                        user_context
                    )
                    
                    # Save to cache
                    await self.save_to_semantic_cache(
                        thought["text"],
                        user_id,
                        result
                    )
                
                # Update database
                self.supabase.table("thoughts").update({
                    "status": "completed",
                    "processed_at": datetime.utcnow().isoformat(),
                    "classification": result["classification"],
                    "analysis": result["analysis"],
                    "value_impact": result["value_impact"],
                    "action_plan": result["action_plan"],
                    "priority": result["priority"]
                }).eq("id", thought["id"]).execute()
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"Error: {e}")
                self.supabase.table("thoughts").update({
                    "status": "failed"
                }).eq("id", thought["id"]).execute()
    
    async def process_single_thought(self, thought_text, user_context):
        """5-agent pipeline with prompt caching"""
        
        system_prompt = [
            {
                "type": "text",
                "text": "You are an AI agent analyzing personal thoughts."
            },
            {
                "type": "text",
                "text": f"USER CONTEXT:\n{json.dumps(user_context, indent=2)}",
                "cache_control": {"type": "ephemeral"}
            }
        ]
        
        # Agent 1: Classification
        classification = await self.classify(thought_text, system_prompt)
        
        # Agent 2: Analysis
        analysis = await self.analyze(thought_text, classification, system_prompt)
        
        # Agent 3: Value Impact
        value_impact = await self.assess_value(
            thought_text, classification, analysis, system_prompt
        )
        
        # Agent 4: Action Planning
        action_plan = await self.plan_actions(
            thought_text, analysis, value_impact, system_prompt
        )
        
        # Agent 5: Prioritization
        priority = await self.prioritize(
            action_plan, value_impact, system_prompt
        )
        
        return {
            "classification": classification,
            "analysis": analysis,
            "value_impact": value_impact,
            "action_plan": action_plan,
            "priority": priority
        }
    
    async def classify(self, thought_text, system_prompt):
        """Agent 1: Classification"""
        response = self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": f"""Classify: "{thought_text}"
Return JSON: type, urgency, entities, emotional_tone, implied_needs"""
            }]
        )
        return json.loads(response.content[0].text)
    
    # Similar implementations for other agents...
    
    async def check_semantic_cache(self, thought_text, user_id):
        """Check for similar cached thoughts"""
        
        # Get embedding
        emb_response = self.openai.embeddings.create(
            input=thought_text,
            model="text-embedding-3-small"
        )
        embedding = emb_response.data[0].embedding
        
        # Vector similarity search
        result = self.supabase.rpc(
            "match_similar_thoughts",
            {
                "query_embedding": embedding,
                "match_threshold": 0.92,
                "match_count": 1,
                "user_id_param": user_id
            }
        ).execute()
        
        if result.data:
            return result.data[0]["response"]
        
        return None
    
    async def save_to_semantic_cache(self, thought_text, user_id, response):
        """Save to semantic cache"""
        
        emb_response = self.openai.embeddings.create(
            input=thought_text,
            model="text-embedding-3-small"
        )
        embedding = emb_response.data[0].embedding
        
        self.supabase.table("thought_cache").insert({
            "user_id": user_id,
            "thought_text": thought_text,
            "embedding": embedding,
            "response": response,
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }).execute()

if __name__ == "__main__":
    processor = BatchThoughtProcessor()
    asyncio.run(processor.process_pending_thoughts())
```

---

## Infrastructure Setup

### Option 1: GitHub Actions (Recommended - Free)

Create `.github/workflows/batch-process.yml`:

```yaml
name: Nightly Thought Processing

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  process-thoughts:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install anthropic supabase openai
      
      - name: Run batch processor
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python batch_processor.py
```

**Setup Steps:**
1. Push code to GitHub repo
2. Go to Settings → Secrets → Actions
3. Add secrets: SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
4. Workflow runs automatically at 2 AM daily

### Option 2: Render Cron Job

Create `render.yaml`:

```yaml
services:
  - type: web
    name: thought-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT"
    
  - type: cron
    name: batch-processor
    env: python
    schedule: "0 2 * * *"
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python batch_processor.py"
```

### Option 3: Self-hosted Cron

```bash
# Add to crontab
crontab -e

# Run at 2 AM daily
0 2 * * * cd /path/to/app && python3 batch_processor.py >> /var/log/thought.log 2>&1
```

### Deployment Checklist

**Supabase Setup:**
1. Create project at supabase.com
2. Enable pgvector extension
3. Run database schema SQL
4. Copy URL and anon key

**Backend Deployment:**
1. Deploy FastAPI to Fly.io/Railway/Render
2. Set environment variables
3. Test API endpoints

**Cron Setup:**
1. Choose GitHub Actions, Render, or self-hosted
2. Configure secrets/environment variables
3. Test with manual trigger
4. Verify scheduled runs

**API Keys Needed:**
- Supabase URL and Key
- Anthropic API Key
- OpenAI API Key (for embeddings)

---

## Cost Analysis

### Infrastructure Costs

**Free Tier Option:**
- Supabase: Free (500MB DB, 2GB bandwidth)
- Fly.io/Railway: Free tier
- GitHub Actions: Free (2000 mins/month)
- **Total: $0/month**

**Paid Option (Better Performance):**
- Supabase Pro: $25/month
- Render/Railway: $7/month
- **Total: $32/month**

### AI API Costs (Personal Use)

**Scenario: 20 thoughts/day**

**Without Caching:**
- 20 thoughts × 5 agents × 2K context = 200K tokens/day
- Input: 200K × $3/MTok = $0.60/day
- Output: ~50K × $15/MTok = $0.75/day
- **Total: $1.35/day = $40/month**

**With Prompt Caching:**
- Cache writes: $0.0075/day
- Cache reads: $0.057/day
- Output: $0.75/day
- **Total: $0.81/day = $24/month (40% savings)**

**With Prompt + Semantic Caching (30% hit rate):**
- Unique thoughts: 14/day
- Processing: $0.57/day
- Embeddings: 20 × $0.02/MTok = $0.001/day
- **Total: $0.57/day = $17/month (58% savings)**

### Total Monthly Cost Estimates

**Minimal (Free hosting):** $17-24/month (AI only)
**Comfortable (Paid hosting):** $49-56/month
**Premium (Higher volume):** $80-100/month

---

## Next Steps

### Phase 1: MVP (Week 1-2)
- [ ] Set up Supabase project
- [ ] Deploy FastAPI backend
- [ ] Implement basic thought input endpoint
- [ ] Create batch processor with 1-2 agents
- [ ] Set up GitHub Actions cron
- [ ] Test end-to-end flow

### Phase 2: Core Features (Week 3-4)
- [ ] Implement all 5 agents
- [ ] Add prompt caching
- [ ] Add semantic caching
- [ ] Weekly synthesis generation
- [ ] Basic web UI for viewing results

### Phase 3: Enhancement (Week 5-6)
- [ ] iOS app (SwiftUI)
- [ ] Voice input
- [ ] Improved UI/UX
- [ ] User context editing
- [ ] Search and filtering

### Phase 4: Polish (Week 7-8)
- [ ] Performance optimization
- [ ] Error handling and retry logic
- [ ] Analytics and monitoring
- [ ] User onboarding flow
- [ ] Documentation

---

## Key Design Decisions

**Why Batch Processing?**
- ✅ Simpler architecture (no queue)
- ✅ Lower hosting costs
- ✅ Better for reflection (not instant gratification)
- ✅ Efficient bulk processing with caching
- ⚠️ Not real-time (acceptable for use case)

**Why Supabase?**
- ✅ Free tier is generous
- ✅ Built-in auth and realtime
- ✅ pgvector support for semantic search
- ✅ Good Python client

**Why Claude API?**
- ✅ Superior reasoning for complex analysis
- ✅ Prompt caching reduces costs dramatically
- ✅ Long context windows (200K tokens)
- ✅ JSON mode for structured outputs

**Why Two-Layer Caching?**
- ✅ Prompt caching: 90% savings on repeated context
- ✅ Semantic caching: Avoid duplicate work
- ✅ Combined: 92% total savings
- ✅ Better user experience (faster results)

---

## Troubleshooting

**Issue: Cron job not running**
- Check GitHub Actions logs
- Verify environment variables are set
- Test batch_processor.py locally
- Ensure API keys are valid

**Issue: High API costs**
- Verify prompt caching is working (check usage stats)
- Check semantic cache hit rate
- Consider batching more aggressively
- Use Claude Haiku for simple classifications

**Issue: Slow processing**
- Add async/await throughout
- Process users in parallel
- Increase rate limiting delays if hitting limits
- Consider splitting into multiple cron jobs

**Issue: Database errors**
- Check Supabase free tier limits
- Verify pgvector extension is enabled
- Ensure indexes are created
- Check for connection pool issues

---

## Additional Resources

**Anthropic Docs:**
- Prompt Caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- API Reference: https://docs.anthropic.com/en/api

**Supabase:**
- Docs: https://supabase.com/docs
- pgvector: https://supabase.com/docs/guides/database/extensions/pgvector

**GitHub Actions:**
- Cron syntax: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule

---

## Contact & Support

This is a reference architecture. Adapt to your specific needs.

**Key Principles:**
1. Start simple, iterate based on usage
2. Monitor costs and optimize caching
3. User context is the foundation
4. Quality of analysis > speed
5. Privacy and data security first

Good luck building! 🚀
