"""
Main batch processor for nightly thought processing
Orchestrates the 5-agent pipeline with caching
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import defaultdict

from loguru import logger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from agents import AgentPipeline
from semantic_cache import SemanticCache
from common.database import DatabaseFactory
from common.database.base import DatabaseAdapter


class BatchThoughtProcessor:
    """
    Batch processor for analyzing pending thoughts
    Runs nightly via cron job
    """

    def __init__(self, db: DatabaseAdapter):
        # Initialize clients
        self.db = db
        self.agent_pipeline = AgentPipeline()
        self.semantic_cache = SemanticCache(self.db)

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
        """Save processing results to database"""
        try:
            update_data = {
                "status": "completed",
                "processed_at": datetime.utcnow(),
                "classification": result.get("classification"),
                "analysis": result.get("analysis"),
                "value_impact": result.get("value_impact"),
                "action_plan": result.get("action_plan"),
                "priority": result.get("priority")
            }

            if embedding:
                update_data["embedding"] = embedding

            await self.db.update_thought(thought_id, **update_data)

            logger.info(f"Saved results for thought {thought_id}")

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
        thought: Dict[str, Any]
    ) -> bool:
        """
        Process a single thought through the pipeline
        Returns True if successful, False otherwise
        """
        thought_id = thought["id"]
        thought_text = thought["text"]
        user_id = thought["user_id"]
        
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

            # Check semantic cache first
            cached_result = await self.semantic_cache.check_cache(
                thought_text,
                user_id
            )

            if cached_result:
                # Cache hit - use cached result
                result = cached_result
                self.stats["cache_hits"] += 1
                logger.info(f"Using cached result for thought {thought_id}")

            else:
                # Cache miss - process with AI
                self.stats["cache_misses"] += 1
                logger.info(f"Processing thought {thought_id} with AI pipeline")

                result = await self.agent_pipeline.process_thought(
                    thought_text,
                    user_context
                )

                # Save to semantic cache
                await self.semantic_cache.save_to_cache(
                    thought_text,
                    user_id,
                    result
                )

            # Get embedding for the thought (for semantic search later)
            embedding = await self.semantic_cache.get_embedding(thought_text)

            # Save results to database
            await self.save_results(thought_id, result, embedding)

            self.stats["processed"] += 1
            return True

        except Exception as e:
            logger.error(f"Failed to process thought {thought_id}: {e}")
            await self.mark_failed(thought_id, str(e))
            self.stats["failed"] += 1
            return False

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


async def main():
    """Entry point for batch processing"""
    continuous_mode = os.getenv('CONTINUOUS_MODE', 'false').lower() == 'true'
    
    db = await DatabaseFactory.create_from_env(use_supabase=False)
    processor = BatchThoughtProcessor(db)
    
    if continuous_mode:
        logger.info("Running in continuous mode - will check for new thoughts every 10 seconds")
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
