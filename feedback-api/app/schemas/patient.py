from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime

class PatientBase(BaseModel):
    """Base patient schema"""
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_language: str = "fr"
    department_id: int

    @validator('preferred_language')
    def validate_language(cls, v):
        allowed_languages = ['fr', 'en', 'douala', 'bassa', 'ewondo']
        if v not in allowed_languages:
            raise ValueError(f'Language must be one of: {allowed_languages}')
        return v

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip().title()

class PatientCreate(PatientBase):
    """Patient creation schema"""
    pass

class PatientUpdate(BaseModel):
    """Patient update schema"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_language: Optional[str] = None
    department_id: Optional[int] = None

    @validator('preferred_language')
    def validate_language(cls, v):
        if v is not None:
            allowed_languages = ['fr', 'en', 'douala', 'bassa', 'ewondo']
            if v not in allowed_languages:
                raise ValueError(f'Language must be one of: {allowed_languages}')
        return v

class Patient(PatientBase):
    """Patient response schema"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PatientWithFeedbacks(Patient):
    """Patient with feedbacks schema"""
    feedbacks: List['FeedbackSummary'] = []

    class Config:
        from_attributes = True

class PatientSummary(BaseModel):
    """Patient summary schema"""
    id: int
    first_name: str
    last_name: str
    preferred_language: str
    department_id: int
    total_feedbacks: int = 0
    avg_rating: Optional[float] = None

    class Config:
        from_attributes = True

# Forward reference resolution
from .feedback import FeedbackSummary
PatientWithFeedbacks.model_rebuild()