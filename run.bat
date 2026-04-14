@echo off
title Adaptive Edge-Cloud Processing System
color 0A
echo.
echo ============================================================
echo   Adaptive Edge-Cloud Image/Video Processing System v2.0
echo ============================================================
echo.

:: Check for .env file
if not exist ".env" (
    echo [WARN] .env not found, copying from .env.example...
    copy .env.example .env >nul 2>&1
)

:: Create required directories
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "checkpoints" mkdir checkpoints

:: Check Redis
echo [1/4] Checking Redis...
docker ps --filter "name=edgecloud-redis" --format "{{.Names}}" | findstr /i "edgecloud-redis" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Starting Redis via Docker...
    docker-compose up -d redis
    timeout /t 3 /nobreak >nul
) else (
    echo       Redis is already running.
)

:: Start Celery Worker
echo [2/4] Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d %~dp0 && python -m celery -A orchestrator.tasks worker --loglevel=info --pool=solo -Q default"
timeout /t 2 /nobreak >nul

:: Start Backend
echo [3/4] Starting FastAPI Backend on port 8000...
start "FastAPI Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul

:: Start Frontend
echo [4/4] Starting React Frontend on port 3000...
start "React Frontend" cmd /k "cd /d %~dp0\frontend && npm start"

echo.
echo ============================================================
echo   All services started!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ============================================================
echo.
pause
