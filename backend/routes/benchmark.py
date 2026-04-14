# backend/routes/benchmark.py
"""Benchmark results endpoint."""

from fastapi import APIRouter, Depends

from backend.security import require_auth
from benchmark.engine import BenchmarkEngine
from benchmark.reporter import BenchmarkReporter

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

_engine = BenchmarkEngine()
_reporter = BenchmarkReporter()


@router.get("/{task_id}")
async def get_benchmark(
    task_id: str,
    _user: str = Depends(require_auth),
):
    """Get benchmark result for a specific task."""
    result = _engine.get_cached(task_id)
    if not result:
        return {"detail": f"No benchmark found for task {task_id}"}
    return result.model_dump()


@router.get("")
async def get_all_benchmarks(_user: str = Depends(require_auth)):
    """Get summary of all cached benchmarks."""
    all_b = _engine.get_all_cached()
    return _reporter.summary(all_b)
