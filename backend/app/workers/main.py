"""ARQ worker entrypoint with scheduled learning sweep."""

import asyncio
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.core.config import settings
from app.workers.enrichment import enrich_item

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HANDLERS = {
    "enrich_item": enrich_item,
    "run_agent": None,  # Set below to avoid circular import
    "learning_sweep": None,  # Set below to avoid circular import
}

# Run the learning sweep once per day at 3 AM
LEARNING_SWEEP_HOUR = 3
_last_sweep_date: str | None = None


async def maybe_run_learning_sweep():
    """Check if it's time for the daily learning sweep."""
    global _last_sweep_date
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    if _last_sweep_date == today:
        return
    if now.hour != LEARNING_SWEEP_HOUR:
        return

    _last_sweep_date = today
    logger.info("Triggering daily learning sweep")
    try:
        from app.services.learning_service import run_learning_sweep
        await run_learning_sweep()
    except Exception as e:
        logger.error(f"Learning sweep failed: {e}", exc_info=True)


async def handle_learning_sweep(ctx: dict):
    """Manual trigger for learning sweep."""
    from app.services.learning_service import run_learning_sweep
    await run_learning_sweep()


async def handle_run_agent(ctx: dict, task_id: str):
    """Run an autonomous agent task."""
    from app.services.agent_service import run_agent
    await run_agent(ctx, task_id)


HANDLERS["run_agent"] = handle_run_agent
HANDLERS["learning_sweep"] = handle_learning_sweep


async def worker_loop():
    """Simple Redis-based worker loop.

    Pulls jobs from 'arq:queue' list and dispatches to handlers.
    Also checks for scheduled tasks between job processing.
    """
    r = aioredis.from_url(settings.redis_url)
    logger.info("Daystrom worker started, waiting for jobs...")

    try:
        while True:
            # Check scheduled tasks
            await maybe_run_learning_sweep()

            # BLPOP blocks until a job is available (5s timeout for scheduled task checks)
            result = await r.blpop("arq:queue", timeout=5)
            if result is None:
                continue

            _, raw = result
            try:
                job = json.loads(raw)
                func_name = job.get("function")
                args = job.get("args", [])

                handler = HANDLERS.get(func_name)
                if handler:
                    logger.info(f"Processing job: {func_name}({args})")
                    await handler({}, *args)
                else:
                    logger.warning(f"Unknown job function: {func_name}")

            except Exception as e:
                logger.error(f"Job failed: {e}", exc_info=True)

    except asyncio.CancelledError:
        logger.info("Worker shutting down")
    finally:
        await r.close()


if __name__ == "__main__":
    asyncio.run(worker_loop())
