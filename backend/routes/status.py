# backend/routes/status.py
"""Task status polling endpoint."""

from fastapi import APIRouter, HTTPException, Depends

from backend.models import TaskState
from backend.security import require_auth
from orchestrator.state_manager import TaskStateManager

router = APIRouter(prefix="/status", tags=["status"])

_state_mgr = TaskStateManager()


@router.get("/{task_id}", response_model=TaskState)
async def get_task_status(
    task_id: str,
    _user: str = Depends(require_auth),
):
    """Poll the current state of a processing task."""
    state = _state_mgr.get(task_id)
    if not state:
        raise HTTPException(404, f"Task {task_id} not found")
    return state
