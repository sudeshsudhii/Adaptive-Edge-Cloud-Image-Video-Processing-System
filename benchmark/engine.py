# benchmark/engine.py
"""
Benchmark Engine — instruments the EXECUTED mode only.

Collects latency, throughput, CPU/GPU usage, cost, and energy.
Caches results for later comparison.
"""

from __future__ import annotations

from typing import Optional

from backend.models import BenchmarkOutput, ExecutionMode, ProcessingResult, SystemProfile
from benchmark import metrics as bm
from benchmark.cache import BenchmarkCache
from agent.energy import EnergyEstimator
from observability.logger import get_logger

logger = get_logger("benchmark_engine")

_cache = BenchmarkCache()
_energy = EnergyEstimator()

# Cost-per-second by mode (USD)
_COST_RATES = {
    ExecutionMode.LOCAL: 0.0,
    ExecutionMode.CLOUD: 0.0000125,
    ExecutionMode.SPLIT: 0.0000063,
}


class BenchmarkEngine:
    """Collects post-execution metrics for the mode that actually ran."""

    def collect(
        self,
        task_id: str,
        mode: ExecutionMode,
        processing_result: ProcessingResult,
        system_profile: SystemProfile,
    ) -> BenchmarkOutput:
        cpu = bm.cpu_usage()
        gpu = bm.gpu_usage()
        latency = processing_result.processing_time_s

        cost = latency * _COST_RATES.get(mode, 0.0)
        energy = _energy.estimate_total(
            cpu_load=cpu,
            gpu_load=gpu,
            execution_time=latency,
            data_size_mb=0.0,
        )

        # speedup = estimated_local / actual
        local_est = self._estimate_local_time(system_profile, processing_result)
        speedup = local_est / max(latency, 0.001)
        throughput = 1.0 / max(latency, 0.001)

        benchmark = BenchmarkOutput(
            mode=mode,
            latency=round(latency, 4),
            throughput=round(throughput, 4),
            cpu_usage=round(cpu, 4),
            gpu_usage=round(gpu, 4),
            cost_usd=round(cost, 8),
            energy_j=round(energy, 2),
            speedup=round(speedup, 4),
        )
        _cache.store(task_id, benchmark)
        logger.info(
            f"Benchmark [{task_id}]: mode={mode.value} latency={latency:.3f}s "
            f"cost=${cost:.6f} energy={energy:.1f}J speedup={speedup:.2f}x"
        )
        return benchmark

    def get_cached(self, task_id: str) -> Optional[BenchmarkOutput]:
        return _cache.get(task_id)

    def get_all_cached(self) -> list[BenchmarkOutput]:
        return _cache.get_all()

    @staticmethod
    def _estimate_local_time(
        system: SystemProfile,
        result: ProcessingResult,
    ) -> float:
        cpu_factor = max(system.cpu_cores * system.cpu_freq, 1.0)
        return result.processing_time_s * (8.0 / cpu_factor)
