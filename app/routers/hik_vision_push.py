from fastapi import APIRouter, Request, Response, Depends, HTTPException
import json, hashlib, datetime as dt
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..crud import get_company_by_edge_key
from ..models import EventLog, User
from ..ws_manager import manager

router = APIRouter(tags=["hikvision"])

def _find_employee_no(obj):
    if isinstance(obj, dict):
        if "employeeNoString" in obj and str(obj["employeeNoString"]).strip():
            return str(obj["employeeNoString"]).strip()
        for k, v in obj.items():
            if k in ("employeeNo", "cardNo", "cardID", "employeeID"):
                val = str(v).strip()
                if val and val != "0":
                    return val
            if isinstance(v, (dict, list)):
                r = _find_employee_no(v)
                if r:
                    return r
    if isinstance(obj, list):
        for it in obj:
            r = _find_employee_no(it)
            if r:
                return r
    return None

def _parse_ts(payload: dict) -> dt.datetime:
    ts = payload.get("dateTime")
    if not ts:
        acs = payload.get("AccessControllerEvent") or {}
        ts = acs.get("dateTime")
    if not ts:
        return dt.datetime.now(dt.timezone.utc)
    try:
        v = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if v.tzinfo is None:
            v = v.replace(tzinfo=dt.timezone.utc)
        return v.astimezone(dt.timezone.utc)
    except Exception:
        return dt.datetime.now(dt.timezone.utc)

@router.post("/hooks/hikvision/{edge_key}/acs_events")
async def hikvision_acs_events(edge_key: str, req: Request, db: Session = Depends(get_db)):
    company = get_company_by_edge_key(db, edge_key)
    if not company:
        raise HTTPException(404, "Unknown edge_key")

    raw = await req.body()
    ct = (req.headers.get("content-type") or "").lower()
    payload = None

    # 1) JSON yoki multipart parsing
    if "multipart" in ct or b"--MIME_boundary" in raw:
        parts = raw.split(b"--MIME_boundary")
        for part in parts:
            if b"Content-Type: application/json" in part:
                chunks = part.split(b"\r\n\r\n", 1)
                if len(chunks) == 2:
                    json_data = chunks[1].strip().rstrip(b"\r\n-")
                    payload = json.loads(json_data.decode("utf-8", errors="ignore"))
                    break
    elif "application/json" in ct:
        payload = json.loads(raw.decode("utf-8", errors="ignore"))

    if not isinstance(payload, dict):
        return Response(status_code=200)

    employee_no = None
    acs = payload.get("AccessControllerEvent") or {}
    employee_no = (acs.get("employeeNoString") or _find_employee_no(payload) or "").strip()

    ts_dt = _parse_ts(payload)

    # 2) user mapping
    user_id = None
    if employee_no:
        # Siz xohlaganingiz: employee_no = user_id (oddiy)
        if employee_no.isdigit():
            u = db.get(User, int(employee_no))
            if u and u.company_id == company.id:
                user_id = u.id
        else:
            # Backward compatible: user.employee_no bilan mapping
            u = db.query(User).filter(User.company_id == company.id, User.employee_no == employee_no).first()
            if u:
                user_id = u.id

    # 3) idempotency
    seed = {"c": company.id, "emp": employee_no, "ts": ts_dt.isoformat(), "p": payload}
    event_id = hashlib.sha256(str(seed).encode()).hexdigest()[:32]
    if db.query(EventLog).filter(EventLog.event_id == event_id).first():
        return Response(status_code=200)

    ev = EventLog(
        event_id=event_id,
        company_id=company.id,
        user_id=user_id,
        employee_no=employee_no or None,
        device_id=None,
        event_type="access",
        payload=payload,
        ts=ts_dt,
    )
    db.add(ev)
    db.commit()

    # realtime ws (frontend)
    await manager.broadcast_to_clients(company.id, {
        "type": "events.access",
        "data": {
            "company_id": company.id,
            "user_id": user_id,
            "employee_no": employee_no,
            "ts": ts_dt.isoformat(),
            "payload": payload,
        }
    })

    return Response(status_code=200)
