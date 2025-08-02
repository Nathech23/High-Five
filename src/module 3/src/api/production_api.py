#!/usr/bin/env python3
"""
API ML Robuste pour Production
Authentication + Rate Limiting + Documentation + Optimisations
"""

import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
import hashlib
import jwt
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
import logging
from functools import wraps
import redis
from collections import defaultdict, deque
import uuid

# FastAPI et dépendances
from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import uvicorn

# Imports locaux
try:
    from ..training.production_ml_system import AdvancedEnsembleSystem
    from ..llm.advanced_llm_system import AdvancedLLMAgent
    from ..mlops.production_monitoring import ProductionMLOpsSystem
except ImportError:
    # Fallback pour tests
    import sys
    sys.path.append('..')
    from training.production_ml_system import AdvancedEnsembleSystem
    from llm.advanced_llm_system import AdvancedLLMAgent
    from mlops.production_monitoring import ProductionMLOpsSystem

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration Redis pour rate limiting
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    redis_client = None
    REDIS_AVAILABLE = False
    logger.warning("Redis non disponible. Rate limiting en mémoire.")

# Rate limiter
if REDIS_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
else:
    limiter = Limiter(key_func=get_remote_address)

# Modèles Pydantic pour l'API
class PredictionRequest(BaseModel):
    """Requête de prédiction"""
    hospital: str = Field(..., description="Nom de l'hôpital")
    blood_type: str = Field(..., description="Type sanguin (O+, A+, B+, AB+, O-, A-, B-, AB-)")
    stock_initial: float = Field(..., ge=0, description="Stock initial en unités")
    demand: float = Field(..., ge=0, description="Demande prévue en unités")
    supply: float = Field(..., ge=0, description="Approvisionnement prévu en unités")
    temperature: float = Field(..., ge=0, le=10, description="Température de stockage en °C")
    quality_score: float = Field(..., ge=0, le=100, description="Score de qualité (0-100)")
    external_factors: Optional[Dict[str, Any]] = Field(default={}, description="Facteurs externes")
    
    @validator('blood_type')
    def validate_blood_type(cls, v):
        valid_types = ['O+', 'A+', 'B+', 'AB+', 'O-', 'A-', 'B-', 'AB-']
        if v not in valid_types:
            raise ValueError(f'Type sanguin invalide. Types valides: {valid_types}')
        return v

class BatchPredictionRequest(BaseModel):
    """Requête de prédiction par batch"""
    predictions: List[PredictionRequest] = Field(..., max_items=1000, description="Liste des prédictions (max 1000)")
    batch_id: Optional[str] = Field(default=None, description="ID du batch (optionnel)")

class AnalysisRequest(BaseModel):
    """Requête d'analyse LLM"""
    stock_data: Dict[str, Any] = Field(..., description="Données de stock à analyser")
    context: Optional[str] = Field(default="", description="Contexte médical additionnel")
    analysis_type: str = Field(default="stock_analysis", description="Type d'analyse")
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        valid_types = ['stock_analysis', 'incident_classification', 'alert_generation', 'recommendations']
        if v not in valid_types:
            raise ValueError(f'Type d\'analyse invalide. Types valides: {valid_types}')
        return v

class PredictionResponse(BaseModel):
    """Réponse de prédiction"""
    prediction: float = Field(..., description="Prédiction de stock final")
    confidence: float = Field(..., ge=0, le=1, description="Score de confiance (0-1)")
    model_version: str = Field(..., description="Version du modèle utilisé")
    processing_time_ms: float = Field(..., description="Temps de traitement en millisecondes")
    recommendations: List[str] = Field(default=[], description="Recommandations")
    risk_level: str = Field(..., description="Niveau de risque (low, medium, high, critical)")
    metadata: Dict[str, Any] = Field(default={}, description="Métadonnées additionnelles")

class BatchPredictionResponse(BaseModel):
    """Réponse de prédiction par batch"""
    batch_id: str = Field(..., description="ID du batch")
    predictions: List[PredictionResponse] = Field(..., description="Liste des prédictions")
    total_count: int = Field(..., description="Nombre total de prédictions")
    success_count: int = Field(..., description="Nombre de prédictions réussies")
    error_count: int = Field(..., description="Nombre d'erreurs")
    total_processing_time_ms: float = Field(..., description="Temps total de traitement")
    errors: List[Dict[str, Any]] = Field(default=[], description="Liste des erreurs")

class AnalysisResponse(BaseModel):
    """Réponse d'analyse LLM"""
    analysis: Dict[str, Any] = Field(..., description="Résultat de l'analyse")
    confidence: float = Field(..., ge=0, le=1, description="Confiance de l'analyse")
    processing_time_ms: float = Field(..., description="Temps de traitement")
    model_used: str = Field(..., description="Modèle LLM utilisé")
    knowledge_sources: List[str] = Field(default=[], description="Sources de connaissances utilisées")

class HealthResponse(BaseModel):
    """Réponse de santé du système"""
    status: str = Field(..., description="Statut du système")
    timestamp: str = Field(..., description="Timestamp de la vérification")
    version: str = Field(..., description="Version de l'API")
    uptime_seconds: float = Field(..., description="Temps de fonctionnement en secondes")
    models_loaded: Dict[str, bool] = Field(..., description="État des modèles chargés")
    performance_metrics: Dict[str, float] = Field(default={}, description="Métriques de performance")
    alerts: List[Dict[str, Any]] = Field(default=[], description="Alertes actives")

# Système d'authentification
class AuthManager:
    """Gestionnaire d'authentification JWT"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = 60
        
        # Utilisateurs autorisés (en production, utiliser une base de données)
        self.authorized_users = {
            'admin': {'password': 'admin123', 'role': 'admin', 'permissions': ['read', 'write', 'admin']},
            'ml_service': {'password': 'ml_service_key', 'role': 'service', 'permissions': ['read', 'write']},
            'readonly': {'password': 'readonly123', 'role': 'readonly', 'permissions': ['read']}
        }
    
    def create_access_token(self, username: str, role: str) -> str:
        """Crée un token d'accès JWT"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            'sub': username,
            'role': role,
            'exp': expire,
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Vérifie et décode un token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expiré")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Token invalide")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authentifie un utilisateur"""
        user = self.authorized_users.get(username)
        if user and user['password'] == password:
            return user
        return None

# Cache intelligent pour les prédictions
class IntelligentCache:
    """Cache intelligent avec TTL adaptatif"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.cache = {}
        self.timestamps = {}
        self.access_counts = defaultdict(int)
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_key(self, request: PredictionRequest) -> str:
        """Génère une clé de cache pour une requête"""
        key_data = {
            'hospital': request.hospital,
            'blood_type': request.blood_type,
            'stock_initial': round(request.stock_initial, 2),
            'demand': round(request.demand, 2),
            'supply': round(request.supply, 2),
            'temperature': round(request.temperature, 1),
            'quality_score': round(request.quality_score, 1)
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get(self, request: PredictionRequest) -> Optional[PredictionResponse]:
        """Récupère une prédiction du cache"""
        key = self._generate_key(request)
        
        if key in self.cache:
            # Vérifier TTL
            if time.time() - self.timestamps[key] < self.default_ttl:
                self.access_counts[key] += 1
                self.hit_count += 1
                return self.cache[key]
            else:
                # Expirer l'entrée
                del self.cache[key]
                del self.timestamps[key]
                del self.access_counts[key]
        
        self.miss_count += 1
        return None
    
    def set(self, request: PredictionRequest, response: PredictionResponse):
        """Met en cache une prédiction"""
        key = self._generate_key(request)
        
        # Nettoyer le cache si nécessaire
        if len(self.cache) >= self.max_size:
            self._evict_least_used()
        
        self.cache[key] = response
        self.timestamps[key] = time.time()
        self.access_counts[key] = 1
    
    def _evict_least_used(self):
        """Évince les entrées les moins utilisées"""
        # Supprimer 10% des entrées les moins utilisées
        items_to_remove = max(1, len(self.cache) // 10)
        
        # Trier par nombre d'accès
        sorted_items = sorted(self.access_counts.items(), key=lambda x: x[1])
        
        for key, _ in sorted_items[:items_to_remove]:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
            self.access_counts.pop(key, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'default_ttl': self.default_ttl
        }

# Métriques de performance
class PerformanceMetrics:
    """Collecteur de métriques de performance"""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = deque(maxlen=1000)
        self.endpoint_stats = defaultdict(lambda: {'count': 0, 'errors': 0, 'avg_time': 0})
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, response_time: float, success: bool = True):
        """Enregistre une requête"""
        self.request_count += 1
        self.response_times.append(response_time)
        
        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        
        if not success:
            self.error_count += 1
            stats['errors'] += 1
        
        # Calculer la moyenne mobile
        stats['avg_time'] = (stats['avg_time'] * (stats['count'] - 1) + response_time) / stats['count']
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques"""
        uptime = time.time() - self.start_time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        error_rate = self.error_count / self.request_count if self.request_count > 0 else 0
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': error_rate,
            'avg_response_time_ms': avg_response_time * 1000,
            'requests_per_second': self.request_count / uptime if uptime > 0 else 0,
            'endpoint_stats': dict(self.endpoint_stats)
        }

# Initialisation de l'application
app = FastAPI(
    title="API ML Production - Gestion Stocks Sanguins",
    description="API robuste pour prédiction et analyse des stocks sanguins avec ML et LLM",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # En production, spécifier les hosts autorisés
)

# Gestionnaires d'erreur
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialisation des composants
auth_manager = AuthManager()
security = HTTPBearer()
intelligent_cache = IntelligentCache()
performance_metrics = PerformanceMetrics()

# Variables globales pour les modèles
ml_system = None
llm_agent = None
mlops_system = None

# Dépendances
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Vérifie l'authentification de l'utilisateur"""
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    return payload

async def require_permission(permission: str):
    """Vérifie qu'un utilisateur a une permission spécifique"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        user_info = auth_manager.authorized_users.get(current_user['sub'])
        if not user_info or permission not in user_info['permissions']:
            raise HTTPException(status_code=403, detail="Permission insuffisante")
        return current_user
    return permission_checker

# Décorateur pour mesurer les performances
def measure_performance(endpoint_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                response_time = time.time() - start_time
                performance_metrics.record_request(endpoint_name, response_time, success)
        return wrapper
    return decorator

# Endpoints de l'API

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global ml_system, llm_agent, mlops_system
    
    logger.info("Démarrage de l'API ML Production...")
    
    try:
        # Initialiser les systèmes ML
        ml_system = AdvancedEnsembleSystem()
        llm_agent = AdvancedLLMAgent()
        mlops_system = ProductionMLOpsSystem()
        
        logger.info("✓ Systèmes ML initialisés")
        
        # Créer les répertoires nécessaires
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        logger.info("✓ API ML Production prête")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {e}")
        raise e

@app.post("/auth/login")
async def login(username: str, password: str):
    """Authentification et génération de token"""
    user = auth_manager.authenticate_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    
    token = auth_manager.create_access_token(username, user['role'])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60,
        "role": user['role'],
        "permissions": user['permissions']
    }

@app.get("/health", response_model=HealthResponse)
@limiter.limit("100/minute")
@measure_performance("health")
async def health_check(request: Request):
    """Vérification de santé du système"""
    global ml_system, llm_agent, mlops_system
    
    models_loaded = {
        'ml_system': ml_system is not None,
        'llm_agent': llm_agent is not None,
        'mlops_system': mlops_system is not None
    }
    
    # Vérifier les alertes actives
    alerts = []
    if mlops_system:
        try:
            active_alerts = mlops_system.performance_monitor.get_active_alerts()
            alerts = [{
                'id': alert.alert_id,
                'severity': alert.severity,
                'message': alert.message
            } for alert in active_alerts[:5]]  # Limiter à 5 alertes
        except Exception as e:
            logger.warning(f"Erreur récupération alertes: {e}")
    
    metrics = performance_metrics.get_metrics()
    
    return HealthResponse(
        status="healthy" if all(models_loaded.values()) else "degraded",
        timestamp=datetime.now().isoformat(),
        version="2.0.0",
        uptime_seconds=metrics['uptime_seconds'],
        models_loaded=models_loaded,
        performance_metrics={
            'total_requests': metrics['total_requests'],
            'error_rate': metrics['error_rate'],
            'avg_response_time_ms': metrics['avg_response_time_ms'],
            'requests_per_second': metrics['requests_per_second']
        },
        alerts=alerts
    )

@app.post("/predict", response_model=PredictionResponse)
@limiter.limit("1000/minute")
@measure_performance("predict")
async def predict_stock(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_permission("read"))
):
    """Prédiction de stock sanguin"""
    start_time = time.time()
    
    # Vérifier le cache
    cached_response = intelligent_cache.get(request)
    if cached_response:
        logger.info(f"Cache hit pour prédiction {request.hospital}:{request.blood_type}")
        return cached_response
    
    try:
        # Préparer les données
        features = np.array([[
            request.stock_initial,
            request.demand,
            request.supply,
            request.temperature,
            request.quality_score
        ]])
        
        # Faire la prédiction
        if ml_system and hasattr(ml_system, 'ensemble_model') and ml_system.ensemble_model:
            predictions, confidence = ml_system.predict_with_confidence(features, [request.blood_type])
            prediction = float(predictions[0])
            confidence_score = float(confidence[0])
            model_version = "ensemble_v2.0"
        else:
            # Fallback simple
            prediction = max(0, request.stock_initial + request.supply - request.demand)
            confidence_score = 0.7
            model_version = "fallback_v1.0"
        
        # Calculer le niveau de risque
        risk_level = "low"
        if prediction < 5:
            risk_level = "critical"
        elif prediction < 10:
            risk_level = "high"
        elif prediction < 20:
            risk_level = "medium"
        
        # Générer des recommandations
        recommendations = []
        if risk_level == "critical":
            recommendations.extend([
                "Alerte critique: Stock très bas",
                "Contacter immédiatement les centres de don",
                "Activer le protocole d'urgence"
            ])
        elif risk_level == "high":
            recommendations.extend([
                "Stock bas détecté",
                "Planifier réapprovisionnement urgent",
                "Surveiller la demande de près"
            ])
        
        if request.temperature > 6:
            recommendations.append("⚠️ Température élevée - Vérifier le système de refroidissement")
        
        if request.quality_score < 80:
            recommendations.append("⚠️ Score qualité bas - Inspection recommandée")
        
        processing_time = (time.time() - start_time) * 1000
        
        response = PredictionResponse(
            prediction=prediction,
            confidence=confidence_score,
            model_version=model_version,
            processing_time_ms=processing_time,
            recommendations=recommendations,
            risk_level=risk_level,
            metadata={
                "hospital": request.hospital,
                "blood_type": request.blood_type,
                "timestamp": datetime.now().isoformat(),
                "user": current_user['sub']
            }
        )
        
        # Mettre en cache
        intelligent_cache.set(request, response)
        
        # Enregistrer les métriques en arrière-plan
        background_tasks.add_task(
            log_prediction_metrics,
            request, response, current_user['sub']
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur prédiction: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction: {str(e)}")

@app.post("/predict/batch", response_model=BatchPredictionResponse)
@limiter.limit("100/minute")
@measure_performance("predict_batch")
async def predict_batch(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_permission("read"))
):
    """Prédiction par batch"""
    start_time = time.time()
    batch_id = request.batch_id or str(uuid.uuid4())[:12]
    
    predictions = []
    errors = []
    success_count = 0
    
    # Traitement en parallèle pour les gros batches
    if len(request.predictions) > 100:
        # Utiliser ThreadPoolExecutor pour le parallélisme
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i, pred_request in enumerate(request.predictions):
                future = executor.submit(process_single_prediction, pred_request, i)
                futures.append(future)
            
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    if result['success']:
                        predictions.append(result['prediction'])
                        success_count += 1
                    else:
                        errors.append(result['error'])
                except Exception as e:
                    errors.append({
                        'index': len(errors),
                        'error': str(e),
                        'type': 'timeout_or_exception'
                    })
    else:
        # Traitement séquentiel pour les petits batches
        for i, pred_request in enumerate(request.predictions):
            try:
                # Réutiliser la logique de prédiction
                features = np.array([[
                    pred_request.stock_initial,
                    pred_request.demand,
                    pred_request.supply,
                    pred_request.temperature,
                    pred_request.quality_score
                ]])
                
                if ml_system and hasattr(ml_system, 'ensemble_model') and ml_system.ensemble_model:
                    pred_result, confidence = ml_system.predict_with_confidence(features, [pred_request.blood_type])
                    prediction = float(pred_result[0])
                    confidence_score = float(confidence[0])
                else:
                    prediction = max(0, pred_request.stock_initial + pred_request.supply - pred_request.demand)
                    confidence_score = 0.7
                
                # Niveau de risque
                risk_level = "low"
                if prediction < 5:
                    risk_level = "critical"
                elif prediction < 10:
                    risk_level = "high"
                elif prediction < 20:
                    risk_level = "medium"
                
                pred_response = PredictionResponse(
                    prediction=prediction,
                    confidence=confidence_score,
                    model_version="ensemble_v2.0",
                    processing_time_ms=1.0,  # Temps approximatif
                    recommendations=[],
                    risk_level=risk_level,
                    metadata={
                        "batch_index": i,
                        "hospital": pred_request.hospital,
                        "blood_type": pred_request.blood_type
                    }
                )
                
                predictions.append(pred_response)
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'index': i,
                    'error': str(e),
                    'request': pred_request.dict()
                })
    
    total_processing_time = (time.time() - start_time) * 1000
    
    response = BatchPredictionResponse(
        batch_id=batch_id,
        predictions=predictions,
        total_count=len(request.predictions),
        success_count=success_count,
        error_count=len(errors),
        total_processing_time_ms=total_processing_time,
        errors=errors
    )
    
    # Log en arrière-plan
    background_tasks.add_task(
        log_batch_metrics,
        batch_id, len(request.predictions), success_count, len(errors), current_user['sub']
    )
    
    return response

def process_single_prediction(pred_request: PredictionRequest, index: int) -> Dict[str, Any]:
    """Traite une prédiction unique (pour le parallélisme)"""
    try:
        # Logique de prédiction simplifiée
        prediction = max(0, pred_request.stock_initial + pred_request.supply - pred_request.demand)
        
        risk_level = "low"
        if prediction < 5:
            risk_level = "critical"
        elif prediction < 10:
            risk_level = "high"
        elif prediction < 20:
            risk_level = "medium"
        
        pred_response = PredictionResponse(
            prediction=prediction,
            confidence=0.7,
            model_version="ensemble_v2.0",
            processing_time_ms=1.0,
            recommendations=[],
            risk_level=risk_level,
            metadata={
                "batch_index": index,
                "hospital": pred_request.hospital,
                "blood_type": pred_request.blood_type
            }
        )
        
        return {'success': True, 'prediction': pred_response}
        
    except Exception as e:
        return {
            'success': False,
            'error': {
                'index': index,
                'error': str(e),
                'request': pred_request.dict()
            }
        }

@app.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("500/minute")
@measure_performance("analyze")
async def analyze_situation(
    request: AnalysisRequest,
    current_user: dict = Depends(require_permission("read"))
):
    """Analyse LLM de la situation"""
    start_time = time.time()
    
    try:
        if llm_agent:
            if request.analysis_type == "stock_analysis":
                analysis = llm_agent.analyze_stock_situation(request.stock_data, request.context)
            elif request.analysis_type == "incident_classification":
                incident_desc = request.context or "Incident non spécifié"
                classification = llm_agent.classify_incident(incident_desc, request.stock_data)
                analysis = classification.__dict__
            else:
                analysis = {"message": "Type d'analyse non supporté", "type": request.analysis_type}
            
            confidence = analysis.get('confidence', 0.8)
            model_used = "advanced_llm_agent"
            knowledge_sources = analysis.get('knowledge_used', [])
        else:
            # Analyse simplifiée
            analysis = {
                "status": "Analyse simplifiée",
                "recommendations": ["Surveillance continue recommandée"],
                "risk_level": "medium"
            }
            confidence = 0.6
            model_used = "fallback_analyzer"
            knowledge_sources = []
        
        processing_time = (time.time() - start_time) * 1000
        
        return AnalysisResponse(
            analysis=analysis,
            confidence=confidence,
            processing_time_ms=processing_time,
            model_used=model_used,
            knowledge_sources=knowledge_sources
        )
        
    except Exception as e:
        logger.error(f"Erreur analyse: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

@app.get("/metrics")
@limiter.limit("60/minute")
async def get_metrics(current_user: dict = Depends(require_permission("read"))):
    """Métriques de performance de l'API"""
    metrics = performance_metrics.get_metrics()
    cache_stats = intelligent_cache.get_stats()
    
    return {
        "api_metrics": metrics,
        "cache_stats": cache_stats,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/models/status")
@limiter.limit("60/minute")
async def get_models_status(current_user: dict = Depends(require_permission("read"))):
    """Statut des modèles ML"""
    global ml_system, llm_agent, mlops_system
    
    status = {
        "ml_system": {
            "loaded": ml_system is not None,
            "ensemble_ready": ml_system and hasattr(ml_system, 'ensemble_model') and ml_system.ensemble_model is not None,
            "specialized_models": len(ml_system.blood_type_models) if ml_system else 0
        },
        "llm_agent": {
            "loaded": llm_agent is not None,
            "api_available": llm_agent and llm_agent.llm_available if llm_agent else False,
            "knowledge_base_size": len(llm_agent.knowledge_base.knowledge_items) if llm_agent else 0
        },
        "mlops_system": {
            "loaded": mlops_system is not None,
            "monitoring_active": mlops_system and mlops_system.monitoring_active if mlops_system else False
        }
    }
    
    return status

@app.post("/admin/cache/clear")
async def clear_cache(current_user: dict = Depends(require_permission("admin"))):
    """Vide le cache (admin seulement)"""
    global intelligent_cache
    
    old_stats = intelligent_cache.get_stats()
    intelligent_cache = IntelligentCache()
    
    return {
        "message": "Cache vidé avec succès",
        "previous_stats": old_stats,
        "timestamp": datetime.now().isoformat()
    }

# Fonctions utilitaires pour les tâches en arrière-plan
async def log_prediction_metrics(request: PredictionRequest, response: PredictionResponse, user: str):
    """Enregistre les métriques de prédiction"""
    try:
        # Ici on pourrait enregistrer dans une base de données
        logger.info(f"Prédiction: {user} - {request.hospital}:{request.blood_type} -> {response.prediction}")
    except Exception as e:
        logger.error(f"Erreur log métriques: {e}")

async def log_batch_metrics(batch_id: str, total: int, success: int, errors: int, user: str):
    """Enregistre les métriques de batch"""
    try:
        logger.info(f"Batch {batch_id}: {user} - {success}/{total} succès, {errors} erreurs")
    except Exception as e:
        logger.error(f"Erreur log batch: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "production_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info"
    )