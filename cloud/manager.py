# cloud/manager.py
"""
Unified cloud manager — selects real (AWS) or simulated provider
based on CLOUD_MODE setting.
"""

from __future__ import annotations

from backend.config import settings
from backend.models import CloudResponse
from cloud.autoscaler import AutoScaler
from cloud.simulator import CloudSimulator
from observability.logger import get_logger
from observability.error_tracker import error_tracker

logger = get_logger("cloud_manager")


class CloudManager:
    """Single entry-point for all cloud operations."""

    def __init__(self) -> None:
        self.mode = settings.CLOUD_MODE
        self.autoscaler = AutoScaler()

        if self.mode == "real":
            try:
                from cloud.aws_provider import AWSProvider
                self._provider = AWSProvider()
                logger.info("CloudManager: using REAL AWS provider")
            except Exception as exc:
                logger.warning(f"AWS init failed ({exc}), falling back to simulator")
                self.mode = "simulated"
                self._provider = CloudSimulator()
        else:
            self._provider = CloudSimulator()
            logger.info("CloudManager: using SIMULATED provider")

    def process(
        self,
        input_path: str,
        operation: str = "edge_detection",
        workload_units: float = 1.0,
    ) -> CloudResponse:
        """
        Process input on the cloud.
        Handles auto-scaling and retries internally.
        """
        # Auto-scale check
        action, target = self.autoscaler.should_scale(workload_units)
        if action == "up":
            logger.info(f"Scaling up to {target} instances")
            if self.mode == "real":
                self._provider.scale_up(target)
            self.autoscaler.current_instances = target

        try:
            response = self._provider.process(input_path, operation)
            return response
        except Exception as exc:
            error_tracker.track("cloud_manager", exc)
            logger.error(f"Cloud processing failed: {exc}")
            raise
