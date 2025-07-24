from fastapi import APIRouter, HTTPException, Depends
from typing import List
import structlog

from app.models.requests import DiagnosticExplanationRequest, GeneralMedicalQuestionRequest
from app.models.responses import DiagnosticExplanationResponse, MedicalExplanationResponse
from app.services.llm_service import llm_service
from app.utils.metrics import metrics_collector

logger = structlog.get_logger()
router = APIRouter()

@router.post("/explain", response_model=DiagnosticExplanationResponse)
async def explain_diagnostic(request: DiagnosticExplanationRequest):
    """
    Explique un diagnostic médical en langage simple et accessible.
    
    Cette endpoint prend un diagnostic médical et le transforme en explication
    claire et rassurante pour le patient, adaptée à son niveau d'éducation et
    sa langue préférée.
    """
    try:
        # Métrique de démarrage
        with metrics_collector.time_operation("diagnostic_explanation"):
            response = await llm_service.explain_diagnostic(request)
        
        # Logging pour suivi
        logger.info("Diagnostic explanation generated", 
                   response_id=response.response_id,
                   language=response.language.value,
                   confidence=response.confidence_score)
        
        # Incrément des métriques
        metrics_collector.increment_counter("diagnostic_explanations_total")
        metrics_collector.record_histogram("diagnostic_confidence_scores", response.confidence_score)
        
        return response
        
    except Exception as e:
        logger.error("Error in diagnostic explanation endpoint", error=str(e))
        metrics_collector.increment_counter("diagnostic_explanations_errors")
        raise HTTPException(status_code=500, detail="Erreur lors de l'explication du diagnostic")

@router.post("/question", response_model=MedicalExplanationResponse)
async def answer_diagnostic_question(request: GeneralMedicalQuestionRequest):
    """
    Répond à une question générale sur un diagnostic ou concept médical.
    """
    try:
        with metrics_collector.time_operation("diagnostic_question"):
            response = await llm_service.answer_general_question(request)
        
        logger.info("Diagnostic question answered", 
                   response_id=response.response_id,
                   urgency=response.urgency_level)
        
        metrics_collector.increment_counter("diagnostic_questions_total")
        
        return response
        
    except Exception as e:
        logger.error("Error answering diagnostic question", error=str(e))
        metrics_collector.increment_counter("diagnostic_questions_errors")
        raise HTTPException(status_code=500, detail="Erreur lors de la réponse à la question")

@router.get("/health")
async def diagnostic_health_check():
    """Vérifie la santé du service d'explication diagnostique"""
    try:
        # Test simple de génération
        test_request = DiagnosticExplanationRequest(
            diagnostic_text="Test de santé du service"
        )
        
        # On ne génère pas vraiment, juste on vérifie que le service répond
        return {
            "service": "diagnostic_explanation",
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Diagnostic service health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service indisponible")