"""
WebSocket connection manager for broadcasting progress updates
to connected frontend clients.
"""

import asyncio
import json
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts progress events."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        """Send a JSON message to all connected clients."""
        dead: list[WebSocket] = []
        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for conn in dead:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)

    async def send_progress(
        self,
        step: str,
        percent: float,
        message: str = "",
        data: dict | None = None,
    ):
        """Convenience method for progress updates."""
        await self.broadcast({
            "type": "progress",
            "step": step,
            "percent": percent,
            "message": message,
            "data": data,
        })

    async def send_log(self, step: str, message: str):
        await self.broadcast({
            "type": "log",
            "step": step,
            "message": message,
        })

    async def send_error(self, step: str, message: str):
        await self.broadcast({
            "type": "error",
            "step": step,
            "message": message,
        })

    async def send_complete(self, step: str, message: str = "", data: dict | None = None):
        await self.broadcast({
            "type": "complete",
            "step": step,
            "percent": 100,
            "message": message,
            "data": data,
        })


# Singleton instance
manager = ConnectionManager()
