import os, uuid
from sqlalchemy.orm import Session
from fastapi import UploadFile
from .models import Company, User, ProvisionJob
from .core.security import gen_api_key
from .core.config import settings

def create_company(db: Session, name: str) -> Company:
    c = Company(name=name, api_key=gen_api_key("api"), edge_key=gen_api_key("edge"))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def get_company_by_api_key(db: Session, api_key: str) -> Company | None:
    return db.query(Company).filter(Company.api_key == api_key).first()

def get_company_by_edge_key(db: Session, edge_key: str) -> Company | None:
    return db.query(Company).filter(Company.edge_key == edge_key).first()

def get_company(db: Session, company_id: int) -> Company | None:
    return db.query(Company).filter(Company.id == company_id).first()

def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    
    # Ensure the media directory exists
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    
    dest = os.path.join(settings.MEDIA_DIR, fname)
    with open(dest, "wb") as f:
        f.write(file.file.read())
    return fname

def make_image_url(company: Company, fname: str) -> str:
    # Local uses edge_key to download
    return f"{settings.PUBLIC_BASE_URL}/media/{fname}?edge_key={company.edge_key}"

def create_user(db: Session, company: Company, first_name: str, last_name: str, phone: str | None, image_filename: str | None) -> User:
    u = User(company_id=company.id, first_name=first_name, last_name=last_name, phone=phone, image_filename=image_filename, status="pending")
    db.add(u)
    db.flush()  # get id
    u.employee_no = f"{company.id}s{u.id}"
    db.flush()
    db.commit()
    db.refresh(u)
    return u

def create_job(db: Session, company_id: int, user_id: int, job_type: str, employee_no: str, payload: dict) -> ProvisionJob:
    j = ProvisionJob(company_id=company_id, user_id=user_id, job_type=job_type, employee_no=employee_no, payload=payload, status="pending")
    db.add(j)
    db.commit()
    db.refresh(j)
    return j

def pending_jobs_for_company(db: Session, company_id: int) -> list[ProvisionJob]:
    return db.query(ProvisionJob).filter(ProvisionJob.company_id == company_id, ProvisionJob.status == "pending").order_by(ProvisionJob.id.asc()).all()
