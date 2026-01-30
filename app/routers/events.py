import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.db import get_db
from ..deps import require_owner
from ..models import EventLog, User
from ..schemas import EventOut, EventOutDetailed, EventPageOut, AttendanceRowOut, AttendancePageOut

router = APIRouter(prefix="/companies/{company_id}", tags=["events"])


def _parse_range(*, start: str | None, end: str | None, tz: dt.tzinfo) -> tuple[dt.datetime | None, dt.datetime | None]:
    """Parse a datetime/date range.

    - If value contains 'T' -> ISO datetime.
    - If value looks like YYYY-MM-DD -> interpreted as local date boundary in tz.
    Returns UTC datetimes.
    """

    def _parse_one(v: str | None, is_end: bool) -> dt.datetime | None:
        if not v:
            return None
        v = v.strip()
        try:
            if "T" in v:
                x = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
                if x.tzinfo is None:
                    x = x.replace(tzinfo=dt.timezone.utc)
                return x.astimezone(dt.timezone.utc)
            # date only
            d = dt.date.fromisoformat(v)
            base = dt.datetime.combine(d, dt.time.min).replace(tzinfo=tz)
            if is_end:
                base = base + dt.timedelta(days=1)
            return base.astimezone(dt.timezone.utc)
        except Exception:
            return None

    return _parse_one(start, False), _parse_one(end, True)


@router.get("/events", response_model=EventPageOut)
def list_events(
    company_id: int,
    user_id: int | None = Query(None),
    employee_no: str | None = Query(None),
    device_id: str | None = Query(None),
    event_type: str | None = Query(None),
    has_user: bool | None = Query(
        None,
        description="If true: only mapped events. If false: only unmapped events.",
    ),
    start: str | None = Query(None, description="ISO datetime or YYYY-MM-DD (company timezone)"),
    end: str | None = Query(None, description="ISO datetime or YYYY-MM-DD (company timezone)"),
    q: str | None = Query(None, description="Search in employee_no/device_id/event_type"),
    include_payload: bool = Query(False),
    sort: str = Query("-ts", description="ts,-ts,id,-id"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    company=Depends(require_owner),
):

    try:
        tz = ZoneInfo(settings.COMPANY_TZ)
    except Exception:
        tz = dt.timezone.utc

    start_utc, end_utc = _parse_range(start=start, end=end, tz=tz)

    qry = db.query(EventLog).filter(EventLog.company_id == company_id)
    if user_id is not None:
        qry = qry.filter(EventLog.user_id == user_id)
    if employee_no:
        qry = qry.filter(EventLog.employee_no == employee_no.strip())
    if device_id:
        qry = qry.filter(EventLog.device_id == device_id.strip())
    if event_type:
        qry = qry.filter(EventLog.event_type == event_type.strip())
    if has_user is not None:
        qry = qry.filter(EventLog.user_id.isnot(None)) if has_user else qry.filter(EventLog.user_id.is_(None))
    if start_utc:
        qry = qry.filter(EventLog.ts >= start_utc)
    if end_utc:
        qry = qry.filter(EventLog.ts < end_utc)
    if q:
        qq = f"%{q.strip().lower()}%"
        qry = qry.filter(
            func.lower(func.coalesce(EventLog.employee_no, "")).like(qq)
            | func.lower(func.coalesce(EventLog.device_id, "")).like(qq)
            | func.lower(func.coalesce(EventLog.event_type, "")).like(qq)
        )

    total = qry.count()

    if sort == "ts":
        qry = qry.order_by(EventLog.ts.asc())
    elif sort == "-ts":
        qry = qry.order_by(EventLog.ts.desc())
    elif sort == "id":
        qry = qry.order_by(EventLog.id.asc())
    else:
        qry = qry.order_by(EventLog.id.desc())

    xs = qry.offset((page - 1) * limit).limit(limit).all()

    if include_payload:
        items = [
            EventOutDetailed(
                id=e.id,
                event_id=e.event_id,
                company_id=e.company_id,
                user_id=e.user_id,
                employee_no=e.employee_no,
                device_id=e.device_id,
                event_type=e.event_type,
                ts=e.ts.astimezone(dt.timezone.utc).isoformat(),
                payload=e.payload or {},
            )
            for e in xs
        ]
    else:
        items = [
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

    return {"total": total, "items": items}


@router.get("/attendance/days", response_model=AttendancePageOut)
def attendance_days(
    company_id: int,
    start_date: str | None = Query(None, description="YYYY-MM-DD (company timezone). Default: last 7 days"),
    end_date: str | None = Query(None, description="YYYY-MM-DD (company timezone). Default: today"),
    user_id: int | None = Query(None),
    q: str | None = Query(None, description="Search users by name/phone"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    company=Depends(require_owner),
):
    try:
        tz = ZoneInfo(settings.COMPANY_TZ)
    except Exception:
        tz = dt.timezone.utc

    today = dt.datetime.now(tz).date()
    end_d = dt.date.fromisoformat(end_date) if end_date else today
    start_d = dt.date.fromisoformat(start_date) if start_date else (end_d - dt.timedelta(days=6))
    if start_d > end_d:
        start_d, end_d = end_d, start_d

    start_local = dt.datetime.combine(start_d, dt.time.min).replace(tzinfo=tz)
    end_local = dt.datetime.combine(end_d, dt.time.min).replace(tzinfo=tz) + dt.timedelta(days=1)
    start_utc = start_local.astimezone(dt.timezone.utc)
    end_utc = end_local.astimezone(dt.timezone.utc)

    # Optional user filter by query
    allowed_user_ids: set[int] | None = None
    if q:
        qq = f"%{q.strip().lower()}%"
        ids = (
            db.query(User.id)
            .filter(User.company_id == company_id)
            .filter(
                func.lower(User.first_name).like(qq)
                | func.lower(User.last_name).like(qq)
                | func.lower(func.coalesce(User.phone, "")).like(qq)
            )
            .all()
        )
        allowed_user_ids = {int(x[0]) for x in ids}
        if not allowed_user_ids:
            return {"total": 0, "items": []}

    if user_id is not None:
        allowed_user_ids = {user_id} if allowed_user_ids is None else (allowed_user_ids & {user_id})
        if not allowed_user_ids:
            return {"total": 0, "items": []}

    q_ev = (
        db.query(EventLog.user_id, EventLog.ts)
        .filter(
            EventLog.company_id == company_id,
            EventLog.user_id.isnot(None),
            EventLog.ts >= start_utc,
            EventLog.ts < end_utc,
        )
    )
    if allowed_user_ids is not None:
        q_ev = q_ev.filter(EventLog.user_id.in_(sorted(list(allowed_user_ids))))

    rows = q_ev.all()
    buckets: dict[tuple[int, str], dict[str, Any]] = {}

    for uid, ts in rows:
        if uid is None:
            continue
        ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)
        local = ts_utc.astimezone(tz)
        d = local.date().isoformat()
        key = (int(uid), d)
        b = buckets.get(key)
        if not b:
            buckets[key] = {"min": ts_utc, "max": ts_utc, "count": 1}
        else:
            b["count"] += 1
            if ts_utc < b["min"]:
                b["min"] = ts_utc
            if ts_utc > b["max"]:
                b["max"] = ts_utc

    if not buckets:
        return {"total": 0, "items": []}

    # Fetch user info
    user_ids = sorted({uid for (uid, _d) in buckets.keys()})
    users = db.query(User).filter(User.company_id == company_id, User.id.in_(user_ids)).all()
    umap = {u.id: u for u in users}

    items_all: list[AttendanceRowOut] = []
    for (uid, d), info in buckets.items():
        u = umap.get(uid)
        first_ts = info["min"]
        last_ts = info["max"]
        try:
            dur = int((last_ts - first_ts).total_seconds() // 60) if last_ts and first_ts else None
        except Exception:
            dur = None

        items_all.append(
            AttendanceRowOut(
                company_id=company_id,
                user_id=uid,
                date=d,
                first_in=first_ts.astimezone(tz).isoformat() if first_ts else None,
                last_out=last_ts.astimezone(tz).isoformat() if last_ts else None,
                duration_min=dur,
                events_count=int(info["count"]),
                first_name=u.first_name if u else None,
                last_name=u.last_name if u else None,
                phone=u.phone if u else None,
            )
        )

    # Sort: newest date first, then user_id
    items_all.sort(key=lambda x: (x.date, x.user_id), reverse=True)
    total = len(items_all)
    start_i = (page - 1) * limit
    end_i = start_i + limit
    return {"total": total, "items": items_all[start_i:end_i]}
