"""Redis Pub/Sub broadcaster for cross-process WebSocket events.

When the application runs multiple workers (e.g. behind gunicorn),
local ConnectionManager only knows about connections on *this* worker.
The broadcaster publishes events to a Redis channel so every worker
can forward the message to its local connections.
"""
import json
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Channel name used in Redis Pub/Sub
CHANNEL = "redteam:ws:broadcast"


class RedisBroadcaster:
    """Publish / subscribe WebSocket events via Redis Pub/Sub."""

    def __init__(self):
        self._pubsub = None
        self._task: Optional[asyncio.Task] = None

    async def connect(self, redis_url: str) -> None:
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(CHANNEL)
            logger.info("Redis broadcaster connected")
        except Exception as exc:
            logger.warning(f"Redis broadcaster unavailable: {exc}")
            self._redis = None
            self._pubsub = None

    async def publish(self, message: dict) -> None:
        """Publish a message to all workers via Redis."""
        if self._redis is None:
            return
        try:
            await self._redis.publish(CHANNEL, json.dumps(message))
        except Exception as exc:
            logger.error(f"Redis publish error: {exc}")

    async def listen(self, callback) -> None:
        """Listen for messages from Redis and invoke callback.

        `callback` receives a parsed dict and should broadcast it
        to local WebSocket connections.
        """
        if self._pubsub is None:
            return
        try:
            async for raw_message in self._pubsub.listen():
                if raw_message["type"] == "message":
                    try:
                        data = json.loads(raw_message["data"])
                        await callback(data)
                    except Exception as exc:
                        logger.error(f"Broadcaster callback error: {exc}")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"Redis listen error: {exc}")

    async def start(self, redis_url: str, callback) -> None:
        """Connect and start listening in the background."""
        await self.connect(redis_url)
        if self._pubsub:
            self._task = asyncio.create_task(self.listen(callback))

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        if self._pubsub:
            await self._pubsub.unsubscribe(CHANNEL)
        if hasattr(self, '_redis') and self._redis:
            await self._redis.aclose()
        logger.info("Redis broadcaster stopped")


broadcaster = RedisBroadcaster()
