# backend/security.py
"""JWT authentication, rate-limiting, and file-upload validation."""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import settings
from observability.logger import get_logger

logger = get_logger("security")

security_scheme = HTTPBearer(auto_error=False)

# ═══════════════════════════════════════════════════════════
#  JWT HELPERS
# ═══════════════════════════════════════════════════════════

# Demo users (production would use a DB)
_USERS = {
    "admin": hashlib.sha256(b"admin123").hexdigest(),
    "researcher": hashlib.sha256(b"research123").hexdigest(),
}


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> str:
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return data["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def authenticate_user(username: str, password: str) -> Optional[str]:
    hashed = hashlib.sha256(password.encode()).hexdigest()
    if _USERS.get(username) == hashed:
        return create_token(username)
    return None


# ═══════════════════════════════════════════════════════════
#  AUTH DEPENDENCY
# ═══════════════════════════════════════════════════════════

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> str:
    """FastAPI dependency — returns the authenticated username."""
    if not settings.AUTH_ENABLED:
        return "dev-user"
    if not credentials:
        raise HTTPException(401, "Missing authorization header")
    return verify_token(credentials.credentials)


# ═══════════════════════════════════════════════════════════
#  RATE LIMITER (token-bucket per IP)
# ═══════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(
        self,
        max_requests: int = settings.RATE_LIMIT_MAX,
        window: int = settings.RATE_LIMIT_WINDOW,
    ) -> None:
        self.max_requests = max_requests
        self.window = window
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, client_ip: str) -> bool:
        now = time.time()
        bucket = self._buckets[client_ip]
        self._buckets[client_ip] = [t for t in bucket if now - t < self.window]
        if len(self._buckets[client_ip]) >= self.max_requests:
            return False
        self._buckets[client_ip].append(now)
        return True


_rate_limiter = RateLimiter()


async def check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.check(ip):
        raise HTTPException(429, "Rate limit exceeded — try again later")


# ═══════════════════════════════════════════════════════════
#  FILE VALIDATION
# ═══════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff",
     ".mp4", ".avi", ".mov", ".webm", ".mkv"}
)


def validate_upload(filename: str, size_bytes: int) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed")
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            400,
            f"File size {size_mb:.1f} MB exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )
