# cloud/autoscaler.py
"""Auto-scaling logic for cloud instances."""

from __future__ import annotations

import math

from decision.scorer import auto_scale_instances
from observability.logger import get_logger

logger = get_logger("autoscaler")


class AutoScaler:
    """
    Computes the required number of cloud instances.

    instances = ceil(total_workload / instance_capacity)

    instance_capacity is defined as the number of processing-units
    (e.g., image frames) a single instance can handle per second.
    """

    def __init__(self, instance_capacity: float = 30.0) -> None:
        self.instance_capacity = instance_capacity
        self.current_instances = 0

    def compute_desired(self, workload_units: float) -> int:
        desired = auto_scale_instances(workload_units, self.instance_capacity)
        desired = max(1, min(desired, 20))  # clamp [1, 20]
        logger.info(
            f"AutoScaler: workload={workload_units:.1f}, "
            f"capacity={self.instance_capacity}, desired={desired}"
        )
        return desired

    def should_scale(self, workload_units: float) -> tuple[str, int]:
        """Returns ('up'|'down'|'none', target_count)."""
        desired = self.compute_desired(workload_units)
        if desired > self.current_instances:
            return "up", desired
        elif desired < self.current_instances:
            return "down", desired
        return "none", desired
