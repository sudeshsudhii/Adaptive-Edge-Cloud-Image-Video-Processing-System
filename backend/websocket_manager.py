# backend/websocket_manager.py
"""WebSocket connection manager for real-time task updates."""

from __future__ import annotations

from typing import Dict, Set

from fastapi import WebSocket

from observability.logger import get_logger

logger = get_logger("websocket")


class WebSocketManager:
    """
    Manages per-task WebSocket subscriptions.

    Usage:
        await ws_manager.connect(ws, task_id)
        await ws_manager.send_task_update(task_id, {"status": "RUNNING"})
    """

    def __init__(self) -> None:
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        self._active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket, task_id: str | None = None) -> None:
        await ws.accept()
        self._active.add(ws)
        if task_id:
            self._subscriptions.setdefault(task_id, set()).add(ws)
        logger.info(f"WS connected (task={task_id}), total={len(self._active)}")

    async def disconnect(self, ws: WebSocket) -> None:
        self._active.discard(ws)
        for subs in self._subscriptions.values():
            subs.discard(ws)
        logger.info(f"WS disconnected, total={len(self._active)}")

    async def send_task_update(self, task_id: str, data: dict) -> None:
        subs = self._subscriptions.get(task_id, set())
        dead: set[WebSocket] = set()
        for ws in subs:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            subs.discard(ws)
            self._active.discard(ws)

    async def broadcast(self, data: dict) -> None:
        dead: set[WebSocket] = set()
        for ws in self._active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._active.discard(ws)


ws_manager = WebSocketManager()
