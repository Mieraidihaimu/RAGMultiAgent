"""
Hybrid search service for thoughts and processing results.
Combines Elasticsearch keyword search with semantic vector search.
"""
import os
import json
from typing import List, Dict, Any, Optional
from uuid import UUID

from search_comparison.config import (
    ElasticsearchConfig,
    SemanticConfig,
    HybridConfig
)
from search_comparison.elasticsearch_engine import ElasticsearchEngine
from search_comparison.semantic_engine import SemanticEngine
from search_comparison.hybrid_engine import HybridEngine


class ThoughtSearchService:
    """
    Hybrid search service for thoughts and their processing results.
    
    Indexes:
    - Thought text
    - Classification categories
    - Analysis insights
    - Value impacts
    - Action plans
    - Priority assessments
    """
    
    def __init__(self):
        # Configure engines for production
        self.es_config = ElasticsearchConfig(
            host=os.getenv("ELASTICSEARCH_HOST", "elasticsearch"),
            port=int(os.getenv("ELASTICSEARCH_PORT", "9200")),
            index_name="thoughts"
        )
        
        self.semantic_config = SemanticConfig(
            provider="local",
            local_model="all-MiniLM-L6-v2"
        )
        
        self.hybrid_config = HybridConfig(
            keyword_weight=0.3,
            semantic_weight=0.7,
            use_rrf=True,
            rrf_k=60
        )
        
        # Initialize engines
        self.es_engine = None
        self.semantic_engine = None
        self.hybrid_engine = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize search engines (call this on startup)"""
        if self._initialized:
            return
        
        try:
            self.es_engine = ElasticsearchEngine(self.es_config)
            self.semantic_engine = SemanticEngine(self.semantic_config)
            self.hybrid_engine = HybridEngine(
                self.es_engine,
                self.semantic_engine,
                self.hybrid_config
            )
            self._initialized = True
            print("✓ Thought search service initialized")
        except Exception as e:
            print(f"✗ Failed to initialize thought search service: {e}")
            raise
    
    def _extract_searchable_text(self, thought: Dict[str, Any]) -> str:
        """
        Extract all searchable text from a thought record.
        Combines thought text with processing results.
        """
        parts = []
        
        # Original thought text (highest importance)
        if thought.get("text"):
            parts.append(thought["text"])
        
        # Classification category
        if thought.get("classification"):
            classification = thought["classification"]
            if isinstance(classification, dict):
                category = classification.get("category", "")
                if category:
                    parts.append(f"Category: {category}")
        
        # Analysis insights
        if thought.get("analysis"):
            analysis = thought["analysis"]
            if isinstance(analysis, dict):
                insights = analysis.get("insights", [])
                if insights:
                    parts.append("Analysis: " + " ".join(insights))
        
        # Value impact
        if thought.get("value_impact"):
            value_impact = thought["value_impact"]
            if isinstance(value_impact, dict):
                impact = value_impact.get("impact_level", "")
                if impact:
                    parts.append(f"Impact: {impact}")
        
        # Action plan
        if thought.get("action_plan"):
            action_plan = thought["action_plan"]
            if isinstance(action_plan, dict):
                actions = action_plan.get("actions", [])
                if actions:
                    parts.append("Actions: " + " ".join([str(a) for a in actions]))
        
        # Priority
        if thought.get("priority"):
            priority = thought["priority"]
            if isinstance(priority, dict):
                level = priority.get("level", "")
                if level:
                    parts.append(f"Priority: {level}")
        
        return " | ".join(parts)
    
    def _format_thought_document(self, thought: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a thought record into a searchable document.
        """
        searchable_text = self._extract_searchable_text(thought)
        
        return {
            "id": f"thought_{thought['id']}",
            "title": thought.get("text", "")[:100],  # First 100 chars as title
            "content": searchable_text,
            "category": self._get_category(thought),
            "tags": self._extract_tags(thought),
            "user_id": str(thought.get("user_id", "")),
            "status": thought.get("status", ""),
            "created_at": str(thought.get("created_at", "")),
            "metadata": {
                "thought_id": str(thought["id"]),
                "processing_mode": thought.get("processing_mode", "single"),
                "group_id": str(thought.get("group_id", "")) if thought.get("group_id") else None
            }
        }
    
    def _get_category(self, thought: Dict[str, Any]) -> str:
        """Extract category from thought classification"""
        if thought.get("classification"):
            classification = thought["classification"]
            if isinstance(classification, dict):
                return classification.get("category", "uncategorized")
        return "uncategorized"
    
    def _extract_tags(self, thought: Dict[str, Any]) -> List[str]:
        """Extract relevant tags from thought"""
        tags = []
        
        # Add status
        if thought.get("status"):
            tags.append(thought["status"])
        
        # Add processing mode
        if thought.get("processing_mode"):
            tags.append(thought["processing_mode"])
        
        # Add priority level if available
        if thought.get("priority"):
            priority = thought["priority"]
            if isinstance(priority, dict) and priority.get("level"):
                tags.append(f"priority_{priority['level']}")
        
        return tags
    
    async def index_thought(self, thought: Dict[str, Any]) -> bool:
        """
        Index a single thought for searching.
        Call this whenever a thought is created or updated.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            document = self._format_thought_document(thought)
            self.hybrid_engine.index_documents([document])
            return True
        except Exception as e:
            print(f"Error indexing thought {thought.get('id')}: {e}")
            return False
    
    async def index_thoughts_batch(self, thoughts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Index multiple thoughts at once.
        Use this for initial indexing or bulk updates.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            documents = [self._format_thought_document(t) for t in thoughts]
            result = self.hybrid_engine.index_documents(documents)
            return result
        except Exception as e:
            print(f"Error batch indexing thoughts: {e}")
            return {"indexed": 0, "error": str(e)}
    
    async def search_thoughts(
        self,
        query: str,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 10,
        search_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Search thoughts with optional filters.
        
        Args:
            query: Search query text
            user_id: Filter by user ID
            status: Filter by status (pending, completed, etc.)
            category: Filter by classification category
            top_k: Number of results to return
            search_mode: "hybrid", "keyword", or "semantic"
        
        Returns:
            Dict with results and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        # Build filters
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
        
        try:
            # Execute search based on mode
            if search_mode == "keyword":
                results = self.es_engine.search(query, top_k=top_k, filters=filters)
            elif search_mode == "semantic":
                results = self.semantic_engine.search(query, top_k=top_k, filters=filters)
            else:  # hybrid (default)
                results = self.hybrid_engine.search(query, top_k=top_k, filters=filters)
            
            # Enhance results with thought metadata
            enhanced_results = []
            for result in results.get("results", []):
                enhanced_result = {
                    **result,
                    "thought_id": result.get("metadata", {}).get("thought_id"),
                    "processing_mode": result.get("metadata", {}).get("processing_mode"),
                    "group_id": result.get("metadata", {}).get("group_id"),
                }
                enhanced_results.append(enhanced_result)
            
            return {
                **results,
                "results": enhanced_results,
                "search_mode": search_mode,
                "filters_applied": filters
            }
            
        except Exception as e:
            print(f"Error searching thoughts: {e}")
            return {
                "query": query,
                "results": [],
                "total_hits": 0,
                "error": str(e)
            }
    
    async def compare_search_modes(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Compare all three search modes side-by-side.
        Useful for understanding search quality.
        """
        if not self._initialized:
            await self.initialize()
        
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        
        try:
            keyword_results = self.es_engine.search(query, top_k=top_k, filters=filters)
            semantic_results = self.semantic_engine.search(query, top_k=top_k, filters=filters)
            hybrid_results = self.hybrid_engine.search(query, top_k=top_k, filters=filters)
            
            return {
                "query": query,
                "keyword": keyword_results,
                "semantic": semantic_results,
                "hybrid": hybrid_results
            }
        except Exception as e:
            print(f"Error comparing search modes: {e}")
            return {"error": str(e)}
    
    async def get_similar_thoughts(
        self,
        thought_id: str,
        user_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find thoughts similar to a given thought.
        Uses semantic similarity on the thought text.
        """
        # This would require fetching the thought first
        # Placeholder for now
        raise NotImplementedError("Similar thoughts search coming soon")


# Global instance
_search_service: Optional[ThoughtSearchService] = None


async def get_search_service() -> ThoughtSearchService:
    """Get or create the global search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = ThoughtSearchService()
        await _search_service.initialize()
    return _search_service


async def close_search_service():
    """Close the search service on shutdown"""
    global _search_service
    if _search_service:
        # Cleanup if needed
        _search_service = None
