"""
Middleware Module
================

Custom middleware components for the API Gateway.

Components:
- Rate limiting middleware
- Security headers middleware
- Request/response logging
"""

from .rate_limit import RateLimitMiddleware

__all__ = [
    "RateLimitMiddleware",
]

# Middleware configuration
MIDDLEWARE_CONFIG = {
    "rate_limit": {
        "enabled": True,
        "requests_per_minute": 100,
        "burst_size": 50
    },
    "security_headers": {
        "enabled": True,
        "hsts_max_age": 31536000
    }
}