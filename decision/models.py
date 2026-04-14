# decision/models.py
"""Configurable thresholds for the decision engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DecisionThresholds:
    """Tuneable knobs for the deterministic decision tree."""

    battery_low: int = 30           # below this → CLOUD
    network_bad: float = 0.7        # N > this → LOCAL (network too poor for cloud)
    system_strong: float = 0.6      # S > this → LOCAL capable
    cpu_load_cap: float = 0.7       # cpu_load > this → offload
    complexity_high: float = 0.6    # C > this → needs heavy compute
    network_good: float = 0.3       # N < this → cloud is reachable

    # Confidence spread
    confidence_high: float = 0.92
    confidence_medium: float = 0.75
    confidence_low: float = 0.55
