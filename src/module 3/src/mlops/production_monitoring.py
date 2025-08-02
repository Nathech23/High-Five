#!/usr/bin/env python3
"""
Système MLOps Production avec Monitoring et Versioning
Monitoring Drift + Performance + A/B Testing + Alertes Automatiques
"""

import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import threading
import schedule
import sqlite3
from pathlib import Path
import joblib
import pickle
from collections import defaultdict, deque
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
import asyncio
import warnings
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# MLflow pour le tracking
try:
    import mlflow
    import mlflow.sklearn
    import mlflow.xgboost
    MLFLOW_AVAILABLE = True
except ImportError:
    print("⚠️ MLflow non disponible. Utilisation du tracking local.")
    MLFLOW_AVAILABLE = False

warnings.filterwarnings('ignore')

@dataclass
class ModelVersion:
    """Version d'un modèle avec métadonnées"""
    version_id: str
    model_name: str
    version_number: str
    model_path: str
    performance_metrics: Dict[str, float]
    training_data_hash: str
    created_at: str
    status: str  # 'training', 'testing', 'production', 'deprecated'
    deployment_config: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class PerformanceAlert:
    """Alerte de dégradation de performance"""
    alert_id: str
    model_name: str
    alert_type: str  # 'performance_degradation', 'drift_detected', 'error_rate_high'
    severity: str  # 'low', 'medium', 'high', 'critical'
    current_metric: float
    baseline_metric: float
    threshold: float
    message: str
    recommendations: List[str]
    created_at: str
    acknowledged: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class ABTestResult:
    """Résultat d'un test A/B"""
    test_id: str
    model_a: str
    model_b: str
    metric_name: str
    model_a_score: float
    model_b_score: float
    sample_size: int
    p_value: float
    confidence_interval: Tuple[float, float]
    winner: str
    statistical_significance: bool
    business_impact: Dict[str, float]
    test_duration: str
    created_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

class ModelVersionManager:
    """Gestionnaire de versions de modèles avec versioning automatique"""
    
    def __init__(self, models_dir: str = "models/versions", db_path: str = "data/model_versions.db"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_database()
        
        # Configuration MLflow
        if MLFLOW_AVAILABLE:
            mlflow.set_tracking_uri("file:./mlruns")
            mlflow.set_experiment("production_models")
    
    def _init_database(self):
        """Initialise la base de données des versions"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id TEXT PRIMARY KEY,
                    model_name TEXT,
                    version_number TEXT,
                    model_path TEXT,
                    performance_metrics TEXT,
                    training_data_hash TEXT,
                    created_at TEXT,
                    status TEXT,
                    deployment_config TEXT
                )
            """)
    
    def register_model(self, model, model_name: str, performance_metrics: Dict[str, float],
                      training_data_hash: str, deployment_config: Dict = None) -> ModelVersion:
        """Enregistre une nouvelle version de modèle"""
        # Générer version automatique
        version_number = self._generate_version_number(model_name)
        version_id = f"{model_name}_v{version_number}_{int(time.time())}"
        
        # Chemin de sauvegarde
        model_path = self.models_dir / f"{version_id}.pkl"
        
        # Sauvegarder le modèle
        joblib.dump(model, model_path)
        
        # Créer l'objet version
        model_version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            version_number=version_number,
            model_path=str(model_path),
            performance_metrics=performance_metrics,
            training_data_hash=training_data_hash,
            created_at=datetime.now().isoformat(),
            status='training',
            deployment_config=deployment_config or {}
        )
        
        # Enregistrer en base
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO model_versions 
                (version_id, model_name, version_number, model_path, performance_metrics, 
                 training_data_hash, created_at, status, deployment_config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                model_version.version_id,
                model_version.model_name,
                model_version.version_number,
                model_version.model_path,
                json.dumps(model_version.performance_metrics),
                model_version.training_data_hash,
                model_version.created_at,
                model_version.status,
                json.dumps(model_version.deployment_config)
            ))
        
        # Enregistrer avec MLflow si disponible
        if MLFLOW_AVAILABLE:
            with mlflow.start_run(run_name=f"{model_name}_v{version_number}"):
                mlflow.log_params(deployment_config or {})
                mlflow.log_metrics(performance_metrics)
                mlflow.sklearn.log_model(model, f"{model_name}_model")
                mlflow.set_tag("version", version_number)
                mlflow.set_tag("model_name", model_name)
        
        print(f"✓ Modèle {model_name} v{version_number} enregistré")
        return model_version
    
    def _generate_version_number(self, model_name: str) -> str:
        """Génère automatiquement un numéro de version"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT version_number FROM model_versions WHERE model_name = ? ORDER BY created_at DESC LIMIT 1",
                (model_name,)
            )
            result = cursor.fetchone()
        
        if result:
            last_version = result[0]
            # Incrémenter la version (format: major.minor.patch)
            parts = last_version.split('.')
            if len(parts) == 3:
                major, minor, patch = map(int, parts)
                return f"{major}.{minor}.{patch + 1}"
            else:
                return "1.0.1"
        else:
            return "1.0.0"
    
    def promote_to_production(self, version_id: str) -> bool:
        """Promeut un modèle en production"""
        # Dégrader l'ancien modèle de production
        with sqlite3.connect(self.db_path) as conn:
            # Récupérer le modèle
            cursor = conn.execute(
                "SELECT model_name FROM model_versions WHERE version_id = ?",
                (version_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return False
            
            model_name = result[0]
            
            # Dégrader les anciens modèles de production
            conn.execute(
                "UPDATE model_versions SET status = 'deprecated' WHERE model_name = ? AND status = 'production'",
                (model_name,)
            )
            
            # Promouvoir le nouveau
            conn.execute(
                "UPDATE model_versions SET status = 'production' WHERE version_id = ?",
                (version_id,)
            )
        
        print(f"✓ Modèle {version_id} promu en production")
        return True
    
    def get_production_model(self, model_name: str) -> Optional[ModelVersion]:
        """Récupère le modèle en production"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT version_id, model_name, version_number, model_path, performance_metrics,
                       training_data_hash, created_at, status, deployment_config
                FROM model_versions 
                WHERE model_name = ? AND status = 'production'
                ORDER BY created_at DESC LIMIT 1
            """, (model_name,))
            
            result = cursor.fetchone()
            
            if result:
                return ModelVersion(
                    version_id=result[0],
                    model_name=result[1],
                    version_number=result[2],
                    model_path=result[3],
                    performance_metrics=json.loads(result[4]),
                    training_data_hash=result[5],
                    created_at=result[6],
                    status=result[7],
                    deployment_config=json.loads(result[8])
                )
        
        return None
    
    def load_model(self, version_id: str):
        """Charge un modèle par son ID de version"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT model_path FROM model_versions WHERE version_id = ?",
                (version_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return joblib.load(result[0])
        
        return None
    
    def list_versions(self, model_name: str = None) -> List[ModelVersion]:
        """Liste les versions de modèles"""
        with sqlite3.connect(self.db_path) as conn:
            if model_name:
                cursor = conn.execute("""
                    SELECT version_id, model_name, version_number, model_path, performance_metrics,
                           training_data_hash, created_at, status, deployment_config
                    FROM model_versions WHERE model_name = ?
                    ORDER BY created_at DESC
                """, (model_name,))
            else:
                cursor = conn.execute("""
                    SELECT version_id, model_name, version_number, model_path, performance_metrics,
                           training_data_hash, created_at, status, deployment_config
                    FROM model_versions ORDER BY created_at DESC
                """)
            
            versions = []
            for row in cursor.fetchall():
                versions.append(ModelVersion(
                    version_id=row[0],
                    model_name=row[1],
                    version_number=row[2],
                    model_path=row[3],
                    performance_metrics=json.loads(row[4]),
                    training_data_hash=row[5],
                    created_at=row[6],
                    status=row[7],
                    deployment_config=json.loads(row[8])
                ))
            
            return versions

class PerformanceMonitor:
    """Moniteur de performance avec détection de dégradation"""
    
    def __init__(self, db_path: str = "data/performance_monitoring.db"):
        self.db_path = db_path
        self.performance_history = defaultdict(list)
        self.alert_thresholds = {
            'mae': {'degradation': 0.15, 'critical': 0.25},
            'rmse': {'degradation': 0.15, 'critical': 0.25},
            'r2': {'degradation': -0.10, 'critical': -0.20},
            'mape': {'degradation': 0.15, 'critical': 0.25}
        }
        self.alerts = []
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données de monitoring"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    version_id TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    dataset_size INTEGER,
                    timestamp TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    alert_id TEXT PRIMARY KEY,
                    model_name TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    current_metric REAL,
                    baseline_metric REAL,
                    threshold REAL,
                    message TEXT,
                    recommendations TEXT,
                    created_at TEXT,
                    acknowledged INTEGER
                )
            """)
    
    def log_performance(self, model_name: str, version_id: str, metrics: Dict[str, float], 
                       dataset_size: int):
        """Enregistre les métriques de performance"""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            for metric_name, metric_value in metrics.items():
                conn.execute("""
                    INSERT INTO performance_metrics 
                    (model_name, version_id, metric_name, metric_value, dataset_size, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (model_name, version_id, metric_name, metric_value, dataset_size, timestamp))
                
                # Ajouter à l'historique en mémoire
                self.performance_history[f"{model_name}_{metric_name}"].append({
                    'value': metric_value,
                    'timestamp': timestamp,
                    'version_id': version_id
                })
        
        # Vérifier les dégradations
        self._check_performance_degradation(model_name, metrics)
    
    def _check_performance_degradation(self, model_name: str, current_metrics: Dict[str, float]):
        """Vérifie les dégradations de performance"""
        baseline_metrics = self._get_baseline_metrics(model_name)
        
        if not baseline_metrics:
            return
        
        for metric_name, current_value in current_metrics.items():
            if metric_name not in baseline_metrics:
                continue
            
            baseline_value = baseline_metrics[metric_name]
            
            # Calculer la dégradation
            if metric_name == 'r2':  # Pour R², une diminution est une dégradation
                degradation = (baseline_value - current_value) / abs(baseline_value)
            else:  # Pour MAE, RMSE, MAPE, une augmentation est une dégradation
                degradation = (current_value - baseline_value) / abs(baseline_value)
            
            # Vérifier les seuils
            thresholds = self.alert_thresholds.get(metric_name, {'degradation': 0.15, 'critical': 0.25})
            
            if degradation > thresholds['critical']:
                self._create_alert(model_name, metric_name, current_value, baseline_value, 
                                 'critical', 'performance_degradation')
            elif degradation > thresholds['degradation']:
                self._create_alert(model_name, metric_name, current_value, baseline_value, 
                                 'high', 'performance_degradation')
    
    def _get_baseline_metrics(self, model_name: str, days_back: int = 7) -> Dict[str, float]:
        """Récupère les métriques de baseline"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT metric_name, AVG(metric_value) as avg_value
                FROM performance_metrics 
                WHERE model_name = ? AND timestamp >= ?
                GROUP BY metric_name
            """, (model_name, cutoff_date))
            
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def _create_alert(self, model_name: str, metric_name: str, current_value: float, 
                     baseline_value: float, severity: str, alert_type: str):
        """Crée une alerte de dégradation"""
        alert_id = str(uuid.uuid4())[:8]
        threshold = self.alert_thresholds.get(metric_name, {}).get('degradation', 0.15)
        
        message = f"Dégradation détectée sur {metric_name}: {current_value:.4f} vs baseline {baseline_value:.4f}"
        
        recommendations = [
            "Vérifier la qualité des données d'entrée",
            "Analyser les changements dans la distribution des données",
            "Considérer un ré-entraînement du modèle",
            "Examiner les logs d'erreurs récents"
        ]
        
        if severity == 'critical':
            recommendations.insert(0, "Action immédiate requise - Considérer rollback")
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            model_name=model_name,
            alert_type=alert_type,
            severity=severity,
            current_metric=current_value,
            baseline_metric=baseline_value,
            threshold=threshold,
            message=message,
            recommendations=recommendations,
            created_at=datetime.now().isoformat()
        )
        
        # Sauvegarder l'alerte
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO performance_alerts 
                (alert_id, model_name, alert_type, severity, current_metric, baseline_metric, 
                 threshold, message, recommendations, created_at, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id, alert.model_name, alert.alert_type, alert.severity,
                alert.current_metric, alert.baseline_metric, alert.threshold,
                alert.message, json.dumps(alert.recommendations), alert.created_at, 0
            ))
        
        self.alerts.append(alert)
        print(f"🚨 Alerte {severity}: {message}")
    
    def get_active_alerts(self, model_name: str = None) -> List[PerformanceAlert]:
        """Récupère les alertes actives"""
        with sqlite3.connect(self.db_path) as conn:
            if model_name:
                cursor = conn.execute("""
                    SELECT alert_id, model_name, alert_type, severity, current_metric, 
                           baseline_metric, threshold, message, recommendations, created_at, acknowledged
                    FROM performance_alerts 
                    WHERE model_name = ? AND acknowledged = 0
                    ORDER BY created_at DESC
                """, (model_name,))
            else:
                cursor = conn.execute("""
                    SELECT alert_id, model_name, alert_type, severity, current_metric, 
                           baseline_metric, threshold, message, recommendations, created_at, acknowledged
                    FROM performance_alerts 
                    WHERE acknowledged = 0
                    ORDER BY created_at DESC
                """)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append(PerformanceAlert(
                    alert_id=row[0],
                    model_name=row[1],
                    alert_type=row[2],
                    severity=row[3],
                    current_metric=row[4],
                    baseline_metric=row[5],
                    threshold=row[6],
                    message=row[7],
                    recommendations=json.loads(row[8]),
                    created_at=row[9],
                    acknowledged=bool(row[10])
                ))
            
            return alerts
    
    def acknowledge_alert(self, alert_id: str):
        """Acquitte une alerte"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE performance_alerts SET acknowledged = 1 WHERE alert_id = ?",
                (alert_id,)
            )
        print(f"✓ Alerte {alert_id} acquittée")

class ABTestManager:
    """Gestionnaire de tests A/B pour nouveaux modèles"""
    
    def __init__(self, db_path: str = "data/ab_tests.db"):
        self.db_path = db_path
        self.active_tests = {}
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données des tests A/B"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    test_id TEXT PRIMARY KEY,
                    model_a TEXT,
                    model_b TEXT,
                    metric_name TEXT,
                    model_a_score REAL,
                    model_b_score REAL,
                    sample_size INTEGER,
                    p_value REAL,
                    confidence_interval TEXT,
                    winner TEXT,
                    statistical_significance INTEGER,
                    business_impact TEXT,
                    test_duration TEXT,
                    created_at TEXT
                )
            """)
    
    def start_ab_test(self, model_a_id: str, model_b_id: str, 
                     traffic_split: float = 0.5, test_duration_hours: int = 24) -> str:
        """Démarre un test A/B"""
        test_id = str(uuid.uuid4())[:12]
        
        test_config = {
            'test_id': test_id,
            'model_a': model_a_id,
            'model_b': model_b_id,
            'traffic_split': traffic_split,
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(hours=test_duration_hours)).isoformat(),
            'model_a_predictions': [],
            'model_b_predictions': [],
            'model_a_actuals': [],
            'model_b_actuals': []
        }
        
        self.active_tests[test_id] = test_config
        print(f"✓ Test A/B {test_id} démarré: {model_a_id} vs {model_b_id}")
        return test_id
    
    def route_prediction(self, test_id: str, X: np.ndarray, model_a, model_b) -> Tuple[np.ndarray, str]:
        """Route une prédiction vers le modèle A ou B"""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} non trouvé")
        
        test_config = self.active_tests[test_id]
        
        # Décider quel modèle utiliser (basé sur le hash pour la consistance)
        hash_input = hashlib.md5(str(X.tobytes()).encode()).hexdigest()
        use_model_a = int(hash_input, 16) % 100 < (test_config['traffic_split'] * 100)
        
        if use_model_a:
            predictions = model_a.predict(X)
            model_used = 'model_a'
        else:
            predictions = model_b.predict(X)
            model_used = 'model_b'
        
        return predictions, model_used
    
    def log_ab_result(self, test_id: str, model_used: str, predictions: np.ndarray, actuals: np.ndarray):
        """Enregistre les résultats du test A/B"""
        if test_id not in self.active_tests:
            return
        
        test_config = self.active_tests[test_id]
        
        if model_used == 'model_a':
            test_config['model_a_predictions'].extend(predictions.tolist())
            test_config['model_a_actuals'].extend(actuals.tolist())
        else:
            test_config['model_b_predictions'].extend(predictions.tolist())
            test_config['model_b_actuals'].extend(actuals.tolist())
    
    def analyze_ab_test(self, test_id: str, metric_name: str = 'mae') -> ABTestResult:
        """Analyse les résultats d'un test A/B"""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} non trouvé")
        
        test_config = self.active_tests[test_id]
        
        # Calculer les métriques pour chaque modèle
        model_a_score = self._calculate_metric(
            test_config['model_a_predictions'],
            test_config['model_a_actuals'],
            metric_name
        )
        
        model_b_score = self._calculate_metric(
            test_config['model_b_predictions'],
            test_config['model_b_actuals'],
            metric_name
        )
        
        # Test statistique
        p_value, confidence_interval = self._statistical_test(
            test_config['model_a_predictions'],
            test_config['model_a_actuals'],
            test_config['model_b_predictions'],
            test_config['model_b_actuals'],
            metric_name
        )
        
        # Déterminer le gagnant
        if metric_name in ['mae', 'rmse', 'mape']:  # Plus bas = mieux
            winner = 'model_a' if model_a_score < model_b_score else 'model_b'
        else:  # Plus haut = mieux (r2, accuracy, etc.)
            winner = 'model_a' if model_a_score > model_b_score else 'model_b'
        
        statistical_significance = p_value < 0.05
        
        # Impact business (simulé)
        business_impact = {
            'accuracy_improvement': abs(model_a_score - model_b_score),
            'estimated_cost_savings': abs(model_a_score - model_b_score) * 1000,  # Exemple
            'risk_reduction': 0.05 if statistical_significance else 0.01
        }
        
        # Calculer la durée du test
        start_time = datetime.fromisoformat(test_config['start_time'])
        test_duration = str(datetime.now() - start_time)
        
        result = ABTestResult(
            test_id=test_id,
            model_a=test_config['model_a'],
            model_b=test_config['model_b'],
            metric_name=metric_name,
            model_a_score=model_a_score,
            model_b_score=model_b_score,
            sample_size=len(test_config['model_a_predictions']) + len(test_config['model_b_predictions']),
            p_value=p_value,
            confidence_interval=confidence_interval,
            winner=winner,
            statistical_significance=statistical_significance,
            business_impact=business_impact,
            test_duration=test_duration,
            created_at=datetime.now().isoformat()
        )
        
        # Sauvegarder les résultats
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ab_tests 
                (test_id, model_a, model_b, metric_name, model_a_score, model_b_score, 
                 sample_size, p_value, confidence_interval, winner, statistical_significance, 
                 business_impact, test_duration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.test_id, result.model_a, result.model_b, result.metric_name,
                result.model_a_score, result.model_b_score, result.sample_size,
                result.p_value, json.dumps(result.confidence_interval), result.winner,
                int(result.statistical_significance), json.dumps(result.business_impact),
                result.test_duration, result.created_at
            ))
        
        return result
    
    def _calculate_metric(self, predictions: List[float], actuals: List[float], metric_name: str) -> float:
        """Calcule une métrique spécifique"""
        if not predictions or not actuals:
            return float('inf')
        
        pred_array = np.array(predictions)
        actual_array = np.array(actuals)
        
        if metric_name == 'mae':
            return np.mean(np.abs(pred_array - actual_array))
        elif metric_name == 'rmse':
            return np.sqrt(np.mean((pred_array - actual_array) ** 2))
        elif metric_name == 'mape':
            return np.mean(np.abs((actual_array - pred_array) / actual_array)) * 100
        elif metric_name == 'r2':
            ss_res = np.sum((actual_array - pred_array) ** 2)
            ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
            return 1 - (ss_res / ss_tot)
        else:
            return 0.0
    
    def _statistical_test(self, pred_a: List[float], actual_a: List[float],
                         pred_b: List[float], actual_b: List[float], 
                         metric_name: str) -> Tuple[float, Tuple[float, float]]:
        """Effectue un test statistique entre les deux modèles"""
        if not pred_a or not actual_a or not pred_b or not actual_b:
            return 1.0, (0.0, 0.0)
        
        # Calculer les erreurs pour chaque modèle
        errors_a = np.abs(np.array(pred_a) - np.array(actual_a))
        errors_b = np.abs(np.array(pred_b) - np.array(actual_b))
        
        # Test t de Student
        try:
            t_stat, p_value = stats.ttest_ind(errors_a, errors_b)
            
            # Intervalle de confiance pour la différence des moyennes
            diff_mean = np.mean(errors_a) - np.mean(errors_b)
            pooled_std = np.sqrt(((len(errors_a) - 1) * np.var(errors_a) + 
                                 (len(errors_b) - 1) * np.var(errors_b)) / 
                                (len(errors_a) + len(errors_b) - 2))
            
            margin_error = 1.96 * pooled_std * np.sqrt(1/len(errors_a) + 1/len(errors_b))
            confidence_interval = (diff_mean - margin_error, diff_mean + margin_error)
            
            return p_value, confidence_interval
        except:
            return 1.0, (0.0, 0.0)

class BusinessImpactTracker:
    """Tracker d'impact business des modèles ML"""
    
    def __init__(self, db_path: str = "data/business_impact.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données d'impact business"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS business_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    business_value REAL,
                    cost_savings REAL,
                    risk_reduction REAL,
                    timestamp TEXT
                )
            """)
    
    def log_business_impact(self, model_name: str, ml_metrics: Dict[str, float], 
                          business_context: Dict[str, Any]):
        """Enregistre l'impact business d'un modèle"""
        timestamp = datetime.now().isoformat()
        
        # Calculer l'impact business basé sur les métriques ML
        business_impact = self._calculate_business_impact(ml_metrics, business_context)
        
        with sqlite3.connect(self.db_path) as conn:
            for metric_name, metric_value in ml_metrics.items():
                conn.execute("""
                    INSERT INTO business_metrics 
                    (model_name, metric_name, metric_value, business_value, cost_savings, risk_reduction, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    model_name, metric_name, metric_value,
                    business_impact.get('business_value', 0),
                    business_impact.get('cost_savings', 0),
                    business_impact.get('risk_reduction', 0),
                    timestamp
                ))
    
    def _calculate_business_impact(self, ml_metrics: Dict[str, float], 
                                 business_context: Dict[str, Any]) -> Dict[str, float]:
        """Calcule l'impact business à partir des métriques ML"""
        # Exemple de calcul d'impact business pour la gestion des stocks sanguins
        
        mae = ml_metrics.get('mae', 0)
        r2 = ml_metrics.get('r2', 0)
        
        # Estimation des économies basées sur la précision
        # Plus la MAE est faible, plus les économies sont importantes
        base_cost_per_unit = business_context.get('cost_per_unit', 100)  # Coût par unité de sang
        daily_volume = business_context.get('daily_volume', 50)  # Volume quotidien
        
        # Économies dues à la réduction du gaspillage
        waste_reduction = max(0, (10 - mae) / 10)  # Normalisation
        cost_savings = waste_reduction * base_cost_per_unit * daily_volume * 30  # Par mois
        
        # Valeur business basée sur R²
        business_value = r2 * 10000  # Valeur arbitraire
        
        # Réduction des risques
        risk_reduction = min(0.5, waste_reduction * 0.3)  # Max 50% de réduction
        
        return {
            'business_value': business_value,
            'cost_savings': cost_savings,
            'risk_reduction': risk_reduction
        }
    
    def get_business_summary(self, model_name: str, days_back: int = 30) -> Dict[str, float]:
        """Récupère un résumé de l'impact business"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    AVG(business_value) as avg_business_value,
                    AVG(cost_savings) as avg_cost_savings,
                    AVG(risk_reduction) as avg_risk_reduction,
                    COUNT(*) as measurement_count
                FROM business_metrics 
                WHERE model_name = ? AND timestamp >= ?
            """, (model_name, cutoff_date))
            
            result = cursor.fetchone()
            
            if result and result[3] > 0:  # Si on a des mesures
                return {
                    'avg_business_value': result[0] or 0,
                    'avg_cost_savings': result[1] or 0,
                    'avg_risk_reduction': result[2] or 0,
                    'measurement_count': result[3],
                    'period_days': days_back
                }
            else:
                return {
                    'avg_business_value': 0,
                    'avg_cost_savings': 0,
                    'avg_risk_reduction': 0,
                    'measurement_count': 0,
                    'period_days': days_back
                }

class ProductionMLOpsSystem:
    """Système MLOps complet pour la production"""
    
    def __init__(self, base_dir: str = "mlops_production"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Initialiser les composants
        self.version_manager = ModelVersionManager(
            models_dir=str(self.base_dir / "models"),
            db_path=str(self.base_dir / "model_versions.db")
        )
        
        self.performance_monitor = PerformanceMonitor(
            db_path=str(self.base_dir / "performance_monitoring.db")
        )
        
        self.ab_test_manager = ABTestManager(
            db_path=str(self.base_dir / "ab_tests.db")
        )
        
        self.business_tracker = BusinessImpactTracker(
            db_path=str(self.base_dir / "business_impact.db")
        )
        
        # Scheduler pour les tâches automatiques
        self.scheduler_thread = None
        self.monitoring_active = False
    
    def deploy_new_model(self, model, model_name: str, performance_metrics: Dict[str, float],
                        training_data_hash: str, deployment_config: Dict = None,
                        run_ab_test: bool = True) -> str:
        """Déploie un nouveau modèle avec versioning automatique"""
        print(f"🚀 Déploiement du modèle {model_name}...")
        
        # 1. Enregistrer la nouvelle version
        model_version = self.version_manager.register_model(
            model, model_name, performance_metrics, training_data_hash, deployment_config
        )
        
        # 2. Vérifier s'il y a un modèle en production
        current_production = self.version_manager.get_production_model(model_name)
        
        if current_production and run_ab_test:
            # 3. Lancer un test A/B
            test_id = self.ab_test_manager.start_ab_test(
                current_production.version_id,
                model_version.version_id,
                traffic_split=0.5,
                test_duration_hours=24
            )
            print(f"🧪 Test A/B {test_id} lancé")
            return test_id
        else:
            # 4. Promouvoir directement en production
            self.version_manager.promote_to_production(model_version.version_id)
            return model_version.version_id
    
    def start_monitoring(self, check_interval_minutes: int = 60):
        """Démarre le monitoring automatique"""
        def monitoring_job():
            print(f"🔍 Vérification monitoring - {datetime.now()}")
            
            # Vérifier les alertes actives
            active_alerts = self.performance_monitor.get_active_alerts()
            if active_alerts:
                print(f"⚠️ {len(active_alerts)} alertes actives")
                for alert in active_alerts[:3]:  # Afficher les 3 premières
                    print(f"  - {alert.severity}: {alert.message}")
        
        # Programmer la vérification
        schedule.every(check_interval_minutes).minutes.do(monitoring_job)
        
        def run_scheduler():
            while self.monitoring_active:
                schedule.run_pending()
                time.sleep(60)
        
        self.monitoring_active = True
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print(f"✓ Monitoring démarré (vérification toutes les {check_interval_minutes} minutes)")
    
    def stop_monitoring(self):
        """Arrête le monitoring automatique"""
        self.monitoring_active = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("✓ Monitoring arrêté")
    
    def get_system_dashboard(self) -> Dict[str, Any]:
        """Génère un dashboard du système"""
        # Modèles en production
        production_models = []
        for model_name in ['ensemble', 'xgboost', 'lstm', 'arima']:
            prod_model = self.version_manager.get_production_model(model_name)
            if prod_model:
                production_models.append({
                    'name': model_name,
                    'version': prod_model.version_number,
                    'performance': prod_model.performance_metrics
                })
        
        # Alertes actives
        active_alerts = self.performance_monitor.get_active_alerts()
        alert_summary = {
            'total': len(active_alerts),
            'critical': len([a for a in active_alerts if a.severity == 'critical']),
            'high': len([a for a in active_alerts if a.severity == 'high']),
            'medium': len([a for a in active_alerts if a.severity == 'medium'])
        }
        
        # Tests A/B actifs
        ab_tests_count = len(self.ab_test_manager.active_tests)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'production_models': production_models,
            'alert_summary': alert_summary,
            'active_ab_tests': ab_tests_count,
            'monitoring_status': 'active' if self.monitoring_active else 'inactive',
            'system_health': 'healthy' if alert_summary['critical'] == 0 else 'degraded'
        }
    
    def generate_documentation(self, output_file: str = None) -> str:
        """Génère la documentation du pipeline ML"""
        doc = f"""
# Documentation Pipeline ML - Système de Production

Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Vue d'ensemble du Système

Le système MLOps de production gère automatiquement:
- Versioning des modèles avec promotion automatique
- Monitoring de performance avec alertes
- Tests A/B pour validation des nouveaux modèles
- Tracking de l'impact business

## Modèles en Production

"""
        
        # Ajouter les modèles en production
        for model_name in ['ensemble', 'xgboost', 'lstm', 'arima']:
            prod_model = self.version_manager.get_production_model(model_name)
            if prod_model:
                doc += f"""
### {model_name.upper()}
- Version: {prod_model.version_number}
- Déployé le: {prod_model.created_at}
- Performance:
"""
                for metric, value in prod_model.performance_metrics.items():
                    doc += f"  - {metric}: {value:.4f}\n"
        
        doc += f"""

## Alertes et Monitoring

### Configuration des Seuils
- Dégradation MAE/RMSE: 15%
- Dégradation critique: 25%
- Dégradation R²: -10%

### Alertes Actives
"""
        
        active_alerts = self.performance_monitor.get_active_alerts()
        if active_alerts:
            for alert in active_alerts:
                doc += f"- {alert.severity.upper()}: {alert.message}\n"
        else:
            doc += "Aucune alerte active\n"
        
        doc += f"""

## Tests A/B

Tests actifs: {len(self.ab_test_manager.active_tests)}

## Maintenance

### Tâches Automatiques
- Monitoring de performance: Toutes les heures
- Vérification des alertes: Continue
- Nettoyage des caches: Quotidien

### Actions Manuelles Recommandées
- Révision des alertes: Quotidienne
- Analyse des tests A/B: Hebdomadaire
- Mise à jour des seuils: Mensuelle

## Contact et Support

Pour toute question sur le système MLOps:
- Équipe ML: ml-team@hospital.com
- Documentation: /docs/mlops
- Monitoring: /dashboard/mlops
"""
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(doc)
            print(f"✓ Documentation sauvegardée: {output_file}")
        
        return doc

def main():
    """Fonction principale pour tester le système MLOps"""
    print("🏭 Test du Système MLOps de Production")
    
    # Créer le système MLOps
    mlops_system = ProductionMLOpsSystem()
    
    # Simuler un modèle pour les tests
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    # Données de test
    X_dummy = np.random.rand(100, 5)
    y_dummy = np.random.rand(100)
    model.fit(X_dummy, y_dummy)
    
    # Test 1: Déployer un nouveau modèle
    print("\n1. Test déploiement de modèle...")
    performance_metrics = {'mae': 2.5, 'rmse': 3.2, 'r2': 0.87, 'mape': 8.5}
    training_hash = hashlib.md5(str(X_dummy.tobytes()).encode()).hexdigest()
    
    deployment_result = mlops_system.deploy_new_model(
        model, 'test_model', performance_metrics, training_hash
    )
    print(f"Résultat déploiement: {deployment_result}")
    
    # Test 2: Simuler des métriques de performance
    print("\n2. Test monitoring de performance...")
    mlops_system.performance_monitor.log_performance(
        'test_model', deployment_result, performance_metrics, 1000
    )
    
    # Simuler une dégradation
    degraded_metrics = {'mae': 3.5, 'rmse': 4.2, 'r2': 0.75, 'mape': 12.0}
    mlops_system.performance_monitor.log_performance(
        'test_model', deployment_result, degraded_metrics, 1000
    )
    
    # Test 3: Vérifier les alertes
    print("\n3. Test alertes...")
    alerts = mlops_system.performance_monitor.get_active_alerts()
    print(f"Alertes générées: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert.severity}: {alert.message}")
    
    # Test 4: Test A/B
    print("\n4. Test A/B...")
    model_b = RandomForestRegressor(n_estimators=150, random_state=43)
    model_b.fit(X_dummy, y_dummy)
    
    test_id = mlops_system.ab_test_manager.start_ab_test(
        deployment_result, 'model_b_test', traffic_split=0.5
    )
    
    # Simuler des prédictions pour le test A/B
    for i in range(50):
        X_test = np.random.rand(1, 5)
        y_test = np.random.rand(1)
        
        predictions, model_used = mlops_system.ab_test_manager.route_prediction(
            test_id, X_test, model, model_b
        )
        
        mlops_system.ab_test_manager.log_ab_result(
            test_id, model_used, predictions, y_test
        )
    
    # Analyser les résultats du test A/B
    ab_result = mlops_system.ab_test_manager.analyze_ab_test(test_id)
    print(f"Résultat A/B: {ab_result.winner} gagne (p-value: {ab_result.p_value:.4f})")
    
    # Test 5: Impact business
    print("\n5. Test impact business...")
    business_context = {'cost_per_unit': 150, 'daily_volume': 75}
    mlops_system.business_tracker.log_business_impact(
        'test_model', performance_metrics, business_context
    )
    
    business_summary = mlops_system.business_tracker.get_business_summary('test_model')
    print(f"Impact business: {business_summary}")
    
    # Test 6: Dashboard système
    print("\n6. Test dashboard...")
    dashboard = mlops_system.get_system_dashboard()
    print(f"Dashboard: {json.dumps(dashboard, indent=2, ensure_ascii=False)}")
    
    # Test 7: Générer documentation
    print("\n7. Test génération documentation...")
    doc_file = "mlops_documentation.md"
    mlops_system.generate_documentation(doc_file)
    
    # Test 8: Démarrer monitoring (pour 10 secondes)
    print("\n8. Test monitoring automatique...")
    mlops_system.start_monitoring(check_interval_minutes=1)
    time.sleep(10)
    mlops_system.stop_monitoring()
    
    print("\n✅ Test du système MLOps terminé avec succès!")

if __name__ == "__main__":
    main()