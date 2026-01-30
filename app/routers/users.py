from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..deps import require_company_access
from ..models import User, EventLog
from ..schemas import UserOut, UserPageOut, UserCreate, UserUpdate
from ..crud import create_user
from ..ws_manager import manager

router = APIRouter(prefix="/companies/{company_id}", tags=["users"])


def user_to_out(company, u: User) -> UserOut:
    return UserOut(
        id=u.id,
        company_id=u.company_id,
        first_name=u.first_name,
        last_name=u.last_name,
        phone=u.phone,
        employee_no=u.employee_no,
        enroll_code=str(u.employee_no or u.id),
        status=u.status,
        last_error=u.last_error,
    )


@router.post("/users", response_model=UserOut)
async def create_user_ep(
    company_id: int,
    body: UserCreate,
    db: Session = Depends(get_db),
    company=Depends(require_company_access),
):
    u = create_user(db, company, body.first_name, body.last_name, body.phone)

    out = user_to_out(company, u)
    await manager.broadcast_to_clients(company.id, {"type": "users.created", "data": out.model_dump()})
    return out


@router.get("/users/{user_id}", response_model=UserOut)
def get_user_ep(
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    company=Depends(require_company_access),
):
    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")
    return user_to_out(company, u)


@router.get("/users", response_model=UserPageOut)
def list_users_ep(
    company_id: int,
    q: str | None = Query(None, description="Search by name/phone/employee_no"),
    status: str | None = Query(None, description="pending|active|failed|deleted"),
    enrolled: bool | None = Query(None, description="Filter users that have at least one mapped event"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    company=Depends(require_company_access),
):

    qry = db.query(User).filter(User.company_id == company_id)
    if status:
        qry = qry.filter(User.status == status)
    if q:
        qq = f"%{q.strip().lower()}%"
        qry = qry.filter(
            func.lower(User.first_name).like(qq)
            | func.lower(User.last_name).like(qq)
            | func.lower(func.coalesce(User.phone, "")).like(qq)
            | func.lower(func.coalesce(User.employee_no, "")).like(qq)
        )
    if enrolled is not None:
        ex = db.query(EventLog.id).filter(EventLog.company_id == company_id, EventLog.user_id == User.id).exists()
        qry = qry.filter(ex) if enrolled else qry.filter(~ex)

    total = qry.count()
    xs = qry.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "items": [user_to_out(company, u) for u in xs]}


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user_ep(
    company_id: int,
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    company=Depends(require_company_access),
):
    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")

    fs = body.model_fields_set  # only update provided fields

    if "first_name" in fs:
        u.first_name = body.first_name  # type: ignore[assignment]
    if "last_name" in fs:
        u.last_name = body.last_name  # type: ignore[assignment]
    if "phone" in fs:
        u.phone = body.phone
    if "status" in fs and body.status is not None:
        u.status = body.status

    # any edit resets error unless you intentionally keep it
    u.last_error = None

    db.add(u)
    db.commit()
    db.refresh(u)

    out = user_to_out(company, u)
    await manager.broadcast_to_clients(company.id, {"type": "users.updated", "data": out.model_dump()})
    return out


@router.delete("/users/{user_id}")
async def delete_user_ep(
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    company=Depends(require_company_access),
):
    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")

    u.status = "deleted"
    db.add(u)
    db.commit()

    await manager.broadcast_to_clients(company.id, {"type": "users.deleted", "data": {"user_id": u.id}})
    return {"ok": True}
