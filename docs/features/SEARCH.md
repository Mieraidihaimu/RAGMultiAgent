# Hybrid Search Integration for Thoughts

## Overview

Integrated hybrid search capability into your RAGMultiAgent project to search thoughts and their processing results. This combines:

- **Elasticsearch** - Keyword search with BM25 and fuzzy matching
- **Semantic Search** - Vector embeddings with sentence-transformers (local, FREE!)
- **Hybrid Fusion** - Reciprocal Rank Fusion (RRF) combines both for best results

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Your Thoughts & Results                   │
│  (text, classification, analysis, value_impact, actions)    │
└────────────┬────────────────────────────────────────────────┘
             │ Indexed into
             ▼
┌─────────────────────────────────────────────────────────────┐
│            ThoughtSearchService (api/search_service.py)     │
│  • Extracts searchable text from all thought fields         │
│  • Formats documents with metadata                          │
│  • Handles batch indexing & real-time updates               │
└──────────┬───────────────────────────────────┬──────────────┘
           │                                   │
           ▼                                   ▼
┌────────────────────────┐      ┌──────────────────────────────┐
│  ElasticsearchEngine   │      │    SemanticEngine            │
│  • BM25 scoring        │      │  • all-MiniLM-L6-v2 (local)  │
│  • Fuzzy matching      │      │  • ChromaDB vector store     │
│  • Custom analyzers    │      │  • Cosine similarity         │
└────────────────────────┘      └──────────────────────────────┘
           │                                   │
           └──────────┬───────────────────────┘
                      ▼
           ┌────────────────────┐
           │   HybridEngine     │
           │  • RRF fusion      │
           │  • Weighted combo  │
           └────────────────────┘
```

## Files Created

### API Integration
- `api/search_service.py` - Core service for indexing & searching thoughts
- `api/search_routes.py` - FastAPI endpoints for search
- `frontend/search.html` - Beautiful web UI for searching thoughts

### Search Comparison Module (Reused)
- `search_comparison/` - Full hybrid search implementation
  - `config.py` - Configuration dataclasses
  - `elasticsearch_engine.py` - Keyword search
  - `semantic_engine.py` - Vector search
  - `hybrid_engine.py` - Fusion algorithms

## API Endpoints

### POST /search/thoughts
Search through your thoughts with filters.

**Request:**
```json
{
  "query": "career decision",
  "user_id": "uuid",
  "status": "completed",  // optional
  "category": "career",    // optional
  "top_k": 10,
  "search_mode": "hybrid"  // "hybrid", "keyword", or "semantic"
}
```

**Response:**
```json
{
  "query": "career decision",
  "results": [
    {
      "thought_id": "uuid",
      "title": "Should I learn Rust...",
      "content": "Full searchable text...",
      "score": 0.872,
      "category": "career",
      "status": "completed",
      "processing_mode": "group",
      "created_at": "2024-10-23..."
    }
  ],
  "total_hits": 12,
  "latency_ms": 45.2,
  "search_mode": "hybrid",
  "filters_applied": {"user_id": "...", "status": "completed"}
}
```

### POST /search/thoughts/compare
Compare all three search modes side-by-side.

**Query Params:**
- `query` - Search text
- `user_id` - Filter by user
- `top_k` - Results per mode (default: 5)

**Returns:** Results from keyword, semantic, and hybrid search for comparison.

### POST /search/index/rebuild
Rebuild search index for a user's thoughts.

**Query Params:**
- `user_id` - User to rebuild index for

Use this when:
- First enabling search on existing data
- Search results seem out of sync
- After bulk updates

## Web UI

Access at: **http://localhost:3000/search.html**

Features:
- Real-time search as you type
- Filter by status, mode, result count
- Compare all search modes side-by-side
- Beautiful gradient design
- Mobile responsive

Example searches:
- "career decision" - Exact keyword match
- "high priority" - Filter by priority
- "should I learn" - Semantic understanding
- "work life balance" - Natural language

## Docker Setup

### Services Required

1. **Elasticsearch** (port 9200)
   ```yaml
   elasticsearch:
     image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
     environment:
       - discovery.type=single-node
       - xpack.security.enabled=false
   ```

2. **API with Search** (port 8000)
   ```yaml
   api:
     environment:
       - ELASTICSEARCH_HOST=elasticsearch
       - ELASTICSEARCH_PORT=9200
     volumes:
       - ./search_comparison:/app/search_comparison
   ```

### Start Services

```bash
# Start with search profile enabled
docker-compose --profile search up -d

# Check search service health
curl http://localhost:8000/search/health

# Check Elasticsearch
curl http://localhost:9200/_cluster/health
```

## Search Modes Explained

### 1. Keyword Search (Elasticsearch)
**Best for:** Exact terms, typos, acronyms

**Strengths:**
- Fast (< 50ms)
- Handles typos with fuzzy matching
- Title boosting (title matches scored 3x higher)
- Custom analyzers (stemming, lowercase, stop words)

**Example:** "pasword resset" → finds "Password Reset Guide"

### 2. Semantic Search (Vectors)
**Best for:** Natural language, synonyms, concepts

**Strengths:**
- Understanding meaning, not just words
- Synonym matching ("change credentials" → "update password")
- Question understanding ("how do I..." queries)
- **FREE** - runs locally with sentence-transformers

**Example:** "I can't log in" → finds login troubleshooting articles

### 3. Hybrid (Default)
**Best for:** Everything - production use

**How it works:**
1. Runs both keyword + semantic search in parallel
2. Uses **Reciprocal Rank Fusion (RRF)** to combine rankings
3. RRF formula: `score = 1/(k + keyword_rank) + 1/(k + semantic_rank)`
4. Rank-based (not score-based) = more robust

**Configuration:**
```python
HybridConfig(
    keyword_weight=0.3,
    semantic_weight=0.7,
    use_rrf=True,
    rrf_k=60
)
```

## Indexing Strategy

### Automatic Indexing (Future Enhancement)
Add to your thought creation/update code:

```python
from search_service import get_search_service

# After creating/updating thought
thought_data = await db.create_thought(...)
search_service = await get_search_service()
await search_service.index_thought(thought_data)
```

### Manual Indexing
For existing data:

```bash
# Via API (requires auth)
curl -X POST "http://localhost:8000/search/index/rebuild?user_id=YOUR_USER_ID"

# Or via Python
from search_service import get_search_service

service = await get_search_service()
thoughts = await db.get_thoughts(user_id="...")
result = await service.index_thoughts_batch(thoughts)
```

## What Gets Indexed

The service extracts and indexes:

1. **Original thought text** (highest weight)
2. **Classification category** ("Category: career")
3. **Analysis insights** ("Analysis: consider long-term impact...")
4. **Value impact level** ("Impact: high")
5. **Action plan items** ("Actions: research, compare, decide")
6. **Priority level** ("Priority: urgent")

All combined with `|` separator for searchability.

## Performance

### Latency Targets
- Keyword only: < 50ms
- Semantic only: < 150ms  
- Hybrid: < 200ms

### Scalability
- Elasticsearch: Millions of documents
- ChromaDB: Hundreds of thousands (in-memory)
- Sentence-transformers: 384-dim vectors, ~90MB model

### Costs
- **$0** - Everything runs locally!
- No OpenAI embeddings API calls
- No external search services
- Self-hosted Elasticsearch + ChromaDB

## Troubleshooting

### Search service not initializing
```bash
# Check logs
docker logs thoughtprocessor-api | grep -i search

# Verify Elasticsearch is running
docker ps | grep elasticsearch
curl http://localhost:9200/_cluster/health

# Test import
docker exec thoughtprocessor-api python -c "from search_comparison import config; print('✓')"
```

### No search results
1. Check if thoughts are indexed:
   ```bash
   curl http://localhost:9200/thoughts/_count
   ```

2. Rebuild index:
   ```bash
   curl -X POST "http://localhost:8000/search/index/rebuild?user_id=YOUR_ID"
   ```

3. Check search service health:
   ```bash
   curl http://localhost:8000/search/health
   ```

### Slow searches
- Check Elasticsearch memory: increase `ES_JAVA_OPTS=-Xms512m -Xmx512m`
- Reduce top_k parameter
- Use keyword-only mode for faster results

## Next Steps

### 1. Auto-indexing on Thought Creation
Integrate search indexing into your thought creation pipeline:

```python
# In api/main.py create_thought endpoint
thought_data = await db.create_thought(...)

if SEARCH_AVAILABLE:
    search_service = await get_search_service()
    asyncio.create_task(search_service.index_thought(thought_data))
```

### 2. Search Analytics
Track what users search for:
- Popular queries
- Zero-result searches (need more content?)
- Click-through rates

### 3. Advanced Features
- **Similar thoughts**: "Find thoughts like this one"
- **Search suggestions**: As-you-type completions
- **Faceted search**: Filter by date ranges, priority, processing mode
- **Search highlighting**: Show matching text snippets

### 4. Production Optimizations
- Elasticsearch clustering for high availability
- Vector index optimization (HNSW parameters)
- Caching popular searches
- Background re-indexing jobs

## Learning Outcomes

By building this, you now understand:

1. **Information Retrieval Fundamentals**
   - BM25 algorithm (saturation-based TF-IDF)
   - Vector embeddings & cosine similarity
   - Hybrid fusion strategies (RRF vs weighted)

2. **Production Search Systems**
   - Indexing strategies (real-time vs batch)
   - Query optimization
   - Result ranking & relevance

3. **Cost-Effective AI**
   - Local embeddings vs API costs ($0 vs $$$)
   - When to use each search mode
   - Trade-offs: accuracy vs speed vs cost

## Resources

- **Elasticsearch Docs**: https://www.elastic.co/guide
- **Sentence Transformers**: https://www.sbert.net/
- **RRF Paper**: "Reciprocal Rank Fusion outperforms Condorcet and individual rank learning" (Cormack et al.)
- **ChromaDB**: https://docs.trychroma.com/

---

**Built**: October 23, 2025
**Stack**: Elasticsearch 8.11 + sentence-transformers + ChromaDB + FastAPI
**Total Cost**: $0/month (all self-hosted)
