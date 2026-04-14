# orchestrator/queue_manager.py
"""Queue inspection and monitoring utilities."""

from __future__ import annotations

from observability.logger import get_logger

logger = get_logger("queue_manager")


class QueueManager:
    """Thin wrapper for inspecting the Celery/Redis task queue."""

    def __init__(self) -> None:
        self._redis = None
        try:
            import redis as _r
            from backend.config import settings
            self._redis = _r.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()
        except Exception:
            logger.warning("QueueManager: Redis unavailable")

    def queue_length(self, queue_name: str = "default") -> int:
        if self._redis:
            try:
                return self._redis.llen(queue_name) or 0
            except Exception:
                pass
        return 0

    def queue_info(self) -> dict:
        length = self.queue_length()
        return {
            "queue_name": "default",
            "pending_tasks": length,
            "redis_connected": self._redis is not None,
        }
