"""
API Endpoints Module
===================

REST API endpoint implementations for all resources.

Endpoints are organized by resource type:
- patients.py: Patient management endpoints
- feedbacks.py: Feedback collection and management
- departments.py: Department management  
- health.py: Health checks and system status

All endpoints follow REST conventions and include:
- Input validation with Pydantic
- Error handling and appropriate HTTP status codes
- OpenAPI documentation
- Authentication where required
"""

# Endpoint categories
PATIENT_ENDPOINTS = [
    "GET /patients",
    "POST /patients", 
    "GET /patients/{id}",
    "PUT /patients/{id}",
    "DELETE /patients/{id}",
    "GET /patients/{id}/feedbacks",
    "GET /patients/summary"
]

FEEDBACK_ENDPOINTS = [
    "GET /feedbacks",
    "POST /feedbacks",
    "GET /feedbacks/{id}", 
    "PUT /feedbacks/{id}",
    "DELETE /feedbacks/{id}",
    "GET /feedbacks/stats",
    "GET /feedbacks/urgent",
    "POST /feedbacks/{id}/mark-urgent",
    "POST /feedbacks/{id}/resolve"
]

DEPARTMENT_ENDPOINTS = [
    "GET /departments",
    "POST /departments",
    "GET /departments/{id}",
    "PUT /departments/{id}", 
    "DELETE /departments/{id}",
    "GET /departments/{id}/stats"
]

HEALTH_ENDPOINTS = [
    "GET /health",
    "GET /health/detailed",
    "GET /health/ready", 
    "GET /health/live",
    "GET /version"
]

# Total endpoint count
TOTAL_ENDPOINTS = len(PATIENT_ENDPOINTS + FEEDBACK_ENDPOINTS + DEPARTMENT_ENDPOINTS + HEALTH_ENDPOINTS)