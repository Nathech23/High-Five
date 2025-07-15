"""
Utilities Module
===============

Common utilities and helper functions for the API Gateway.

Components:
- Structured logging
- Response formatting
- Error handling utilities
"""

from .logger import (
    setup_logger,
    log_with_context,
    log_api_request,
    log_error_with_context
)

__all__ = [
    # Logging utilities
    "setup_logger",
    "log_with_context", 
    "log_api_request",
    "log_error_with_context",
]

# Default logger setup
import logging
logger = logging.getLogger(__name__)