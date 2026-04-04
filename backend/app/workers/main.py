"""ARQ worker entrypoint."""

import asyncio
import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings
from app.workers.enrichment import enrich_item

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HANDLERS = {
    "enrich_item": enrich_item,
}


async def worker_loop():
    """Simple Redis-based worker loop.

    Pulls jobs from 'arq:queue' list and dispatches to handlers.
    """
    r = aioredis.from_url(settings.redis_url)
    logger.info("Daystrom worker started, waiting for jobs...")

    try:
        while True:
            # BLPOP blocks until a job is available (5s timeout for graceful shutdown checks)
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
