"""WebSocket connection manager with Redis pub/sub broadcasting"""
import json
import asyncio
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        # user_id -> set of active WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        # scan_id -> set of user_ids subscribed
        self._scan_subscribers: Dict[int, Set[int]] = {}
        self._lock = asyncio.Lock()

    @property
    def active_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        # accept() is called by the endpoint before connect() to allow sending close frames on auth failure
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user={user_id}, total={self.active_connections}")

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}, total={self.active_connections}")

    async def subscribe_scan(self, user_id: int, scan_id: int) -> None:
        async with self._lock:
            if scan_id not in self._scan_subscribers:
                self._scan_subscribers[scan_id] = set()
            self._scan_subscribers[scan_id].add(user_id)

    async def unsubscribe_scan(self, user_id: int, scan_id: int) -> None:
        async with self._lock:
            if scan_id in self._scan_subscribers:
                self._scan_subscribers[scan_id].discard(user_id)

    async def send_personal(self, user_id: int, message: dict) -> None:
        """Send message to a specific user's connections."""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        data = json.dumps(message)
        connections = self._connections.get(user_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_text(data)
            except Exception:
                await self.disconnect(ws, user_id)

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected users."""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        data = json.dumps(message)
        for user_id, connections in list(self._connections.items()):
            for ws in connections.copy():
                try:
                    await ws.send_text(data)
                except Exception:
                    await self.disconnect(ws, user_id)

    async def broadcast_to_scan(self, scan_id: int, message: dict) -> None:
        """Broadcast message to users subscribed to a specific scan."""
        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        subscribers = self._scan_subscribers.get(scan_id, set()).copy()
        for user_id in subscribers:
            await self.send_personal(user_id, message)

    async def send_scan_progress(
        self, scan_id: int, progress: int, status: str, details: Optional[str] = None
    ) -> None:
        await self.broadcast_to_scan(scan_id, {
            "type": "scan_progress",
            "payload": {
                "scan_id": scan_id,
                "progress": progress,
                "status": status,
                "details": details,
            },
        })

    async def send_scan_completed(self, scan_id: int, findings_count: int) -> None:
        await self.broadcast_to_scan(scan_id, {
            "type": "scan_completed",
            "payload": {
                "scan_id": scan_id,
                "findings_count": findings_count,
            },
        })

    async def send_new_finding(self, user_id: int, finding: dict) -> None:
        await self.send_personal(user_id, {
            "type": "finding_new",
            "payload": finding,
        })

    async def send_alert(self, user_id: int, title: str, message: str, severity: str = "info") -> None:
        await self.send_personal(user_id, {
            "type": "alert",
            "payload": {"title": title, "message": message, "severity": severity},
        })

    async def send_notification(self, user_id: int, title: str, message: str, severity: str = "info") -> None:
        await self.send_personal(user_id, {
            "type": "notification",
            "payload": {"title": title, "message": message, "severity": severity},
        })


# Singleton instance
ws_manager = ConnectionManager()
