"""Elasticsearch fuzzy matching search engine."""
import time
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from .config import ElasticsearchConfig


class ElasticsearchEngine:
    """Traditional keyword-based search with fuzzy matching."""
    
    def __init__(self, config: ElasticsearchConfig):
        self.config = config
        self.es = Elasticsearch(
            [f"http://{config.host}:{config.port}"],
            request_timeout=30
        )
        self._ensure_index()
    
    def _ensure_index(self):
        """Create index with optimized settings for text search."""
        if self.es.indices.exists(index=self.config.index_name):
            return
        
        # Index mapping optimized for full-text search
        mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "custom_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",  # Handle accents
                                "english_stop",
                                "english_stemmer",
                                "edge_ngram_filter"  # Better autocomplete
                            ]
                        }
                    },
                    "filter": {
                        "english_stop": {
                            "type": "stop",
                            "stopwords": "_english_"
                        },
                        "english_stemmer": {
                            "type": "stemmer",
                            "language": "english"
                        },
                        "edge_ngram_filter": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 15
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "custom_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "custom_analyzer"
                    },
                    "category": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "group_id": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"}
                }
            }
        }
        
        self.es.indices.create(index=self.config.index_name, **mapping)
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk index documents."""
        start_time = time.time()
        
        actions = [
            {
                "_index": self.config.index_name,
                "_id": doc["id"],
                "_source": doc
            }
            for doc in documents
        ]
        
        try:
            success, failed = bulk(self.es, actions, refresh=True, raise_on_error=False)
        except Exception as e:
            print(f"Bulk indexing error: {e}")
            if hasattr(e, 'errors'):
                for error in e.errors:
                    print(f"Document error: {error}")
            raise
        
        # Print detailed errors if any failed
        if failed:
            print(f"Warning: {failed} documents failed to index")
        
        elapsed = time.time() - start_time
        
        return {
            "indexed": success,
            "failed": failed,
            "time_seconds": elapsed,
            "docs_per_second": success / elapsed if elapsed > 0 else 0
        }
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search with fuzzy matching.
        
        Key features:
        - Fuzzy matching for typo tolerance
        - BM25 ranking algorithm
        - Boost title matches over content
        """
        start_time = time.time()
        
        # Build multi-match query with fuzzy matching
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content"],  # Boost title 3x
                    "type": "best_fields",
                    "fuzziness": self.config.fuzziness,
                    "prefix_length": self.config.prefix_length,
                    "max_expansions": self.config.max_expansions,
                    "operator": "or"
                }
            }
        ]
        
        # Add filters if provided
        filter_clauses = []
        if filters:
            for field, value in filters.items():
                filter_clauses.append({"term": {field: value}})
        
        # Construct full query
        es_query = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "size": top_k,
            "track_scores": True,
            "_source": ["id", "title", "content", "category", "tags"]
        }
        
        response = self.es.search(index=self.config.index_name, **es_query)
        
        elapsed = time.time() - start_time
        
        # Format results
        results = []
        for hit in response["hits"]["hits"]:
            results.append({
                "id": hit["_source"]["id"],
                "title": hit["_source"]["title"],
                "content": hit["_source"]["content"],
                "category": hit["_source"].get("category"),
                "score": hit["_score"],
                "max_score": response["hits"]["max_score"],
                "normalized_score": hit["_score"] / response["hits"]["max_score"] 
                    if response["hits"]["max_score"] and response["hits"]["max_score"] > 0 else 0
            })
        
        return {
            "query": query,
            "results": results,
            "total_hits": response["hits"]["total"]["value"],
            "latency_ms": elapsed * 1000,
            "engine": "elasticsearch"
        }
    
    def explain(self, query: str, doc_id: str) -> Dict[str, Any]:
        """
        Explain why a document matched (or didn't match) a query.
        Great for understanding BM25 scoring.
        """
        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content"],
                    "fuzziness": self.config.fuzziness
                }
            }
        }
        
        explanation = self.es.explain(
            index=self.config.index_name,
            id=doc_id,
            **es_query
        )
        
        return {
            "matched": explanation["matched"],
            "explanation": explanation.get("explanation", {}),
            "doc_id": doc_id,
            "query": query
        }
    
    def clear_index(self):
        """Delete all documents from index."""
        if self.es.indices.exists(index=self.config.index_name):
            self.es.indices.delete(index=self.config.index_name)
            self._ensure_index()
