from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..core.db import SessionLocal
from ..crud import get_company_by_api_key
from ..ws_manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/company/{company_id}")
async def ws_company(ws: WebSocket, company_id: int, api_key: str = Query(...)):
    """Frontend realtime channel.

    Connect: ws://HOST/ws/company/{company_id}?api_key=...
    Server broadcasts events:
      - events.access
      - users.created / users.updated / users.deleted
    """
    await ws.accept()
    db = SessionLocal()
    try:
        c = get_company_by_api_key(db, api_key)
        if not c or c.id != company_id:
            await ws.close(code=4401)
            return

        await manager.add_client(company_id, ws)

        while True:
            # We don't require client->server messages. Just keep the socket open.
            await ws.receive_text()

    except WebSocketDisconnect:
        pass
    finally:
        await manager.remove_client(company_id, ws)
        db.close()
