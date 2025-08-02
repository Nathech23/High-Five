#!/usr/bin/env python3
"""
API FastAPI Simplifiée - Système de Prédiction des Stocks de Sang
Version compatible avec les dépendances de base
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

# Configuration
app = FastAPI(
    title="🩸 Blood Stock Prediction API",
    description="Système de prédiction des stocks de sang - Hôpital Général Douala",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles globaux (chargés au démarrage)
simple_model = None
scaler = None
label_encoders = {}
feature_names = []

# Cache en mémoire
prediction_cache = {}
analysis_cache = {}

class BloodStockData(BaseModel):
    """Modèle de données pour une prédiction"""
    hospital: str = Field(..., description="Nom de l'hôpital")
    blood_type: str = Field(..., description="Type de sang (A+, A-, B+, B-, AB+, AB-, O+, O-)")
    stock_initial: float = Field(..., ge=0, description="Stock initial")
    demand: float = Field(..., ge=0, description="Demande")
    supply: float = Field(..., ge=0, description="Approvisionnement")
    temperature: float = Field(..., ge=2, le=8, description="Température de conservation")
    days_to_expiry: int = Field(..., ge=1, le=42, description="Jours avant expiration")
    quality_score: float = Field(..., ge=0, le=100, description="Score de qualité")
    quality_comment: Optional[str] = Field(None, description="Commentaire sur la qualité")

class PredictionRequest(BaseModel):
    """Requête de prédiction"""
    data: List[BloodStockData]
    model_type: str = Field(default="simple", description="Type de modèle (simple)")

class PredictionResponse(BaseModel):
    """Réponse de prédiction"""
    predictions: List[float]
    model_used: str
    processing_time: float
    timestamp: str
    confidence_scores: Optional[List[float]] = None

class AnalysisRequest(BaseModel):
    """Requête d'analyse"""
    data: List[BloodStockData]

class AnalysisResponse(BaseModel):
    """Réponse d'analyse"""
    analyses: List[Dict[str, Any]]
    processing_time: float
    timestamp: str

class SimplePredictor:
    """Prédicteur simple basé sur RandomForest"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.is_trained = False
    
    def prepare_features(self, data: List[BloodStockData]) -> np.ndarray:
        """Prépare les features pour la prédiction"""
        df = pd.DataFrame([item.dict() for item in data])
        
        # Features numériques
        numeric_features = [
            'stock_initial', 'demand', 'supply', 'temperature', 
            'days_to_expiry', 'quality_score'
        ]
        
        # Encoder les variables catégorielles
        if 'hospital' not in self.label_encoders:
            self.label_encoders['hospital'] = LabelEncoder()
            # Fit avec des valeurs par défaut
            hospitals = ['Hôpital Général Douala', 'Hôpital Laquintinie', 'Hôpital de District Bonassama']
            self.label_encoders['hospital'].fit(hospitals)
        
        if 'blood_type' not in self.label_encoders:
            self.label_encoders['blood_type'] = LabelEncoder()
            blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            self.label_encoders['blood_type'].fit(blood_types)
        
        # Encoder les données
        try:
            df['hospital_encoded'] = self.label_encoders['hospital'].transform(df['hospital'])
        except ValueError:
            # Valeur inconnue, utiliser la première classe
            df['hospital_encoded'] = 0
        
        try:
            df['blood_type_encoded'] = self.label_encoders['blood_type'].transform(df['blood_type'])
        except ValueError:
            # Valeur inconnue, utiliser O+
            df['blood_type_encoded'] = 6  # Index de O+
        
        # Features finales
        feature_columns = numeric_features + ['hospital_encoded', 'blood_type_encoded']
        features = df[feature_columns].values
        
        # Scaling
        if self.is_trained:
            features = self.scaler.transform(features)
        
        return features
    
    def train_simple_model(self):
        """Entraîne un modèle simple avec des données synthétiques"""
        # Générer des données d'entraînement simples
        np.random.seed(42)
        n_samples = 1000
        
        # Features aléatoires
        stock_initial = np.random.uniform(10, 100, n_samples)
        demand = np.random.uniform(5, 30, n_samples)
        supply = np.random.uniform(5, 35, n_samples)
        temperature = np.random.uniform(2, 8, n_samples)
        days_to_expiry = np.random.randint(1, 43, n_samples)
        quality_score = np.random.uniform(60, 100, n_samples)
        hospital_encoded = np.random.randint(0, 3, n_samples)
        blood_type_encoded = np.random.randint(0, 8, n_samples)
        
        X = np.column_stack([
            stock_initial, demand, supply, temperature, 
            days_to_expiry, quality_score, hospital_encoded, blood_type_encoded
        ])
        
        # Target: stock final basé sur une formule simple
        y = (stock_initial + supply - demand + 
             np.random.normal(0, 5, n_samples) +  # Bruit
             (quality_score - 80) * 0.1 +  # Impact qualité
             (40 - days_to_expiry) * 0.05)  # Impact expiration
        
        # Assurer que y est positif
        y = np.maximum(y, 0)
        
        # Scaling
        X_scaled = self.scaler.fit_transform(X)
        
        # Entraînement
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        print("✅ Modèle simple entraîné avec succès")
    
    def predict(self, data: List[BloodStockData]) -> tuple:
        """Fait des prédictions"""
        if not self.is_trained:
            self.train_simple_model()
        
        features = self.prepare_features(data)
        predictions = self.model.predict(features)
        
        # Confidence scores (variance des arbres)
        tree_predictions = np.array([tree.predict(features) for tree in self.model.estimators_])
        confidence_scores = 1.0 / (1.0 + np.std(tree_predictions, axis=0))
        
        return predictions.tolist(), confidence_scores.tolist()

class SimpleAnalyzer:
    """Analyseur simple pour les commentaires"""
    
    def __init__(self):
        self.urgency_keywords = {
            'critique': ['urgent', 'critique', 'contamination', 'danger', 'immédiat'],
            'élevée': ['attention', 'problème', 'vérifier', 'rapidement', 'important'],
            'moyenne': ['surveiller', 'observer', 'contrôler', 'bientôt'],
            'faible': ['normal', 'bon', 'excellent', 'parfait', 'stable']
        }
    
    def analyze_urgency(self, comment: str, quality_score: float, days_to_expiry: int) -> Dict[str, Any]:
        """Analyse l'urgence d'un commentaire"""
        if not comment:
            comment = "Aucun commentaire"
        
        comment_lower = comment.lower()
        urgency_score = 0
        detected_keywords = []
        
        # Analyse par mots-clés
        for level, keywords in self.urgency_keywords.items():
            for keyword in keywords:
                if keyword in comment_lower:
                    detected_keywords.append(keyword)
                    if level == 'critique':
                        urgency_score += 30
                    elif level == 'élevée':
                        urgency_score += 20
                    elif level == 'moyenne':
                        urgency_score += 10
                    else:  # faible
                        urgency_score -= 5
        
        # Facteurs numériques
        if quality_score < 70:
            urgency_score += 25
        elif quality_score < 80:
            urgency_score += 10
        
        if days_to_expiry <= 3:
            urgency_score += 30
        elif days_to_expiry <= 7:
            urgency_score += 15
        elif days_to_expiry <= 14:
            urgency_score += 5
        
        # Normaliser le score
        urgency_score = max(0, min(100, urgency_score))
        
        # Déterminer le niveau
        if urgency_score >= 80:
            urgency_level = "CRITIQUE"
            priority = "IMMÉDIATE"
        elif urgency_score >= 60:
            urgency_level = "ÉLEVÉE"
            priority = "24H"
        elif urgency_score >= 40:
            urgency_level = "MOYENNE"
            priority = "SURVEILLANCE"
        else:
            urgency_level = "FAIBLE"
            priority = "ROUTINE"
        
        # Recommandations
        recommendations = []
        if urgency_score >= 80:
            recommendations.extend(["Action immédiate requise", "Alerter l'équipe médicale"])
        elif urgency_score >= 60:
            recommendations.extend(["Vérification dans les 24h", "Surveillance renforcée"])
        elif urgency_score >= 40:
            recommendations.append("Contrôle de routine programmé")
        else:
            recommendations.append("Maintenir la surveillance standard")
        
        return {
            'urgency_score': urgency_score,
            'urgency_level': urgency_level,
            'priority': priority,
            'detected_keywords': detected_keywords,
            'recommendations': recommendations,
            'risk_factors': self._identify_risk_factors(comment_lower, quality_score, days_to_expiry)
        }
    
    def _identify_risk_factors(self, comment: str, quality_score: float, days_to_expiry: int) -> List[str]:
        """Identifie les facteurs de risque"""
        risk_factors = []
        
        if quality_score < 70:
            risk_factors.append("Qualité dégradée")
        if days_to_expiry <= 7:
            risk_factors.append("Expiration proche")
        if any(word in comment for word in ['contamination', 'infection']):
            risk_factors.append("Risque de contamination")
        if any(word in comment for word in ['température', 'chaud', 'froid']):
            risk_factors.append("Problème de température")
        
        return risk_factors

# Initialisation des modèles
simple_predictor = SimplePredictor()
simple_analyzer = SimpleAnalyzer()

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    print("🚀 Démarrage de l'API Blood Stock Prediction")
    print("📊 Chargement du modèle simple...")
    
    # Entraîner le modèle simple
    simple_predictor.train_simple_model()
    
    print("✅ API prête!")

@app.get("/health")
async def health_check():
    """Vérification de santé de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "model_status": "loaded" if simple_predictor.is_trained else "not_loaded",
        "features": [
            "Prédiction des stocks de sang",
            "Analyse d'urgence des commentaires",
            "Recommandations intelligentes"
        ]
    }

@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "🩸 API de Prédiction des Stocks de Sang",
        "hospital": "Hôpital Général Douala",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict_blood_stock(request: PredictionRequest):
    """Prédiction des stocks de sang"""
    start_time = time.time()
    
    try:
        # Vérifier le cache
        cache_key = str(hash(str(request.dict())))
        if cache_key in prediction_cache:
            cached_result = prediction_cache[cache_key]
            cached_result["from_cache"] = True
            return cached_result
        
        # Validation des données
        if not request.data:
            raise HTTPException(status_code=400, detail="Aucune donnée fournie")
        
        # Prédiction
        predictions, confidence_scores = simple_predictor.predict(request.data)
        
        processing_time = time.time() - start_time
        
        result = PredictionResponse(
            predictions=predictions,
            model_used="simple_random_forest",
            processing_time=processing_time,
            timestamp=datetime.now().isoformat(),
            confidence_scores=confidence_scores
        )
        
        # Mettre en cache
        prediction_cache[cache_key] = result.dict()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de prédiction: {str(e)}")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_quality_comments(request: AnalysisRequest):
    """Analyse des commentaires de qualité"""
    start_time = time.time()
    
    try:
        analyses = []
        
        for item in request.data:
            analysis = simple_analyzer.analyze_urgency(
                item.quality_comment or "",
                item.quality_score,
                item.days_to_expiry
            )
            
            # Ajouter les informations contextuelles
            analysis.update({
                'hospital': item.hospital,
                'blood_type': item.blood_type,
                'quality_score': item.quality_score,
                'days_to_expiry': item.days_to_expiry,
                'comment': item.quality_comment or "Aucun commentaire"
            })
            
            analyses.append(analysis)
        
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            analyses=analyses,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")

@app.post("/recommend")
async def get_recommendations(request: AnalysisRequest):
    """Génération de recommandations intelligentes"""
    start_time = time.time()
    
    try:
        recommendations = []
        
        for item in request.data:
            # Analyse d'urgence
            analysis = simple_analyzer.analyze_urgency(
                item.quality_comment or "",
                item.quality_score,
                item.days_to_expiry
            )
            
            # Recommandations spécifiques
            item_recommendations = {
                'hospital': item.hospital,
                'blood_type': item.blood_type,
                'urgency_level': analysis['urgency_level'],
                'priority': analysis['priority'],
                'actions': analysis['recommendations'],
                'risk_factors': analysis['risk_factors']
            }
            
            # Recommandations additionnelles basées sur les données
            if item.stock_initial < 20:
                item_recommendations['actions'].append("Réapprovisionnement urgent")
            
            if item.demand > item.supply:
                item_recommendations['actions'].append("Augmenter les commandes")
            
            if item.temperature < 2 or item.temperature > 8:
                item_recommendations['actions'].append("Vérifier le système de refroidissement")
            
            recommendations.append(item_recommendations)
        
        processing_time = time.time() - start_time
        
        return {
            "recommendations": recommendations,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat(),
            "total_items": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de recommandation: {str(e)}")

@app.get("/stats")
async def get_api_stats():
    """Statistiques de l'API"""
    return {
        "cache_size": {
            "predictions": len(prediction_cache),
            "analyses": len(analysis_cache)
        },
        "model_info": {
            "type": "RandomForestRegressor",
            "trained": simple_predictor.is_trained,
            "features": 8
        },
        "uptime": "Depuis le démarrage",
        "endpoints": [
            "/health", "/predict", "/analyze", "/recommend", "/stats"
        ]
    }

@app.delete("/cache")
async def clear_cache():
    """Vider le cache"""
    global prediction_cache, analysis_cache
    
    cache_sizes = {
        "predictions_cleared": len(prediction_cache),
        "analyses_cleared": len(analysis_cache)
    }
    
    prediction_cache.clear()
    analysis_cache.clear()
    
    return {
        "message": "Cache vidé avec succès",
        "timestamp": datetime.now().isoformat(),
        **cache_sizes
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)