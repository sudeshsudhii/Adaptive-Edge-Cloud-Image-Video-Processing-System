@echo off
title Adaptive Edge-Cloud Processing System
color 0A
echo.
echo ============================================================
echo   Adaptive Edge-Cloud Image/Video Processing System v2.0
echo ============================================================
echo.

if not exist ".env" (
    echo [WARN] .env not found, copying from .env.example...
    copy .env.example .env >nul 2>&1
)

if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "checkpoints" mkdir checkpoints

where docker >nul 2>&1
if %errorlevel% equ 0 (
    echo [1/4] Docker found, starting Redis...
    docker-compose up -d redis
    timeout /t 3 /nobreak >nul

    echo [2/4] Starting Celery Worker...
    start "Celery Worker" cmd /k "cd /d %~dp0 && py -m celery -A orchestrator.tasks worker --loglevel=info --pool=solo -Q default"
    timeout /t 2 /nobreak >nul
) else (
    echo [1/4] Docker not found, using backend local executor mode...
    echo [2/4] Skipping Celery worker in local executor mode...
)

echo [3/4] Starting FastAPI Backend on port 8000...
start "FastAPI Backend" cmd /k "cd /d %~dp0 && py -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul

echo [4/4] Starting React Frontend on port 3000...
start "React Frontend" cmd /k "cd /d %~dp0\\frontend && set BROWSER=none && npm start"

echo.
echo ============================================================
echo   Services started
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ============================================================
echo.
pause
