#!/bin/bash
set -e

# Script d'entrée pour le conteneur Docker
echo "🩸 Démarrage du service ML de prédiction des stocks de sang"
echo "Version: 1.0.0"
echo "Port: $PORT"
echo "Modèles: $MODEL_PATH"
echo "Données: $DATA_PATH"

# Vérifier que les modèles existent
if [ ! -d "$MODEL_PATH" ]; then
    echo "⚠️ Répertoire des modèles non trouvé: $MODEL_PATH"
    echo "Création du répertoire..."
    mkdir -p "$MODEL_PATH"
fi

# Vérifier que les données existent
if [ ! -d "$DATA_PATH" ]; then
    echo "⚠️ Répertoire des données non trouvé: $DATA_PATH"
    echo "Création du répertoire..."
    mkdir -p "$DATA_PATH"
fi

# Fonction de nettoyage
cleanup() {
    echo "🛑 Arrêt du service..."
    exit 0
}

# Capturer les signaux d'arrêt
trap cleanup SIGTERM SIGINT

# Vérifier la santé des modèles
echo "🔍 Vérification des modèles..."
python -c "
import os
import sys
sys.path.append('/app/src')

try:
    from training.ensemble_model import EnsemblePredictor
    from llm_integration.llm_analyzer import LLMBloodStockAnalyzer
    print('✅ Modules importés avec succès')
except Exception as e:
    print(f'❌ Erreur d\'import: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la vérification des modèles"
    exit 1
fi

# Générer des données de test si nécessaire
if [ ! -f "$DATA_PATH/synthetic/blood_stock_data.csv" ]; then
    echo "📊 Génération des données de test..."
    cd /app
    python -m src.data_generation.generate_synthetic_data
fi

# Démarrer MLflow en arrière-plan (optionnel)
if [ "$ENABLE_MLFLOW" = "true" ]; then
    echo "🔬 Démarrage de MLflow..."
    mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri file:///app/mlruns &
    MLFLOW_PID=$!
fi

# Démarrer l'API
echo "🚀 Démarrage de l'API FastAPI..."
cd /app

# Mode de démarrage selon l'environnement
if [ "$ENVIRONMENT" = "development" ]; then
    echo "🔧 Mode développement"
    python -m uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --reload
else
    echo "🏭 Mode production"
    python -m gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
fi

# Attendre les processus en arrière-plan
wait