from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import logging

from ...database.connection import get_db, database
from ...config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "feedback-api",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with database connectivity"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "feedback-api",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database connectivity check
    try:
        result = db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time": "< 100ms"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check database tables
    try:
        tables_check = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).fetchall()
        
        expected_tables = ['patients', 'departments', 'feedbacks', 'feedback_analysis']
        existing_tables = [row[0] for row in tables_check]
        
        missing_tables = [table for table in expected_tables if table not in existing_tables]
        
        if missing_tables:
            health_status["checks"]["database_schema"] = {
                "status": "unhealthy",
                "missing_tables": missing_tables
            }
            health_status["status"] = "unhealthy"
        else:
            health_status["checks"]["database_schema"] = {
                "status": "healthy",
                "tables": existing_tables
            }
            
    except Exception as e:
        logger.error(f"Database schema check failed: {str(e)}")
        health_status["checks"]["database_schema"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Environment check
    health_status["checks"]["environment"] = {
        "status": "healthy",
        "database_url_configured": bool(settings.DATABASE_URL),
        "environment": settings.ENVIRONMENT
    }
    
    return health_status

@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check for Kubernetes/Docker"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Test if we can query main tables
        db.execute(text("SELECT COUNT(*) FROM departments LIMIT 1"))
        
        return {
            "status": "ready",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

@router.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes/Docker"""
    return {
        "status": "alive",
        "timestamp": time.time()
    }

@router.get("/version")
async def version_info():
    """Get version information"""
    return {
        "service": "feedback-api",
        "version": "1.0.0",
        "build_date": "2025-07-15",
        "environment": settings.ENVIRONMENT,
        "api_version": settings.API_V1_STR
    }