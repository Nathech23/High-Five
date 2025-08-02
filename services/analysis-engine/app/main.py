from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from .nlp_analyzer import FeedbackAnalyzer
import time
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title="Feedback Analysis Engine", 
    version="1.0.0",
    description="API d'analyse de feedbacks patients multilingue"
)

# Initialisation de l'analyseur (global pour éviter de recharger)
analyzer = FeedbackAnalyzer()

# Modèles Pydantic
class AnalysisRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

class AnalysisResponse(BaseModel):
    original_text: str
    language: str
    sentiment: str
    predicted_rating: int
    themes: List[str]
    keywords: List[str]
    is_urgent: bool
    processing_time_ms: float

class BatchAnalysisRequest(BaseModel):
    feedbacks: List[AnalysisRequest]

class HealthResponse(BaseModel):
    status: str
    analyzer_loaded: bool
    version: str

# Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "Feedback Analysis Engine API",
        "version": "1.0.0",
        "endpoints": "/docs pour la documentation"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de l'API"""
    return HealthResponse(
        status="healthy",
        analyzer_loaded=analyzer is not None,
        version="1.0.0"
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_feedback(request: AnalysisRequest):
    """Analyser un feedback unique"""
    try:
        start_time = time.time()
        
        # Validation
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Le texte ne peut pas être vide")
        
        if len(request.text) > 1000:
            raise HTTPException(status_code=400, detail="Texte trop long (max 1000 caractères)")
        
        # Analyse
        result = analyzer.analyze_feedback(request.text)
        
        processing_time = (time.time() - start_time) * 1000  # en ms
        
        return AnalysisResponse(
            original_text=result["original_text"],
            language=result["language"],
            sentiment=result["sentiment"],
            predicted_rating=result["predicted_rating"],
            themes=result["themes"],
            keywords=result["keywords"],
            is_urgent=result["is_urgent"],
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

@app.post("/analyze/batch")
async def analyze_batch(request: BatchAnalysisRequest):
    """Analyser plusieurs feedbacks en lot"""
    try:
        if len(request.feedbacks) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 feedbacks par batch")
        
        start_time = time.time()
        results = []
        
        for feedback_req in request.feedbacks:
            if feedback_req.text.strip():  # Ignorer les textes vides
                result = analyzer.analyze_feedback(feedback_req.text)
                results.append(result)
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "results": results,
            "total_processed": len(results),
            "processing_time_ms": round(processing_time, 2),
            "avg_time_per_feedback_ms": round(processing_time / len(results), 2) if results else 0
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse batch : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

@app.get("/stats")
async def get_stats():
    """Statistiques sur les types de feedbacks supportés"""
    from .data.manual_labels import MANUAL_SENTIMENT_LABELS
    
    stats = {
        "supported_feedbacks": len(MANUAL_SENTIMENT_LABELS),
        "feedback_types": list(MANUAL_SENTIMENT_LABELS.keys()),
        "sentiment_distribution": {
            "positive": len([v for v in MANUAL_SENTIMENT_LABELS.values() if 'positive' in v['sentiment_range']]),
            "neutral": len([v for v in MANUAL_SENTIMENT_LABELS.values() if 'neutral' in v['sentiment_range']]),
            "negative": len([v for v in MANUAL_SENTIMENT_LABELS.values() if 'negative' in v['sentiment_range']])
        }
    }
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)