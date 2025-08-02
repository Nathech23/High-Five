#!/usr/bin/env python3
"""
Script d'installation rapide pour le module RAG médical
Installe les dépendances et configure l'environnement
"""

import sys
import subprocess
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def run_command(command, description):
    """Exécute une commande et gère les erreurs"""
    logger.info(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed:")
        logger.error(f"Command: {command}")
        logger.error(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Vérifie la version de Python"""
    logger.info("=== Checking Python Version ===")
    
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8 or higher is required")
        logger.error(f"Current version: {sys.version}")
        return False
    
    logger.info(f"✅ Python version: {sys.version}")
    return True

def install_dependencies():
    """Installe les dépendances Python"""
    logger.info("=== Installing Dependencies ===")
    
    # Mettre à jour pip
    if not run_command(
        "python -m pip install --upgrade pip",
        "Upgrading pip"
    ):
        return False
    
    # Installer les dépendances
    if not run_command(
        "pip install -r requirements.txt",
        "Installing Python dependencies"
    ):
        return False
    
    return True

def setup_environment():
    """Configure l'environnement"""
    logger.info("=== Setting Up Environment ===")
    
    # Créer le fichier .env s'il n'existe pas
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        try:
            import shutil
            shutil.copy(env_example, env_file)
            logger.info("✅ Created .env file from .env.example")
            logger.warning("⚠️  Please edit .env file with your configuration")
        except Exception as e:
            logger.error(f"❌ Failed to create .env file: {e}")
            return False
    
    # Créer les répertoires nécessaires
    directories = [
        "documents",
        "embeddings",
        "logs",
        "backups"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")
    
    return True

def check_optional_dependencies():
    """Vérifie les dépendances optionnelles"""
    logger.info("=== Checking Optional Dependencies ===")
    
    # Vérifier PostgreSQL
    try:
        import psycopg2
        logger.info("✅ PostgreSQL driver (psycopg2) is available")
    except ImportError:
        logger.warning("⚠️  PostgreSQL driver not found. Install with: pip install psycopg2-binary")
    
    # Vérifier PyTorch
    try:
        import torch
        logger.info(f"✅ PyTorch is available (version: {torch.__version__})")
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA is available (devices: {torch.cuda.device_count()})")
        else:
            logger.info("ℹ️  CUDA not available, using CPU")
    except ImportError:
        logger.warning("⚠️  PyTorch not found. Install with: pip install torch")
    
    # Vérifier les modèles sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("✅ Sentence-transformers is available")
        
        # Tester le chargement du modèle par défaut
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Default embedding model loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️  Could not load default model: {e}")
            
    except ImportError:
        logger.warning("⚠️  Sentence-transformers not found")
    
    return True

def run_initial_tests():
    """Exécute des tests initiaux"""
    logger.info("=== Running Initial Tests ===")
    
    try:
        # Test d'import des modules principaux
        from config.settings import settings
        logger.info("✅ Configuration module imported successfully")
        
        from database.models import MedicalDocument
        logger.info("✅ Database models imported successfully")
        
        from embeddings.embedding_manager import EmbeddingManager
        logger.info("✅ Embedding manager imported successfully")
        
        logger.info("✅ All core modules imported successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Module import test failed: {e}")
        return False

def display_next_steps():
    """Affiche les prochaines étapes"""
    logger.info("=== Next Steps ===")
    logger.info("")
    logger.info("1. 📝 Edit the .env file with your configuration:")
    logger.info("   - PostgreSQL connection details")
    logger.info("   - Chroma settings")
    logger.info("   - Model preferences")
    logger.info("")
    logger.info("2. 🗄️  Set up your databases:")
    logger.info("   python scripts/setup_databases.py")
    logger.info("")
    logger.info("3. 🧪 Test the connections:")
    logger.info("   python scripts/test_connections.py")
    logger.info("")
    logger.info("4. 📚 Add your medical documents to the 'documents' folder")
    logger.info("")
    logger.info("5. 🚀 Start using the RAG system!")
    logger.info("")

def main():
    """Fonction principale d'installation"""
    logger.info("🏥 Hôpital Général Douala - Medical RAG Module Installation")
    logger.info("=" * 60)
    
    success_count = 0
    total_steps = 5
    
    # 1. Vérifier la version Python
    if check_python_version():
        success_count += 1
    
    # 2. Installer les dépendances
    if install_dependencies():
        success_count += 1
    
    # 3. Configurer l'environnement
    if setup_environment():
        success_count += 1
    
    # 4. Vérifier les dépendances optionnelles
    if check_optional_dependencies():
        success_count += 1
    
    # 5. Exécuter les tests initiaux
    if run_initial_tests():
        success_count += 1
    
    # Résumé
    logger.info("=== Installation Summary ===")
    logger.info(f"Steps completed: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        logger.info("🎉 Installation completed successfully!")
        display_next_steps()
        return True
    else:
        logger.error("❌ Installation incomplete")
        logger.error("Please check the errors above and try again.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during installation: {e}")
        sys.exit(1)