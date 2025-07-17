"""
Services Module
==============

Business logic services for the Feedback API.

Services encapsulate business logic and provide a clean interface
between the API endpoints and the data layer.

Components:
- PatientService: Patient management business logic
- FeedbackService: Feedback processing and analytics
- Common service utilities and base classes
"""

from .patient_service import PatientService
from .feedback_service import FeedbackService

__all__ = [
    "PatientService",
    "FeedbackService",
]

# Service configuration
SERVICE_CONFIG = {
    "cache_enabled": True,
    "cache_ttl": 300,
    "batch_size": 100,
    "max_query_limit": 1000
}

# Common service exceptions
class ServiceError(Exception):
    """Base service exception"""
    pass

class NotFoundError(ServiceError):
    """Resource not found exception"""
    pass

class ValidationError(ServiceError):
    """Data validation exception"""
    pass

class BusinessLogicError(ServiceError):
    """Business logic violation exception"""
    pass

# Export exceptions for use in endpoints
__all__.extend([
    "ServiceError",
    "NotFoundError", 
    "ValidationError",
    "BusinessLogicError"
])