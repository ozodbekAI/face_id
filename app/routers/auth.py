import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.auth import verify_password
from ..crud import (
    get_account_by_username,
    create_session,
    revoke_session,
    set_account_password,
)
from ..deps import require_account
from ..schemas import LoginRequest, TokenResponse, MeResponse, ChangePasswordRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, req: Request, db: Session = Depends(get_db)):
    acc = get_account_by_username(db, body.username)
    if not acc or not acc.is_active:
        raise HTTPException(401, "Invalid credentials")
    if not verify_password(body.password, acc.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token, exp = create_session(
        db,
        acc,
        user_agent=req.headers.get("user-agent"),
        ip=req.client.host if req.client else None,
    )

    return TokenResponse(
        access_token=token,
        expires_at=exp.astimezone(dt.timezone.utc).isoformat(),
        role=acc.role,
        company_id=acc.company_id,
    )


@router.get("/me", response_model=MeResponse)
def me(acc=Depends(require_account)):
    return MeResponse(
        id=acc.id,
        username=acc.username,
        role=acc.role,
        company_id=acc.company_id,
        is_active=bool(acc.is_active),
    )


@router.post("/logout")
def logout(acc=Depends(require_account), db: Session = Depends(get_db)):
    token = getattr(acc, "_raw_token", None)
    if token:
        revoke_session(db, token)
    return {"ok": True}


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, acc=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, acc.password_hash):
        raise HTTPException(400, "Old password is wrong")
    set_account_password(db, acc, body.new_password)
    return {"ok": True}
