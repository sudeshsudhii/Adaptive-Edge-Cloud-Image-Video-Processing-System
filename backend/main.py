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
    allow_origins=[
        settings.FRONTEND_URL,
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request middleware (logging + rate-limit + latency targets) ──
_LATENCY_WARN_THRESHOLD = 0.5  # seconds — strict target

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
    log_fn = logger.info
    if duration > _LATENCY_WARN_THRESHOLD:
        log_fn = logger.warning
        metrics.inc_counter("http_slow_requests", path=str(request.url.path))
    log_fn(
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

# ── Static file serving for processed outputs ─────────────
app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="outputs")


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
    import asyncio
    settings.ensure_dirs()
    # Pre-warm broker check so first /process doesn't block on Redis timeout
    try:
        from orchestrator.scheduler import _check_broker
        await asyncio.to_thread(_check_broker)
    except Exception:
        pass
    # Pre-warm the asyncio default thread pool + profiler caches
    # This ensures the first /process call doesn't pay 300ms thread pool init cost
    try:
        from agent.profiler import SystemProfiler
        from agent.network import NetworkProfiler
        _sp, _np = SystemProfiler(), NetworkProfiler()
        await asyncio.gather(
            asyncio.to_thread(_sp.snapshot),
            asyncio.to_thread(_np.snapshot),
        )
    except Exception:
        pass
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
