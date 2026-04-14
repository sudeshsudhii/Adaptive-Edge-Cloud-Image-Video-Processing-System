# processing/engine.py
"""
Main processing dispatcher.

Routes execution to the correct backend based on ExecutionMode:
    LOCAL → LocalProcessor (CPU pool) or GPUProcessor
    CLOUD → CloudManager
    SPLIT → SplitPipeline
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from backend.config import settings
from backend.models import ExecutionMode, ProcessingResult, TaskPayload
from cloud.manager import CloudManager
from processing.gpu_processor import GPUProcessor
from processing.local_processor import LocalProcessor
from processing.operations import (
    extract_frames,
    frames_to_video,
    load_image,
    save_image,
)
from processing.split_pipeline import SplitPipeline
from observability.logger import get_logger
from observability.error_tracker import error_tracker

logger = get_logger("processing_engine")


class ProcessingEngine:
    """Unified dispatcher — routes work to LOCAL, CLOUD, or SPLIT."""

    def __init__(self) -> None:
        self.local = LocalProcessor()
        self.gpu = GPUProcessor()
        self.cloud = CloudManager()
        self.split = SplitPipeline()

    def execute(
        self,
        mode: ExecutionMode,
        payload: TaskPayload,
        progress_callback: Optional[Callable] = None,
    ) -> ProcessingResult:
        start = time.time()
        task_id = payload.task_id
        file_path = payload.file_path
        is_video = payload.input_schema.file_type.value == "video"
        operation = "edge_detection"  # default operation

        try:
            if mode == ExecutionMode.LOCAL:
                output_path, stages = self._local(
                    task_id, file_path, operation, is_video, progress_callback
                )
            elif mode == ExecutionMode.CLOUD:
                output_path, stages = self._cloud(
                    task_id, file_path, operation, progress_callback
                )
            elif mode == ExecutionMode.SPLIT:
                output_path, stages = self._split(
                    task_id, file_path, operation, is_video, progress_callback
                )
            else:
                raise ValueError(f"Unknown mode: {mode}")

            elapsed = time.time() - start
            return ProcessingResult(
                task_id=task_id,
                mode_used=mode,
                output_path=output_path,
                processing_time_s=round(elapsed, 4),
                stages_completed=stages,
            )

        except Exception as exc:
            error_tracker.track("processing_engine", exc, task_id=task_id)
            elapsed = time.time() - start
            return ProcessingResult(
                task_id=task_id,
                mode_used=mode,
                output_path="",
                processing_time_s=round(elapsed, 4),
                stages_completed=[],
                error=str(exc),
            )

    # ── LOCAL ─────────────────────────────────────────────
    def _local(
        self,
        task_id: str,
        file_path: str,
        operation: str,
        is_video: bool,
        progress_callback: Optional[Callable],
    ) -> tuple[str, list[str]]:
        output_dir = settings.OUTPUT_DIR / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        stages: list[str] = []

        if is_video:
            frames = extract_frames(file_path)
            stages.append("frame_extraction")

            # Use GPU if available, else CPU pool
            if self.gpu.gpu_available:
                results = self.gpu.process_batch(frames, operation, progress_callback)
                stages.append("gpu_processing")
            else:
                results = self.local.process_batch(frames, operation, progress_callback)
                stages.append("cpu_processing")

            out_path = str(output_dir / "result.mp4")
            frames_to_video(results, out_path)
            stages.append("video_assembly")
        else:
            img = load_image(file_path)
            stages.append("image_load")

            if self.gpu.gpu_available:
                results = self.gpu.process_batch([img], operation, progress_callback)
                result_img = results[0]
                stages.append("gpu_processing")
            else:
                result_img = self.local.process_single(img, operation)
                stages.append("cpu_processing")

            out_path = str(output_dir / "result.png")
            save_image(result_img, out_path)
            stages.append("save")

        return out_path, stages

    # ── CLOUD ─────────────────────────────────────────────
    def _cloud(
        self,
        task_id: str,
        file_path: str,
        operation: str,
        progress_callback: Optional[Callable],
    ) -> tuple[str, list[str]]:
        if progress_callback:
            progress_callback(10.0, "uploading_to_cloud")

        workload = Path(file_path).stat().st_size / (1024 * 1024)
        resp = self.cloud.process(file_path, operation, workload_units=workload)

        output_path = resp.output_path or file_path
        if progress_callback:
            progress_callback(100.0, "cloud_complete")

        return output_path, ["cloud_upload", "cloud_processing", "cloud_download"]

    # ── SPLIT ─────────────────────────────────────────────
    def _split(
        self,
        task_id: str,
        file_path: str,
        operation: str,
        is_video: bool,
        progress_callback: Optional[Callable],
    ) -> tuple[str, list[str]]:
        out_path = self.split.execute(
            task_id, file_path, operation, is_video, progress_callback
        )
        return out_path, SplitPipeline.STAGES
