import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """Quản lý tất cả WebSocket connections, hỗ trợ broadcast theo node_id."""

    def __init__(self):
        self._lock = asyncio.Lock()
        # node_id -> set of websockets; key "all" = subscribe mọi node
        self._subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, subscribe_to: str = "all"):
        await ws.accept()
        async with self._lock:
            if subscribe_to not in self._subscriptions:
                self._subscriptions[subscribe_to] = set()
            self._subscriptions[subscribe_to].add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            for key in list(self._subscriptions.keys()):
                self._subscriptions[key].discard(ws)
                if not self._subscriptions[key]:
                    del self._subscriptions[key]

    async def subscribe(self, ws: WebSocket, node_id: str):
        async with self._lock:
            if node_id not in self._subscriptions:
                self._subscriptions[node_id] = set()
            self._subscriptions[node_id].add(ws)

    async def broadcast(self, node_id: int, message: dict):
        """Gửi message đến tất cả client đang subscribe node_id này hoặc 'all'."""
        payload = json.dumps(message, ensure_ascii=False, default=str)
        targets: Set[WebSocket] = set()

        async with self._lock:
            targets.update(self._subscriptions.get(str(node_id), set()))
            targets.update(self._subscriptions.get("all", set()))

        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)

        # Dọn connections đã chết
        if stale:
            async with self._lock:
                for ws in stale:
                    for key in list(self._subscriptions.keys()):
                        self._subscriptions[key].discard(ws)

    async def broadcast_all(self, message: dict):
        """Gửi đến MỌI client đang kết nối, bất kể subscribe gì."""
        payload = json.dumps(message, ensure_ascii=False, default=str)
        stale: list[WebSocket] = []

        async with self._lock:
            all_ws: Set[WebSocket] = set()
            for s in self._subscriptions.values():
                all_ws.update(s)

        for ws in all_ws:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    for key in list(self._subscriptions.keys()):
                        self._subscriptions[key].discard(ws)


ws_manager = WebSocketManager()
