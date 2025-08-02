from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class DepartmentBase(BaseModel):
    """Base department schema"""
    name: str
    code: str

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Department name must be at least 2 characters long')
        return v.strip()

    @validator('code')
    def validate_code(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Department code must be at least 2 characters long')
        return v.strip().upper()

class DepartmentCreate(DepartmentBase):
    """Department creation schema"""
    pass

class DepartmentUpdate(BaseModel):
    """Department update schema"""
    name: Optional[str] = None
    code: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or len(v.strip()) < 2):
            raise ValueError('Department name must be at least 2 characters long')
        return v.strip() if v else v

    @validator('code')
    def validate_code(cls, v):
        if v is not None and (not v or len(v.strip()) < 2):
            raise ValueError('Department code must be at least 2 characters long')
        return v.strip().upper() if v else v

class Department(DepartmentBase):
    """Department response schema"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True