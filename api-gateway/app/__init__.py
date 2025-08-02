"""
DGH API Gateway
===============

API Gateway with Authentication for Douala General Hospital Feedback System.

This service handles:
- JWT Authentication and authorization
- Rate limiting and security middleware
- Request routing and load balancing
- CORS and security headers

Author: DGH Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "DGH Development Team"
__email__ = "piodjiele@gmail.com"
__description__ = "API Gateway with Authentication for DGH Feedback System"

# Package metadata
__title__ = "DGH API Gateway"
__license__ = "MIT"
__copyright__ = "2025 Douala General Hospital"

# Logging configuration
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())