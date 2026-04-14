# backend/config.py
"""Centralised, env-driven configuration with sensible defaults."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class _Settings:
    """Singleton settings read once from environment."""

    # ── Application ──
    APP_NAME: str = os.getenv("APP_NAME", "EdgeCloudProcessor")
    APP_VERSION: str = os.getenv("APP_VERSION", "2.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ── Server ──
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # ── Redis ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_STATE_DB: str = os.getenv("REDIS_STATE_DB", "redis://localhost:6379/1")
    REDIS_CACHE_DB: str = os.getenv("REDIS_CACHE_DB", "redis://localhost:6379/2")

    # ── Auth ──
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

    # ── Cloud ──
    CLOUD_MODE: str = os.getenv("CLOUD_MODE", "simulated")  # real | simulated
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "edgecloud-processing")
    AWS_EC2_INSTANCE_TYPE: str = os.getenv("AWS_EC2_INSTANCE_TYPE", "t3.micro")

    # ── Rate Limiting ──
    RATE_LIMIT_MAX: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # ── Uploads / Storage ──
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
    UPLOAD_DIR: Path = _PROJECT_ROOT / os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: Path = _PROJECT_ROOT / os.getenv("OUTPUT_DIR", "outputs")
    CHECKPOINT_DIR: Path = _PROJECT_ROOT / "checkpoints"

    # ── Processing ──
    LOCAL_WORKERS: int = int(os.getenv("LOCAL_WORKER_PROCESSES", "4"))
    GPU_SAFETY_FACTOR: float = float(os.getenv("GPU_MEMORY_SAFETY_FACTOR", "0.7"))
    RAY_NUM_CPUS: int = int(os.getenv("RAY_NUM_CPUS", "4"))

    # ── Energy model ──
    CPU_TDP_W: float = float(os.getenv("CPU_TDP_W", "65"))
    GPU_TDP_W: float = float(os.getenv("GPU_TDP_W", "150"))
    CPU_IDLE_W: float = float(os.getenv("CPU_IDLE_W", "10"))
    GPU_IDLE_W: float = float(os.getenv("GPU_IDLE_W", "15"))

    def ensure_dirs(self) -> None:
        """Create runtime directories if missing."""
        for d in (self.UPLOAD_DIR, self.OUTPUT_DIR, self.CHECKPOINT_DIR):
            d.mkdir(parents=True, exist_ok=True)


settings = _Settings()
settings.ensure_dirs()
