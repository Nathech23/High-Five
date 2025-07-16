"""
API Module
==========

REST API endpoints and routing for the Feedback API.

This module contains all the API endpoints organized by resource:
- Patient endpoints
- Feedback endpoints  
- Department endpoints
- Health check endpoints
"""

# API version and metadata
API_VERSION = "1.0.0"
API_TITLE = "DGH Feedback API"
API_DESCRIPTION = """
## Patient Feedback Management API

This API provides endpoints for managing:

###  Patients
- Create, read, update, and delete patient records
- Multilingual support for patient preferences
- Patient feedback history and statistics

###  Feedbacks  
- Collect patient feedback in multiple languages
- Real-time sentiment analysis and categorization
- Urgent feedback detection and alerting
- Statistical reporting and analytics

###  Departments
- Hospital department management
- Department-specific feedback analytics
- Performance tracking and reporting

### Analytics
- Real-time feedback statistics
- Sentiment analysis and trending
- Department performance metrics
- Multilingual feedback distribution

###  Languages Supported
- **French (fr)**: Français
- **English (en)**: English  
- **Douala**: Langue locale du Cameroun
- **Bassa**: Langue locale du Cameroun
- **Ewondo**: Langue locale du Cameroun
"""

# HTTP status codes used in API
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_500_INTERNAL_SERVER_ERROR = 500