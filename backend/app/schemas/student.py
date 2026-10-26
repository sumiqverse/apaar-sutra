"""Pydantic v2 schemas for Students and Academic Records."""

from datetime import date, datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AcademicRecordBase(BaseModel):
    semester: int = Field(..., ge=1, le=12)
    course_code: str = Field(..., min_length=2, max_length=32)
    course_name: str = Field(..., min_length=2, max_length=150)
    credits: float = Field(..., ge=0.0)
    grade_point: float = Field(..., ge=0.0, le=10.0)
    result_status: str = Field("PASS")


class AcademicRecordResponse(AcademicRecordBase):
    id: uuid.UUID
    student_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentBase(BaseModel):
    apaar_id: str = Field(..., min_length=12, max_length=12, description="12-digit APAAR ID")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    dob: date
    gender: str = Field(..., pattern="^(MALE|FEMALE|OTHER)$")
    enrollment_number: str = Field(..., min_length=3, max_length=64)
    program_name: str = Field(..., min_length=2, max_length=150)
    admission_year: int = Field(..., ge=1990, le=2030)


class StudentCreate(StudentBase):
    institution_id: uuid.UUID
    aadhaar_reference: str = Field(..., min_length=12, max_length=12, description="Raw Aadhaar to be hashed immediately")


class StudentResponse(BaseModel):
    id: uuid.UUID
    apaar_id: str
    masked_apaar_id: str
    institution_id: uuid.UUID
    first_name: str
    last_name: str
    dob: date
    gender: str
    enrollment_number: str
    program_name: str
    admission_year: int
    status: str
    verification_status: str
    academic_records: List[AcademicRecordResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
