#!/usr/bin/env python3
"""
Script d'installation automatique pour le Module 2: Collecte et Préparation des Données Médicales

Ce script configure automatiquement l'environnement pour la collecte de données médicales.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform

def print_header():
    """Affiche l'en-tête du script d'installation"""
    print("\n" + "="*80)
    print("📚 MODULE 2: COLLECTE ET PRÉPARATION DES DONNÉES MÉDICALES")
    print("🏥 Hôpital Général de Douala - Hackathon")
    print("="*80 + "\n")

def check_python_version():
    """Vérifie la version de Python"""
    print("🔍 Vérification de la version Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ requis. Version actuelle:", sys.version)
        print("   Veuillez mettre à jour Python avant de continuer.")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} détecté")
    return True

def install_dependencies():
    """Installe les dépendances Python"""
    print("\n📦 Installation des dépendances...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ Fichier requirements.txt introuvable")
        return False
    
    try:
        # Installation des dépendances
        print("   Installation en cours... (cela peut prendre quelques minutes)")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], capture_output=True, text=True, check=True)
        
        print("✅ Dépendances installées avec succès")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation des dépendances:")
        print(f"   {e.stderr}")
        return False

def setup_directories():
    """Crée les répertoires nécessaires"""
    print("\n📁 Création des répertoires...")
    
    base_path = Path(__file__).parent
    directories = [
        "data/raw",
        "data/processed",
        "data/validated",
        "data/translated",
        "data/organized",
        "outputs/reports",
        "outputs/exports",
        "outputs/backups",
        "logs",
        "temp",
        "cache"
    ]
    
    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    print("✅ Répertoires créés")
    return True

def setup_environment():
    """Configure l'environnement (.env)"""
    print("\n⚙️ Configuration de l'environnement...")
    
    base_path = Path(__file__).parent
    env_example = base_path / ".env.example"
    env_file = base_path / ".env"
    
    # Créer .env.example s'il n'existe pas
    if not env_example.exists():
        env_content = """
# Configuration du Module 2: Collecte de Données Médicales

# === PARAMÈTRES GÉNÉRAUX ===
PROJECT_NAME="Module2_DataCollection"
ENVIRONMENT="development"
DEBUG=true
LOG_LEVEL="INFO"

# === COLLECTE DE DONNÉES ===
TARGET_DOCUMENTS=200
MAX_RETRY_ATTEMPTS=3
REQUEST_DELAY=1.0
USER_AGENT="MedicalDataCollector/1.0"

# === TRAITEMENT ===
MIN_CONTENT_LENGTH=300
MAX_CONTENT_LENGTH=50000
TARGET_SUMMARY_LENGTH=200
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# === VALIDATION ===
MIN_CONFIDENCE_THRESHOLD=0.7
MIN_SOURCE_CREDIBILITY=0.6
REQUIRE_MEDICAL_VALIDATION=true

# === TRADUCTION ===
DEFAULT_SOURCE_LANGUAGE="en"
TARGET_LANGUAGES="fr,ff,ewo,dua"
TRANSLATION_SERVICE="google"

# === ORGANISATION ===
MAX_HIERARCHY_DEPTH=4
MIN_DOCUMENTS_PER_NODE=3
MAX_DOCUMENTS_PER_NODE=20

# === API KEYS (optionnelles) ===
# GOOGLE_TRANSLATE_API_KEY="your_key_here"
# OPENAI_API_KEY="your_key_here"
# DEEPL_API_KEY="your_key_here"

# === BASE DE DONNÉES (optionnelle) ===
# DATABASE_URL="postgresql://user:password@localhost:5432/medical_data"

# === SÉCURITÉ ===
SECRET_KEY="your_secret_key_here"
ALLOWED_HOSTS="localhost,127.0.0.1"
"""
        
        with open(env_example, 'w', encoding='utf-8') as f:
            f.write(env_content.strip())
        print("   ✅ .env.example créé")
    
    # Copier vers .env si n'existe pas
    if not env_file.exists():
        shutil.copy2(env_example, env_file)
        print("   ✅ .env créé à partir de .env.example")
    else:
        print("   ℹ️ .env existe déjà")
    
    return True

def install_nlp_models():
    """Installe les modèles NLP nécessaires"""
    print("\n🧠 Installation des modèles NLP...")
    
    # Installation des modèles spaCy
    models = [
        ("fr_core_news_sm", "Français"),
        ("en_core_web_sm", "Anglais")
    ]
    
    for model, language in models:
        try:
            print(f"   Installation du modèle {language}...")
            subprocess.run([
                sys.executable, "-m", "spacy", "download", model
            ], capture_output=True, check=True)
            print(f"   ✅ Modèle {language} installé")
        except subprocess.CalledProcessError:
            print(f"   ⚠️ Échec installation modèle {language} (optionnel)")
    
    # Installation des données NLTK
    try:
        print("   Installation des données NLTK...")
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        print("   ✅ Données NLTK installées")
    except Exception as e:
        print(f"   ⚠️ Échec installation NLTK: {e}")
    
    return True

def test_installation():
    """Teste l'installation"""
    print("\n🧪 Test de l'installation...")
    
    try:
        # Test d'import du module
        sys.path.insert(0, str(Path(__file__).parent))
        
        print("   Test des imports...")
        from config import settings
        from collectors.who_collector import WHOCollector
        from processors.data_processor import MedicalDataProcessor
        print("   ✅ Imports réussis")
        
        # Test de création des objets
        print("   Test de création des objets...")
        collector = WHOCollector()
        processor = MedicalDataProcessor()
        print("   ✅ Objets créés avec succès")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur lors du test: {e}")
        return False

def print_next_steps():
    """Affiche les prochaines étapes"""
    print("\n" + "="*80)
    print("🎉 INSTALLATION TERMINÉE AVEC SUCCÈS!")
    print("="*80)
    
    print("\n📋 PROCHAINES ÉTAPES:")
    print("\n1. 📝 Configurer les paramètres:")
    print("   - Éditer le fichier .env selon vos besoins")
    print("   - Ajouter vos clés API si nécessaire")
    
    print("\n2. 🚀 Lancer la collecte:")
    print("   python main_orchestrator.py")
    
    print("\n3. 📊 Voir les résultats:")
    print("   - Données brutes: data/raw/")
    print("   - Données traitées: data/processed/")
    print("   - Rapports: outputs/reports/")
    
    print("\n4. 🔧 Scripts utiles:")
    print("   - Test rapide: python quick_start.py")
    print("   - Collecte WHO: python -m collectors.who_collector")
    print("   - Collecte CDC: python -m collectors.cdc_collector")
    
    print("\n📚 DOCUMENTATION:")
    print("   - README.md pour plus d'informations")
    print("   - config/settings.py pour les paramètres")
    
    print("\n" + "="*80)
    print("🏥 Prêt pour la collecte de données médicales!")
    print("="*80 + "\n")

def main():
    """Fonction principale d'installation"""
    print_header()
    
    # Vérifications et installations
    steps = [
        ("Vérification Python", check_python_version),
        ("Installation dépendances", install_dependencies),
        ("Création répertoires", setup_directories),
        ("Configuration environnement", setup_environment),
        ("Installation modèles NLP", install_nlp_models),
        ("Test installation", test_installation)
    ]
    
    success = True
    for step_name, step_func in steps:
        try:
            if not step_func():
                success = False
                break
        except KeyboardInterrupt:
            print("\n❌ Installation interrompue par l'utilisateur")
            return False
        except Exception as e:
            print(f"❌ Erreur lors de '{step_name}': {e}")
            success = False
            break
    
    if success:
        print_next_steps()
        return True
    else:
        print("\n❌ Installation échouée. Veuillez corriger les erreurs et réessayer.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)