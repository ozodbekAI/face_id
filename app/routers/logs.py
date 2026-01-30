import os

from fastapi import APIRouter, HTTPException, Query

from ..core.config import settings

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/tail")
def tail_log(
    name: str = Query("app.log", description="log file name"),
    lines: int = Query(200, ge=1, le=2000),
):
    if "/" in name or "\\" in name:
        raise HTTPException(400, "invalid log name")
    path = os.path.join(settings.LOG_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(404, "log not found")

    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        block = 4096
        data = b""
        while size > 0 and data.count(b"\n") <= lines:
            step = min(block, size)
            f.seek(-step, os.SEEK_CUR)
            data = f.read(step) + data
            f.seek(-step, os.SEEK_CUR)
            size -= step

    txt = data.decode("utf-8", errors="replace")
    xs = txt.splitlines()[-lines:]
    return {"name": name, "lines": xs}
