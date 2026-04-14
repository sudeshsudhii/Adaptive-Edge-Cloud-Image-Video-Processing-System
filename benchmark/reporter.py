# benchmark/reporter.py
"""Generates structured benchmark reports."""

from __future__ import annotations

from typing import List

from backend.models import BenchmarkOutput
from observability.logger import get_logger

logger = get_logger("bench_reporter")


class BenchmarkReporter:
    """Formats benchmark results for API responses and logging."""

    @staticmethod
    def summary(benchmarks: List[BenchmarkOutput]) -> dict:
        if not benchmarks:
            return {"count": 0}

        avg_latency = sum(b.latency for b in benchmarks) / len(benchmarks)
        avg_cost = sum(b.cost_usd for b in benchmarks) / len(benchmarks)
        avg_energy = sum(b.energy_j for b in benchmarks) / len(benchmarks)
        modes = {}
        for b in benchmarks:
            modes.setdefault(b.mode.value, []).append(b.latency)

        mode_summary = {
            m: {
                "count": len(lats),
                "avg_latency": round(sum(lats) / len(lats), 4),
            }
            for m, lats in modes.items()
        }

        return {
            "count": len(benchmarks),
            "avg_latency_s": round(avg_latency, 4),
            "avg_cost_usd": round(avg_cost, 8),
            "avg_energy_j": round(avg_energy, 2),
            "by_mode": mode_summary,
        }

    @staticmethod
    def to_table(benchmarks: List[BenchmarkOutput]) -> str:
        header = f"{'Mode':<8} {'Latency':<10} {'Throughput':<12} {'CPU%':<6} {'GPU%':<6} {'Cost($)':<10} {'Energy(J)':<10} {'Speedup':<8}"
        lines = [header, "-" * len(header)]
        for b in benchmarks:
            lines.append(
                f"{b.mode.value:<8} {b.latency:<10.4f} {b.throughput:<12.4f} "
                f"{b.cpu_usage:<6.1%} {b.gpu_usage:<6.1%} {b.cost_usd:<10.6f} "
                f"{b.energy_j:<10.2f} {b.speedup:<8.2f}"
            )
        return "\n".join(lines)
