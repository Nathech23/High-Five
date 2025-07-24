from fastapi import APIRouter, HTTPException
import structlog
from datetime import datetime

from app.models.requests import TherapeuticExplanationRequest
from app.models.responses import TherapeuticExplanationResponse
from app.services.llm_service import llm_service
from app.utils.metrics import metrics_collector

logger = structlog.get_logger()
router = APIRouter()

@router.post("/explain", response_model=TherapeuticExplanationResponse)
async def explain_therapeutic(request: TherapeuticExplanationRequest):
    """
    Explique un traitement ou médicament en langage accessible.
    
    Transforme les prescriptions médicales en explications claires sur:
    - Pourquoi le traitement a été prescrit
    - Comment le prendre correctement
    - Les effets attendus et secondaires
    - Les recommandations de style de vie
    """
    try:
        with metrics_collector.time_operation("therapeutic_explanation"):
            response = await llm_service.explain_therapeutic(request)
        
        logger.info("Therapeutic explanation generated",
                   response_id=response.response_id,
                   medication=request.medication_name,
                   type=request.explanation_type.value)
        
        metrics_collector.increment_counter("therapeutic_explanations_total")
        metrics_collector.increment_counter(f"therapeutic_explanations_{request.explanation_type.value}")
        
        return response
        
    except Exception as e:
        logger.error("Error in therapeutic explanation endpoint", error=str(e))
        metrics_collector.increment_counter("therapeutic_explanations_errors")
        raise HTTPException(status_code=500, detail="Erreur lors de l'explication thérapeutique")

@router.post("/medication/explain", response_model=TherapeuticExplanationResponse)
async def explain_medication(request: TherapeuticExplanationRequest):
    """
    Endpoint spécialisé pour l'explication des médicaments.
    """
    # Force le type d'explication à "medication"
    request.explanation_type = "medication"
    
    try:
        with metrics_collector.time_operation("medication_explanation"):
            response = await llm_service.explain_therapeutic(request)
        
        logger.info("Medication explanation generated",
                   response_id=response.response_id,
                   medication=request.medication_name)
        
        metrics_collector.increment_counter("medication_explanations_total")
        
        return response
        
    except Exception as e:
        logger.error("Error in medication explanation endpoint", error=str(e))
        metrics_collector.increment_counter("medication_explanations_errors")
        raise HTTPException(status_code=500, detail="Erreur lors de l'explication du médicament")

@router.get("/health")
async def therapeutic_health_check():
    """Vérifie la santé du service d'explication thérapeutique"""
    try:
        return {
            "service": "therapeutic_explanation",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "supported_types": ["treatment", "medication", "lifestyle", "followup"]
        }
        
    except Exception as e:
        logger.error("Therapeutic service health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service indisponible")
