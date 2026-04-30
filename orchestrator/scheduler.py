"""Task scheduler with Celery enqueue and local fallback execution."""

from __future__ import annotations

import threading
import time

import redis

from backend.config import settings
from backend.models import ProcessingResponse, TaskPayload, TaskStatus
from observability.logger import get_logger
from orchestrator.state_manager import TaskStateManager
from orchestrator.tasks import process_task, run_processing_task

logger = get_logger("scheduler")

# ── Broker availability cache (module-level, shared) ──
_broker_checked = False
_broker_available_result = False
_broker_check_time = 0.0
_BROKER_CACHE_TTL = 300.0  # seconds (5 min — Redis availability rarely changes)


def _check_broker() -> bool:
    """Check if Redis broker is available, with 30s TTL cache."""
    global _broker_checked, _broker_available_result, _broker_check_time
    now = time.time()
    if _broker_checked and (now - _broker_check_time) < _BROKER_CACHE_TTL:
        return _broker_available_result
    try:
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
        client.ping()
        _broker_available_result = True
    except Exception:
        _broker_available_result = False
    finally:
        _broker_checked = True
        _broker_check_time = now
    return _broker_available_result


class TaskScheduler:
    """Entry-point used by the backend to submit processing tasks."""

    def __init__(self) -> None:
        self.state_mgr = TaskStateManager()

    @staticmethod
    def _run_local(task_id: str, payload_dict: dict) -> None:
        try:
            run_processing_task(payload_dict)
        except Exception as exc:
            logger.error(f"Local execution failed for {task_id}: {exc}")

    def submit(self, payload: TaskPayload) -> ProcessingResponse:
        """Create state record and enqueue the task or run it locally."""
        task_id = payload.task_id
        payload_dict = payload.model_dump(mode="json")

        self.state_mgr.create(task_id)

        if _check_broker():
            try:
                process_task.apply_async(
                    args=[payload_dict],
                    task_id=task_id,
                    queue="default",
                    priority=payload.priority,
                )
                logger.info(f"Scheduled task {task_id} (priority={payload.priority})")
                return ProcessingResponse(
                    task_id=task_id,
                    status=TaskStatus.PENDING,
                    message="Task submitted to processing queue",
                )
            except Exception as exc:
                logger.warning(
                    f"Queue submit failed for {task_id}, falling back to local mode: {exc}"
                )

        threading.Thread(
            target=self._run_local,
            args=(task_id, payload_dict),
            name=f"edgecloud-task-{task_id}",
            daemon=True,
        ).start()
        logger.info(f"Running task {task_id} in local in-process mode")
        return ProcessingResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Task submitted to local executor",
        )
