import datetime as dt
from sqlalchemy import Column, Integer, String, DateTime, Index
from .core.db import Base
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.db import Base

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    edge_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    jobs = relationship("ProvisionJob", back_populates="company", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    employee_no: Mapped[str | None] = mapped_column(String(64), index=True)  # "{company_id}s{user_id}"
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|active|failed|deleted
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), onupdate=lambda: dt.datetime.now(dt.timezone.utc))

    company = relationship("Company", back_populates="users")
    jobs = relationship("ProvisionJob", back_populates="user", cascade="all, delete-orphan")


class ProvisionJob(Base):
    __tablename__ = "provision_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    job_type: Mapped[str] = mapped_column(String(20), nullable=False)  # create|update|delete
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|sent|acked|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), onupdate=lambda: dt.datetime.now(dt.timezone.utc))

    company = relationship("Company", back_populates="jobs")
    user = relationship("User", back_populates="jobs")


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # uuid or hash
    company_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    employee_no: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ts: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))



class AccessEvent(Base):
    __tablename__ = "access_events"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=False, index=True)
    employee_no = Column(String(64), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        Index("ix_access_events_company_employee_ts", "company_id", "employee_no", "ts"),
    )
