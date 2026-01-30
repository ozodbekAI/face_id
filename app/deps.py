from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .core.db import get_db
from .core.config import settings
from .crud import get_company_by_api_key

def require_company(x_api_key: str = Header(..., alias="X-API-Key"), db: Session = Depends(get_db)):
    c = get_company_by_api_key(db, x_api_key)
    if not c:
        raise HTTPException(401, "Invalid API key")
    return c


def require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")):
    """Protect /admin endpoints.

    If settings.ADMIN_KEY is empty, admin endpoints are open (useful for local/dev).
    """
    if settings.ADMIN_KEY and x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(401, "Invalid admin key")
    return True
