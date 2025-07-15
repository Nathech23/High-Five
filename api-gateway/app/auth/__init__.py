"""
Authentication Module
====================

Handles JWT authentication, user management, and authorization for the API Gateway.

Components:
- JWT token generation and validation
- User models and schemas
- Authentication middleware
"""

from .jwt_handler import JWTHandler
from .models import (
    User,
    UserCreate, 
    UserLogin,
    UserInDB,
    Token,
    TokenData
)

# Public API exports
__all__ = [
    # Main handler
    "JWTHandler",
    
    # User models
    "User",
    "UserCreate",
    "UserLogin", 
    "UserInDB",
    
    # Token models
    "Token",
    "TokenData",
]

# Default JWT handler instance
jwt_handler = JWTHandler()

# Convenience functions
def create_access_token(data: dict) -> str:
    """Create access token - convenience function"""
    return jwt_handler.create_access_token(data)

def verify_token(token: str) -> dict:
    """Verify token - convenience function"""
    return jwt_handler.decode_token(token)