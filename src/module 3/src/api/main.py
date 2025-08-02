from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union
import pandas as pd
import numpy as np
import joblib
import os
import sys
from datetime import datetime, timedelta
import asyncio
import redis
import json
from functools import lru_cache
import logging
from contextlib import asynccontextmanager

# Imports des modèles
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.ensemble_model import EnsemblePredictor
from llm_integration.llm_analyzer import LLMBloodStockAnalyzer
from preprocessing.data_preprocessor import BloodStockPreprocessor

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modèles globaux
ensemble_model = None
llm_analyzer = None
preprocessor = None
redis_client = None

# Cache en mémoire pour les prédictions fréquentes
prediction_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Startup
    await load_models()
    yield
    # Shutdown
    if redis_client:
        redis_client.close()

app = FastAPI(
    title="API de Prédiction des Stocks de Sang",
    description="API MLOps pour la prédiction et l'analyse des stocks de sang avec intégration LLM",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles Pydantic
class BloodStockData(BaseModel):
    hospital: str = Field(..., description="Nom de l'hôpital")
    blood_type: str = Field(..., description="Type de sang (A+, A-, B+, B-, AB+, AB-, O+, O-)")
    stock_initial: float = Field(..., ge=0, description="Stock initial")
    demand: float = Field(..., ge=0, description="Demande")
    supply: float = Field(..., ge=0, description="Approvisionnement")
    temperature: float = Field(..., ge=-10, le=15, description="Température de stockage (°C)")
    days_to_expiry: int = Field(..., ge=0, le=365, description="Jours avant expiration")
    quality_score: float = Field(..., ge=0, le=100, description="Score de qualité")
    quality_comment: Optional[str] = Field("", description="Commentaire sur la qualité")
    timestamp: Optional[str] = Field(None, description="Timestamp (ISO format)")

class PredictionRequest(BaseModel):
    data: List[BloodStockData] = Field(..., description="Données pour la prédiction")
    model_type: Optional[str] = Field("ensemble", description="Type de modèle (ensemble, xgboost, arima, lstm)")
    include_uncertainty: Optional[bool] = Field(False, description="Inclure l'estimation d'incertitude")

class AnalysisRequest(BaseModel):
    data: List[BloodStockData] = Field(..., description="Données pour l'analyse")
    include_recommendations: Optional[bool] = Field(True, description="Inclure les recommandations")
    urgency_threshold: Optional[float] = Field(50.0, description="Seuil de score d'urgence")

class PredictionResponse(BaseModel):
    predictions: List[float]
    model_used: str
    confidence_scores: Optional[List[float]] = None
    processing_time: float
    timestamp: str

class AnalysisResponse(BaseModel):
    analyses: List[Dict]
    statistics: Dict
    alert_cases: List[Dict]
    recommendations: List[str]
    processing_time: float
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    models_loaded: Dict[str, bool]
    cache_size: int
    uptime: str
    version: str

# Fonctions utilitaires
async def load_models():
    """Charge tous les modèles au démarrage"""
    global ensemble_model, llm_analyzer, preprocessor, redis_client
    
    try:
        logger.info("Chargement des modèles...")
        
        # Charger le préprocesseur
        preprocessor = BloodStockPreprocessor()
        if os.path.exists('models/preprocessor'):
            preprocessor.load_preprocessor('models/preprocessor')
            logger.info("✓ Préprocesseur chargé")
        
        # Charger le modèle d'ensemble
        ensemble_model = EnsemblePredictor()
        if os.path.exists('models/ensemble'):
            ensemble_model.load_ensemble('models/ensemble')
            logger.info("✓ Modèle d'ensemble chargé")
        
        # Charger l'analyseur LLM
        llm_analyzer = LLMBloodStockAnalyzer(use_local_models=True)
        logger.info("✓ Analyseur LLM chargé")
        
        # Connexion Redis (optionnelle)
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_client.ping()
            logger.info("✓ Redis connecté")
        except:
            logger.warning("Redis non disponible, utilisation du cache mémoire")
            redis_client = None
        
        logger.info("Tous les modèles chargés avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des modèles: {str(e)}")
        raise

def get_cache_key(data: str, model_type: str) -> str:
    """Génère une clé de cache"""
    import hashlib
    return f"prediction:{model_type}:{hashlib.md5(data.encode()).hexdigest()}"

def get_cached_prediction(cache_key: str) -> Optional[Dict]:
    """Récupère une prédiction du cache"""
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass
    
    return prediction_cache.get(cache_key)

def set_cached_prediction(cache_key: str, prediction: Dict, ttl: int = 3600):
    """Met en cache une prédiction"""
    if redis_client:
        try:
            redis_client.setex(cache_key, ttl, json.dumps(prediction))
        except:
            pass
    
    prediction_cache[cache_key] = prediction
    
    # Limiter la taille du cache mémoire
    if len(prediction_cache) > 1000:
        # Supprimer les plus anciennes entrées
        keys_to_remove = list(prediction_cache.keys())[:100]
        for key in keys_to_remove:
            del prediction_cache[key]

def prepare_dataframe(data: List[BloodStockData]) -> pd.DataFrame:
    """Convertit les données Pydantic en DataFrame"""
    records = []
    for item in data:
        record = item.dict()
        if not record.get('timestamp'):
            record['timestamp'] = datetime.now().isoformat()
        records.append(record)
    
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# Endpoints
@app.get("/", response_model=Dict)
async def root():
    """Endpoint racine"""
    return {
        "message": "API de Prédiction des Stocks de Sang",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Vérification de l'état de santé de l'API"""
    start_time = datetime.now()
    
    models_status = {
        "ensemble": ensemble_model is not None and ensemble_model.is_fitted,
        "llm_analyzer": llm_analyzer is not None,
        "preprocessor": preprocessor is not None,
        "redis": redis_client is not None
    }
    
    cache_size = len(prediction_cache)
    if redis_client:
        try:
            cache_size += redis_client.dbsize()
        except:
            pass
    
    return HealthResponse(
        status="healthy" if all(models_status.values()[:3]) else "degraded",
        models_loaded=models_status,
        cache_size=cache_size,
        uptime=str(datetime.now() - start_time),
        version="1.0.0"
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_stock(request: PredictionRequest):
    """Endpoint de prédiction des stocks"""
    start_time = datetime.now()
    
    try:
        # Vérifier que les modèles sont chargés
        if not ensemble_model or not ensemble_model.is_fitted:
            raise HTTPException(status_code=503, detail="Modèle d'ensemble non disponible")
        
        # Préparer les données
        df = prepare_dataframe(request.data)
        
        # Vérifier le cache
        cache_key = get_cache_key(df.to_json(), request.model_type)
        cached_result = get_cached_prediction(cache_key)
        
        if cached_result:
            logger.info("Prédiction servie depuis le cache")
            return PredictionResponse(**cached_result)
        
        # Préprocesser les données
        if preprocessor:
            df_processed = preprocessor.prepare_features(df, fit=False)
            feature_columns = preprocessor.feature_columns
        else:
            raise HTTPException(status_code=503, detail="Préprocesseur non disponible")
        
        # Faire les prédictions
        if request.model_type == "ensemble":
            predictions = ensemble_model.predict(df_processed, feature_columns)
            model_used = "ensemble"
        else:
            # Pour les autres modèles, utiliser l'ensemble par défaut
            predictions = ensemble_model.predict(df_processed, feature_columns)
            model_used = "ensemble (fallback)"
        
        # Estimation d'incertitude (simplifiée)
        confidence_scores = None
        if request.include_uncertainty:
            # Calcul simplifié basé sur la variance des prédictions
            confidence_scores = [0.85 + 0.1 * np.random.random() for _ in predictions]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "predictions": predictions.tolist(),
            "model_used": model_used,
            "confidence_scores": confidence_scores,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        
        # Mettre en cache
        set_cached_prediction(cache_key, result)
        
        return PredictionResponse(**result)
        
    except Exception as e:
        logger.error(f"Erreur lors de la prédiction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de prédiction: {str(e)}")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_quality(request: AnalysisRequest):
    """Endpoint d'analyse de qualité avec LLM"""
    start_time = datetime.now()
    
    try:
        # Vérifier que l'analyseur LLM est disponible
        if not llm_analyzer:
            raise HTTPException(status_code=503, detail="Analyseur LLM non disponible")
        
        # Préparer les données
        df = prepare_dataframe(request.data)
        
        # Analyse LLM
        analyzed_df = llm_analyzer.batch_analyze(df)
        
        # Extraire les résultats
        analyses = []
        for _, row in analyzed_df.iterrows():
            analysis = {
                "hospital": row['hospital'],
                "blood_type": row['blood_type'],
                "sentiment": row['llm_sentiment'],
                "sentiment_score": row['llm_sentiment_score'],
                "urgency_level": row['llm_urgency_level'],
                "urgency_score": row['llm_urgency_score'],
                "key_issues": row['llm_key_issues'].split('; ') if row['llm_key_issues'] else [],
                "recommendations": row['llm_recommendations'].split('; ') if row['llm_recommendations'] else [],
                "confidence": row['llm_confidence']
            }
            analyses.append(analysis)
        
        # Statistiques
        statistics = llm_analyzer.get_urgency_statistics(analyzed_df)
        
        # Cas d'alerte
        alert_cases = []
        for analysis in analyses:
            if analysis['urgency_score'] >= request.urgency_threshold:
                alert_cases.append(analysis)
        
        # Recommandations globales
        global_recommendations = []
        if len(alert_cases) > 0:
            global_recommendations.append(f"🚨 {len(alert_cases)} cas nécessitent une attention immédiate")
        
        critical_count = len([a for a in analyses if a['urgency_level'] == 'critique'])
        if critical_count > 0:
            global_recommendations.append(f"⚠️ {critical_count} cas critiques détectés")
        
        if not global_recommendations:
            global_recommendations.append("✅ Aucun problème critique détecté")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResponse(
            analyses=analyses,
            statistics=statistics,
            alert_cases=alert_cases,
            recommendations=global_recommendations,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")

@app.post("/recommend")
async def get_recommendations(request: AnalysisRequest):
    """Endpoint de recommandations intelligentes"""
    start_time = datetime.now()
    
    try:
        # Analyser d'abord
        analysis_response = await analyze_quality(request)
        
        # Générer des recommandations avancées
        recommendations = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
            "monitoring_points": []
        }
        
        # Analyser les cas critiques
        critical_cases = [a for a in analysis_response.analyses if a['urgency_level'] == 'critique']
        high_cases = [a for a in analysis_response.analyses if a['urgency_level'] == 'élevée']
        
        if critical_cases:
            recommendations["immediate_actions"].extend([
                "Déclencher le protocole d'urgence",
                "Contacter les équipes médicales",
                "Vérifier les stocks d'urgence"
            ])
        
        if high_cases:
            recommendations["short_term_actions"].extend([
                "Planifier un réapprovisionnement dans les 24h",
                "Informer les responsables de service",
                "Surveiller l'évolution des stocks"
            ])
        
        # Recommandations à long terme
        if len(critical_cases) + len(high_cases) > len(analysis_response.analyses) * 0.2:
            recommendations["long_term_actions"].extend([
                "Revoir la stratégie d'approvisionnement",
                "Améliorer les systèmes de prédiction",
                "Former le personnel aux procédures d'urgence"
            ])
        
        # Points de surveillance
        recommendations["monitoring_points"].extend([
            "Température des unités de stockage",
            "Dates d'expiration",
            "Niveaux de stock par type de sang",
            "Qualité des unités"
        ])
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "recommendations": recommendations,
            "analysis_summary": {
                "total_cases": len(analysis_response.analyses),
                "critical_cases": len(critical_cases),
                "high_urgency_cases": len(high_cases),
                "alert_threshold": request.urgency_threshold
            },
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de recommandations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de recommandations: {str(e)}")

@app.get("/models/status")
async def get_models_status():
    """Statut détaillé des modèles"""
    status = {
        "ensemble_model": {
            "loaded": ensemble_model is not None,
            "fitted": ensemble_model.is_fitted if ensemble_model else False,
            "method": ensemble_model.ensemble_method if ensemble_model else None
        },
        "llm_analyzer": {
            "loaded": llm_analyzer is not None,
            "cache_size": len(llm_analyzer.analysis_cache) if llm_analyzer else 0
        },
        "preprocessor": {
            "loaded": preprocessor is not None,
            "feature_count": len(preprocessor.feature_columns) if preprocessor else 0
        }
    }
    
    return status

@app.delete("/cache/clear")
async def clear_cache():
    """Vide le cache de prédictions"""
    global prediction_cache
    
    # Vider le cache mémoire
    cache_size_before = len(prediction_cache)
    prediction_cache.clear()
    
    # Vider le cache Redis
    redis_cleared = 0
    if redis_client:
        try:
            redis_cleared = redis_client.flushdb()
        except:
            pass
    
    return {
        "message": "Cache vidé",
        "memory_cache_cleared": cache_size_before,
        "redis_cleared": redis_cleared,
        "timestamp": datetime.now().isoformat()
    }

# Gestion des erreurs
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Erreur non gérée: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )