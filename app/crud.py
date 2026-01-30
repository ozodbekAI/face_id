from sqlalchemy import func
from sqlalchemy.orm import Session
from .core.security import gen_api_key
from .models import Company, User


# ==========================
# Companies
# ==========================

def create_company(db: Session, name: str) -> Company:
    c = Company(name=name, api_key=gen_api_key("api"), edge_key=gen_api_key("edge"))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def list_companies(db: Session, q: str | None, page: int, limit: int) -> tuple[int, list[Company]]:
    qry = db.query(Company)
    if q:
        qn = f"%{q.strip().lower()}%"
        qry = qry.filter(func.lower(Company.name).like(qn))
    total = qry.count()
    items = qry.order_by(Company.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return total, items


def update_company(
    db: Session,
    company_id: int,
    *,
    name: str | None = None,
    rotate_api_key: bool = False,
    rotate_edge_key: bool = False,
) -> Company | None:
    c = get_company(db, company_id)
    if not c:
        return None
    if name is not None:
        c.name = name
    if rotate_api_key:
        c.api_key = gen_api_key("api")
    if rotate_edge_key:
        c.edge_key = gen_api_key("edge")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def delete_company(db: Session, company_id: int) -> bool:
    c = get_company(db, company_id)
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


def get_company_by_api_key(db: Session, api_key: str) -> Company | None:
    return db.query(Company).filter(Company.api_key == api_key).first()


def get_company_by_edge_key(db: Session, edge_key: str) -> Company | None:
    return db.query(Company).filter(Company.edge_key == edge_key).first()


def get_company(db: Session, company_id: int) -> Company | None:
    return db.query(Company).filter(Company.id == company_id).first()


# ==========================
# Users
# ==========================

def create_user(
    db: Session,
    company: Company,
    first_name: str,
    last_name: str,
    phone: str | None,
) -> User:
    u = User(
        company_id=company.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        status="pending",
    )
    db.add(u)
    db.flush()  # get id

    # Manual enrollment code for terminal: just user.id
    u.employee_no = str(u.id)

    db.add(u)
    db.commit()
    db.refresh(u)
    return u
