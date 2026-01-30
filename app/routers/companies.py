from fastapi import APIRouter, Depends

from ..deps import require_company_access
from ..schemas import CompanyOut

router = APIRouter(prefix="/companies/{company_id}", tags=["companies"])


@router.get("/info", response_model=CompanyOut)
def company_info(company=Depends(require_company_access)):
    """Owner/admin can view their company info (includes keys)."""
    return company
