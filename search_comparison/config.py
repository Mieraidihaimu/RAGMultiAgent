"""Configuration for search comparison experiments."""
import os
from dataclasses import dataclass
from typing import Literal

@dataclass
class ElasticsearchConfig:
    """Elasticsearch configuration."""
    host: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    port: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    index_name: str = "search_comparison_docs"
    
    # Fuzzy search parameters
    fuzziness: str = "AUTO"  # AUTO, 0, 1, 2
    prefix_length: int = 2
    max_expansions: int = 50


@dataclass
class SemanticConfig:
    """Semantic search configuration."""
    # Embedding model options
    provider: Literal["openai", "local", "anthropic"] = "local"
    
    # OpenAI settings
    openai_model: str = "text-embedding-3-small"  # or text-embedding-3-large
    openai_dimensions: int = 1536
    
    # Local model settings (FREE!)
    local_model: str = "all-MiniLM-L6-v2"  # Fast, 384 dimensions
    # local_model: str = "all-mpnet-base-v2"  # Better quality, 768 dimensions
    
    # Vector DB
    vector_db: Literal["chroma", "numpy"] = "chroma"
    top_k: int = 10
    similarity_threshold: float = 0.7


@dataclass
class HybridConfig:
    """Hybrid search configuration."""
    # Weighting between keyword and semantic
    keyword_weight: float = 0.3
    semantic_weight: float = 0.7
    
    # Reciprocal Rank Fusion parameters
    use_rrf: bool = True
    rrf_k: int = 60  # Constant for RRF formula


@dataclass
class BenchmarkConfig:
    """Benchmarking configuration."""
    num_warmup_queries: int = 5
    num_benchmark_queries: int = 100
    
    # Cost tracking
    openai_embedding_cost_per_1k_tokens: float = 0.00002  # text-embedding-3-small
    elasticsearch_cost_per_hour: float = 0.10  # Approximate EC2/cloud cost
    
    # Metrics
    relevance_judgments_file: str = "search_comparison/data/relevance_judgments.json"


# Default configs
ES_CONFIG = ElasticsearchConfig()
SEMANTIC_CONFIG = SemanticConfig()
HYBRID_CONFIG = HybridConfig()
BENCHMARK_CONFIG = BenchmarkConfig()
