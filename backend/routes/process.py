# backend/routes/process.py
"""Processing submission endpoint."""

from __future__ import annotations

import asyncio
import threading

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


def _prewarm():
    """Pre-warm caches in background so first request is fast."""
    try:
        _sys.snapshot()
        _net.snapshot()
    except Exception:
        pass
    # Pre-warm broker check so first submit is fast
    try:
        from orchestrator.scheduler import _check_broker
        _check_broker()
    except Exception:
        pass


# Pre-warm on module load (non-blocking background thread)
threading.Thread(target=_prewarm, daemon=True, name="profiler-prewarm").start()


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
    # Run both profilers concurrently in thread pool
    system_profile, network_profile = await asyncio.gather(
        asyncio.to_thread(_sys.snapshot),
        asyncio.to_thread(_net.snapshot),
    )

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

    response = await asyncio.to_thread(_scheduler.submit, payload)
    logger.info(f"Task submitted: {response.task_id}")
    return response

