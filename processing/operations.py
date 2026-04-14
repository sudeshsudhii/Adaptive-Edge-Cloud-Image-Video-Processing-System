# processing/operations.py
"""
Concrete image / video operations using OpenCV + PIL.

Every function takes a numpy array and returns a numpy array.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import List

from observability.logger import get_logger

logger = get_logger("operations")


# ═══════════════════════════════════════════════════════════
#  IMAGE LOADING / SAVING
# ═══════════════════════════════════════════════════════════

def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {path}")
    return img


def save_image(img: np.ndarray, path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(path, img)
    return path


def get_image_info(path: str) -> dict:
    """Return resolution, size, and type metadata."""
    img = load_image(path)
    h, w = img.shape[:2]
    size_mb = Path(path).stat().st_size / (1024 * 1024)
    ext = Path(path).suffix.lower()
    is_video = ext in {".mp4", ".avi", ".mov", ".webm", ".mkv"}
    return {
        "width": w,
        "height": h,
        "channels": img.shape[2] if len(img.shape) == 3 else 1,
        "size_mb": round(size_mb, 3),
        "is_video": is_video,
    }


# ═══════════════════════════════════════════════════════════
#  VIDEO HELPERS
# ═══════════════════════════════════════════════════════════

def extract_frames(video_path: str, max_frames: int = 300) -> List[np.ndarray]:
    """Extract up to max_frames from a video file."""
    cap = cv2.VideoCapture(video_path)
    frames: List[np.ndarray] = []
    while cap.isOpened() and len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    logger.info(f"Extracted {len(frames)} frames from {video_path}")
    return frames


def frames_to_video(
    frames: List[np.ndarray],
    output_path: str,
    fps: float = 30.0,
) -> str:
    """Reassemble processed frames into a video."""
    if not frames:
        raise ValueError("No frames to write")
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    for f in frames:
        if len(f.shape) == 2:
            f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
        if f.shape[:2] != (h, w):
            f = cv2.resize(f, (w, h))
        writer.write(f)
    writer.release()
    logger.info(f"Wrote {len(frames)} frames → {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════
#  IMAGE OPERATIONS
# ═══════════════════════════════════════════════════════════

def resize_half(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)


def edge_detection(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return cv2.Canny(gray, 100, 200)


def gaussian_blur(img: np.ndarray, ksize: int = 15) -> np.ndarray:
    return cv2.GaussianBlur(img, (ksize, ksize), 0)


def sharpen(img: np.ndarray) -> np.ndarray:
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(img, -1, kernel)


def normalize_image(img: np.ndarray) -> np.ndarray:
    return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)


def grayscale(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


# ── Operation registry ───────────────────────────────────
OPERATIONS = {
    "resize_half": resize_half,
    "edge_detection": edge_detection,
    "blur": gaussian_blur,
    "sharpen": sharpen,
    "normalize": normalize_image,
    "grayscale": grayscale,
}


def apply_operation(img: np.ndarray, operation: str) -> np.ndarray:
    fn = OPERATIONS.get(operation)
    if fn is None:
        raise ValueError(f"Unknown operation: {operation}. Available: {list(OPERATIONS)}")
    return fn(img)
