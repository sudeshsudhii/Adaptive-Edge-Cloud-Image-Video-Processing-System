# decision/engine.py
"""
Deterministic Decision Engine.

Selects LOCAL, CLOUD, or SPLIT based on system capability,
network conditions, energy constraints, and workload complexity.
"""

from __future__ import annotations

from backend.models import (
    DecisionResult,
    ExecutionMode,
    InputSchema,
    NetworkProfile,
    SystemProfile,
)
from decision.models import DecisionThresholds
from decision.scorer import network_score, system_score, workload_complexity
from agent.energy import EnergyEstimator
from observability.logger import get_logger

logger = get_logger("decision_engine")


class DecisionEngine:
    """Pure-function decision tree — no side effects, fully deterministic."""

    def __init__(self, thresholds: DecisionThresholds | None = None) -> None:
        self.t = thresholds or DecisionThresholds()
        self._energy = EnergyEstimator()

    def decide(
        self,
        system: SystemProfile,
        network: NetworkProfile,
        input_schema: InputSchema,
    ) -> DecisionResult:
        # ── Compute Scores ──
        s_score = system_score(
            system.cpu_cores, system.cpu_freq,
            system.gpu_cores, system.ram_gb,
        )
        n_score = network_score(network.latency_ms, network.bandwidth_mbps)
        c_score = workload_complexity(
            input_schema.resolution[0],
            input_schema.resolution[1],
            input_schema.frames,
        )

        # Estimate energy for local execution (rough)
        est_time = max(0.1, c_score * 10.0)  # heuristic seconds
        energy_est = self._energy.estimate_total(
            cpu_load=system.cpu_load,
            gpu_load=0.5 if system.gpu_available else 0.0,
            execution_time=est_time,
            data_size_mb=input_schema.size_mb,
        )

        # ── Decision Tree ──
        mode: ExecutionMode
        reasoning: str
        confidence: float

        if system.battery != -1 and system.battery < self.t.battery_low:
            mode = ExecutionMode.CLOUD
            reasoning = (
                f"Battery critically low ({system.battery}% < {self.t.battery_low}%)"
                " — offloading to cloud to preserve energy."
            )
            confidence = self.t.confidence_high

        elif n_score > self.t.network_bad:
            mode = ExecutionMode.LOCAL
            reasoning = (
                f"Network too poor (score={n_score:.2f} > {self.t.network_bad})"
                " — cloud would be unreliable; processing locally."
            )
            confidence = self.t.confidence_high

        elif s_score > self.t.system_strong and system.cpu_load < self.t.cpu_load_cap:
            mode = ExecutionMode.LOCAL
            reasoning = (
                f"System is powerful (S={s_score:.2f}) and load is low "
                f"({system.cpu_load:.0%} < {self.t.cpu_load_cap:.0%})"
                " — processing locally."
            )
            confidence = self.t.confidence_medium

        elif c_score > self.t.complexity_high and n_score < self.t.network_good:
            mode = ExecutionMode.SPLIT
            reasoning = (
                f"Workload is complex (C={c_score:.2f}) but network is good "
                f"(N={n_score:.2f}) — splitting pipeline: "
                "pre/post-processing locally, heavy compute on cloud."
            )
            confidence = self.t.confidence_medium

        else:
            mode = ExecutionMode.CLOUD
            reasoning = (
                f"Default cloud: S={s_score:.2f}, N={n_score:.2f}, "
                f"C={c_score:.2f} — delegating to cloud for best result."
            )
            confidence = self.t.confidence_low

        result = DecisionResult(
            mode=mode,
            system_score=round(s_score, 4),
            network_score=round(n_score, 4),
            complexity_score=round(c_score, 4),
            energy_estimate_j=round(energy_est, 2),
            reasoning=reasoning,
            confidence=confidence,
        )
        logger.info(
            f"Decision: {mode.value} | S={s_score:.3f} N={n_score:.3f} "
            f"C={c_score:.3f} | {reasoning}",
            extra={"mode": mode.value},
        )
        return result
