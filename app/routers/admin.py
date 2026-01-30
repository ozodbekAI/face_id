from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..schemas import CompanyCreate, CompanyOut
from ..crud import create_company

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/companies", response_model=CompanyOut)
def admin_create_company(body: CompanyCreate, db: Session = Depends(get_db)):
    return create_company(db, body.name)
