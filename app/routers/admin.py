from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..deps import require_admin
from ..schemas import CompanyCreate, CompanyOut, CompanyUpdate, CompanyPageOut
from ..crud import create_company, get_company, list_companies, update_company, delete_company

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/companies", response_model=CompanyOut, dependencies=[Depends(require_admin)])
def admin_create_company(body: CompanyCreate, db: Session = Depends(get_db)):
    return create_company(db, body.name)


@router.get("/companies", response_model=CompanyPageOut, dependencies=[Depends(require_admin)])
def admin_list_companies(
    q: str | None = Query(None, description="Search by company name"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total, items = list_companies(db, q=q, page=page, limit=limit)
    return {"total": total, "items": items}


@router.get("/companies/{company_id}", response_model=CompanyOut, dependencies=[Depends(require_admin)])
def admin_get_company(company_id: int, db: Session = Depends(get_db)):
    c = get_company(db, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


@router.put("/companies/{company_id}", response_model=CompanyOut, dependencies=[Depends(require_admin)])
def admin_update_company(company_id: int, body: CompanyUpdate, db: Session = Depends(get_db)):
    c = update_company(db, company_id, name=body.name, rotate_api_key=body.rotate_api_key, rotate_edge_key=body.rotate_edge_key)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


@router.delete("/companies/{company_id}", dependencies=[Depends(require_admin)])
def admin_delete_company(company_id: int, db: Session = Depends(get_db)):
    ok = delete_company(db, company_id)
    if not ok:
        raise HTTPException(404, "Company not found")
    return {"ok": True}
