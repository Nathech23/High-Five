from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
import uvicorn

from app.core.config import settings
from app.core.llm_manager import llm_manager
from app.utils.cache import cache_manager
from app.utils.metrics import metrics_collector
from app.api.v1.endpoints import diagnostic, therapeutic, health

# Configuration du logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Démarrage
    logger.info("Starting LLM Medical Service")
    
    try:
        # Initialisation des composants
        await llm_manager.initialize()
        await cache_manager.initialize()
        
        # Démarrage du serveur de métriques
        if not settings.debug:
            metrics_collector.start_metrics_server()
        
        logger.info("LLM Medical Service started successfully")
        
    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        raise
    
    yield  # L'application fonctionne ici
    
    # Arrêt
    logger.info("Shutting down LLM Medical Service")

# Création de l'application FastAPI
app = FastAPI(
    title=settings.project_name,
    description="Service LLM pour explications médicales - Track 2 Datathon DGH",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(
    diagnostic.router,
    prefix=f"{settings.api_v1_str}/diagnostic",
    tags=["Explications Diagnostiques"]
)

app.include_router(
    therapeutic.router,
    prefix=f"{settings.api_v1_str}/therapeutic",
    tags=["Explications Thérapeutiques"]
)

app.include_router(
    health.router,
    prefix=f"{settings.api_v1_str}/health",
    tags=["Santé du Service"]
)

@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "service": "LLM Medical Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled in production",
        "health": f"{settings.api_v1_str}/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
