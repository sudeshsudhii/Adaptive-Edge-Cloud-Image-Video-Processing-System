# processing/gpu_processor.py
"""
Memory-safe GPU processing with PyTorch / CUDA.

Features:
    • Dynamic batch sizing based on available VRAM
    • Automatic OOM → CPU fallback
    • Device auto-selection (CUDA / CPU)
"""

from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np

from backend.config import settings
from observability.logger import get_logger

logger = get_logger("gpu_processor")

# ── Lazy torch import (allows system to run even without torch) ──
_torch = None
_TORCH_AVAILABLE = False

def _ensure_torch():
    global _torch, _TORCH_AVAILABLE
    if _torch is None:
        try:
            import torch
            _torch = torch
            _TORCH_AVAILABLE = True
        except ImportError:
            _TORCH_AVAILABLE = False


class GPUProcessor:
    """Batch-oriented, memory-safe GPU image processor."""

    def __init__(self) -> None:
        _ensure_torch()
        if _TORCH_AVAILABLE and _torch.cuda.is_available():
            self.device = _torch.device("cuda")
            self.gpu_available = True
            props = _torch.cuda.get_device_properties(0)
            self.gpu_name = props.name
            self.total_vram_mb = props.total_mem // (1024 * 1024)
            logger.info(f"GPU: {self.gpu_name}, VRAM={self.total_vram_mb} MB")
        else:
            self.device = _torch.device("cpu") if _TORCH_AVAILABLE else None
            self.gpu_available = False
            self.gpu_name = "CPU (fallback)"
            self.total_vram_mb = 0
            logger.warning("No CUDA GPU detected — using CPU fallback")

    # ── Public API ────────────────────────────────────────
    def process_batch(
        self,
        images: List[np.ndarray],
        operation: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[np.ndarray]:
        if not images:
            return []
        if not _TORCH_AVAILABLE:
            return self._cpu_fallback_batch(images, operation, progress_callback)

        sample_mb = images[0].nbytes / (1024 * 1024)
        batch_size = self._compute_batch_size(sample_mb)
        logger.info(
            f"GPU batch_size={batch_size} for {len(images)} images "
            f"({sample_mb:.1f} MB each) on {self.device}"
        )

        results: List[np.ndarray] = []
        total = len(images)

        for i in range(0, total, batch_size):
            batch = images[i : i + batch_size]
            try:
                batch_result = self._process_on_device(batch, operation)
                results.extend(batch_result)
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    logger.warning(f"GPU OOM at index {i}, falling back to CPU")
                    _torch.cuda.empty_cache()
                    results.extend(self._cpu_fallback_batch(batch, operation))
                else:
                    raise
            if progress_callback:
                pct = min(100.0, ((i + len(batch)) / total) * 100)
                progress_callback(pct, f"gpu_batch_{i // batch_size}")

        return results

    # ── Batch-size calculator ─────────────────────────────
    def _compute_batch_size(self, single_item_mb: float) -> int:
        if not self.gpu_available:
            import psutil
            avail_mb = psutil.virtual_memory().available / (1024 * 1024)
            return max(1, min(int(avail_mb * 0.4 / max(single_item_mb, 1)), 64))

        free_vram = (
            _torch.cuda.get_device_properties(0).total_mem
            - _torch.cuda.memory_allocated(0)
        ) // (1024 * 1024)
        usable = free_vram * settings.GPU_SAFETY_FACTOR
        return max(1, min(int(usable / max(single_item_mb * 4, 1)), 256))

    # ── GPU execution ─────────────────────────────────────
    def _process_on_device(
        self, images: List[np.ndarray], operation: str
    ) -> List[np.ndarray]:
        tensors = []
        for img in images:
            t = _torch.from_numpy(img.astype(np.float32))
            if len(t.shape) == 3:
                t = t.permute(2, 0, 1).unsqueeze(0)  # HWC → BCHW
            else:
                t = t.unsqueeze(0).unsqueeze(0)       # HW → B1HW
            tensors.append(t)
        batch = _torch.cat(tensors, dim=0).to(self.device)

        with _torch.no_grad():
            if operation == "edge_detection":
                output = self._sobel_edges(batch)
            elif operation == "blur":
                output = self._blur(batch)
            elif operation == "normalize":
                mn, mx = batch.min(), batch.max()
                output = (batch - mn) / (mx - mn + 1e-8) * 255
            elif operation == "resize_half":
                output = _torch.nn.functional.interpolate(
                    batch, scale_factor=0.5, mode="bilinear", align_corners=False
                )
            else:
                output = batch

        return self._tensors_to_numpy(output)

    def _sobel_edges(self, batch: "torch.Tensor") -> "torch.Tensor":
        # Convert to grayscale
        if batch.shape[1] == 3:
            gray = (
                0.299 * batch[:, 0:1]
                + 0.587 * batch[:, 1:2]
                + 0.114 * batch[:, 2:3]
            )
        else:
            gray = batch
        sx = _torch.tensor(
            [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
            dtype=_torch.float32, device=self.device,
        ).view(1, 1, 3, 3)
        sy = sx.permute(0, 1, 3, 2)
        gx = _torch.nn.functional.conv2d(gray, sx, padding=1)
        gy = _torch.nn.functional.conv2d(gray, sy, padding=1)
        return _torch.sqrt(gx ** 2 + gy ** 2)

    def _blur(self, batch: "torch.Tensor") -> "torch.Tensor":
        k = 5
        kernel = _torch.ones(1, 1, k, k, device=self.device) / (k * k)
        c = batch.shape[1]
        kernel = kernel.expand(c, 1, -1, -1)
        return _torch.nn.functional.conv2d(batch, kernel, padding=k // 2, groups=c)

    @staticmethod
    def _tensors_to_numpy(output: "torch.Tensor") -> List[np.ndarray]:
        arr = output.cpu().numpy()
        results = []
        for j in range(arr.shape[0]):
            img = arr[j]
            if img.shape[0] in (1, 3):
                img = img.transpose(1, 2, 0)
            if img.shape[-1] == 1:
                img = img.squeeze(-1)
            img = np.clip(img, 0, 255).astype(np.uint8)
            results.append(img)
        return results

    # ── CPU fallback ──────────────────────────────────────
    def _cpu_fallback_batch(
        self,
        images: List[np.ndarray],
        operation: str,
        progress_callback: Optional[Callable] = None,
    ) -> List[np.ndarray]:
        from processing.operations import apply_operation
        results = []
        for i, img in enumerate(images):
            results.append(apply_operation(img, operation))
            if progress_callback:
                progress_callback((i + 1) / len(images) * 100, f"cpu_fallback_{i}")
        return results
