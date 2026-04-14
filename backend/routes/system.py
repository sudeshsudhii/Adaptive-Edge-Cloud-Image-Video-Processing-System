# backend/routes/system.py
"""System profiling endpoints."""

from fastapi import APIRouter, Depends

from agent.profiler import SystemProfiler
from agent.network import NetworkProfiler
from backend.models import SystemProfile, NetworkProfile
from backend.security import require_auth

router = APIRouter(prefix="/system", tags=["system"])

_sys_profiler = SystemProfiler()
_net_profiler = NetworkProfiler()


@router.get("/profile", response_model=SystemProfile)
async def get_system_profile(_user: str = Depends(require_auth)):
    return _sys_profiler.snapshot()


@router.get("/network", response_model=NetworkProfile)
async def get_network_profile(_user: str = Depends(require_auth)):
    return _net_profiler.snapshot()


@router.get("/full")
async def get_full_profile(_user: str = Depends(require_auth)):
    return {
        "system": _sys_profiler.snapshot().model_dump(),
        "network": _net_profiler.snapshot().model_dump(),
    }
