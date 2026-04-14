# storage/local_store.py
"""Local filesystem storage with organised directory structure."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from backend.config import settings
from observability.logger import get_logger

logger = get_logger("local_store")


class LocalStore:
    """Manages uploads, outputs, and checkpoints on the local filesystem."""

    def __init__(self) -> None:
        self.upload_dir = settings.UPLOAD_DIR
        self.output_dir = settings.OUTPUT_DIR
        self.checkpoint_dir = settings.CHECKPOINT_DIR
        for d in (self.upload_dir, self.output_dir, self.checkpoint_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_upload(self, filename: str, data: bytes) -> Path:
        dest = self.upload_dir / filename
        dest.write_bytes(data)
        logger.info(f"Saved upload: {dest} ({len(data)} bytes)")
        return dest

    def save_output(self, task_id: str, filename: str, data: bytes) -> Path:
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        dest = task_dir / filename
        dest.write_bytes(data)
        logger.info(f"Saved output: {dest}")
        return dest

    def save_checkpoint(self, task_id: str, stage: str, data: bytes) -> Path:
        task_dir = self.checkpoint_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        dest = task_dir / f"{stage}.dat"
        dest.write_bytes(data)
        logger.debug(f"Checkpoint saved: {dest}")
        return dest

    def load_checkpoint(self, task_id: str, stage: str) -> Optional[bytes]:
        path = self.checkpoint_dir / task_id / f"{stage}.dat"
        if path.exists():
            return path.read_bytes()
        return None

    def get_output_path(self, task_id: str) -> Path:
        return self.output_dir / task_id

    def cleanup_task(self, task_id: str) -> None:
        for base in (self.output_dir, self.checkpoint_dir):
            d = base / task_id
            if d.exists():
                shutil.rmtree(d)
                logger.info(f"Cleaned up: {d}")
