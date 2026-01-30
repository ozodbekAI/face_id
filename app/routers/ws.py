from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..core.db import SessionLocal
from ..crud import get_company_by_api_key, get_account_by_session_token
from ..ws_manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/company/{company_id}")
async def ws_company(
    ws: WebSocket,
    company_id: int,
    token: str | None = Query(None, description="Bearer token from /auth/login"),
    api_key: str | None = Query(None, description="Legacy: company api_key"),
):
    """Frontend realtime channel.

    Connect:
      - ws://HOST/ws/company/{company_id}?token=...   (recommended)
      - ws://HOST/ws/company/{company_id}?api_key=... (legacy)
    Server broadcasts events:
      - events.access
      - users.created / users.updated / users.deleted
    """
    await ws.accept()
    db = SessionLocal()
    try:
        if token:
            acc = get_account_by_session_token(db, token)
            if not acc:
                await ws.close(code=4401)
                return
            if acc.role == "owner" and acc.company_id != company_id:
                await ws.close(code=4403)
                return
        elif api_key:
            c = get_company_by_api_key(db, api_key)
            if not c or c.id != company_id:
                await ws.close(code=4401)
                return
        else:
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
