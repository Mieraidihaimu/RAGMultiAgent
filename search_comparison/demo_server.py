#!/usr/bin/env python3
"""Interactive web demo for search comparison."""
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time

from .config import ES_CONFIG, SEMANTIC_CONFIG, HYBRID_CONFIG
from .elasticsearch_engine import ElasticsearchEngine
from .semantic_engine import SemanticEngine
from .hybrid_engine import HybridEngine
from .sample_data import get_sample_documents

app = FastAPI(title="Search Comparison API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

es_engine = None
semantic_engine = None
hybrid_engine = None
indexed = False


@app.on_event("startup")
async def startup_event():
    """Initialize search engines and index sample data."""
    global es_engine, semantic_engine, hybrid_engine, indexed
    
    print("Starting search comparison service...")
    
    ES_CONFIG.host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
    ES_CONFIG.port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            es_engine = ElasticsearchEngine(ES_CONFIG)
            print(f"✓ Connected to Elasticsearch")
            break
        except Exception as e:
            retry_count += 1
            print(f"Waiting for Elasticsearch... ({retry_count}/{max_retries}): {str(e)}")
            time.sleep(2)
    
    if es_engine is None:
        raise Exception("Failed to connect to Elasticsearch")
    
    print(f"Loading semantic engine...")
    semantic_engine = SemanticEngine(SEMANTIC_CONFIG)
    print("✓ Semantic engine ready")
    
    hybrid_engine = HybridEngine(es_engine, semantic_engine, HYBRID_CONFIG)
    print("✓ Hybrid engine ready")
    
    print("Indexing sample documents...")
    documents = get_sample_documents()
    result = hybrid_engine.index_documents(documents)
    indexed = True
    print(f"✓ Indexed {result['indexed']} documents")
    print("Search comparison service is ready! 🚀")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve interactive web UI."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Search Comparison</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { text-align: center; color: #333; margin-bottom: 10px; font-size: 2.5em; }
            .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
            .search-box { display: flex; gap: 10px; margin-bottom: 30px; }
            input[type="text"] {
                flex: 1;
                padding: 15px 20px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 16px;
            }
            input[type="text"]:focus { outline: none; border-color: #667eea; }
            button {
                padding: 15px 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                cursor: pointer;
            }
            button:hover { transform: translateY(-2px); }
            .examples {
                margin-bottom: 30px;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
            }
            .example-tag {
                display: inline-block;
                padding: 8px 15px;
                background: white;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                margin: 4px;
                cursor: pointer;
            }
            .example-tag:hover { border-color: #667eea; background: #f0f0ff; }
            .results-container {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }
            .result-column {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 20px;
            }
            .result-column h2 { font-size: 1.3em; margin-bottom: 10px; color: #333; }
            .stats {
                font-size: 12px;
                color: #666;
                margin-bottom: 15px;
                padding: 10px;
                background: white;
                border-radius: 8px;
            }
            .result-item {
                background: white;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                border-left: 4px solid #667eea;
            }
            .result-title { font-weight: 600; color: #333; margin-bottom: 5px; }
            .result-content { font-size: 14px; color: #666; line-height: 1.5; }
            .result-meta {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #999;
                margin-top: 8px;
            }
            .score { font-weight: 600; color: #667eea; }
            @media (max-width: 1200px) {
                .results-container { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Search Engine Comparison</h1>
            <p class="subtitle">Compare Elasticsearch, Semantic, and Hybrid search</p>
            
            <div class="examples">
                <h3>💡 Try these:</h3>
                <span class="example-tag" onclick="search('password reset')">password reset</span>
                <span class="example-tag" onclick="search('pasword resset')">typos</span>
                <span class="example-tag" onclick="search('I can\\'t log in')">natural language</span>
                <span class="example-tag" onclick="search('change credentials')">synonyms</span>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Enter your search query..." onkeypress="if(event.key==='Enter') search()">
                <button onclick="search()">Search</button>
            </div>
            
            <div id="results"></div>
        </div>
        
        <script>
            function search(query) {
                const searchInput = document.getElementById('searchInput');
                const resultsDiv = document.getElementById('results');
                
                if (query) searchInput.value = query;
                
                const searchQuery = searchInput.value.trim();
                if (!searchQuery) return;
                
                resultsDiv.innerHTML = '<div style="text-align:center;padding:40px;">🔄 Searching...</div>';
                
                fetch('/api/search/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: searchQuery, top_k: 5 })
                })
                .then(r => r.json())
                .then(data => {
                    resultsDiv.innerHTML = `
                        <div class="results-container">
                            ${renderColumn('Elasticsearch', data.elasticsearch, '⚡')}
                            ${renderColumn('Semantic', data.semantic, '🧠')}
                            ${renderColumn('Hybrid', data.hybrid, '🔮')}
                        </div>
                    `;
                })
                .catch(e => {
                    resultsDiv.innerHTML = `<div style="color:#c33;padding:20px;">❌ Error: ${e.message}</div>`;
                });
            }
            
            function renderColumn(title, data, icon) {
                const resultsHtml = data.results.map((r, i) => `
                    <div class="result-item">
                        <div class="result-title">${i + 1}. ${r.title}</div>
                        <div class="result-content">${r.content.substring(0, 100)}...</div>
                        <div class="result-meta">
                            <span>${r.category || 'N/A'}</span>
                            <span class="score">${(r.score || r.hybrid_score || 0).toFixed(3)}</span>
                        </div>
                    </div>
                `).join('');
                
                return `
                    <div class="result-column">
                        <h2>${icon} ${title}</h2>
                        <div class="stats">⏱️ ${data.latency_ms.toFixed(1)}ms | 📊 ${data.total_hits} hits</div>
                        ${resultsHtml || '<p style="color:#999;">No results</p>'}
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "indexed": indexed,
        "elasticsearch": ES_CONFIG.host,
        "embedding_provider": SEMANTIC_CONFIG.provider
    }


@app.post("/api/search/compare")
async def compare_search(request: SearchRequest):
    """Compare all three search engines."""
    es_results = es_engine.search(request.query, top_k=request.top_k)
    semantic_results = semantic_engine.search(request.query, top_k=request.top_k)
    hybrid_results = hybrid_engine.search(request.query, top_k=request.top_k)
    
    return {
        "elasticsearch": es_results,
        "semantic": semantic_results,
        "hybrid": hybrid_results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
