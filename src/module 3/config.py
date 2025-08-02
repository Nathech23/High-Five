#!/usr/bin/env python3
"""
Configuration centralisée pour le système MLOps
Module 1: ML/IA + LLM + MLOps - Système de Prédiction des Stocks de Sang
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json

# Chemins de base
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"
EVALUATION_DIR = BASE_DIR / "evaluation"
DEMO_RESULTS_DIR = BASE_DIR / "demo_results"

@dataclass
class DataConfig:
    """Configuration pour les données"""
    synthetic_data_path: str = str(DATA_DIR / "synthetic" / "blood_stock_data.csv")
    processed_data_dir: str = str(DATA_DIR / "processed")
    llm_analysis_dir: str = str(DATA_DIR / "llm_analysis")
    
    # Paramètres de génération de données
    num_hospitals: int = 5
    num_records_per_hospital: int = 2500  # Total: 12,500 enregistrements
    start_date: str = "2023-01-01"
    end_date: str = "2024-12-31"
    
    # Types de sang
    blood_types: list = None
    
    def __post_init__(self):
        if self.blood_types is None:
            self.blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

@dataclass
class ModelConfig:
    """Configuration pour les modèles ML"""
    # Chemins des modèles
    arima_model_path: str = str(MODELS_DIR / "arima_model.pkl")
    xgboost_model_path: str = str(MODELS_DIR / "xgboost_model.pkl")
    lstm_model_path: str = str(MODELS_DIR / "lstm_model.h5")
    ensemble_model_path: str = str(MODELS_DIR / "ensemble_model.pkl")
    preprocessor_path: str = str(MODELS_DIR / "preprocessor.pkl")
    
    # Paramètres d'entraînement
    test_size: float = 0.2
    val_size: float = 0.2
    random_state: int = 42
    
    # Paramètres ARIMA
    arima_max_p: int = 5
    arima_max_d: int = 2
    arima_max_q: int = 5
    
    # Paramètres XGBoost
    xgboost_n_trials: int = 100
    xgboost_cv_folds: int = 5
    
    # Paramètres LSTM
    lstm_sequence_length: int = 30
    lstm_epochs: int = 100
    lstm_batch_size: int = 32
    lstm_patience: int = 15
    
    # Paramètres Ensemble
    ensemble_methods: list = None
    
    def __post_init__(self):
        if self.ensemble_methods is None:
            self.ensemble_methods = ["weighted_average", "stacking", "voting"]

@dataclass
class LLMConfig:
    """Configuration pour l'intégration LLM"""
    # API Keys (à définir via variables d'environnement)
    openai_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    
    # Modèles locaux
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Paramètres d'analyse
    urgency_threshold_high: float = 80.0
    urgency_threshold_medium: float = 50.0
    batch_size: int = 32
    max_text_length: int = 512
    
    # Cache
    enable_cache: bool = True
    cache_ttl_hours: int = 24
    
    def __post_init__(self):
        # Récupérer les clés API depuis les variables d'environnement
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")

@dataclass
class APIConfig:
    """Configuration pour l'API FastAPI"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # secondes
    
    # Cache
    redis_url: Optional[str] = None
    cache_ttl: int = 300  # 5 minutes
    
    # Timeouts
    prediction_timeout: float = 30.0
    llm_analysis_timeout: float = 60.0
    
    def __post_init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"

@dataclass
class MLflowConfig:
    """Configuration pour MLflow"""
    tracking_uri: str = "./mlruns"
    experiment_name: str = "blood_stock_prediction"
    
    # Métriques à tracker
    metrics_to_track: list = None
    
    def __post_init__(self):
        if self.metrics_to_track is None:
            self.metrics_to_track = ["mae", "rmse", "mape", "r2_score"]
        
        # Utiliser MLflow cloud si configuré
        cloud_uri = os.getenv("MLFLOW_TRACKING_URI")
        if cloud_uri:
            self.tracking_uri = cloud_uri

@dataclass
class DeploymentConfig:
    """Configuration pour le déploiement"""
    # Docker
    docker_image_name: str = "blood-stock-ml-service"
    docker_tag: str = "latest"
    
    # HuggingFace Spaces
    hf_space_name: Optional[str] = None
    hf_token: Optional[str] = None
    
    # Google Cloud Run
    gcp_project_id: Optional[str] = None
    gcp_region: str = "us-central1"
    gcp_service_name: str = "blood-stock-ml-service"
    
    # Monitoring
    enable_monitoring: bool = True
    health_check_interval: int = 30  # secondes
    
    def __post_init__(self):
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID")

class Config:
    """Configuration principale du système"""
    
    def __init__(self):
        self.data = DataConfig()
        self.model = ModelConfig()
        self.llm = LLMConfig()
        self.api = APIConfig()
        self.mlflow = MLflowConfig()
        self.deployment = DeploymentConfig()
        
        # Créer les répertoires nécessaires
        self._create_directories()
    
    def _create_directories(self):
        """Crée les répertoires nécessaires"""
        directories = [
            DATA_DIR,
            DATA_DIR / "synthetic",
            DATA_DIR / "processed",
            DATA_DIR / "llm_analysis",
            MODELS_DIR,
            LOGS_DIR,
            EVALUATION_DIR,
            DEMO_RESULTS_DIR
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire"""
        return {
            "data": self.data.__dict__,
            "model": self.model.__dict__,
            "llm": self.llm.__dict__,
            "api": self.api.__dict__,
            "mlflow": self.mlflow.__dict__,
            "deployment": self.deployment.__dict__
        }
    
    def save_config(self, path: Optional[str] = None):
        """Sauvegarde la configuration"""
        if path is None:
            path = BASE_DIR / "config.json"
        
        config_dict = self.to_dict()
        
        # Masquer les clés sensibles
        sensitive_keys = ["openai_api_key", "huggingface_api_key", "hf_token"]
        for section in config_dict.values():
            for key in sensitive_keys:
                if key in section and section[key]:
                    section[key] = "***MASKED***"
        
        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def validate_environment(self) -> Dict[str, bool]:
        """Valide l'environnement et les dépendances"""
        validation_results = {}
        
        # Vérifier les répertoires
        validation_results["directories_created"] = all([
            DATA_DIR.exists(),
            MODELS_DIR.exists(),
            LOGS_DIR.exists()
        ])
        
        # Vérifier les variables d'environnement optionnelles
        validation_results["openai_configured"] = bool(self.llm.openai_api_key)
        validation_results["huggingface_configured"] = bool(self.llm.huggingface_api_key)
        validation_results["mlflow_cloud_configured"] = "MLFLOW_TRACKING_URI" in os.environ
        validation_results["gcp_configured"] = bool(self.deployment.gcp_project_id)
        
        # Vérifier les dépendances Python (basique)
        try:
            import pandas, numpy, sklearn, tensorflow, xgboost
            validation_results["python_dependencies"] = True
        except ImportError:
            validation_results["python_dependencies"] = False
        
        return validation_results
    
    def print_validation_report(self):
        """Affiche un rapport de validation"""
        results = self.validate_environment()
        
        print("\n" + "="*60)
        print("🔧 RAPPORT DE VALIDATION DE L'ENVIRONNEMENT")
        print("="*60)
        
        for check, status in results.items():
            icon = "✅" if status else "❌"
            print(f"{icon} {check.replace('_', ' ').title()}: {'OK' if status else 'MANQUANT'}")
        
        # Recommandations
        print("\n📋 RECOMMANDATIONS:")
        
        if not results.get("openai_configured"):
            print("   • Définir OPENAI_API_KEY pour l'analyse LLM avancée")
        
        if not results.get("huggingface_configured"):
            print("   • Définir HUGGINGFACE_API_KEY pour les modèles HF privés")
        
        if not results.get("mlflow_cloud_configured"):
            print("   • Définir MLFLOW_TRACKING_URI pour MLflow cloud")
        
        if not results.get("gcp_configured"):
            print("   • Définir GCP_PROJECT_ID pour le déploiement GCP")
        
        if not results.get("python_dependencies"):
            print("   • Installer les dépendances: pip install -r requirements.txt")
        
        print("\n🚀 Configuration prête pour le déploiement!")

# Instance globale de configuration
config = Config()

def get_config() -> Config:
    """Retourne l'instance de configuration globale"""
    return config

def setup_environment():
    """Configure l'environnement pour le développement"""
    # Variables d'environnement par défaut pour le développement
    dev_env_vars = {
        "PYTHONPATH": str(BASE_DIR),
        "MLFLOW_TRACKING_URI": str(BASE_DIR / "mlruns"),
        "DEBUG": "true"
    }
    
    for key, value in dev_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
    
    print("🔧 Environnement de développement configuré")

if __name__ == "__main__":
    # Test de la configuration
    config = get_config()
    config.print_validation_report()
    config.save_config()
    print(f"\n💾 Configuration sauvegardée: {BASE_DIR / 'config.json'}")