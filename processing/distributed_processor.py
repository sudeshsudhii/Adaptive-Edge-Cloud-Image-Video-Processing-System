# processing/distributed_processor.py
"""
Ray-based distributed processing — called INSIDE Celery tasks.

Ray handles sub-task parallelism while Celery owns the lifecycle.
"""

from __future__ import annotations

from typing import List

import numpy as np

from backend.config import settings
from observability.logger import get_logger

logger = get_logger("distributed")

_ray = None
_RAY_AVAILABLE = False


def _ensure_ray():
    global _ray, _RAY_AVAILABLE
    if _ray is None:
        try:
            import ray
            _ray = ray
            if not _ray.is_initialized():
                _ray.init(
                    ignore_reinit_error=True,
                    num_cpus=settings.RAY_NUM_CPUS,
                    logging_level="warning",
                )
            _RAY_AVAILABLE = True
            logger.info(f"Ray initialised with {settings.RAY_NUM_CPUS} CPUs")
        except ImportError:
            _RAY_AVAILABLE = False
            logger.warning("Ray not available — distributed processing disabled")


def _process_chunk_local(chunk: np.ndarray, operation: str) -> np.ndarray:
    """Fallback when Ray is not available."""
    from processing.operations import apply_operation
    return apply_operation(chunk, operation)


def distributed_process(
    data_chunks: List[np.ndarray],
    operation: str,
) -> List[np.ndarray]:
    """
    Distribute processing across Ray workers.

    Falls back to sequential processing if Ray is unavailable.
    """
    _ensure_ray()

    if not _RAY_AVAILABLE or len(data_chunks) <= 2:
        logger.info(f"Processing {len(data_chunks)} chunks sequentially")
        return [_process_chunk_local(c, operation) for c in data_chunks]

    @_ray.remote
    def _ray_worker(chunk: np.ndarray, op: str) -> np.ndarray:
        import cv2
        import numpy as _np
        from processing.operations import apply_operation
        return apply_operation(chunk, op)

    futures = [_ray_worker.remote(c, operation) for c in data_chunks]
    results = _ray.get(futures)
    logger.info(f"Distributed: {len(data_chunks)} chunks processed via Ray")
    return results
