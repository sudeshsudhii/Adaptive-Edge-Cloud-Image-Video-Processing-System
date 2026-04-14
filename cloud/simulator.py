# cloud/simulator.py
"""
Simulated cloud provider — no real infrastructure required.

Adds realistic latency, cost, and jitter to mimic real cloud behaviour.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

import cv2
import numpy as np

from backend.config import settings
from backend.models import CloudResponse
from observability.logger import get_logger

logger = get_logger("cloud_sim")

# ── Simulated provider profiles ──────────────────────────
_PROFILES = {
    "aws": {"base_latency": 0.3, "cost_per_sec": 0.0000125, "avail": 0.999},
    "azure": {"base_latency": 0.35, "cost_per_sec": 0.0000130, "avail": 0.998},
    "gcp": {"base_latency": 0.28, "cost_per_sec": 0.0000120, "avail": 0.999},
}


class CloudSimulator:
    """Simulates cloud processing with realistic timing and cost."""

    def __init__(self, provider: str = "aws") -> None:
        self.provider = provider
        self.profile = _PROFILES.get(provider, _PROFILES["aws"])

    def process(self, input_path: str, operation: str) -> CloudResponse:
        """Simulate cloud processing: apply operation locally + add latency."""
        start = time.time()

        # Simulated network upload/download latency
        base = self.profile["base_latency"]
        jitter = random.uniform(-0.1, 0.2)
        sim_latency = max(0.05, base + jitter)
        time.sleep(sim_latency)

        # Actually perform the operation locally (to produce real output)
        output_path = self._do_work(input_path, operation)

        elapsed = time.time() - start
        cost = elapsed * self.profile["cost_per_sec"]

        logger.info(
            f"Cloud sim [{self.provider}]: {operation} "
            f"took {elapsed:.3f}s, cost=${cost:.6f}"
        )
        return CloudResponse(
            provider=f"simulated-{self.provider}",
            instance_id=f"sim-{random.randint(1000, 9999)}",
            processing_time_s=round(elapsed, 4),
            cost_usd=round(cost, 8),
            output_path=output_path,
        )

    def _do_work(self, input_path: str, operation: str) -> str:
        """Run the actual image operation locally as a stand-in for cloud."""
        try:
            img = cv2.imread(input_path)
            if img is None:
                # If not an image, just copy the file
                out = str(settings.OUTPUT_DIR / f"cloud_{Path(input_path).name}")
                import shutil
                shutil.copy2(input_path, out)
                return out

            if operation == "edge_detection":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                result = cv2.Canny(gray, 100, 200)
            elif operation == "blur":
                result = cv2.GaussianBlur(img, (15, 15), 0)
            elif operation == "resize_half":
                h, w = img.shape[:2]
                result = cv2.resize(img, (w // 2, h // 2))
            elif operation == "sharpen":
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                result = cv2.filter2D(img, -1, kernel)
            else:
                result = img

            out_path = str(
                settings.OUTPUT_DIR / f"cloud_{Path(input_path).stem}_{operation}.png"
            )
            cv2.imwrite(out_path, result)
            return out_path
        except Exception as exc:
            logger.error(f"Cloud sim work failed: {exc}")
            return input_path
