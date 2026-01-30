import logging
import secrets

from fastapi import FastAPI

from .core.db import engine, Base, SessionLocal
from .core.logging_setup import setup_logging
from .core.config import settings
from .crud import ensure_bootstrap_admin
from .models import Account
from .routers import admin, users, ws, logs, events, hik_vision_push, companies
from .routers import auth

setup_logging()

app = FastAPI(title="FaceID Global Backend", swagger_ui_parameters={"persistAuthorization": True})

@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)

    # Bootstrap admin account (no register flow)
    db = SessionLocal()
    try:
        existing_admin = db.query(Account).filter(Account.role == "admin").first()
        if not existing_admin:
            pwd = settings.ROOT_ADMIN_PASSWORD
            if not pwd:
                pwd = secrets.token_urlsafe(12)
            ensure_bootstrap_admin(db, username=settings.ROOT_ADMIN_USERNAME, password=pwd)
            logging.getLogger("app").warning(
                "BOOTSTRAP ADMIN CREATED: username=%s password=%s (set ROOT_ADMIN_PASSWORD to control this)",
                settings.ROOT_ADMIN_USERNAME,
                pwd,
            )
    finally:
        db.close()

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(users.router)
app.include_router(ws.router)
app.include_router(logs.router)
app.include_router(events.router)
app.include_router(hik_vision_push.router)

@app.get("/health")
def health():
    return {"ok": True}
