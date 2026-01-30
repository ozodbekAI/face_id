from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .core.db import get_db
from .crud import get_account_by_session_token, get_company
from .models import Account, Company


bearer_scheme = HTTPBearer()


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def require_account(
    db: Session = Depends(get_db),
    cred: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> Account:
    if not cred or not cred.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    if (cred.scheme or "").lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = cred.credentials.strip()
    acc = get_account_by_session_token(db, token)
    if not acc:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return acc


def require_admin(acc: Account = Depends(require_account)) -> Account:
    if acc.role != "admin":
        raise HTTPException(403, "Admin only")
    return acc


def require_owner(acc: Account = Depends(require_account)) -> Account:
    if acc.role != "owner":
        raise HTTPException(403, "Owner only")
    if not acc.company_id:
        raise HTTPException(403, "Owner must be bound to a company")
    return acc


def require_company_access(
    company_id: int,
    acc: Account = Depends(require_account),
    db: Session = Depends(get_db),
) -> Company:
    # admin -> any company
    if acc.role == "owner":
        if acc.company_id != company_id:
            raise HTTPException(403, "Wrong company")
    c = get_company(db, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return c
