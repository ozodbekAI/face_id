import secrets
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.db import get_db
from ..deps import require_admin
from ..schemas import (
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    CompanyPageOut,
    OwnerCreate,
    OwnerOut,
    OwnerCreatedResponse,
    OwnerPageOut,
)
from ..crud import (
    create_company,
    get_company,
    list_companies,
    update_company,
    delete_company,
    create_owner,
    set_account_password,
)
from ..models import Account

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/companies", response_model=CompanyOut)
def admin_create_company(body: CompanyCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    return create_company(db, body.name)


@router.get("/companies", response_model=CompanyPageOut)
def admin_list_companies(
    q: str | None = Query(None, description="Search by company name"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    total, items = list_companies(db, q=q, page=page, limit=limit)
    return {"total": total, "items": items}


@router.get("/companies/{company_id}", response_model=CompanyOut)
def admin_get_company(company_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = get_company(db, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


@router.put("/companies/{company_id}", response_model=CompanyOut)
def admin_update_company(company_id: int, body: CompanyUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = update_company(db, company_id, name=body.name, rotate_api_key=body.rotate_api_key, rotate_edge_key=body.rotate_edge_key)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


@router.delete("/companies/{company_id}")
def admin_delete_company(company_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    ok = delete_company(db, company_id)
    if not ok:
        raise HTTPException(404, "Company not found")
    return {"ok": True}


# ==========================
# Owners
# ==========================


def _owner_to_out(acc: Account) -> OwnerOut:
    return OwnerOut(
        id=acc.id,
        username=acc.username,
        role=acc.role,
        company_id=int(acc.company_id or 0),
        is_active=bool(acc.is_active),
        created_at=acc.created_at.astimezone(dt.timezone.utc).isoformat() if getattr(acc, "created_at", None) else None,
    )


@router.post("/owners", response_model=OwnerCreatedResponse)
def admin_create_owner(body: OwnerCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    # ensure company exists
    c = get_company(db, body.company_id)
    if not c:
        raise HTTPException(404, "Company not found")

    if db.query(Account).filter(Account.username == body.username).first():
        raise HTTPException(409, "Username already exists")

    pwd = body.password or secrets.token_urlsafe(12)
    acc = create_owner(db, username=body.username, password=pwd, company_id=body.company_id)
    out = _owner_to_out(acc)
    return OwnerCreatedResponse(**out.model_dump(), password=pwd)


@router.get("/owners", response_model=OwnerPageOut)
def admin_list_owners(
    company_id: int | None = Query(None),
    q: str | None = Query(None, description="Search by username"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    qry = db.query(Account).filter(Account.role == "owner")
    if company_id is not None:
        qry = qry.filter(Account.company_id == company_id)
    if q:
        qq = f"%{q.strip().lower()}%"
        qry = qry.filter(func.lower(Account.username).like(qq))
    total = qry.count()
    xs = qry.order_by(Account.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "items": [_owner_to_out(a) for a in xs]}


@router.get("/owners/{owner_id}", response_model=OwnerOut)
def admin_get_owner(owner_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    acc = db.get(Account, owner_id)
    if not acc or acc.role != "owner":
        raise HTTPException(404, "Owner not found")
    return _owner_to_out(acc)


@router.post("/owners/{owner_id}/reset-password", response_model=OwnerCreatedResponse)
def admin_reset_owner_password(owner_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    acc = db.get(Account, owner_id)
    if not acc or acc.role != "owner":
        raise HTTPException(404, "Owner not found")
    pwd = secrets.token_urlsafe(12)
    set_account_password(db, acc, pwd)
    out = _owner_to_out(acc)
    return OwnerCreatedResponse(**out.model_dump(), password=pwd)


@router.delete("/owners/{owner_id}")
def admin_delete_owner(owner_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    acc = db.get(Account, owner_id)
    if not acc or acc.role != "owner":
        raise HTTPException(404, "Owner not found")
    db.delete(acc)
    db.commit()
    return {"ok": True}
