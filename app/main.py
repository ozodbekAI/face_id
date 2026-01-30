from fastapi import FastAPI
from .core.db import engine, Base
from .core.logging_setup import setup_logging
from .routers import admin, users, ws, media, logs, events, hik_vision_push

setup_logging()

app = FastAPI(title="FaceID Global Backend")

@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)

app.include_router(admin.router)
app.include_router(users.router)
app.include_router(ws.router)
app.include_router(media.router)
app.include_router(logs.router)
app.include_router(events.router)
app.include_router(hik_vision_push.router)

@app.get("/health")
def health():
    return {"ok": True}
