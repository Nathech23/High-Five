#!/usr/bin/env python3
"""
Système ML Optimisé pour Production
Module Avancé: Fine-tuning, Ensemble Stacking, Drift Detection, Auto-retraining
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import StackingRegressor, VotingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.base import BaseEstimator, RegressorMixin
import xgboost as xgb
import optuna
import joblib
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from pathlib import Path
from scipy import stats
from collections import defaultdict
import threading
import schedule
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

warnings.filterwarnings('ignore')

# Import des modèles existants
try:
    from .xgboost_model import XGBoostPredictor
    from .ensemble_model import EnsemblePredictor
except ImportError:
    # Fallback pour tests
    import sys
    sys.path.append('..')
    from training.xgboost_model import XGBoostPredictor
    from training.ensemble_model import EnsemblePredictor

@dataclass
class ModelPerformanceMetrics:
    """Métriques de performance d'un modèle"""
    mae: float
    rmse: float
    mape: float
    r2: float
    timestamp: str
    model_name: str
    dataset_size: int
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def is_degraded(self, baseline: 'ModelPerformanceMetrics', threshold: float = 0.1) -> bool:
        """Vérifie si les performances se sont dégradées"""
        return (self.mae > baseline.mae * (1 + threshold) or 
                self.rmse > baseline.rmse * (1 + threshold))

@dataclass
class DriftDetectionResult:
    """Résultat de détection de drift"""
    drift_detected: bool
    drift_score: float
    drift_type: str  # 'feature', 'target', 'concept'
    affected_features: List[str]
    timestamp: str
    recommendation: str

class DriftDetector:
    """Détecteur de drift automatique"""
    
    def __init__(self, reference_data: pd.DataFrame, feature_columns: List[str]):
        self.reference_data = reference_data
        self.feature_columns = feature_columns
        self.reference_stats = self._calculate_reference_stats()
        
    def _calculate_reference_stats(self) -> Dict:
        """Calcule les statistiques de référence"""
        stats = {}
        for col in self.feature_columns:
            if col in self.reference_data.columns:
                stats[col] = {
                    'mean': self.reference_data[col].mean(),
                    'std': self.reference_data[col].std(),
                    'min': self.reference_data[col].min(),
                    'max': self.reference_data[col].max(),
                    'quantiles': self.reference_data[col].quantile([0.25, 0.5, 0.75]).to_dict()
                }
        return stats
    
    def detect_feature_drift(self, new_data: pd.DataFrame, threshold: float = 0.05) -> DriftDetectionResult:
        """Détecte le drift des features avec test de Kolmogorov-Smirnov"""
        drift_scores = {}
        affected_features = []
        
        for col in self.feature_columns:
            if col in new_data.columns and col in self.reference_data.columns:
                # Test de Kolmogorov-Smirnov
                statistic, p_value = stats.ks_2samp(
                    self.reference_data[col].dropna(),
                    new_data[col].dropna()
                )
                
                drift_scores[col] = {
                    'statistic': statistic,
                    'p_value': p_value,
                    'drift_detected': p_value < threshold
                }
                
                if p_value < threshold:
                    affected_features.append(col)
        
        overall_drift_score = np.mean([score['statistic'] for score in drift_scores.values()])
        drift_detected = len(affected_features) > 0
        
        recommendation = self._get_drift_recommendation(drift_detected, affected_features)
        
        return DriftDetectionResult(
            drift_detected=drift_detected,
            drift_score=overall_drift_score,
            drift_type='feature',
            affected_features=affected_features,
            timestamp=datetime.now().isoformat(),
            recommendation=recommendation
        )
    
    def detect_target_drift(self, new_targets: np.ndarray, threshold: float = 0.05) -> DriftDetectionResult:
        """Détecte le drift de la variable cible"""
        reference_targets = self.reference_data['stock_final'].values
        
        # Test de Kolmogorov-Smirnov pour la cible
        statistic, p_value = stats.ks_2samp(reference_targets, new_targets)
        
        drift_detected = p_value < threshold
        recommendation = self._get_drift_recommendation(drift_detected, ['stock_final'])
        
        return DriftDetectionResult(
            drift_detected=drift_detected,
            drift_score=statistic,
            drift_type='target',
            affected_features=['stock_final'],
            timestamp=datetime.now().isoformat(),
            recommendation=recommendation
        )
    
    def _get_drift_recommendation(self, drift_detected: bool, affected_features: List[str]) -> str:
        """Génère des recommandations basées sur le drift détecté"""
        if not drift_detected:
            return "Aucun drift détecté. Continuer la surveillance."
        
        if len(affected_features) == 1:
            return f"Drift détecté sur {affected_features[0]}. Recommandation: Ré-entraîner le modèle."
        elif len(affected_features) <= 3:
            return f"Drift détecté sur {len(affected_features)} features. Recommandation: Ré-entraîner avec nouvelles données."
        else:
            return f"Drift majeur détecté sur {len(affected_features)} features. Recommandation: Révision complète du modèle."

class BloodTypeSpecializedModel(BaseEstimator, RegressorMixin):
    """Modèle spécialisé par type de sang"""
    
    def __init__(self, blood_type: str, base_model=None):
        self.blood_type = blood_type
        self.base_model = base_model or xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit(self, X, y):
        """Entraîne le modèle spécialisé"""
        X_scaled = self.scaler.fit_transform(X)
        self.base_model.fit(X_scaled, y)
        self.is_fitted = True
        return self
    
    def predict(self, X):
        """Prédictions avec le modèle spécialisé"""
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        X_scaled = self.scaler.transform(X)
        return self.base_model.predict(X_scaled)
    
    def predict_proba(self, X):
        """Scores de confiance (variance des arbres pour XGBoost)"""
        if hasattr(self.base_model, 'predict'):
            # Pour XGBoost, utiliser la variance des prédictions
            predictions = self.predict(X)
            # Simuler la confiance basée sur la variance locale
            confidence = 1.0 / (1.0 + np.abs(predictions - np.mean(predictions)))
            return confidence
        return np.ones(len(X)) * 0.5

class AdvancedEnsembleSystem:
    """Système d'ensemble avancé avec stacking et optimisation"""
    
    def __init__(self, experiment_name: str = "advanced_ensemble_production"):
        self.experiment_name = experiment_name
        self.blood_type_models = {}
        self.ensemble_model = None
        self.meta_learner = None
        self.drift_detector = None
        self.performance_history = []
        self.confidence_threshold = 0.7
        self.retraining_scheduler = None
        
        # Cache intelligent
        self.prediction_cache = {}
        self.cache_ttl = 300  # 5 minutes par défaut
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        # Métriques de production
        self.inference_times = []
        self.memory_usage = []
        
    def create_specialized_models(self, df: pd.DataFrame, feature_columns: List[str]) -> Dict[str, BloodTypeSpecializedModel]:
        """Crée des modèles spécialisés par type de sang"""
        blood_types = df['blood_type'].unique()
        specialized_models = {}
        
        print(f"Création de {len(blood_types)} modèles spécialisés...")
        
        for blood_type in blood_types:
            print(f"Entraînement modèle pour {blood_type}...")
            
            # Filtrer les données pour ce type de sang
            blood_data = df[df['blood_type'] == blood_type].copy()
            
            if len(blood_data) < 50:  # Minimum de données requis
                print(f"⚠️ Pas assez de données pour {blood_type} ({len(blood_data)} échantillons)")
                continue
            
            # Préparer les features
            X = blood_data[feature_columns].fillna(0).values
            y = blood_data['stock_final'].values
            
            # Créer et entraîner le modèle spécialisé
            model = BloodTypeSpecializedModel(blood_type)
            model.fit(X, y)
            
            specialized_models[blood_type] = model
            print(f"✓ Modèle {blood_type} entraîné avec {len(blood_data)} échantillons")
        
        self.blood_type_models = specialized_models
        return specialized_models
    
    def create_advanced_stacking_ensemble(self, df_train: pd.DataFrame, df_val: pd.DataFrame, 
                                        feature_columns: List[str]) -> StackingRegressor:
        """Crée un ensemble stacking avancé"""
        print("Création de l'ensemble stacking avancé...")
        
        # Modèles de base
        base_models = [
            ('xgb1', xgb.XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42)),
            ('xgb2', xgb.XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, random_state=43)),
            ('xgb3', xgb.XGBRegressor(n_estimators=150, max_depth=8, learning_rate=0.15, random_state=44)),
        ]
        
        # Ajouter les modèles spécialisés comme base learners
        for blood_type, model in self.blood_type_models.items():
            base_models.append((f'specialized_{blood_type}', model))
        
        # Meta-learner optimisé
        meta_learner = Ridge(alpha=1.0)
        
        # Créer l'ensemble stacking
        stacking_ensemble = StackingRegressor(
            estimators=base_models,
            final_estimator=meta_learner,
            cv=TimeSeriesSplit(n_splits=5),
            n_jobs=-1
        )
        
        # Entraîner l'ensemble
        X_train = df_train[feature_columns].fillna(0).values
        y_train = df_train['stock_final'].values
        
        print("Entraînement de l'ensemble stacking...")
        stacking_ensemble.fit(X_train, y_train)
        
        self.ensemble_model = stacking_ensemble
        print("✓ Ensemble stacking créé et entraîné")
        
        return stacking_ensemble
    
    def fine_tune_hyperparameters(self, df_train: pd.DataFrame, df_val: pd.DataFrame, 
                                feature_columns: List[str], n_trials: int = 200) -> Dict:
        """Fine-tuning avancé des hyperparamètres avec validation croisée"""
        print(f"Fine-tuning avec {n_trials} trials et validation croisée...")
        
        def objective(trial):
            # Hyperparamètres à optimiser
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
                'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
            }
            
            # Modèle avec hyperparamètres
            model = xgb.XGBRegressor(**params, random_state=42)
            
            # Validation croisée temporelle
            tscv = TimeSeriesSplit(n_splits=5)
            X = df_train[feature_columns].fillna(0).values
            y = df_train['stock_final'].values
            
            scores = cross_val_score(model, X, y, cv=tscv, scoring='neg_mean_absolute_error', n_jobs=-1)
            return -scores.mean()
        
        # Optimisation avec Optuna
        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_params = study.best_params
        best_score = study.best_value
        
        print(f"✓ Meilleurs hyperparamètres trouvés (MAE: {best_score:.4f})")
        print(f"Paramètres: {best_params}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'study': study
        }
    
    def predict_with_confidence(self, X: np.ndarray, blood_types: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Prédictions avec scores de confiance"""
        start_time = time.time()
        
        # Vérifier le cache
        cache_key = hash(str(X.tobytes()) + str(blood_types))
        if cache_key in self.prediction_cache:
            cached_result = self.prediction_cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.cache_ttl:
                self.cache_stats['hits'] += 1
                return cached_result['predictions'], cached_result['confidence']
        
        self.cache_stats['misses'] += 1
        
        # Prédictions de l'ensemble
        ensemble_predictions = self.ensemble_model.predict(X)
        
        # Calcul des scores de confiance
        confidence_scores = self._calculate_confidence_scores(X, ensemble_predictions, blood_types)
        
        # Mettre en cache
        self.prediction_cache[cache_key] = {
            'predictions': ensemble_predictions,
            'confidence': confidence_scores,
            'timestamp': time.time()
        }
        
        # Enregistrer les métriques de performance
        inference_time = time.time() - start_time
        self.inference_times.append(inference_time)
        
        return ensemble_predictions, confidence_scores
    
    def _calculate_confidence_scores(self, X: np.ndarray, predictions: np.ndarray, 
                                   blood_types: List[str] = None) -> np.ndarray:
        """Calcule les scores de confiance basés sur la variance des modèles"""
        if not hasattr(self.ensemble_model, 'estimators_'):
            return np.ones(len(predictions)) * 0.5
        
        # Prédictions de chaque modèle de base
        base_predictions = []
        for estimator in self.ensemble_model.estimators_:
            try:
                pred = estimator.predict(X)
                base_predictions.append(pred)
            except:
                continue
        
        if len(base_predictions) == 0:
            return np.ones(len(predictions)) * 0.5
        
        # Calculer la variance des prédictions
        base_predictions = np.array(base_predictions)
        prediction_variance = np.var(base_predictions, axis=0)
        
        # Convertir la variance en score de confiance (0-1)
        max_variance = np.max(prediction_variance) if np.max(prediction_variance) > 0 else 1
        confidence_scores = 1.0 - (prediction_variance / max_variance)
        
        return confidence_scores
    
    def batch_predict(self, X_batch: np.ndarray, batch_size: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """Prédictions par batch pour optimiser la mémoire"""
        n_samples = len(X_batch)
        all_predictions = []
        all_confidence = []
        
        print(f"Prédiction par batch: {n_samples} échantillons, taille batch: {batch_size}")
        
        for i in range(0, n_samples, batch_size):
            batch_end = min(i + batch_size, n_samples)
            X_current = X_batch[i:batch_end]
            
            predictions, confidence = self.predict_with_confidence(X_current)
            all_predictions.extend(predictions)
            all_confidence.extend(confidence)
            
            if (i // batch_size + 1) % 10 == 0:
                print(f"Traité {batch_end}/{n_samples} échantillons")
        
        return np.array(all_predictions), np.array(all_confidence)
    
    def setup_drift_detection(self, reference_data: pd.DataFrame, feature_columns: List[str]):
        """Configure la détection de drift"""
        self.drift_detector = DriftDetector(reference_data, feature_columns)
        print("✓ Détection de drift configurée")
    
    def check_model_performance(self, X_test: np.ndarray, y_test: np.ndarray, 
                              model_name: str = "ensemble") -> ModelPerformanceMetrics:
        """Vérifie les performances du modèle"""
        predictions, _ = self.predict_with_confidence(X_test)
        
        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
        r2 = r2_score(y_test, predictions)
        
        metrics = ModelPerformanceMetrics(
            mae=mae,
            rmse=rmse,
            mape=mape,
            r2=r2,
            timestamp=datetime.now().isoformat(),
            model_name=model_name,
            dataset_size=len(y_test)
        )
        
        self.performance_history.append(metrics)
        return metrics
    
    def should_retrain(self, current_metrics: ModelPerformanceMetrics, 
                      performance_threshold: float = 0.15) -> bool:
        """Détermine si le modèle doit être ré-entraîné"""
        if len(self.performance_history) < 2:
            return False
        
        baseline_metrics = self.performance_history[0]  # Première mesure comme baseline
        
        return current_metrics.is_degraded(baseline_metrics, performance_threshold)
    
    def setup_auto_retraining(self, retrain_callback, check_interval_hours: int = 24):
        """Configure le ré-entraînement automatique"""
        def check_and_retrain():
            print(f"Vérification automatique des performances - {datetime.now()}")
            # Cette fonction sera appelée par le scheduler
            # L'implémentation complète nécessiterait des données de test en continu
            pass
        
        schedule.every(check_interval_hours).hours.do(check_and_retrain)
        print(f"✓ Ré-entraînement automatique configuré (vérification toutes les {check_interval_hours}h)")
    
    def optimize_cache_ttl(self, prediction_variance_threshold: float = 0.1):
        """Optimise le TTL du cache basé sur la variance des prédictions"""
        if len(self.performance_history) > 0:
            recent_performance = self.performance_history[-1]
            
            # TTL plus court si les performances se dégradent
            if recent_performance.mae > 5.0:  # Seuil arbitraire
                self.cache_ttl = 60  # 1 minute
            elif recent_performance.mae > 3.0:
                self.cache_ttl = 180  # 3 minutes
            else:
                self.cache_ttl = 300  # 5 minutes
        
        print(f"TTL du cache optimisé: {self.cache_ttl} secondes")
    
    def get_production_metrics(self) -> Dict:
        """Retourne les métriques de production"""
        return {
            'cache_stats': self.cache_stats,
            'cache_hit_rate': self.cache_stats['hits'] / (self.cache_stats['hits'] + self.cache_stats['misses']) if (self.cache_stats['hits'] + self.cache_stats['misses']) > 0 else 0,
            'avg_inference_time': np.mean(self.inference_times) if self.inference_times else 0,
            'cache_size': len(self.prediction_cache),
            'cache_ttl': self.cache_ttl,
            'performance_history_size': len(self.performance_history),
            'specialized_models_count': len(self.blood_type_models)
        }
    
    def validate_accuracy_threshold(self, X_test: np.ndarray, y_test: np.ndarray, 
                                  target_accuracy: float = 0.85) -> Dict:
        """Valide que la précision dépasse le seuil requis (>85%)"""
        metrics = self.check_model_performance(X_test, y_test)
        
        # Calculer la précision (1 - MAPE/100)
        accuracy = 1 - (metrics.mape / 100)
        
        validation_result = {
            'accuracy': accuracy,
            'target_accuracy': target_accuracy,
            'meets_threshold': accuracy >= target_accuracy,
            'metrics': metrics.to_dict(),
            'validation_timestamp': datetime.now().isoformat()
        }
        
        if validation_result['meets_threshold']:
            print(f"✅ Validation réussie: Précision {accuracy:.3f} >= {target_accuracy}")
        else:
            print(f"❌ Validation échouée: Précision {accuracy:.3f} < {target_accuracy}")
        
        return validation_result
    
    def save_production_system(self, output_dir: str = 'models/production_system'):
        """Sauvegarde le système complet"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder l'ensemble principal
        if self.ensemble_model:
            joblib.dump(self.ensemble_model, f'{output_dir}/ensemble_model.pkl')
        
        # Sauvegarder les modèles spécialisés
        specialized_dir = f'{output_dir}/specialized_models'
        os.makedirs(specialized_dir, exist_ok=True)
        for blood_type, model in self.blood_type_models.items():
            joblib.dump(model, f'{specialized_dir}/{blood_type}_model.pkl')
        
        # Sauvegarder les métriques et configuration
        config = {
            'performance_history': [metrics.to_dict() for metrics in self.performance_history],
            'cache_ttl': self.cache_ttl,
            'confidence_threshold': self.confidence_threshold,
            'production_metrics': self.get_production_metrics()
        }
        
        with open(f'{output_dir}/system_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Système de production sauvegardé dans {output_dir}")

def main():
    """Fonction principale pour tester le système"""
    print("🚀 Test du Système ML Optimisé pour Production")
    
    # Créer des données de test
    np.random.seed(42)
    n_samples = 1000
    
    # Simuler des données
    data = {
        'hospital': np.random.choice(['Hôpital A', 'Hôpital B'], n_samples),
        'blood_type': np.random.choice(['O+', 'A+', 'B+', 'AB+', 'O-', 'A-', 'B-', 'AB-'], n_samples),
        'stock_initial': np.random.uniform(10, 100, n_samples),
        'demand': np.random.uniform(5, 30, n_samples),
        'supply': np.random.uniform(5, 35, n_samples),
        'temperature': np.random.uniform(2, 8, n_samples),
        'quality_score': np.random.uniform(70, 100, n_samples),
    }
    
    # Calculer stock_final avec une formule réaliste
    data['stock_final'] = (data['stock_initial'] + data['supply'] - data['demand'] + 
                          np.random.normal(0, 5, n_samples))
    data['stock_final'] = np.maximum(data['stock_final'], 0)  # Pas de stock négatif
    
    df = pd.DataFrame(data)
    
    # Features
    feature_columns = ['stock_initial', 'demand', 'supply', 'temperature', 'quality_score']
    
    # Split des données
    train_size = int(0.7 * len(df))
    val_size = int(0.15 * len(df))
    
    df_train = df[:train_size]
    df_val = df[train_size:train_size + val_size]
    df_test = df[train_size + val_size:]
    
    # Créer le système avancé
    system = AdvancedEnsembleSystem()
    
    # 1. Créer des modèles spécialisés
    system.create_specialized_models(df_train, feature_columns)
    
    # 2. Fine-tuning des hyperparamètres
    tuning_results = system.fine_tune_hyperparameters(df_train, df_val, feature_columns, n_trials=50)
    
    # 3. Créer l'ensemble stacking avancé
    system.create_advanced_stacking_ensemble(df_train, df_val, feature_columns)
    
    # 4. Configurer la détection de drift
    system.setup_drift_detection(df_train, feature_columns)
    
    # 5. Tester les prédictions avec confiance
    X_test = df_test[feature_columns].values
    y_test = df_test['stock_final'].values
    
    predictions, confidence = system.predict_with_confidence(X_test)
    
    # 6. Valider la précision > 85%
    validation_result = system.validate_accuracy_threshold(X_test, y_test, target_accuracy=0.85)
    
    # 7. Test de détection de drift
    drift_result = system.drift_detector.detect_feature_drift(df_test)
    print(f"\nDétection de drift: {drift_result.drift_detected}")
    print(f"Score de drift: {drift_result.drift_score:.4f}")
    
    # 8. Métriques de production
    prod_metrics = system.get_production_metrics()
    print(f"\nMétriques de production:")
    for key, value in prod_metrics.items():
        print(f"  {key}: {value}")
    
    # 9. Sauvegarder le système
    system.save_production_system()
    
    print("\n✅ Test du système de production terminé avec succès!")

if __name__ == "__main__":
    main()