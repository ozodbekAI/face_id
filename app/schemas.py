from pydantic import BaseModel, Field
from typing import Optional, Any

class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AccessEventIn(BaseModel):
    employee_no: str
    ts: str | None = None  

class AccessEventOut(BaseModel):
    id: int
    company_id: int
    employee_no: str
    ts: str

    class Config:
        from_attributes = True


class CompanyOut(BaseModel):
    id: int
    name: str
    api_key: str
    edge_key: str

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    company_id: int
    first_name: str
    last_name: str
    phone: Optional[str] = None
    employee_no: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    last_error: Optional[str] = None

    class Config:
        from_attributes = True

class EventIn(BaseModel):
    event_id: str
    company_id: int | None = None
    device_id: str | None = None
    employee_no: str | None = None
    event_type: str
    payload: dict = {}
    ts: str | None = None


class EventCreateIn(BaseModel):
    employee_no: str
    device_id: str | None = None
    event_type: str = "access"
    payload: dict = {}
    ts: str | None = None  
    event_id: str | None = None


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


class AttendanceDayOut(BaseModel):
    company_id: int
    user_id: int
    date: str  # YYYY-MM-DD (company timezone)
    first_in: str | None = None
    last_out: str | None = None
    events_count: int

class AckIn(BaseModel):
    job_id: int
    status: str  # ok|failed
    error: str | None = None


class AttendanceRequest(BaseModel):
    company_id: str
    user_id: str
    start_date: str 
    end_date: str   