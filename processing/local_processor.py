# processing/local_processor.py
"""CPU-parallel processing using multiprocessing.Pool."""

from __future__ import annotations

import multiprocessing as mp
from typing import Callable, List, Optional

import numpy as np

from backend.config import settings
from processing.operations import apply_operation
from observability.logger import get_logger

logger = get_logger("local_processor")


def _worker(args: tuple) -> np.ndarray:
    """Standalone worker function (must be top-level for pickling)."""
    img, operation = args
    return apply_operation(img, operation)


class LocalProcessor:
    """Process images in parallel using a CPU process pool."""

    def __init__(self, num_workers: int = settings.LOCAL_WORKERS) -> None:
        self.num_workers = min(num_workers, mp.cpu_count() or 4)

    def process_batch(
        self,
        images: List[np.ndarray],
        operation: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[np.ndarray]:
        if not images:
            return []

        logger.info(
            f"LocalProcessor: {len(images)} images × '{operation}' "
            f"with {self.num_workers} workers"
        )
        args = [(img, operation) for img in images]

        results: List[np.ndarray] = []
        with mp.Pool(processes=self.num_workers) as pool:
            for i, result in enumerate(pool.imap(_worker, args)):
                results.append(result)
                if progress_callback and (i + 1) % max(1, len(images) // 10) == 0:
                    pct = ((i + 1) / len(images)) * 100
                    progress_callback(pct, f"local_batch_{i + 1}")

        logger.info(f"LocalProcessor: completed {len(results)} images")
        return results

    def process_single(self, img: np.ndarray, operation: str) -> np.ndarray:
        return apply_operation(img, operation)
