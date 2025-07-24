from fastapi import APIRouter, HTTPException
from datetime import datetime
import structlog

from app.models.responses import HealthCheckResponse
from app.core.llm_manager import llm_manager
from app.utils.cache import cache_manager
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()

@router.get("/", response_model=HealthCheckResponse)
async def health_check():
    """
    Vérifie la santé globale du service LLM.
    
    Retourne l'état de tous les composants critiques:
    - Disponibilité du modèle LLM
    - Connexion cache Redis
    - Métriques de performance
    """
    try:
        # Vérification du LLM
        llm_health = await llm_manager.health_check()
        
        # Vérification du cache
        cache_health = await cache_manager.health_check()
        
        # Détermination du statut global
        overall_status = "healthy"
        if not llm_health["available"]:
            overall_status = "degraded - LLM unavailable"
        elif not cache_health["available"]:
            overall_status = "degraded - Cache unavailable"
        
        response = HealthCheckResponse(
            status=overall_status,
            llm_model=settings.llm_model,
            model_available=llm_health["available"],
            cache_status=cache_health["status"]
        )
        
        logger.info("Health check completed", status=overall_status)
        return response
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service health check failed")

@router.get("/detailed")
async def detailed_health_check():
    """
    Vérifie détaillé de tous les composants du service.
    """
    try:
        # Vérifications détaillées
        llm_health = await llm_manager.health_check()
        cache_health = await cache_manager.health_check()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "service": "LLM Medical Service",
            "version": "1.0.0",
            "components": {
                "llm": llm_health,
                "cache": cache_health,
                "config": {
                    "model": settings.llm_model,
                    "temperature": settings.llm_temperature,
                    "max_tokens": settings.llm_max_tokens
                }
            },
            "capabilities": {
                "diagnostic_explanations": True,
                "therapeutic_explanations": True,
                "multilingual_support": True,
                "safety_validation": True
            }
        }
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Detailed health check failed")