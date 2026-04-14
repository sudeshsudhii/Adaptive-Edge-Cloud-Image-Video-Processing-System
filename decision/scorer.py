# decision/scorer.py
"""
Normalisation and scoring functions for the decision engine.

All scores are mapped to [0, 1].
"""

from __future__ import annotations

import math


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Clamp-normalise *value* into [0, 1]."""
    if max_val <= min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


# ═══════════════════════════════════════════════════════════
#  SYSTEM SCORE
# ═══════════════════════════════════════════════════════════

def system_score(
    cpu_cores: int,
    cpu_freq: float,
    gpu_cores: int,
    ram_gb: float,
    *,
    w_cpu: float = 0.40,
    w_gpu: float = 0.35,
    w_ram: float = 0.25,
) -> float:
    """
    S = w1·CPU_norm + w2·GPU_norm + w3·RAM_norm

    CPU_norm  = normalize(cores × freq_GHz,  0,  80)     # 16C × 5 GHz
    GPU_norm  = normalize(cuda_cores,         0,  10496)  # RTX 4090
    RAM_norm  = normalize(ram_gb,             0,  64)
    """
    cpu_n = normalize(cpu_cores * cpu_freq, 0.0, 80.0)
    gpu_n = normalize(gpu_cores, 0, 10496)
    ram_n = normalize(ram_gb, 0.0, 64.0)
    return w_cpu * cpu_n + w_gpu * gpu_n + w_ram * ram_n


# ═══════════════════════════════════════════════════════════
#  WORKLOAD COMPLEXITY
# ═══════════════════════════════════════════════════════════

def workload_complexity(width: int, height: int, frames: int) -> float:
    """
    C = normalize(W × H × F, 0, 3840 × 2160 × 1800)
    """
    max_c = 3840 * 2160 * 1800  # 4K@60fps, 30 s
    return normalize(width * height * frames, 0, max_c)


# ═══════════════════════════════════════════════════════════
#  NETWORK SCORE (higher = worse)
# ═══════════════════════════════════════════════════════════

def network_score(latency_ms: float, bandwidth_mbps: float) -> float:
    """
    N = normalize(latency_s + 1/bandwidth, 0, 2.0)
    """
    bw_inv = 1.0 / max(bandwidth_mbps, 0.1)
    raw = (latency_ms / 1000.0) + bw_inv
    return normalize(raw, 0.0, 2.0)


# ═══════════════════════════════════════════════════════════
#  CLOUD PROVIDER SCORE (lower = better)
# ═══════════════════════════════════════════════════════════

def cloud_provider_score(
    cost_norm: float,
    latency_norm: float,
    availability_norm: float,
) -> float:
    """Score = 0.4·cost + 0.4·latency − 0.2·availability"""
    return 0.4 * cost_norm + 0.4 * latency_norm - 0.2 * availability_norm


# ═══════════════════════════════════════════════════════════
#  AUTO-SCALING
# ═══════════════════════════════════════════════════════════

def auto_scale_instances(
    total_workload: float,
    instance_capacity: float,
) -> int:
    """instances = ceil(workload / capacity)"""
    return math.ceil(total_workload / max(instance_capacity, 1.0))
