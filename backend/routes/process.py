# backend/routes/process.py
"""Processing submission endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent.network import NetworkProfiler
from agent.profiler import SystemProfiler
from backend.models import (
    ExecutionMode,
    InputSchema,
    ProcessingResponse,
    TaskPayload,
)
from backend.security import require_auth
from orchestrator.scheduler import TaskScheduler
from observability.logger import get_logger

logger = get_logger("route_process")
router = APIRouter(prefix="/process", tags=["processing"])

_scheduler = TaskScheduler()
_sys = SystemProfiler()
_net = NetworkProfiler()


@router.post("", response_model=ProcessingResponse, status_code=202)
async def submit_processing(
    input_schema: InputSchema,
    file_path: str,
    mode: str | None = None,
    priority: int = 5,
    _user: str = Depends(require_auth),
):
    """
    Submit a processing task.

    Returns immediately with a task_id (HTTP 202 Accepted).
    Poll GET /status/{task_id} for progress.
    """
    system_profile = _sys.snapshot()
    network_profile = _net.snapshot()

    requested_mode = None
    if mode:
        try:
            requested_mode = ExecutionMode(mode.upper())
        except ValueError:
            pass

    payload = TaskPayload(
        input_schema=input_schema,
        file_path=file_path,
        system_profile=system_profile,
        network_profile=network_profile,
        requested_mode=requested_mode,
        priority=priority,
    )

    response = _scheduler.submit(payload)
    logger.info(f"Task submitted: {response.task_id}")
    return response
