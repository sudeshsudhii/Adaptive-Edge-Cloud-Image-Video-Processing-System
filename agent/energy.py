# agent/energy.py
"""
Multi-component energy estimation model.

E_total = E_cpu + E_gpu + E_network

    E_cpu     = (P_idle + utilisation × (TDP − P_idle)) × time
    E_gpu     = (P_idle_gpu + utilisation × (TDP_gpu − P_idle_gpu)) × time
    E_network = data_size_MB × J_per_MB
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings
from observability.logger import get_logger

logger = get_logger("energy")

NETWORK_J_PER_MB = 0.2  # WiFi estimate


@dataclass
class EnergyBreakdown:
    cpu_energy_j: float
    gpu_energy_j: float
    network_energy_j: float
    total_energy_j: float


class EnergyEstimator:
    """Configurable, physics-informed energy model."""

    def __init__(
        self,
        cpu_tdp: float = settings.CPU_TDP_W,
        gpu_tdp: float = settings.GPU_TDP_W,
        cpu_idle: float = settings.CPU_IDLE_W,
        gpu_idle: float = settings.GPU_IDLE_W,
    ) -> None:
        self.cpu_tdp = cpu_tdp
        self.gpu_tdp = gpu_tdp
        self.cpu_idle = cpu_idle
        self.gpu_idle = gpu_idle

    # ── Component estimates ───────────────────────────────
    def cpu_energy(self, load: float, time_s: float) -> float:
        power = self.cpu_idle + load * (self.cpu_tdp - self.cpu_idle)
        return power * time_s

    def gpu_energy(self, load: float, time_s: float) -> float:
        if load <= 0:
            return 0.0
        power = self.gpu_idle + load * (self.gpu_tdp - self.gpu_idle)
        return power * time_s

    @staticmethod
    def network_energy(data_mb: float) -> float:
        return data_mb * NETWORK_J_PER_MB

    # ── Aggregate ─────────────────────────────────────────
    def estimate_total(
        self,
        cpu_load: float,
        gpu_load: float,
        execution_time: float,
        data_size_mb: float = 0.0,
    ) -> float:
        return self.breakdown(
            cpu_load, gpu_load, execution_time, data_size_mb
        ).total_energy_j

    def breakdown(
        self,
        cpu_load: float,
        gpu_load: float,
        execution_time: float,
        data_size_mb: float = 0.0,
    ) -> EnergyBreakdown:
        e_cpu = self.cpu_energy(cpu_load, execution_time)
        e_gpu = self.gpu_energy(gpu_load, execution_time)
        e_net = self.network_energy(data_size_mb)
        total = e_cpu + e_gpu + e_net
        logger.debug(
            f"Energy breakdown: CPU={e_cpu:.2f}J GPU={e_gpu:.2f}J "
            f"Net={e_net:.2f}J Total={total:.2f}J"
        )
        return EnergyBreakdown(e_cpu, e_gpu, e_net, total)
