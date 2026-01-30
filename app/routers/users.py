from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..deps import require_company
from ..models import User
from ..schemas import UserOut
from ..crud import save_upload, create_user, create_job, make_image_url
from ..ws_manager import manager

router = APIRouter(prefix="/companies/{company_id}", tags=["users"])

def user_to_out(company, u: User) -> UserOut:
    image_url = make_image_url(company, u.image_filename) if u.image_filename else None
    return UserOut(
        id=u.id,
        company_id=u.company_id,
        first_name=u.first_name,
        last_name=u.last_name,
        phone=u.phone,
        employee_no=u.employee_no,
        image_url=image_url,
        status=u.status,
        last_error=u.last_error,
    )

@router.post("/users", response_model=UserOut)
async def create_user_ep(
    company_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    company = Depends(require_company),
):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")

    image_filename = save_upload(image) if image else None
    u = create_user(db, company, first_name, last_name, phone, image_filename)

    payload = {
        "company_id": company.id,
        "user_id": u.id,
        "employee_no": u.employee_no,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "image_url": make_image_url(company, u.image_filename) if u.image_filename else None,
    }
    job = create_job(db, company.id, u.id, "create", u.employee_no, payload)

    # try push to edge immediately
    if manager.edge_connected(company.id):
        await manager.send_to_edges(company.id, {"type": "user.provision", "data": {"job_id": job.id, **payload}})
        # mark sent
        job.status = "sent"
        db.add(job)
        db.commit()

    return user_to_out(company, u)

@router.get("/users/{user_id}", response_model=UserOut)
def get_user_ep(company_id: int, user_id: int, db: Session = Depends(get_db), company=Depends(require_company)):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")
    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")
    return user_to_out(company, u)

@router.get("/users", response_model=list[UserOut])
def list_users_ep(company_id: int, db: Session = Depends(get_db), company=Depends(require_company)):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")
    xs = db.query(User).filter(User.company_id == company_id).order_by(User.id.desc()).all()
    return [user_to_out(company, u) for u in xs]

@router.put("/users/{user_id}", response_model=UserOut)
async def update_user_ep(
    company_id: int,
    user_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    company=Depends(require_company),
):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")
    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")

    if image:
        u.image_filename = save_upload(image)
    u.first_name = first_name
    u.last_name = last_name
    u.phone = phone
    u.status = "pending"
    u.last_error = None
    db.add(u)
    db.commit()
    db.refresh(u)

    payload = {
        "company_id": company.id,
        "user_id": u.id,
        "employee_no": u.employee_no,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "image_url": make_image_url(company, u.image_filename) if u.image_filename else None,
    }
    job = create_job(db, company.id, u.id, "update", u.employee_no, payload)

    if manager.edge_connected(company.id):
        await manager.send_to_edges(company.id, {"type": "user.update", "data": {"job_id": job.id, **payload}})
        job.status = "sent"
        db.add(job)
        db.commit()

    return user_to_out(company, u)

@router.delete("/users/{user_id}")
async def delete_user_ep(company_id: int, user_id: int, db: Session = Depends(get_db), company=Depends(require_company)):
    if company.id != company_id:
        raise HTTPException(403, "Wrong company")
    u = db.get(User, user_id)
    if not u or u.company_id != company_id:
        raise HTTPException(404, "User not found")

    u.status = "deleted"
    db.add(u)
    db.commit()

    payload = {"company_id": company.id, "user_id": u.id, "employee_no": u.employee_no}
    job = create_job(db, company.id, u.id, "delete", u.employee_no, payload)

    if manager.edge_connected(company.id):
        await manager.send_to_edges(company.id, {"type": "user.delete", "data": {"job_id": job.id, **payload}})
        job.status = "sent"
        db.add(job)
        db.commit()

    return {"ok": True}
