import datetime as dt
import hashlib
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.db import SessionLocal
from ..crud import get_company_by_edge_key, get_company_by_api_key, pending_jobs_for_company
from ..models import ProvisionJob, User, EventLog
from ..ws_manager import manager
from ..utils import parse_employee_no

router = APIRouter(tags=["ws"])

async def _send_pending_jobs(db: Session, company_id: int):
    jobs = pending_jobs_for_company(db, company_id)
    for j in jobs:
        msg_type = {"create": "user.provision", "update": "user.update", "delete": "user.delete"}.get(j.job_type, "user.provision")
        await manager.send_to_edges(company_id, {"type": msg_type, "data": {"job_id": j.id, **j.payload}})
        j.status = "sent"
        db.add(j)
    db.commit()

@router.websocket("/ws/edge")
async def ws_edge(ws: WebSocket, edge_key: str = Query(...), company_id: int = Query(...)):
    await ws.accept()
    db = SessionLocal()
    try:
        c = get_company_by_edge_key(db, edge_key)
        if not c or c.id != company_id:
            await ws.close(code=4401)
            return

        await manager.add_edge(company_id, ws)
        await _send_pending_jobs(db, company_id)

        while True:
            msg = await ws.receive_json()
            typ = msg.get("type")
            data = msg.get("data") or {}

            if typ in ("user.provisioned", "user.updated", "user.deleted"):
                job_id = int(data.get("job_id"))
                status = data.get("status") or "ok"
                err = data.get("error")
                j = db.get(ProvisionJob, job_id)
                if j:
                    j.status = "acked" if status == "ok" else "failed"
                    j.error = err
                    db.add(j)
                    # update user status too
                    u = db.get(User, j.user_id)
                    if u:
                        u.status = "active" if status == "ok" and typ != "user.deleted" else ("deleted" if typ == "user.deleted" else "failed")
                        u.last_error = err
                        db.add(u)
                    db.commit()
                    await manager.broadcast_to_clients(company_id, {"type": "users.changed", "data": {"user_id": j.user_id, "status": u.status if u else None, "error": err}})

            elif typ == "event":
                # data must include employee_no like "19s2"
                employee_no = data.get("employee_no") or data.get("employeeNo") or ""
                parsed = parse_employee_no(employee_no)
                if not parsed:
                    # still log but without user mapping
                    event_id = data.get("event_id") or hashlib.sha256(str(data).encode()).hexdigest()[:32]
                    ev = EventLog(
                        event_id=event_id,
                        company_id=company_id,
                        user_id=None,
                        employee_no=employee_no or None,
                        device_id=data.get("device_id"),
                        event_type=data.get("event_type") or "unknown",
                        payload=data.get("payload") or {},
                        ts=dt.datetime.now(dt.timezone.utc),
                    )
                    db.add(ev)
                    db.commit()
                    await manager.broadcast_to_clients(company_id, {"type": "events.raw", "data": data})
                    continue

                c_id, u_id = parsed
                # trust employee_no company_id (must match socket company_id)
                if c_id != company_id:
                    continue

                event_id = data.get("event_id") or hashlib.sha256(str(data).encode()).hexdigest()[:32]
                if db.query(EventLog).filter(EventLog.event_id == event_id).first():
                    continue

                ev = EventLog(
                    event_id=event_id,
                    company_id=c_id,
                    user_id=u_id,
                    employee_no=employee_no,
                    device_id=data.get("device_id"),
                    event_type=data.get("event_type") or "access",
                    payload=data.get("payload") or {},
                    ts=dt.datetime.now(dt.timezone.utc),
                )
                db.add(ev)
                db.commit()

                # broadcast to company room (frontend)
                await manager.broadcast_to_clients(company_id, {
                    "type": "events.access",
                    "data": {
                        "company_id": c_id,
                        "user_id": u_id,
                        "employee_no": employee_no,
                        "device_id": data.get("device_id"),
                        "event_type": data.get("event_type") or "access",
                        "payload": data.get("payload") or {},
                    }
                })
            else:
                # ignore unknown
                pass

    except WebSocketDisconnect:
        pass
    finally:
        await manager.remove_edge(company_id, ws)
        db.close()


@router.websocket("/ws/company/{company_id}")
async def ws_company(ws: WebSocket, company_id: int, api_key: str = Query(...)):
    await ws.accept()
    db = SessionLocal()
    try:
        c = get_company_by_api_key(db, api_key)
        if not c or c.id != company_id:
            await ws.close(code=4401)
            return

        await manager.add_client(company_id, ws)

        while True:
            # keep alive; we don't expect client->server messages for now
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.remove_client(company_id, ws)
        db.close()
