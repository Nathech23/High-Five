"""
Tests Module
===========

Comprehensive test suite for the DGH Feedback System.

Test Categories:
- Unit tests for individual components
- Integration tests for complete workflows  
- API endpoint tests with various scenarios
- Performance and load testing
- Security and authentication testing

Test Coverage:
- API Gateway authentication and middleware
- Feedback API CRUD operations
- Database operations and constraints
- Error handling and edge cases
- Multilingual functionality

Author: DGH Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__test_framework__ = "pytest"
__coverage_target__ = "95%"

# Test configuration
TEST_CONFIG = {
    "database_url": "sqlite:///./test.db",
    "test_timeout": 30,
    "parallel_workers": 4,
    "coverage_threshold": 95
}

# Test data constants
TEST_LANGUAGES = ["fr", "en", "douala", "bassa", "ewondo"]
TEST_DEPARTMENTS = ["Urgences", "Cardiologie", "Pédiatrie"]
TEST_USERS = ["admin", "staff", "viewer"]

# Test utilities
import logging
logging.getLogger("test").setLevel(logging.WARNING)

def get_test_database_url():
    """Get test database URL"""
    return TEST_CONFIG["database_url"]

def get_test_config():
    """Get test configuration"""
    return TEST_CONFIG.copy()

# Common test assertions
def assert_valid_response(response, expected_status=200):
    """Assert API response is valid"""
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.headers["content-type"].startswith("application/json")

def assert_valid_jwt_token(token):
    """Assert JWT token is valid format"""
    assert isinstance(token, str)
    assert len(token.split('.')) == 3  # JWT has 3 parts

# Export test utilities
__all__ = [
    "TEST_CONFIG",
    "TEST_LANGUAGES", 
    "TEST_DEPARTMENTS",
    "TEST_USERS",
    "get_test_database_url",
    "get_test_config",
    "assert_valid_response",
    "assert_valid_jwt_token"
]