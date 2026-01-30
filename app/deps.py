from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .core.db import get_db
from .crud import get_company_by_api_key

def require_company(x_api_key: str = Header(..., alias="X-API-Key"), db: Session = Depends(get_db)):
    c = get_company_by_api_key(db, x_api_key)
    if not c:
        raise HTTPException(401, "Invalid API key")
    return c
