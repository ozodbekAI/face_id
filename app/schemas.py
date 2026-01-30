from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ==========================
# Auth / RBAC
# ==========================


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str

    role: str
    company_id: int | None = None


class MeResponse(BaseModel):
    id: int
    username: str
    role: str
    company_id: int | None = None
    is_active: bool


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=6, max_length=200)


class OwnerCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    company_id: int
    password: str | None = Field(default=None, min_length=6, max_length=200)


class OwnerOut(BaseModel):
    id: int
    username: str
    role: str
    company_id: int
    is_active: bool
    created_at: str | None = None


class OwnerCreatedResponse(OwnerOut):
    # returned only on create/reset
    password: str


class OwnerPageOut(BaseModel):
    total: int
    items: list[OwnerOut]


# ==========================
# Company
# ==========================


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    rotate_api_key: bool = False
    rotate_edge_key: bool = False


class CompanyOut(BaseModel):
    id: int
    name: str
    api_key: str
    edge_key: str

    class Config:
        from_attributes = True


class CompanyPageOut(BaseModel):
    total: int
    items: list[CompanyOut]


# ==========================
# Users
# ==========================


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default=None, description="pending|active|failed|deleted")


class UserOut(BaseModel):
    id: int
    company_id: int
    first_name: str
    last_name: str
    phone: Optional[str] = None

    # Terminal enrollment code (recommended: str(user.id))
    employee_no: Optional[str] = None
    enroll_code: str
    status: str
    last_error: Optional[str] = None

    class Config:
        from_attributes = True


class UserPageOut(BaseModel):
    total: int
    items: list[UserOut]


# ==========================
# Events
# ==========================


class EventOut(BaseModel):
    id: int
    event_id: str
    company_id: int
    user_id: int | None = None
    employee_no: str | None = None
    device_id: str | None = None
    event_type: str
    ts: str

    class Config:
        from_attributes = True


class EventOutDetailed(EventOut):
    payload: dict = {}


class EventPageOut(BaseModel):
    total: int
    items: list[EventOut] | list[EventOutDetailed]


# ==========================
# Attendance
# ==========================


class AttendanceRowOut(BaseModel):
    company_id: int
    user_id: int
    date: str  # YYYY-MM-DD (company timezone)
    first_in: str | None = None
    last_out: str | None = None
    duration_min: int | None = None
    events_count: int

    # Optional user info
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class AttendancePageOut(BaseModel):
    total: int
    items: list[AttendanceRowOut]
