# Module 1: ML/IA + LLM + MLOps - Système de Prévision des Stocks de Sang

## Architecture du Projet

### 1. Pipeline MLOps et CI/CD ML
- MLflow pour tracking des expériences
- DVC pour versioning des données et modèles
- Pipeline automatisé : data → train → validate → deploy
- HuggingFace Hub pour déploiement
- GitHub Actions pour CI/CD
- Docker pour containerisation
- Tests automatiques de précision

### 2. Modèles ML de Prévision
- Dataset synthétique 10k+ entrées
- ARIMA pour time series
- XGBoost pour multi-variable
- LSTM avec TensorFlow
- Ensemble voting
- Métriques automatiques (MAE, RMSE, MAPE)
- Validation temporelle avec backtesting
- Optimisation hyperparamètres avec Optuna

### 3. Intégration LLM
- OpenAI/HuggingFace pour analyse textuelle
- Classification urgence/normale
- Système de recommandations intelligentes
- API endpoints optimisés
- Cache et rate limiting

### 4. Déploiement
- Service ML containerisé
- Auto-scaling
- Déploiement cloud (HuggingFace Spaces/Google Cloud Run)

## Structure du Projet

```
module1_mlops/
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
├── models/
│   ├── arima/
│   ├── xgboost/
│   ├── lstm/
│   └── ensemble/
├── src/
│   ├── data_generation/
│   ├── preprocessing/
│   ├── training/
│   ├── prediction/
│   ├── llm_integration/
│   └── api/
├── mlops/
│   ├── mlflow/
│   ├── dvc/
│   ├── docker/
│   └── github_actions/
├── tests/
├── notebooks/
└── deployment/
```

## Installation et Usage

```bash
# Installation des dépendances
pip install -r requirements.txt

# Génération des données synthétiques
python src/data_generation/generate_synthetic_data.py

# Entraînement des modèles
python src/training/train_all_models.py

# Lancement de l'API
python src/api/main.py

# Tests
pytest tests/
```

## Métriques de Performance
- Latence API < 2 secondes
- Précision modèles > 85%
- Disponibilité > 99%
- Auto-scaling basé sur la charge