# backend/routes/upload.py
"""File upload endpoint with validation."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from backend.config import settings
from backend.security import require_auth, validate_upload
from observability.logger import get_logger

logger = get_logger("upload")
router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    _user: str = Depends(require_auth),
):
    """Upload an image or video file. Returns file metadata."""
    contents = await file.read()
    validate_upload(file.filename or "unknown", len(contents))

    # Generate unique filename
    ext = Path(file.filename or "file").suffix
    unique_name = f"{uuid.uuid4().hex[:10]}{ext}"
    dest = settings.UPLOAD_DIR / unique_name
    dest.write_bytes(contents)

    # Extract metadata
    size_mb = round(len(contents) / (1024 * 1024), 3)
    is_video = ext.lower() in {".mp4", ".avi", ".mov", ".webm", ".mkv"}

    width, height, frames = 0, 0, 1
    try:
        import cv2
        if is_video:
            cap = cv2.VideoCapture(str(dest))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
        else:
            img = cv2.imread(str(dest))
            if img is not None:
                height, width = img.shape[:2]
    except Exception as exc:
        logger.warning(f"Metadata extraction failed: {exc}")

    logger.info(f"Uploaded: {unique_name} ({size_mb} MB, {width}×{height})")

    return {
        "file_path": str(dest),
        "filename": unique_name,
        "file_type": "video" if is_video else "image",
        "resolution": [width, height],
        "frames": max(frames, 1),
        "size_mb": size_mb,
    }
