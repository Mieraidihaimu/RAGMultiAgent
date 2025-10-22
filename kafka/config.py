"""
Kafka configuration settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class KafkaConfig(BaseSettings):
    """Kafka configuration loaded from environment variables"""

    # Kafka Connection
    bootstrap_servers: str = "localhost:9092"
    topic_name: str = "thought-processing"
    consumer_group: str = "thought-workers"

    # Topic Configuration
    num_partitions: int = 3
    replication_factor: int = 1
    retention_ms: int = 604800000  # 7 days in milliseconds

    # Consumer Configuration
    auto_offset_reset: str = "earliest"  # Start from beginning if no offset
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 5000
    session_timeout_ms: int = 30000
    max_poll_records: int = 10

    # Producer Configuration
    acks: str = "1"  # Wait for leader acknowledgment
    retries: int = 3
    max_in_flight_requests_per_connection: int = 5
    compression_type: str = "gzip"  # Reduce network bandwidth

    # Error Handling
    dead_letter_topic: str = "thought-processing-dlq"
    max_retries: int = 3
    retry_backoff_ms: int = 1000

    # Performance
    batch_size: int = 16384  # 16KB batch size
    linger_ms: int = 10  # Wait 10ms for batching
    buffer_memory: int = 33554432  # 32MB buffer

    class Config:
        env_prefix = "KAFKA_"
        case_sensitive = False

    def get_bootstrap_servers_list(self) -> List[str]:
        """Get bootstrap servers as a list"""
        return [s.strip() for s in self.bootstrap_servers.split(',')]


# Global configuration instance
kafka_config = KafkaConfig()
