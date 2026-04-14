# observability/error_tracker.py
"""Centralized error aggregation and tracking."""

from __future__ import annotations

import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict

from observability.logger import get_logger

logger = get_logger("errors")


@dataclass
class TrackedError:
    timestamp: str
    module: str
    error_type: str
    message: str
    task_id: Optional[str] = None
    stack_trace: Optional[str] = None


class ErrorTracker:
    """Ring-buffer of recent errors with per-type counters."""

    def __init__(self, max_errors: int = 1000) -> None:
        self._errors: deque[TrackedError] = deque(maxlen=max_errors)
        self._counts: Dict[str, int] = {}

    def track(
        self,
        module: str,
        error: Exception,
        task_id: Optional[str] = None,
    ) -> None:
        err = TrackedError(
            timestamp=datetime.now(timezone.utc).isoformat(),
            module=module,
            error_type=type(error).__name__,
            message=str(error),
            task_id=task_id,
            stack_trace=traceback.format_exc(),
        )
        self._errors.append(err)
        key = f"{module}:{err.error_type}"
        self._counts[key] = self._counts.get(key, 0) + 1
        logger.error(
            f"[{module}] {err.error_type}: {err.message}",
            extra={"task_id": task_id, "error_type": err.error_type},
        )

    def get_recent(self, count: int = 20) -> List[dict]:
        return [
            {
                "timestamp": e.timestamp,
                "module": e.module,
                "error_type": e.error_type,
                "message": e.message,
                "task_id": e.task_id,
            }
            for e in list(self._errors)[-count:]
        ]

    def get_summary(self) -> dict:
        return {
            "total_errors": len(self._errors),
            "by_type": dict(self._counts),
            "recent": self.get_recent(5),
        }


# Module-level singleton
error_tracker = ErrorTracker()
