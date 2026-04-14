# orchestrator/scheduler.py
"""
Task scheduler — submits TaskPayloads to the Celery queue
and creates the initial TaskState.
"""

from __future__ import annotations

from backend.models import ProcessingResponse, TaskPayload, TaskStatus
from orchestrator.state_manager import TaskStateManager
from orchestrator.tasks import process_task
from observability.logger import get_logger

logger = get_logger("scheduler")


class TaskScheduler:
    """Entry-point used by the backend to submit processing tasks."""

    def __init__(self) -> None:
        self.state_mgr = TaskStateManager()

    def submit(self, payload: TaskPayload) -> ProcessingResponse:
        """Create state record and enqueue the Celery task."""
        task_id = payload.task_id

        # Persist initial state
        self.state_mgr.create(task_id)

        # Enqueue
        process_task.apply_async(
            args=[payload.model_dump(mode="json")],
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
