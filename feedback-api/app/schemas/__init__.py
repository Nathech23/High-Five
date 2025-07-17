"""
Schemas Module
=============

Pydantic schemas for request/response validation and serialization.

Components:
- Patient schemas (create, update, response)
- Feedback schemas (create, update, response, analytics)
- Department schemas (create, update, response)
- Common validation utilities
"""

from .patient import (
    Patient,
    PatientCreate,
    PatientUpdate,
    PatientSummary,
    PatientWithFeedbacks
)
from .feedback import (
    Feedback,
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackWithAnalysis,
    FeedbackSummary,
    FeedbackStats,
    FeedbackAnalysis,
    FeedbackAnalysisCreate
)
from .department import (
    Department,
    DepartmentCreate,
    DepartmentUpdate
)

__all__ = [
    # Patient schemas
    "Patient",
    "PatientCreate", 
    "PatientUpdate",
    "PatientSummary",
    "PatientWithFeedbacks",
    
    # Feedback schemas
    "Feedback",
    "FeedbackCreate",
    "FeedbackUpdate", 
    "FeedbackWithAnalysis",
    "FeedbackSummary",
    "FeedbackStats",
    "FeedbackAnalysis",
    "FeedbackAnalysisCreate",
    
    # Department schemas
    "Department",
    "DepartmentCreate",
    "DepartmentUpdate",
]

# Schema validation settings
VALIDATION_CONFIG = {
    "validate_assignment": True,
    "use_enum_values": True,
    "extra": "forbid"
}

# Common field constraints
CONSTRAINTS = {
    "name_min_length": 2,
    "name_max_length": 100,
    "text_min_length": 10,
    "text_max_length": 5000,
    "rating_min": 1.0,
    "rating_max": 5.0
}