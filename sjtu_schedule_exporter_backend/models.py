import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel


class SessionField(BaseModel):
    session: str


class LoginResponse(BaseModel):
    session: str


class StudentIDResponse(BaseModel):
    student_id: int


class TermStartResponse(BaseModel):
    term_start: datetime.date


class MailSentResponse(BaseModel):
    to_address: str


class LoginFields(BaseModel):
    username: str
    password: str


class Class(BaseModel):
    name: str
    course_id: str
    class_name: str
    class_id: str
    day: int
    week: list
    time: Tuple[datetime.time, datetime.time]
    location: Optional[str] = None
    credit: Optional[int] = None
    assessment: Optional[str] = None
    remark: Optional[str] = None
    teacher_name: Optional[List[str]] = None
    teacher_title: Optional[List[str]] = None
    hour_total: Optional[int] = None
    hour_remark: Optional[dict] = None
    hour_week: Optional[int] = None
    field: Optional[str] = None


class Schedule(BaseModel):
    classes: List[Class]
