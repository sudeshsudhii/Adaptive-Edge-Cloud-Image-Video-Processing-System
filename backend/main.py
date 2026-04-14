# backend/main.py
"""
FastAPI application entry-point.

Wires together: CORS, auth middleware, rate limiting, routes,
WebSocket, metrics, and startup events.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.security import check_rate_limit
from backend.websocket_manager import ws_manager
from backend.routes import auth, benchmark, health, process, status, system, upload
from observability.logger import get_logger
from observability.metrics_collector import metrics
from observability.error_tracker import error_tracker

logger = get_logger("main")

# ═══════════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="Adaptive Edge-Cloud Processing API",
    version=settings.APP_VERSION,
    description=(
        "Intelligent image/video processing with dynamic LOCAL / CLOUD / SPLIT "
        "execution, auto-scaling, and real-time benchmarking."
    ),
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request middleware (logging + rate-limit) ─────────────
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    start = time.time()
    await check_rate_limit(request)
    response = await call_next(request)
    duration = time.time() - start
    metrics.observe("http_request_duration_s", duration)
    metrics.inc_counter(
        "http_requests_total",
        method=request.method,
        path=str(request.url.path),
    )
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} "
        f"({duration:.3f}s)"
    )
    return response


# ── Routes ────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(process.router)
app.include_router(status.router)
app.include_router(system.router)
app.include_router(benchmark.router)


# ── WebSocket ─────────────────────────────────────────────
@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await ws_manager.connect(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


# ── Metrics endpoint ──────────────────────────────────────
@app.get("/metrics", tags=["observability"])
async def get_metrics():
    return metrics.export()


# ── Error summary ─────────────────────────────────────────
@app.get("/errors", tags=["observability"])
async def get_errors():
    return error_tracker.get_summary()


# ── Startup ───────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    settings.ensure_dirs()
    logger.info(
        f"{settings.APP_NAME} v{settings.APP_VERSION} starting on "
        f"http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}"
    )


# ── Entrypoint ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
    )
