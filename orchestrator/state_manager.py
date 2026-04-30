# orchestrator/state_manager.py
"""
Redis-backed task state persistence with in-memory fallback.

Enforces legal state transitions:
    PENDING → RUNNING, FAILED
    RUNNING → COMPLETED, FAILED
    FAILED  → PENDING  (retry)
    COMPLETED → (terminal)
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Optional

from backend.models import (
    BenchmarkOutput,
    ExecutionMode,
    ProcessingResult,
    TaskState,
    TaskStatus,
)
from observability.logger import get_logger

logger = get_logger("state_manager")

_VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.FAILED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.FAILED: {TaskStatus.PENDING, TaskStatus.RUNNING},  # retry
    TaskStatus.COMPLETED: set(),                     # terminal
}


class TaskStateManager:
    """Tracks task lifecycle in Redis (db-1) with dict fallback."""

    KEY_PREFIX = "task:"
    TTL = 86400  # 24 h
    _shared_mem: dict[str, str] = {}
    _shared_lock = RLock()
    _redis_checked = False
    _shared_redis = None

    def __init__(self, redis_url: str | None = None) -> None:
        # Use cached Redis connection to avoid repeated slow connection attempts
        if TaskStateManager._redis_checked:
            self._redis = TaskStateManager._shared_redis
            return

        self._redis = None
        url = redis_url
        if url is None:
            from backend.config import settings
            url = settings.REDIS_STATE_DB

        try:
            import redis as _r
            self._redis = _r.from_url(
                url, decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            self._redis.ping()
            logger.info("TaskStateManager → Redis connected")
        except Exception:
            self._redis = None
            logger.warning("TaskStateManager → Redis unavailable, using memory")
        finally:
            TaskStateManager._shared_redis = self._redis
            TaskStateManager._redis_checked = True

    # ── helpers ───────────────────────────────────────────
    def _key(self, tid: str) -> str:
        return f"{self.KEY_PREFIX}{tid}"

    def _set(self, tid: str, raw: str) -> None:
        if self._redis:
            try:
                self._redis.setex(self._key(tid), self.TTL, raw)
                return
            except Exception:
                pass
        with self._shared_lock:
            self._shared_mem[tid] = raw

    def _get(self, tid: str) -> Optional[str]:
        if self._redis:
            try:
                val = self._redis.get(self._key(tid))
                if val:
                    return val
            except Exception:
                pass
        with self._shared_lock:
            return self._shared_mem.get(tid)

    # ── public API ────────────────────────────────────────
    def create(self, task_id: str) -> TaskState:
        state = TaskState(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self._set(task_id, state.model_dump_json())
        logger.info(f"Task created: {task_id}")
        return state

    def transition(self, task_id: str, new_status: TaskStatus, **kwargs) -> TaskState:
        raw = self._get(task_id)
        if not raw:
            raise ValueError(f"Task {task_id} not found in state store")

        state = TaskState.model_validate_json(raw)

        allowed = _VALID_TRANSITIONS.get(state.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Illegal transition: {state.status.value} → {new_status.value}"
            )

        state.status = new_status
        now = datetime.now(timezone.utc)
        if new_status == TaskStatus.RUNNING:
            state.started_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            state.completed_at = now

        for k, v in kwargs.items():
            if hasattr(state, k):
                setattr(state, k, v)

        self._set(task_id, state.model_dump_json())
        logger.info(f"Task {task_id} → {new_status.value}")
        return state

    def update_progress(self, task_id: str, pct: float, stage: str) -> None:
        raw = self._get(task_id)
        if not raw:
            return
        state = TaskState.model_validate_json(raw)
        state.progress_pct = pct
        state.current_stage = stage
        self._set(task_id, state.model_dump_json())

    def get(self, task_id: str) -> Optional[TaskState]:
        raw = self._get(task_id)
        return TaskState.model_validate_json(raw) if raw else None
