# backend/routes/health.py
"""Health-check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "edge-cloud-processor", "version": "2.0.0"}
