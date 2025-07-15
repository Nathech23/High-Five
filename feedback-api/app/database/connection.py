from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from databases import Database
import logging

from ..config import settings

logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=0,
    echo=settings.DATABASE_ECHO
)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async database instance
database = Database(DATABASE_URL)

# Metadata
metadata = MetaData()

def get_database():
    """Get database connection"""
    return database

def get_db():
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def check_database_connection():
    """Check database connection"""
    try:
        await database.connect()
        logger.info("Database connection successful")
        await database.disconnect()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False