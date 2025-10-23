"""Semantic search engine using vector embeddings."""
import time
import numpy as np
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import SemanticConfig


class SemanticEngine:
    """Vector embedding-based semantic search."""
    
    def __init__(self, config: SemanticConfig):
        self.config = config
        
        # Initialize embedding model
        if config.provider == "local":
            print(f"Loading local embedding model: {config.local_model}")
            self.model = SentenceTransformer(config.local_model)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
        else:
            raise ValueError(f"Only 'local' provider supported in this version")
        
        # Initialize vector database
        self.client = chromadb.Client(Settings(anonymized_telemetry=False))
        try:
            self.collection = self.client.get_collection(name="semantic_search")
        except:
            self.collection = self.client.create_collection(
                name="semantic_search",
                metadata={"hnsw:space": "cosine"}
            )
        
        # Cost tracking
        self.total_tokens = 0
        self.total_api_calls = 0
    
    def _embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        return self.model.encode(text, normalize_embeddings=True)
    
    def _embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts efficiently."""
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index documents with vector embeddings."""
        start_time = time.time()
        
        texts = [f"{doc['title']} {doc['content']}" for doc in documents]
        embeddings = self._embed_batch(texts)
        
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=[{
                "id": doc["id"],
                "title": doc["title"],
                "category": doc.get("category", ""),
                "tags": ",".join(doc.get("tags", []))
            } for doc in documents],
            ids=[doc["id"] for doc in documents]
        )
        
        elapsed = time.time() - start_time
        
        return {
            "indexed": len(documents),
            "time_seconds": elapsed,
            "docs_per_second": len(documents) / elapsed if elapsed > 0 else 0,
            "embedding_dimension": self.embedding_dim
        }
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Semantic search using vector similarity."""
        start_time = time.time()
        
        query_embedding = self._embed_text(query)
        
        where = {}
        if filters:
            for field, value in filters.items():
                where[field] = value
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where if where else None
        )
        
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "title": results["metadatas"][0][i]["title"],
                "content": results["documents"][0][i],
                "category": results["metadatas"][0][i].get("category"),
                "score": 1 - results["distances"][0][i],
                "distance": results["distances"][0][i]
            })
        
        elapsed = time.time() - start_time
        
        return {
            "query": query,
            "results": formatted_results,
            "total_hits": len(formatted_results),
            "latency_ms": elapsed * 1000,
            "engine": "semantic"
        }
    
    def get_embedding_cost(self) -> Dict[str, Any]:
        """Calculate total embedding cost."""
        return {
            "provider": "local",
            "model": self.config.local_model,
            "cost_usd": 0.0,
            "note": "Free! Running locally"
        }
    
    def clear_index(self):
        """Clear all indexed documents."""
        self.client.delete_collection(name="semantic_search")
        self.collection = self.client.create_collection(
            name="semantic_search",
            metadata={"hnsw:space": "cosine"}
        )
