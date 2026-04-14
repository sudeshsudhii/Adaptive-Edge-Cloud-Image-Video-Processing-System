# agent/profiler.py
"""System capability profiler — CPU, GPU, RAM, battery."""

from __future__ import annotations

import psutil

from backend.models import SystemProfile
from observability.logger import get_logger

logger = get_logger("profiler")


class SystemProfiler:
    """Captures a point-in-time snapshot of local hardware capabilities."""

    def snapshot(self) -> SystemProfile:
        cpu_freq = psutil.cpu_freq()
        freq_ghz = round((cpu_freq.current / 1000) if cpu_freq else 0.0, 2)

        battery = psutil.sensors_battery()
        battery_pct = int(battery.percent) if battery else -1  # -1 = no battery (desktop)

        gpu_available = False
        gpu_cores = 0
        gpu_vram_mb = 0

        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_available = True
                # GPUtil doesn't expose CUDA core count; use a default estimate
                gpu_cores = 1024
                gpu_vram_mb = int(gpu.memoryTotal)
                logger.info(f"GPU detected: {gpu.name}, VRAM={gpu_vram_mb} MB")
        except Exception:
            logger.info("No GPU detected or GPUtil unavailable")

        # Also try torch for better GPU info
        if not gpu_available:
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_available = True
                    props = torch.cuda.get_device_properties(0)
                    gpu_cores = props.multi_processor_count * 128  # approximate
                    gpu_vram_mb = props.total_mem // (1024 * 1024)
                    logger.info(f"GPU via torch: {props.name}, VRAM={gpu_vram_mb} MB")
            except Exception:
                pass

        mem = psutil.virtual_memory()

        profile = SystemProfile(
            cpu_cores=psutil.cpu_count(logical=True) or 4,
            cpu_freq=freq_ghz,
            gpu_available=gpu_available,
            gpu_cores=gpu_cores,
            gpu_vram_mb=gpu_vram_mb,
            ram_gb=round(mem.total / (1024 ** 3), 2),
            battery=battery_pct,
            cpu_load=round(psutil.cpu_percent(interval=0.5) / 100.0, 3),
        )
        logger.info(
            f"System profile: {profile.cpu_cores}C/{freq_ghz}GHz, "
            f"GPU={profile.gpu_available}, RAM={profile.ram_gb}GB, "
            f"Battery={profile.battery}%, Load={profile.cpu_load}"
        )
        return profile
