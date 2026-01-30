import asyncio
from typing import Dict, Set
from fastapi import WebSocket

class CompanyWSManager:
    def __init__(self) -> None:
        self._edges: Dict[int, Set[WebSocket]] = {}
        self._clients: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def add_edge(self, company_id: int, ws: WebSocket):
        async with self._lock:
            self._edges.setdefault(company_id, set()).add(ws)

    async def remove_edge(self, company_id: int, ws: WebSocket):
        async with self._lock:
            self._edges.get(company_id, set()).discard(ws)

    async def add_client(self, company_id: int, ws: WebSocket):
        async with self._lock:
            self._clients.setdefault(company_id, set()).add(ws)

    async def remove_client(self, company_id: int, ws: WebSocket):
        async with self._lock:
            self._clients.get(company_id, set()).discard(ws)

    async def send_to_edges(self, company_id: int, msg: dict):
        edges = list(self._edges.get(company_id, set()))
        for ws in edges:
            try:
                await ws.send_json(msg)
            except Exception:
                pass

    async def broadcast_to_clients(self, company_id: int, msg: dict):
        clients = list(self._clients.get(company_id, set()))
        for ws in clients:
            try:
                await ws.send_json(msg)
            except Exception:
                pass

    def edge_connected(self, company_id: int) -> bool:
        return bool(self._edges.get(company_id))

manager = CompanyWSManager()
