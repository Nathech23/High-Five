from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class FeedbackBase(BaseModel):
    """Base feedback schema"""
    patient_id: int
    department_id: int
    rating: float
    feedback_text: str
    language: str
    wait_time_min: Optional[float] = None
    resolution_time_min: Optional[float] = None

    @validator('rating')
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

    @validator('language')
    def validate_language(cls, v):
        allowed_languages = ['fr', 'en', 'douala', 'bassa', 'ewondo']
        if v not in allowed_languages:
            raise ValueError(f'Language must be one of: {allowed_languages}')
        return v

    @validator('feedback_text')
    def validate_feedback_text(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('Feedback text must be at least 10 characters long')
        return v.strip()

    @validator('wait_time_min', 'resolution_time_min')
    def validate_times(cls, v):
        if v is not None and v < 0:
            raise ValueError('Time values must be positive')
        return v

class FeedbackCreate(FeedbackBase):
    """Feedback creation schema"""
    pass

class FeedbackUpdate(BaseModel):
    """Feedback update schema"""
    rating: Optional[float] = None
    feedback_text: Optional[str] = None
    wait_time_min: Optional[float] = None
    resolution_time_min: Optional[float] = None
    status: Optional[str] = None

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['pending', 'reviewed', 'resolved']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v

class Feedback(FeedbackBase):
    """Feedback response schema"""
    id: int
    is_urgent: bool = False
    status: str = "pending"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FeedbackWithAnalysis(Feedback):
    """Feedback with analysis schema"""
    analysis: Optional['FeedbackAnalysis'] = None

    class Config:
        from_attributes = True

class FeedbackSummary(BaseModel):
    """Feedback summary schema"""
    id: int
    rating: float
    language: str
    is_urgent: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackAnalysisBase(BaseModel):
    """Base feedback analysis schema"""
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    themes: Optional[str] = None  # JSON string
    keywords: Optional[str] = None  # JSON string
    urgency_score: float = 0.0
    confidence_score: Optional[float] = None

class FeedbackAnalysisCreate(FeedbackAnalysisBase):
    """Feedback analysis creation schema"""
    feedback_id: int

class FeedbackAnalysis(FeedbackAnalysisBase):
    """Feedback analysis response schema"""
    id: int
    feedback_id: int
    processed_at: datetime

    class Config:
        from_attributes = True

class FeedbackStats(BaseModel):
    """Feedback statistics schema"""
    total_feedbacks: int
    avg_rating: float
    sentiment_distribution: dict
    urgent_count: int
    by_department: dict
    by_language: dict
    recent_trend: List[dict]

# Forward reference resolution
FeedbackWithAnalysis.model_rebuild()