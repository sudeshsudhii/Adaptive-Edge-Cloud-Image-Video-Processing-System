# orchestrator/queue_manager.py
"""Queue inspection and monitoring utilities."""

from __future__ import annotations

from observability.logger import get_logger

logger = get_logger("queue_manager")


class QueueManager:
    """Thin wrapper for inspecting the Celery/Redis task queue."""

    _redis_checked = False
    _shared_redis = None

    def __init__(self) -> None:
        if QueueManager._redis_checked:
            self._redis = QueueManager._shared_redis
            return

        self._redis = None
        try:
            import redis as _r
            from backend.config import settings
            self._redis = _r.from_url(
                settings.REDIS_URL, decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            self._redis.ping()
        except Exception:
            self._redis = None
            logger.warning("QueueManager: Redis unavailable")
        finally:
            QueueManager._shared_redis = self._redis
            QueueManager._redis_checked = True

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
