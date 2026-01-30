from sqlalchemy import func
import datetime as dt

from sqlalchemy.orm import Session

from .core.security import gen_api_key
from .core.auth import hash_password, new_token, token_hash, expires_at
from .models import Company, User, Account, AccountSession


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
# Accounts / Auth
# ==========================

def get_account_by_username(db: Session, username: str) -> Account | None:
    return db.query(Account).filter(Account.username == username).first()


def get_account_by_session_token(db: Session, token: str) -> Account | None:
    th = token_hash(token)
    now = dt.datetime.now(dt.timezone.utc)
    sess = (
        db.query(AccountSession)
        .filter(AccountSession.token_hash == th, AccountSession.expires_at > now)
        .first()
    )
    if not sess:
        return None
    acc = db.get(Account, sess.account_id)
    if not acc or not acc.is_active:
        return None
    # touch
    sess.last_seen_at = now
    db.add(sess)
    db.commit()
    return acc


def create_session(db: Session, acc: Account, *, user_agent: str | None = None, ip: str | None = None) -> tuple[str, dt.datetime]:
    token = new_token()
    exp = expires_at()
    sess = AccountSession(
        account_id=acc.id,
        token_hash=token_hash(token),
        expires_at=exp,
        user_agent=user_agent,
        ip=ip,
    )
    acc.last_login_at = dt.datetime.now(dt.timezone.utc)
    db.add(sess)
    db.add(acc)
    db.commit()
    return token, exp


def revoke_session(db: Session, token: str) -> bool:
    th = token_hash(token)
    s = db.query(AccountSession).filter(AccountSession.token_hash == th).first()
    if not s:
        return False
    db.delete(s)
    db.commit()
    return True


def create_owner(db: Session, *, username: str, password: str, company_id: int) -> Account:
    acc = Account(
        username=username,
        password_hash=hash_password(password),
        role="owner",
        company_id=company_id,
        is_active=True,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def set_account_password(db: Session, acc: Account, new_password: str) -> Account:
    acc.password_hash = hash_password(new_password)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def ensure_bootstrap_admin(db: Session, *, username: str, password: str) -> Account:
    """Create an initial admin account if none exists."""
    existing = db.query(Account).filter(Account.role == "admin").first()
    if existing:
        return existing
    acc = Account(
        username=username,
        password_hash=hash_password(password),
        role="admin",
        company_id=None,
        is_active=True,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


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
