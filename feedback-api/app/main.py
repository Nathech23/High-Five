from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from contextlib import asynccontextmanager

from .config import settings
from .database.connection import database, engine
from .database.models import Base
from .api.endpoints import patients, feedbacks, departments, health
from .utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Feedback API")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Connect to database
    await database.connect()
    logger.info("Connected to database")
    
    yield
    
    # Shutdown
    await database.disconnect()
    logger.info("Disconnected from database")

# FastAPI app
app = FastAPI(
    title="DGH Feedback API",
    description="Patient Feedback Management API for Douala General Hospital",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    patients.router,
    prefix=f"{settings.API_V1_STR}/patients",
    tags=["Patients"]
)
app.include_router(
    feedbacks.router,
    prefix=f"{settings.API_V1_STR}/feedbacks",
    tags=["Feedbacks"]
)
app.include_router(
    departments.router,
    prefix=f"{settings.API_V1_STR}/departments",
    tags=["Departments"]
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DGH Feedback API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": time.time()
    }

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    return {
        "total_patients": 150,
        "total_feedbacks": 500,
        "avg_rating": 4.2,
        "response_time_avg": 0.180
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )