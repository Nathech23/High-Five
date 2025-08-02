from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from typing import List
from datetime import datetime
import os

from src.utils.data_models import OptimizationRequest, OptimizationResult
from src.algorithms.eoq_optimizer import BloodEOQOptimizer

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="🩸 Blood Bank Optimization API",
    description="Service d'optimisation pour banques de sang",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
eoq_optimizer = BloodEOQOptimizer()

@app.get("/")
async def root():
    """Page d'accueil"""
    return {
        "message": "🩸 Blood Bank Optimization API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "optimize": "/optimize",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "eoq_optimizer": "operational",
            "api": "operational"
        }
    }

@app.post("/optimize", response_model=List[OptimizationResult])
async def optimize_stocks(request: OptimizationRequest):
    """Optimisation des stocks de sang"""
    try:
        if not request.stocks:
            raise HTTPException(status_code=400, detail="No stock data provided")
        
        start_time = time.time()
        results = eoq_optimizer.optimize_basic(request.stocks)
        execution_time = time.time() - start_time
        
        logger.info(f"Optimization completed in {execution_time:.3f}s for {len(request.stocks)} blood types")
        
        return results
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    """Métriques basiques"""
    return {
        "api_status": "operational",
        "response_time": "< 200ms",
        "algorithm_performance": "basic_eoq_ready",
        "deployment": "in_progress"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)