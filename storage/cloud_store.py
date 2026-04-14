# storage/cloud_store.py
"""S3-compatible cloud object storage (real or simulated)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from backend.config import settings
from observability.logger import get_logger

logger = get_logger("cloud_store")


class CloudStore:
    """
    Thin wrapper around S3.
    When CLOUD_MODE=simulated, files are written to a local directory
    that masquerades as a bucket.
    """

    def __init__(self) -> None:
        self.mode = settings.CLOUD_MODE
        self._bucket = settings.AWS_S3_BUCKET
        self._client = None

        if self.mode == "real":
            try:
                import boto3
                self._client = boto3.client("s3", region_name=settings.AWS_REGION)
                logger.info(f"CloudStore: connected to S3 bucket={self._bucket}")
            except Exception as exc:
                logger.warning(f"S3 init failed ({exc}), falling back to simulated")
                self.mode = "simulated"

        if self.mode == "simulated":
            self._sim_root = settings.OUTPUT_DIR / "_cloud_sim"
            self._sim_root.mkdir(parents=True, exist_ok=True)
            logger.info(f"CloudStore: simulated mode → {self._sim_root}")

    def upload(self, local_path: str, key: str) -> str:
        if self.mode == "real" and self._client:
            self._client.upload_file(local_path, self._bucket, key)
            url = f"s3://{self._bucket}/{key}"
        else:
            dest = self._sim_root / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(local_path, dest)
            url = str(dest)
        logger.info(f"CloudStore upload: {key} → {url}")
        return url

    def download(self, key: str, local_path: str) -> str:
        if self.mode == "real" and self._client:
            self._client.download_file(self._bucket, key, local_path)
        else:
            src = self._sim_root / key
            import shutil
            shutil.copy2(src, local_path)
        logger.info(f"CloudStore download: {key} → {local_path}")
        return local_path

    def exists(self, key: str) -> bool:
        if self.mode == "real" and self._client:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False
        return (self._sim_root / key).exists()
