"""
Database Module
==============

Database connectivity, models, and utilities for the Feedback API.

Components:
- SQLAlchemy database connection
- Database models (Patient, Feedback, Department, etc.)
- Database utilities and helpers
"""

from .connection import (
    database,
    engine,
    SessionLocal,
    get_db,
    get_database,
    check_database_connection
)
from .models import (
    Base,
    Patient,
    Feedback,
    Department,
    FeedbackAnalysis,
    ContactPreference,
    ReminderType,
    Reminder
)

__all__ = [
    # Connection components
    "database",
    "engine", 
    "SessionLocal",
    "get_db",
    "get_database",
    "check_database_connection",
    
    # Model components
    "Base",
    "Patient",
    "Feedback", 
    "Department",
    "FeedbackAnalysis",
    "ContactPreference",
    "ReminderType",
    "Reminder",
]

# Database metadata
DATABASE_VERSION = "1.0.0"
REQUIRED_TABLES = [
    "departments",
    "patients", 
    "feedbacks",
    "feedback_analysis",
    "contact_preferences",
    "reminder_types",
    "reminders"
]

# Database utilities
async def init_database():
    """Initialize database connection"""
    await database.connect()

async def close_database():
    """Close database connection"""
    await database.disconnect()