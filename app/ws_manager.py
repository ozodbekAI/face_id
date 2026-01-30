import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class CompanyWSManager:
    """WebSocket hub for frontend clients.

    Edge/local-device websocket support is intentionally removed.
    Your Hikvision devices push events directly to HTTP webhook, and
    the frontend listens here for realtime updates.
    """

    def __init__(self) -> None:
        self._clients: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def add_client(self, company_id: int, ws: WebSocket):
        async with self._lock:
            self._clients.setdefault(company_id, set()).add(ws)

    async def remove_client(self, company_id: int, ws: WebSocket):
        async with self._lock:
            self._clients.get(company_id, set()).discard(ws)

    async def broadcast_to_clients(self, company_id: int, msg: dict):
        clients = list(self._clients.get(company_id, set()))
        for ws in clients:
            try:
                await ws.send_json(msg)
            except Exception:
                pass


manager = CompanyWSManager()
