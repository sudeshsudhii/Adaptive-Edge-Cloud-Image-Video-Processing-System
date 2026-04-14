# backend/routes/auth.py
"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException

from backend.models import LoginRequest, TokenResponse
from backend.security import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    token = authenticate_user(body.username, body.password)
    if not token:
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=token)
