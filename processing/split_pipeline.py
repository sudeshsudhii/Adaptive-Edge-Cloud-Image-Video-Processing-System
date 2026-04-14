# processing/split_pipeline.py
"""
SPLIT (hybrid) pipeline — 4 stages:

    1. Preprocess   → LOCAL   (resize, normalise)
    2. Feature ext. → CLOUD   (edge detection / transforms)
    3. Heavy compute→ CLOUD   (inference / filtering)
    4. Post-process → LOCAL   (format conversion, save)

Checkpoints are saved after each stage for fault tolerance.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from backend.config import settings
from backend.models import CloudResponse
from cloud.manager import CloudManager
from processing.operations import (
    apply_operation, load_image, save_image,
    extract_frames, frames_to_video,
)
from storage.local_store import LocalStore
from observability.logger import get_logger

logger = get_logger("split_pipeline")


class SplitPipeline:
    """Four-stage hybrid LOCAL ↔ CLOUD pipeline with checkpointing."""

    STAGES = ["preprocess", "feature_extraction", "heavy_compute", "postprocess"]

    def __init__(self) -> None:
        self.cloud = CloudManager()
        self.store = LocalStore()

    def execute(
        self,
        task_id: str,
        file_path: str,
        operation: str = "edge_detection",
        is_video: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Run the full split pipeline; returns path to output file."""

        def _progress(pct: float, stage: str):
            if progress_callback:
                progress_callback(pct, stage)

        # ── Stage 1: Preprocess (LOCAL) ──
        _progress(5.0, "preprocess")
        logger.info(f"[{task_id}] Stage 1: preprocess (LOCAL)")

        if is_video:
            frames = extract_frames(file_path)
            frames = [cv2.resize(f, (f.shape[1] // 2, f.shape[0] // 2)) for f in frames]
            # Save checkpoint
            prep_path = str(settings.CHECKPOINT_DIR / task_id / "preprocessed.avi")
            Path(prep_path).parent.mkdir(parents=True, exist_ok=True)
            frames_to_video(frames, prep_path)
        else:
            img = load_image(file_path)
            img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2))
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
            prep_path = str(settings.CHECKPOINT_DIR / task_id / "preprocessed.png")
            save_image(img, prep_path)

        self.store.save_checkpoint(task_id, "preprocess", Path(prep_path).read_bytes())
        _progress(25.0, "preprocess_done")

        # ── Stage 2: Feature Extraction (CLOUD) ──
        _progress(30.0, "feature_extraction")
        logger.info(f"[{task_id}] Stage 2: feature extraction (CLOUD)")
        cloud_resp: CloudResponse = self.cloud.process(prep_path, "edge_detection")
        feat_path = cloud_resp.output_path or prep_path
        _progress(50.0, "feature_extraction_done")

        # ── Stage 3: Heavy Compute (CLOUD) ──
        _progress(55.0, "heavy_compute")
        logger.info(f"[{task_id}] Stage 3: heavy compute (CLOUD)")
        cloud_resp2: CloudResponse = self.cloud.process(feat_path, operation)
        compute_path = cloud_resp2.output_path or feat_path
        _progress(75.0, "heavy_compute_done")

        # ── Stage 4: Post-process (LOCAL) ──
        _progress(80.0, "postprocess")
        logger.info(f"[{task_id}] Stage 4: postprocess (LOCAL)")

        output_dir = settings.OUTPUT_DIR / task_id
        output_dir.mkdir(parents=True, exist_ok=True)

        if is_video:
            out_path = str(output_dir / "result.mp4")
            # Re-read the cloud output, apply final filter
            post_frames = extract_frames(compute_path)
            post_frames = [cv2.normalize(f, None, 0, 255, cv2.NORM_MINMAX) for f in post_frames]
            frames_to_video(post_frames, out_path)
        else:
            result_img = load_image(compute_path)
            result_img = cv2.normalize(result_img, None, 0, 255, cv2.NORM_MINMAX)
            out_path = str(output_dir / "result.png")
            save_image(result_img, out_path)

        _progress(100.0, "postprocess_done")
        logger.info(f"[{task_id}] Split pipeline complete → {out_path}")
        return out_path
