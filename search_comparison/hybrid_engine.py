"""Hybrid search combining Elasticsearch and semantic search."""
from typing import List, Dict, Any, Optional
import time

from elasticsearch_engine import ElasticsearchEngine
from semantic_engine import SemanticEngine
from config import HybridConfig


class HybridEngine:
    """
    Combines keyword and semantic search for best of both worlds.
    
    Strategies:
    1. Weighted combination - Multiply scores by weights and sum
    2. Reciprocal Rank Fusion (RRF) - Rank-based combination
    """
    
    def __init__(
        self,
        es_engine: ElasticsearchEngine,
        semantic_engine: SemanticEngine,
        config: HybridConfig
    ):
        self.es_engine = es_engine
        self.semantic_engine = semantic_engine
        self.config = config
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index documents in both engines."""
        start_time = time.time()
        
        es_result = self.es_engine.index_documents(documents)
        semantic_result = self.semantic_engine.index_documents(documents)
        
        elapsed = time.time() - start_time
        
        return {
            "indexed": len(documents),
            "time_seconds": elapsed,
            "elasticsearch": es_result,
            "semantic": semantic_result
        }
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Hybrid search using both engines.
        """
        start_time = time.time()
        
        # Get results from both engines
        # Fetch more results than needed for better fusion
        fetch_k = min(top_k * 3, 50)
        
        es_results = self.es_engine.search(query, top_k=fetch_k, filters=filters)
        semantic_results = self.semantic_engine.search(query, top_k=fetch_k, filters=filters)
        
        # Combine results
        if self.config.use_rrf:
            combined = self._reciprocal_rank_fusion(
                es_results["results"],
                semantic_results["results"],
                top_k
            )
        else:
            combined = self._weighted_combination(
                es_results["results"],
                semantic_results["results"],
                top_k
            )
        
        elapsed = time.time() - start_time
        
        return {
            "query": query,
            "results": combined,
            "total_hits": len(combined),
            "latency_ms": elapsed * 1000,
            "engine": "hybrid",
            "elasticsearch_hits": es_results["total_hits"],
            "semantic_hits": semantic_results["total_hits"],
            "fusion_method": "rrf" if self.config.use_rrf else "weighted"
        }
    
    def _weighted_combination(
        self,
        es_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Combine results using weighted score combination.
        
        Score = (keyword_weight * keyword_score) + (semantic_weight * semantic_score)
        """
        # Normalize scores to [0, 1]
        es_normalized = self._normalize_scores(es_results)
        semantic_normalized = self._normalize_scores(semantic_results)
        
        # Create lookup dictionaries
        es_lookup = {r["id"]: r for r in es_normalized}
        semantic_lookup = {r["id"]: r for r in semantic_normalized}
        
        # Get all unique document IDs
        all_ids = set(es_lookup.keys()) | set(semantic_lookup.keys())
        
        # Calculate combined scores
        combined_scores = {}
        for doc_id in all_ids:
            es_score = es_lookup.get(doc_id, {}).get("normalized_score", 0)
            semantic_score = semantic_lookup.get(doc_id, {}).get("score", 0)
            
            combined_score = (
                self.config.keyword_weight * es_score +
                self.config.semantic_weight * semantic_score
            )
            
            # Get document data (prefer semantic for content)
            doc_data = semantic_lookup.get(doc_id) or es_lookup.get(doc_id)
            
            combined_scores[doc_id] = {
                **doc_data,
                "hybrid_score": combined_score,
                "keyword_score": es_score,
                "semantic_score": semantic_score,
                "fusion": "weighted"
            }
        
        # Sort by combined score and return top-k
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        es_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).
        
        RRF is rank-based, not score-based, which makes it more robust.
        Formula: RRF_score = sum(1 / (k + rank)) for each result list
        
        k is a constant (typically 60) that reduces impact of high rankings
        """
        # Create rank lookup for each engine
        es_ranks = {r["id"]: i + 1 for i, r in enumerate(es_results)}
        semantic_ranks = {r["id"]: i + 1 for i, r in enumerate(semantic_results)}
        
        # Get all unique document IDs
        all_ids = set(es_ranks.keys()) | set(semantic_ranks.keys())
        
        # Create lookup for document data
        es_lookup = {r["id"]: r for r in es_results}
        semantic_lookup = {r["id"]: r for r in semantic_results}
        
        # Calculate RRF scores
        rrf_scores = {}
        k = self.config.rrf_k
        
        for doc_id in all_ids:
            # Get ranks (use large number if not found)
            es_rank = es_ranks.get(doc_id, 1000)
            semantic_rank = semantic_ranks.get(doc_id, 1000)
            
            # Calculate RRF score
            rrf_score = (1 / (k + es_rank)) + (1 / (k + semantic_rank))
            
            # Get document data
            doc_data = semantic_lookup.get(doc_id) or es_lookup.get(doc_id)
            
            rrf_scores[doc_id] = {
                **doc_data,
                "hybrid_score": rrf_score,
                "keyword_rank": es_rank if es_rank < 1000 else None,
                "semantic_rank": semantic_rank if semantic_rank < 1000 else None,
                "fusion": "rrf"
            }
        
        # Sort by RRF score and return top-k
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def _normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize scores to [0, 1] range using min-max normalization."""
        if not results:
            return results
        
        scores = [r.get("score", 0) for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            # All scores are the same
            for r in results:
                r["normalized_score"] = 1.0
        else:
            for r in results:
                original_score = r.get("score", 0)
                r["normalized_score"] = (original_score - min_score) / (max_score - min_score)
        
        return results
    
    def clear_index(self):
        """Clear both indices."""
        self.es_engine.clear_index()
        self.semantic_engine.clear_index()
