# benchmark/metrics.py
"""Runtime metric collectors wrapping psutil / GPUtil."""

from __future__ import annotations

import psutil

from observability.logger import get_logger

logger = get_logger("bench_metrics")


def cpu_usage() -> float:
    """Return current CPU usage as a fraction [0, 1]."""
    return psutil.cpu_percent(interval=0.2) / 100.0


def gpu_usage() -> float:
    """Return current GPU load as a fraction [0, 1]."""
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].load
    except Exception:
        pass
    # Try torch
    try:
        import torch
        if torch.cuda.is_available():
            alloc = torch.cuda.memory_allocated(0)
            total = torch.cuda.get_device_properties(0).total_mem
            return alloc / total if total > 0 else 0.0
    except Exception:
        pass
    return 0.0


def memory_usage_pct() -> float:
    return psutil.virtual_memory().percent / 100.0
