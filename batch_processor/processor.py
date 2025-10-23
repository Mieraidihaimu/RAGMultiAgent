"""
Thought processor - supports both batch mode and Kafka streaming mode
Orchestrates the 5-agent pipeline with caching and real-time updates
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from uuid import UUID

from loguru import logger
from prometheus_client import Counter, Histogram, Gauge, start_http_server

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from agents import AgentPipeline
from semantic_cache import SemanticCache
from common.database import DatabaseFactory
from common.database.base import DatabaseAdapter

# Prometheus metrics
THOUGHTS_PROCESSED = Counter(
    'batch_processor_thoughts_processed_total',
    'Total number of thoughts processed'
)
THOUGHTS_FAILED = Counter(
    'batch_processor_thoughts_failed_total',
    'Total number of thoughts that failed processing'
)
CACHE_HITS = Counter(
    'batch_processor_cache_hits_total',
    'Total number of cache hits'
)
CACHE_MISSES = Counter(
    'batch_processor_cache_misses_total',
    'Total number of cache misses'
)
PROCESSING_DURATION = Histogram(
    'batch_processor_processing_duration_seconds',
    'Time spent processing a thought',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)
ACTIVE_WORKERS = Gauge(
    'batch_processor_active_workers',
    'Number of active workers'
)
QUEUE_SIZE = Gauge(
    'batch_processor_queue_size',
    'Number of thoughts in queue'
)

# Import Kafka and SSE if in Kafka mode
if settings.kafka_mode or settings.kafka_enabled:
    try:
        from kafka.consumer import KafkaThoughtConsumer
        from kafka.events import ThoughtEvent, ThoughtCreatedEvent, EventType
        import redis.asyncio as aioredis
        KAFKA_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Kafka/Redis libraries not available: {e}")
        KAFKA_AVAILABLE = False
else:
    KAFKA_AVAILABLE = False


class ThoughtProcessor:
    """
    Core thought processor - shared between batch and Kafka modes
    Handles the 5-agent pipeline with caching and SSE updates
    """

    def __init__(self, db: DatabaseAdapter, redis_client: Optional[aioredis.Redis] = None):
        # Initialize clients
        self.db = db
        self.agent_pipeline = AgentPipeline()
        self.semantic_cache = SemanticCache(self.db)
        self.redis_client = redis_client

        # Processing stats
        self.stats = {
            "total_thoughts": 0,
            "processed": 0,
            "failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "start_time": None,
            "end_time": None
        }

    async def _publish_sse_update(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Publish SSE update via Redis pub/sub"""
        if not self.redis_client:
            return

        try:
            # Convert UUIDs to strings for JSON serialization
            def convert_uuids(obj):
                if isinstance(obj, UUID):
                    return str(obj)
                elif isinstance(obj, dict):
                    return {k: convert_uuids(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_uuids(item) for item in obj]
                return obj
            
            channel = f"thought_updates:{user_id}"
            payload = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": convert_uuids(data)
            }
            await self.redis_client.publish(channel, json.dumps(payload))
            logger.debug(f"Published SSE update: {event_type} to {channel}")
        except Exception as e:
            logger.warning(f"Failed to publish SSE update: {e}")

    async def get_pending_thoughts(self) -> List[Dict[str, Any]]:
        """
        Fetch all pending thoughts with user context
        """
        try:
            thoughts = await self.db.get_pending_thoughts()
            logger.info(f"Found {len(thoughts)} pending thoughts")
            return thoughts

        except Exception as e:
            logger.error(f"Failed to fetch pending thoughts: {e}")
            raise

    async def mark_processing(self, thought_id: str, attempts: int):
        """Mark thought as currently being processed"""
        try:
            await self.db.update_thought(
                thought_id,
                status="processing",
                processing_attempts=attempts + 1
            )

        except Exception as e:
            logger.warning(f"Failed to mark thought {thought_id} as processing: {e}")

    async def save_results(
        self,
        thought_id: str,
        result: Dict[str, Any],
        embedding: List[float] = None
    ):
        """
        Save processing results to database
        Handles both single mode and group mode results
        """
        try:
            # Check if this is group mode result
            if result.get("mode") == "group":
                # Group mode: save consolidated output (convert dict to JSON string)
                consolidated = result.get("consolidated")
                if isinstance(consolidated, dict):
                    consolidated = json.dumps(consolidated)
                
                update_data = {
                    "status": "completed",
                    "processed_at": datetime.utcnow(),
                    "consolidated_output": consolidated,
                    # Clear single-mode fields for group mode
                    "classification": None,
                    "analysis": None,
                    "value_impact": None,
                    "action_plan": None,
                    "priority": None
                }
            else:
                # Single mode: save individual agent outputs
                update_data = {
                    "status": "completed",
                    "processed_at": datetime.utcnow(),
                    "classification": result.get("classification"),
                    "analysis": result.get("analysis"),
                    "value_impact": result.get("value_impact"),
                    "action_plan": result.get("action_plan"),
                    "priority": result.get("priority"),
                    "consolidated_output": None
                }

            if embedding:
                update_data["embedding"] = embedding

            await self.db.update_thought(thought_id, **update_data)

            logger.info(f"Saved results for thought {thought_id} (mode: {result.get('mode', 'single')})")

        except Exception as e:
            logger.error(f"Failed to save results for thought {thought_id}: {e}")
            raise

    async def mark_failed(self, thought_id: str, error_message: str):
        """Mark thought as failed"""
        try:
            await self.db.update_thought(
                thought_id,
                status="failed",
                error_message=error_message[:500]  # Limit error message length
            )

            logger.warning(f"Marked thought {thought_id} as failed")

        except Exception as e:
            logger.error(f"Failed to mark thought {thought_id} as failed: {e}")

    async def process_single_thought(
        self,
        thought: Dict[str, Any],
        publish_updates: bool = True
    ) -> bool:
        """
        Process a single thought through the pipeline
        Supports both 'single' and 'group' processing modes
        Returns True if successful, False otherwise
        """
        thought_id = thought["id"]
        thought_text = thought["text"]
        user_id = thought["user_id"]
        processing_mode = thought.get("processing_mode", "single")
        group_id = thought.get("group_id")
        start_time = datetime.utcnow()

        # Start timing for Prometheus
        with PROCESSING_DURATION.time():
            # Parse user_context (might be JSON string or dict)
            user_context = thought["context"]
            if isinstance(user_context, str):
                try:
                    user_context = json.loads(user_context)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse user_context as JSON, using empty dict")
                    user_context = {}
            elif user_context is None:
                user_context = {}

            try:
                # Mark as processing
                await self.mark_processing(thought_id, thought.get('processing_attempts', 0))

                # SSE Update: Processing started
                if publish_updates:
                    await self._publish_sse_update(
                        user_id,
                        "thought_processing",
                        {
                            "thought_id": thought_id,
                            "status": "processing",
                            "mode": processing_mode,
                            "message": "Starting AI analysis..."
                        }
                    )

                # Route to appropriate processing method based on mode
                if processing_mode == "group" and group_id:
                    result = await self._process_group_mode(
                        thought_id,
                        thought_text,
                        user_id,
                        user_context,
                        group_id,
                        publish_updates
                    )
                else:
                    # Default single mode processing
                    result = await self._process_single_mode(
                        thought_id,
                        thought_text,
                        user_id,
                        user_context,
                        publish_updates
                    )

                # Get embedding for the thought (for semantic search later)
                embedding = await self.semantic_cache.get_embedding(thought_text)

                # Save results to database (mode-specific)
                await self.save_results(thought_id, result, embedding)

                # Calculate processing time
                processing_time = (datetime.utcnow() - start_time).total_seconds()

                # SSE Update: Completed
                if publish_updates:
                    await self._publish_sse_update(
                        user_id,
                        "thought_completed",
                        {
                            "thought_id": thought_id,
                            "status": "completed",
                            "mode": processing_mode,
                            "message": "Analysis complete!",
                            "processing_time_seconds": processing_time
                        }
                    )

                # Update Prometheus metrics
                THOUGHTS_PROCESSED.inc()
                self.stats["processed"] += 1
                return True

            except Exception as e:
                logger.error(f"Failed to process thought {thought_id}: {e}")
                await self.mark_failed(thought_id, str(e))

                # SSE Update: Failed
                if publish_updates:
                    await self._publish_sse_update(
                        user_id,
                        "thought_failed",
                        {"thought_id": thought_id, "status": "failed", "error": str(e)}
                    )

                # Update Prometheus metrics
                THOUGHTS_FAILED.inc()
                self.stats["failed"] += 1
                return False

    async def _process_single_mode(
        self,
        thought_id: str,
        thought_text: str,
        user_id: str,
        user_context: Dict[str, Any],
        publish_updates: bool
    ) -> Dict[str, Any]:
        """
        Process thought in single mode (personal LLM feedback)
        Uses semantic caching
        """
        # Check semantic cache first
        cached_result = await self.semantic_cache.check_cache(
            thought_text,
            user_id
        )

        if cached_result:
            # Cache hit - use cached result
            result = cached_result
            CACHE_HITS.inc()
            self.stats["cache_hits"] += 1
            logger.info(f"Using cached result for thought {thought_id}")

            # Simulate agent progress for UX (instant, but user sees progression)
            if publish_updates:
                agent_names = ["Classifier", "Analyzer", "Value Assessor", "Action Planner", "Prioritizer"]
                for i, agent_name in enumerate(agent_names, 1):
                    await self._publish_sse_update(
                        user_id,
                        "thought_agent_completed",
                        {
                            "thought_id": thought_id,
                            "agent": agent_name,
                            "progress": f"{i}/5",
                            "agent_number": i,
                            "total_agents": 5
                        }
                    )
                    await asyncio.sleep(0.1)  # Small delay for UI progression

        else:
            # Cache miss - process with AI
            CACHE_MISSES.inc()
            self.stats["cache_misses"] += 1
            logger.info(f"Processing thought {thought_id} with AI pipeline")

            # Process through 5-agent pipeline with progress updates
            result = await self._process_with_agent_updates(
                thought_text,
                user_context,
                user_id,
                thought_id,
                publish_updates
            )

            # Save to semantic cache
            await self.semantic_cache.save_to_cache(
                thought_text,
                user_id,
                result
            )

        return result

    async def _process_group_mode(
        self,
        thought_id: str,
        thought_text: str,
        user_id: str,
        user_context: Dict[str, Any],
        group_id: str,
        publish_updates: bool
    ) -> Dict[str, Any]:
        """
        Process thought in group mode (multiple persona perspectives)
        No caching for group mode (too many variations)
        """
        import time

        # Fetch group and personas
        group = await self.db.get_persona_group(group_id, include_personas=True)
        
        if not group:
            raise ValueError(f"Persona group {group_id} not found")
        
        personas = group.get('personas', [])
        
        if not personas:
            raise ValueError(f"Persona group {group_id} has no personas")
        
        logger.info(f"Processing thought {thought_id} with {len(personas)} personas from group '{group['name']}'")

        # SSE Update: Group processing started
        if publish_updates:
            await self._publish_sse_update(
                user_id,
                "group_processing_started",
                {
                    "thought_id": thought_id,
                    "group_name": group['name'],
                    "persona_count": len(personas)
                }
            )

        # Process through all personas in parallel
        result = await self.agent_pipeline.process_thought_with_group(
            thought_text,
            user_context,
            personas
        )

        # Publish persona-level SSE updates
        if publish_updates:
            for i, persona_output in enumerate(result['persona_outputs'], 1):
                await self._publish_sse_update(
                    user_id,
                    "persona_completed",
                    {
                        "thought_id": thought_id,
                        "persona_id": persona_output['persona_id'],
                        "persona_name": persona_output['persona_name'],
                        "progress": f"{i}/{len(personas)}",
                        "has_error": persona_output['error'] is not None
                    }
                )
            
            # Consolidation started
            await self._publish_sse_update(
                user_id,
                "consolidation_started",
                {
                    "thought_id": thought_id,
                    "message": "Synthesizing perspectives..."
                }
            )

        # Save individual persona runs to database
        for persona_output in result['persona_outputs']:
            if persona_output['error'] is None:
                try:
                    processing_time_ms = int(result.get('processing_time_seconds', 0) * 1000)
                    
                    # Convert persona output to JSON string
                    output_json = persona_output['output']
                    if isinstance(output_json, dict):
                        output_json = json.dumps(output_json)
                    
                    await self.db.create_thought_persona_run(
                        thought_id=thought_id,
                        persona_id=persona_output['persona_id'],
                        group_id=group_id,
                        persona_name=persona_output['persona_name'],
                        persona_output=output_json,
                        processing_time_ms=processing_time_ms
                    )
                except Exception as e:
                    logger.warning(f"Failed to save persona run: {e}")

        return result

    async def _process_with_agent_updates(
        self,
        thought_text: str,
        user_context: Dict[str, Any],
        user_id: str,
        thought_id: str,
        publish_updates: bool
    ) -> Dict[str, Any]:
        """
        Process thought through 5-agent pipeline with progress updates
        """
        agent_names = ["Classifier", "Analyzer", "Value Assessor", "Action Planner", "Prioritizer"]

        # For now, use the existing process_thought method
        # In the future, this could be refactored to process agents individually
        result = await self.agent_pipeline.process_thought(thought_text, user_context)

        # Publish progress updates (simulated for now, since we don't have individual agent hooks yet)
        if publish_updates:
            for i, agent_name in enumerate(agent_names, 1):
                await self._publish_sse_update(
                    user_id,
                    "thought_agent_completed",
                    {
                        "thought_id": thought_id,
                        "agent": agent_name,
                        "progress": f"{i}/5",
                        "agent_number": i,
                        "total_agents": 5
                    }
                )
                # Small delay between agents for realistic progression
                await asyncio.sleep(3)  # ~15 seconds total for 5 agents

        return result

    async def process_user_batch(
        self,
        user_id: str,
        thoughts: List[Dict[str, Any]]
    ):
        """
        Process all thoughts for a single user
        """
        logger.info(f"Processing {len(thoughts)} thoughts for user {user_id}")

        for thought in thoughts:
            await self.process_single_thought(thought)

            # Rate limiting to avoid API throttling (reduced for faster testing)
            await asyncio.sleep(1)

    async def generate_weekly_synthesis(self, user_id: str):
        """
        Generate weekly synthesis for a user
        Summarizes all thoughts from the past week
        """
        try:
            # Get thoughts from past week
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_start = week_ago.date()
            week_end = datetime.utcnow().date()

            thoughts = await self.db.get_thoughts(
                user_id=user_id,
                status="completed",
                # A bit of a hack to get all thoughts from the last 7 days
                limit=1000, 
            )
            thoughts = [t for t in thoughts if t['created_at'] > week_ago]

            if len(thoughts) < 3:
                logger.info(f"Not enough thoughts for synthesis (user {user_id})")
                return

            # Get user context
            user = await self.db.get_user(user_id)
            user_context = user["context"]

            # Generate synthesis using AI
            synthesis = await self._create_synthesis(thoughts, user_context)

            # Save synthesis
            await self.db.save_weekly_synthesis(
                user_id=user_id,
                week_start=week_start,
                week_end=week_end,
                synthesis=synthesis
            )

            logger.info(f"Created weekly synthesis for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to create weekly synthesis: {e}")

    async def _create_synthesis(
        self,
        thoughts: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create weekly synthesis using AI
        """
        # Prepare summary of thoughts
        thought_summaries = []
        for t in thoughts:
            summary = {
                "text": t["text"],
                "priority": t.get("priority", {}).get("priority_level"),
                "value_score": t.get("value_impact", {}).get("weighted_total")
            }
            thought_summaries.append(summary)

        system_prompt = [
            {
                "type": "text",
                "text": "You are a personal insights AI creating weekly summaries."
            },
            {
                "type": "text",
                "text": f"USER CONTEXT:\n{user_context}",
                "cache_control": {"type": "ephemeral"}
            }
        ]

        prompt = f"""Create a weekly synthesis from these {len(thoughts)} thoughts:

{thought_summaries}

Return JSON with:
- key_themes: [main themes that emerged]
- progress_areas: [areas where user is making progress]
- challenges: [recurring challenges or blockers]
- opportunities: [opportunities user should consider]
- patterns: [behavioral or thought patterns noticed]
- recommendations: [3-5 actionable recommendations for next week]
- encouragement: [personal, encouraging message]
"""

        try:
            response = self.agent_pipeline.client.messages.create(
                model=settings.claude_model,
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            synthesis = json.loads(response.content[0].text)
            return synthesis

        except Exception as e:
            logger.error(f"Failed to generate synthesis: {e}")
            return {"error": str(e)}

    async def run_batch(self):
        """
        Main batch processing entry point
        """
        # Reset stats for this run
        self.stats = {
            "total_thoughts": 0,
            "processed": 0,
            "failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "start_time": None,
            "end_time": None
        }
        self.stats["start_time"] = datetime.utcnow()
        logger.info("="*60)
        logger.info("Starting batch processing run")
        logger.info(f"Time: {self.stats['start_time']}")
        logger.info("="*60)

        try:
            # Get all pending thoughts
            thoughts = await self.get_pending_thoughts()
            self.stats["total_thoughts"] = len(thoughts)

            if len(thoughts) == 0:
                logger.info("No pending thoughts to process")
                return

            # Group thoughts by user
            by_user = defaultdict(list)
            for thought in thoughts:
                by_user[thought["user_id"]].append(thought)

            logger.info(f"Processing thoughts for {len(by_user)} users")

            # Process each user's thoughts
            for user_id, user_thoughts in by_user.items():
                await self.process_user_batch(user_id, user_thoughts)

            # Weekly synthesis on Sundays
            if datetime.utcnow().weekday() == 6:
                logger.info("Sunday - generating weekly syntheses")
                for user_id in by_user.keys():
                    await self.generate_weekly_synthesis(user_id)

            # Cleanup expired cache entries
            await self.semantic_cache.cleanup_expired()

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise

        finally:
            self.stats["end_time"] = datetime.utcnow()
            duration = (self.stats["end_time"] - self.stats["start_time"])

            # Log final statistics
            logger.info("="*60)
            logger.info("Batch processing complete!")
            logger.info(f"Duration: {duration.total_seconds():.1f} seconds")
            logger.info(f"Total thoughts: {self.stats['total_thoughts']}")
            logger.info(f"Processed: {self.stats['processed']}")
            logger.info(f"Failed: {self.stats['failed']}")
            logger.info(f"Cache hits: {self.stats['cache_hits']}")
            logger.info(f"Cache misses: {self.stats['cache_misses']}")

            if self.stats['cache_hits'] + self.stats['cache_misses'] > 0:
                hit_rate = (
                    self.stats['cache_hits'] /
                    (self.stats['cache_hits'] + self.stats['cache_misses'])
                ) * 100
                logger.info(f"Cache hit rate: {hit_rate:.1f}%")

            logger.info("="*60)


# Backward compatibility alias
BatchThoughtProcessor = ThoughtProcessor


async def republish_pending_thoughts(db: DatabaseAdapter):
    """
    Scan database for pending thoughts and republish them to Kafka
    This handles thoughts that were created while workers were down
    """
    try:
        from kafka.producer import KafkaThoughtProducer
        
        logger.info("Scanning for pending thoughts to republish...")
        
        # Get all pending thoughts from database with user context
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    t.id, 
                    t.user_id, 
                    t.text, 
                    t.created_at,
                    u.context as user_context
                FROM thoughts t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.status = 'pending'
                ORDER BY t.created_at ASC
            """)
        
        if not rows:
            logger.info("No pending thoughts found.")
            return
        
        logger.info(f"Found {len(rows)} pending thought(s) to republish")
        
        # Initialize Kafka producer
        producer = KafkaThoughtProducer(settings.kafka_bootstrap_servers)
        await producer.start()
        
        republished_count = 0
        failed_count = 0
        
        for row in rows:
            try:
                thought_id = str(row['id'])
                user_id = str(row['user_id']) if row['user_id'] else None
                text = row['text']
                user_context = row['user_context'] if row['user_context'] else {}
                
                # Parse context if it's a JSON string
                if isinstance(user_context, str):
                    try:
                        import json
                        user_context = json.loads(user_context)
                    except:
                        user_context = {}
                
                # Skip if no user_id (should not happen with schema)
                if not user_id:
                    logger.warning(f"Skipping thought {thought_id} - no user_id")
                    continue
                
                # Republish to Kafka
                success = await producer.send_thought_created(
                    user_id=user_id,
                    thought_id=thought_id,
                    text=text,
                    user_context=user_context
                )
                
                if success:
                    republished_count += 1
                    logger.info(f"✓ Republished thought {thought_id}")
                else:
                    failed_count += 1
                    logger.error(f"✗ Failed to republish thought {thought_id}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error republishing thought {row['id']}: {e}")
        
        await producer.stop()
        
        logger.info(f"Republish complete: {republished_count} succeeded, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error in republish_pending_thoughts: {e}", exc_info=True)


async def kafka_consumer_mode(db: DatabaseAdapter, redis_client: aioredis.Redis):
    """
    Run as Kafka consumer - processes thoughts from Kafka topic
    """
    logger.info("="*60)
    logger.info("Starting Kafka consumer mode")
    logger.info(f"Bootstrap servers: {settings.kafka_bootstrap_servers}")
    logger.info(f"Topic: {settings.kafka_topic}")
    logger.info(f"Consumer group: {settings.kafka_consumer_group}")
    logger.info("="*60)

    # Initialize processor with Redis for SSE
    processor = ThoughtProcessor(db, redis_client)

    # Startup scan: Republish any pending thoughts to Kafka
    # This handles thoughts that were created while workers were down
    await republish_pending_thoughts(db)

    # Define message handler
    async def handle_thought_event(event: ThoughtEvent) -> bool:
        """Handle incoming thought events from Kafka"""
        try:
            if event.event_type == EventType.THOUGHT_CREATED:
                logger.info(f"Processing thought from Kafka: {event.thought_id}")

                # Fetch thought from database
                thought = await db.get_thought(event.thought_id, event.user_id)

                if not thought:
                    logger.error(f"Thought not found in DB: {event.thought_id}")
                    return False

                # Fetch user context from users table
                user = await db.get_user(event.user_id)
                if user and user.get('context'):
                    thought['context'] = user['context']
                else:
                    thought['context'] = {}

                # Process thought with SSE updates
                success = await processor.process_single_thought(thought, publish_updates=True)

                return success
            else:
                logger.debug(f"Ignoring non-created event: {event.event_type}")
                return True  # Not an error, just not our concern

        except Exception as e:
            logger.error(f"Error handling Kafka event: {e}", exc_info=True)
            return False

    # Start Kafka consumer
    consumer = KafkaThoughtConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        consumer_group=settings.kafka_consumer_group
    )

    try:
        await consumer.start()
        await consumer.consume(handle_thought_event)
    except KeyboardInterrupt:
        logger.info("Kafka consumer interrupted by user")
    finally:
        await consumer.stop()


async def batch_mode(db: DatabaseAdapter):
    """
    Run as batch processor - processes pending thoughts from database
    Legacy mode (kept for backward compatibility)
    """
    continuous_mode = os.getenv('CONTINUOUS_MODE', 'false').lower() == 'true'

    processor = ThoughtProcessor(db, redis_client=None)  # No SSE in batch mode

    if continuous_mode:
        logger.info("Running in continuous batch mode - checking every 10 seconds")
        try:
            while True:
                await processor.run_batch()
                logger.info("Waiting 10 seconds before next check...")
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            logger.info("Continuous mode stopped by user")
    else:
        logger.info("Running in single-batch mode")
        await processor.run_batch()


async def main():
    """
    Entry point - detects mode (Kafka vs Batch) and runs accordingly
    """
    # Start Prometheus metrics server on port 8001
    try:
        start_http_server(8001)
        logger.info("Prometheus metrics server started on port 8001")
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")

    # Determine mode
    kafka_mode_enabled = settings.kafka_mode or settings.kafka_enabled

    if kafka_mode_enabled and KAFKA_AVAILABLE:
        logger.info("🚀 Starting in KAFKA STREAMING mode")
        ACTIVE_WORKERS.set(1)

        # Initialize database
        db = await DatabaseFactory.create_from_env(use_supabase=False)

        # Initialize Redis for SSE
        try:
            redis_client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await redis_client.ping()
            logger.info(f"Connected to Redis: {settings.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Continuing without Redis (SSE updates disabled)")
            redis_client = None

        try:
            await kafka_consumer_mode(db, redis_client)
        finally:
            await db.disconnect()
            if redis_client:
                await redis_client.close()

    else:
        if kafka_mode_enabled and not KAFKA_AVAILABLE:
            logger.warning(
                "Kafka mode requested but libraries not available. "
                "Falling back to batch mode. "
                "Install: pip install aiokafka redis aioredis"
            )

        logger.info("📋 Starting in BATCH mode (legacy)")

        # Initialize database
        db = await DatabaseFactory.create_from_env(use_supabase=False)

        try:
            await batch_mode(db)
        finally:
            await db.disconnect()


if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/batch_processor.log",
        rotation="10 MB",
        retention="30 days",
        level=settings.log_level
    )

    logger.info("Batch processor starting...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Batch processor interrupted by user")
    except Exception as e:
        logger.error(f"Batch processor crashed: {e}")
        raise
