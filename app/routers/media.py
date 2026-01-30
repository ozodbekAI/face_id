import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..core.config import settings
from ..core.db import SessionLocal
from ..crud import get_company_by_edge_key

router = APIRouter(tags=["media"])

@router.get("/media/{filename}")
def get_media(filename: str, edge_key: str = Query(...)):
    # only edge devices can download images (edge_key)
    db = SessionLocal()
    try:
        c = get_company_by_edge_key(db, edge_key)
        if not c:
            raise HTTPException(401, "Invalid edge key")
        path = os.path.join(settings.MEDIA_DIR, filename)
        if not os.path.exists(path):
            raise HTTPException(404, "Not found")
        return FileResponse(path)
    finally:
        db.close()
