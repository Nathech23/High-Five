# 🛠️ Guide d'Installation - Système MLOps de Prédiction des Stocks de Sang

## 🏥 Hôpital Général Douala - Module 1: ML/IA + LLM + MLOps

---

## ⚡ Installation Rapide (Recommandée)

### Étape 1: Prérequis

```bash
# Vérifier Python (version 3.8+)
python --version

# Mettre à jour pip
python -m pip install --upgrade pip

# Installer les outils de build
pip install setuptools wheel
```

### Étape 2: Installation des Dépendances de Base

```bash
# Installer les dépendances essentielles
pip install -r requirements.txt
```

### Étape 3: Test de l'Installation

```bash
# Tester la configuration
python config.py

# Lancer la démonstration
python demo.py
```

---

## 🔧 Installation Complète (Optionnelle)

Si vous souhaitez installer toutes les fonctionnalités avancées :

### Dépendances ML Avancées

```bash
# Machine Learning
pip install tensorflow xgboost statsmodels optuna

# MLOps
pip install mlflow dvc

# LLM Integration
pip install transformers openai sentence-transformers

# Monitoring
pip install redis prometheus-client
```

### Variables d'Environnement (Optionnelles)

Créer un fichier `.env` :

```env
# API Keys (optionnelles)
OPENAI_API_KEY=your_openai_key_here
HUGGINGFACE_API_KEY=your_hf_key_here

# MLflow (optionnel)
MLFLOW_TRACKING_URI=./mlruns

# Redis (optionnel)
REDIS_URL=redis://localhost:6379

# Déploiement (optionnel)
GCP_PROJECT_ID=your_gcp_project
HUGGINGFACE_TOKEN=your_hf_token
```

---

## 🚀 Démarrage Rapide

### 1. Génération de Données

```bash
# Générer 12,000+ enregistrements de données synthétiques
python src/data_generation/generate_synthetic_data.py
```

### 2. API FastAPI

```bash
# Démarrer l'API (mode développement)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Accéder à l'API
# http://localhost:8000
# Documentation: http://localhost:8000/docs
```

### 3. Tests

```bash
# Lancer les tests
python tests/test_complete_system.py

# Tests avec pytest (si installé)
pytest tests/ -v
```

---

## 🐳 Installation Docker

### Option 1: Build Local

```bash
# Construire l'image
docker build -t blood-stock-ml .

# Lancer le conteneur
docker run -p 8000:8000 blood-stock-ml
```

### Option 2: Docker Compose (Recommandé)

Créer `docker-compose.yml` :

```yaml
version: '3.8'
services:
  blood-stock-ml:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
    volumes:
      - ./data:/app/data
      - ./models:/app/models
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

```bash
# Démarrer avec Docker Compose
docker-compose up -d
```

---

## 🔍 Résolution des Problèmes

### Problème 1: Erreurs d'Installation pip

**Symptôme**: `BackendUnavailable: Cannot import 'setuptools.build_meta'`

**Solution**:
```bash
# Mettre à jour les outils de build
pip install --upgrade setuptools wheel pip

# Réinstaller
pip install -r requirements.txt
```

### Problème 2: Conflits de Dépendances

**Symptôme**: Erreurs de résolution de dépendances

**Solution**:
```bash
# Utiliser un environnement virtuel
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Installer dans l'environnement propre
pip install -r requirements.txt
```

### Problème 3: Modules Manquants

**Symptôme**: `ModuleNotFoundError`

**Solution**:
```bash
# Ajouter le répertoire src au PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Ou utiliser le script de configuration
python config.py
```

### Problème 4: Erreurs TensorFlow/GPU

**Symptôme**: Erreurs CUDA ou GPU

**Solution**:
```bash
# Installer TensorFlow CPU uniquement
pip install tensorflow-cpu

# Ou ignorer les avertissements GPU
export TF_CPP_MIN_LOG_LEVEL=2
```

---

## 📋 Vérification de l'Installation

### Script de Vérification

```python
# verification.py
import sys
import importlib

required_modules = [
    'pandas', 'numpy', 'sklearn', 'fastapi', 
    'uvicorn', 'requests', 'tqdm', 'joblib'
]

optional_modules = [
    'tensorflow', 'xgboost', 'mlflow', 
    'transformers', 'openai'
]

print("🔍 Vérification des modules requis:")
for module in required_modules:
    try:
        importlib.import_module(module)
        print(f"✅ {module}")
    except ImportError:
        print(f"❌ {module} - MANQUANT")

print("\n🔍 Vérification des modules optionnels:")
for module in optional_modules:
    try:
        importlib.import_module(module)
        print(f"✅ {module}")
    except ImportError:
        print(f"⚠️ {module} - Optionnel")

print("\n🎯 Installation vérifiée!")
```

```bash
# Lancer la vérification
python verification.py
```

---

## 🌟 Fonctionnalités par Niveau d'Installation

### Niveau 1: Installation Minimale ✅
- ✅ Génération de données synthétiques
- ✅ API FastAPI basique
- ✅ Tests unitaires
- ✅ Configuration système

### Niveau 2: Installation Standard
- ✅ Niveau 1 +
- ✅ Modèles ML (XGBoost, scikit-learn)
- ✅ Préprocessing avancé
- ✅ Métriques et évaluation

### Niveau 3: Installation Complète
- ✅ Niveau 2 +
- ✅ Deep Learning (TensorFlow, LSTM)
- ✅ MLOps (MLflow, DVC)
- ✅ LLM Integration (OpenAI, HuggingFace)
- ✅ Monitoring et alertes

---

## 📞 Support

### En cas de problème:

1. **Vérifier les prérequis**: Python 3.8+, pip à jour
2. **Consulter les logs**: Erreurs détaillées dans la console
3. **Environnement virtuel**: Toujours recommandé
4. **Documentation**: Consulter `TECHNICAL_DOCUMENTATION.md`
5. **Tests**: Lancer `python tests/test_complete_system.py`

### Commandes de Diagnostic

```bash
# Informations système
python --version
pip --version
pip list

# Test de configuration
python config.py

# Test des imports
python -c "import pandas, numpy, sklearn, fastapi; print('✅ Modules de base OK')"

# Test de l'API
curl http://localhost:8000/health
```

---

## 🎯 Prochaines Étapes

Après installation réussie :

1. **📊 Générer des données**: `python src/data_generation/generate_synthetic_data.py`
2. **🚀 Démarrer l'API**: `uvicorn src.api.main:app --reload`
3. **🧪 Lancer les tests**: `python tests/test_complete_system.py`
4. **📖 Consulter la doc**: `TECHNICAL_DOCUMENTATION.md`
5. **🎮 Démonstration**: `python demo.py`
