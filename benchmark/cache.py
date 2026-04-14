# benchmark/cache.py
"""Benchmark result cache (Redis + in-memory fallback)."""

from __future__ import annotations

from typing import Optional

from backend.models import BenchmarkOutput
from observability.logger import get_logger

logger = get_logger("bench_cache")


class BenchmarkCache:
    """Two-tier cache: memory dict + optional Redis."""

    def __init__(self) -> None:
        self._memory: dict[str, str] = {}
        self._redis = None
        try:
            import redis as _redis_lib
            from backend.config import settings
            self._redis = _redis_lib.from_url(
                settings.REDIS_CACHE_DB, decode_responses=True
            )
            self._redis.ping()
            logger.info("BenchmarkCache: connected to Redis")
        except Exception:
            logger.info("BenchmarkCache: Redis unavailable, using memory only")

    def store(self, task_id: str, benchmark: BenchmarkOutput) -> None:
        data = benchmark.model_dump_json()
        self._memory[task_id] = data
        if self._redis:
            try:
                self._redis.setex(f"bench:{task_id}", 3600, data)
            except Exception:
                pass

    def get(self, task_id: str) -> Optional[BenchmarkOutput]:
        raw = self._memory.get(task_id)
        if not raw and self._redis:
            try:
                raw = self._redis.get(f"bench:{task_id}")
            except Exception:
                pass
        if raw:
            return BenchmarkOutput.model_validate_json(raw)
        return None

    def get_all(self) -> list[BenchmarkOutput]:
        results = []
        for raw in self._memory.values():
            try:
                results.append(BenchmarkOutput.model_validate_json(raw))
            except Exception:
                pass
        return results
