"""
DGH Feedback API
===============

Patient Feedback Management API for Douala General Hospital.

This service handles:
- Patient management (CRUD operations)
- Feedback collection and analysis
- Department management
- Statistical reporting and analytics

Features:
- Multilingual support (FR, EN, Douala, Bassa, Ewondo)
- Real-time feedback processing
- Sentiment analysis ready
- RESTful API with OpenAPI documentation

Author: DGH Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "DGH Development Team" 
__email__ = "dev@dgh.cm"
__description__ = "Patient Feedback Management API for Douala General Hospital"

# Package metadata
__title__ = "DGH Feedback API"
__license__ = "MIT"
__copyright__ = "2025 Douala General Hospital"

# API information
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Supported languages
SUPPORTED_LANGUAGES = ["fr", "en", "douala", "bassa", "ewondo"]

# Application constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 1000
CACHE_TTL_SECONDS = 300

# Logging configuration
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())