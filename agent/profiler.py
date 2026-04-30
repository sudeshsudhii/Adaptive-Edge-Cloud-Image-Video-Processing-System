# agent/profiler.py
"""System capability profiler — CPU, GPU, RAM, battery."""

from __future__ import annotations

import time

import psutil

from backend.models import SystemProfile
from observability.logger import get_logger

logger = get_logger("profiler")

# ── Cached GPU detection (done once per process) ──
_GPU_CACHE: dict | None = None

def _detect_gpu_info() -> dict:
    """Probe GPU availability once, cache globally."""
    global _GPU_CACHE
    if _GPU_CACHE is not None:
        return _GPU_CACHE

    info = {"gpu_available": False, "gpu_cores": 0, "gpu_vram_mb": 0}

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            info["gpu_available"] = True
            info["gpu_cores"] = 1024  # GPUtil doesn't expose CUDA core count
            info["gpu_vram_mb"] = int(gpu.memoryTotal)
            logger.info(f"GPU detected: {gpu.name}, VRAM={info['gpu_vram_mb']} MB")
    except Exception:
        logger.info("No GPU detected or GPUtil unavailable")

    if not info["gpu_available"]:
        try:
            import torch
            if torch.cuda.is_available():
                info["gpu_available"] = True
                props = torch.cuda.get_device_properties(0)
                info["gpu_cores"] = props.multi_processor_count * 128
                info["gpu_vram_mb"] = props.total_mem // (1024 * 1024)
                logger.info(f"GPU via torch: {props.name}, VRAM={info['gpu_vram_mb']} MB")
        except Exception:
            pass

    _GPU_CACHE = info
    return info


# ── Snapshot cache TTL ──
_PROFILE_CACHE_TTL = 10.0  # seconds


class SystemProfiler:
    """Captures a point-in-time snapshot of local hardware capabilities."""

    # Class-level cache shared across all instances
    _cache: SystemProfile | None = None
    _cache_time: float = 0.0

    def __init__(self) -> None:
        pass

    def snapshot(self) -> SystemProfile:
        """Return cached profile if fresh, otherwise re-measure."""
        now = time.time()
        if SystemProfiler._cache is not None and (now - SystemProfiler._cache_time) < _PROFILE_CACHE_TTL:
            return SystemProfiler._cache

        cpu_freq = psutil.cpu_freq()
        freq_ghz = round((cpu_freq.current / 1000) if cpu_freq else 0.0, 2)

        battery = psutil.sensors_battery()
        battery_pct = int(battery.percent) if battery else -1  # -1 = no battery (desktop)

        gpu = _detect_gpu_info()

        mem = psutil.virtual_memory()

        profile = SystemProfile(
            cpu_cores=psutil.cpu_count(logical=True) or 4,
            cpu_freq=freq_ghz,
            gpu_available=gpu["gpu_available"],
            gpu_cores=gpu["gpu_cores"],
            gpu_vram_mb=gpu["gpu_vram_mb"],
            ram_gb=round(mem.total / (1024 ** 3), 2),
            battery=battery_pct,
            cpu_load=round(psutil.cpu_percent(interval=0) / 100.0, 3),
        )
        logger.info(
            f"System profile: {profile.cpu_cores}C/{freq_ghz}GHz, "
            f"GPU={profile.gpu_available}, RAM={profile.ram_gb}GB, "
            f"Battery={profile.battery}%, Load={profile.cpu_load}"
        )
        SystemProfiler._cache = profile
        SystemProfiler._cache_time = now
        return profile

