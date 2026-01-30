import datetime as dt
import hashlib
import uuid
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.db import get_db
from ..deps import require_company
from ..models import EventLog, User
from ..schemas import EventCreateIn, EventOut, AttendanceDayOut
from ..utils import parse_employee_no
from ..ws_manager import manager


router = APIRouter(prefix="/companies/{company_id}", tags=["events"])


def _parse_ts(ts: str | None) -> dt.datetime:
    if not ts:
        return dt.datetime.now(dt.timezone.utc)
    try:
        v = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if v.tzinfo is None:
            v = v.replace(tzinfo=dt.timezone.utc)
        return v.astimezone(dt.timezone.utc)
    except Exception:
        return dt.datetime.now(dt.timezone.utc)


@router.post("/events", response_model=EventOut)
async def ingest_event(
    company_id: int,
    body: EventCreateIn,
    db: Session = Depends(get_db),
    company=Depends(require_company),
):
    """Edge/local backend sends access events here (HTTP)."""
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")

    employee_no = (body.employee_no or "").strip()
    if not employee_no:
        raise HTTPException(422, "employee_no required")

    parsed = parse_employee_no(employee_no)
    user_id = None
    if parsed:
        c_id, u_id = parsed
        if c_id != company_id:
            raise HTTPException(422, "employee_no company_id mismatch")
        # Make sure user exists in this company
        u = db.get(User, u_id)
        if not u or u.company_id != company_id:
            raise HTTPException(404, "User not found for employee_no")
        user_id = u_id

    ts_dt = _parse_ts(body.ts)

    # Idempotency: if device didn't provide event_id, derive a stable hash
    event_id = body.event_id
    if not event_id:
        seed = {
            "company_id": company_id,
            "employee_no": employee_no,
            "device_id": body.device_id,
            "event_type": body.event_type,
            "ts": ts_dt.isoformat(),
            "payload": body.payload,
        }
        event_id = hashlib.sha256(str(seed).encode()).hexdigest()[:32]

    existing = db.query(EventLog).filter(EventLog.event_id == event_id).first()
    if existing:
        return EventOut(
            id=existing.id,
            event_id=existing.event_id,
            company_id=existing.company_id,
            user_id=existing.user_id,
            employee_no=existing.employee_no,
            device_id=existing.device_id,
            event_type=existing.event_type,
            ts=existing.ts.astimezone(dt.timezone.utc).isoformat(),
        )

    ev = EventLog(
        event_id=event_id,
        company_id=company_id,
        user_id=user_id,
        employee_no=employee_no,
        device_id=body.device_id,
        event_type=body.event_type or "access",
        payload=body.payload or {},
        ts=ts_dt,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # Broadcast to company WS clients
    await manager.broadcast_to_clients(company_id, {
        "type": "events.access",
        "data": {
            "company_id": company_id,
            "user_id": user_id,
            "employee_no": employee_no,
            "device_id": body.device_id,
            "event_type": body.event_type or "access",
            "ts": ts_dt.isoformat(),
            "payload": body.payload or {},
        }
    })

    return EventOut(
        id=ev.id,
        event_id=ev.event_id,
        company_id=ev.company_id,
        user_id=ev.user_id,
        employee_no=ev.employee_no,
        device_id=ev.device_id,
        event_type=ev.event_type,
        ts=ev.ts.astimezone(dt.timezone.utc).isoformat(),
    )


@router.get("/users/{user_id}/attendance", response_model=AttendanceDayOut)
def attendance_day(
    company_id: int,
    user_id: int,
    date: str | None = Query(None, description="YYYY-MM-DD. Default=today in company timezone"),
    db: Session = Depends(get_db),
    company=Depends(require_company),
):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")

    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")

    try:
        tz = ZoneInfo(settings.COMPANY_TZ)
    except Exception:
        tz = dt.timezone.utc

    if date:
        d = dt.date.fromisoformat(date)
    else:
        d = dt.datetime.now(tz).date()

    start_local = dt.datetime.combine(d, dt.time.min).replace(tzinfo=tz)
    end_local = start_local + dt.timedelta(days=1)

    start_utc = start_local.astimezone(dt.timezone.utc)
    end_utc = end_local.astimezone(dt.timezone.utc)

    q = db.query(EventLog).filter(
        EventLog.company_id == company_id,
        EventLog.user_id == user_id,
        EventLog.ts >= start_utc,
        EventLog.ts < end_utc,
    )

    count = q.count()
    first = q.order_by(EventLog.ts.asc()).first()
    last = q.order_by(EventLog.ts.desc()).first() if count > 1 else None

    return AttendanceDayOut(
        company_id=company_id,
        user_id=user_id,
        date=d.isoformat(),
        first_in=first.ts.astimezone(tz).isoformat() if first else None,
        last_out=last.ts.astimezone(tz).isoformat() if last else None,
        events_count=count,
    )


@router.get("/users/{user_id}/events", response_model=list[EventOut])
def list_user_events(
    company_id: int,
    user_id: int,
    date: str | None = Query(None, description="YYYY-MM-DD (company timezone)"),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
    company=Depends(require_company),
):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")

    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")

    try:
        tz = ZoneInfo(settings.COMPANY_TZ)
    except Exception:
        tz = dt.timezone.utc

    q = db.query(EventLog).filter(EventLog.company_id == company_id, EventLog.user_id == user_id)
    if date:
        d = dt.date.fromisoformat(date)
        start_local = dt.datetime.combine(d, dt.time.min).replace(tzinfo=tz)
        end_local = start_local + dt.timedelta(days=1)
        q = q.filter(EventLog.ts >= start_local.astimezone(dt.timezone.utc), EventLog.ts < end_local.astimezone(dt.timezone.utc))

    xs = q.order_by(EventLog.ts.asc()).limit(limit).all()
    return [
        EventOut(
            id=e.id,
            event_id=e.event_id,
            company_id=e.company_id,
            user_id=e.user_id,
            employee_no=e.employee_no,
            device_id=e.device_id,
            event_type=e.event_type,
            ts=e.ts.astimezone(dt.timezone.utc).isoformat(),
        )
        for e in xs
    ]