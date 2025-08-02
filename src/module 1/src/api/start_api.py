"""Script de démarrage pour l'API de rappels"""

import uvicorn
import os
import sys
import logging
from pathlib import Path

# Ajouter le répertoire courant au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_api import config

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, config.api.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_reminders.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Charger les variables d'environnement depuis le fichier .env"""
    
    # Charger le fichier .env s'il existe
    env_file = Path('.env')
    if env_file.exists():
        logger.info("Chargement du fichier .env")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value
    else:
        logger.warning("Fichier .env non trouvé. Assurez-vous que les variables d'environnement sont définies.")
    
    # Vérifier les variables critiques
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")
        logger.error("Veuillez créer un fichier .env avec les variables requises.")
        return False
    
    return True

def check_dependencies():
    """Vérifier que toutes les dépendances sont disponibles"""
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'redis',
        'asyncpg',
        'twilio',
        'pydantic',
        'httpx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Packages manquants: {', '.join(missing_packages)}")
        logger.error("Installez-les avec: pip install " + ' '.join(missing_packages))
        return False
    
    logger.info("Toutes les dépendances sont disponibles")
    return True

def check_services():
    """Vérifier que les services externes sont accessibles"""
    
    import redis
    import asyncpg
    import asyncio
    
    # Test Redis
    try:
        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            socket_timeout=5
        )
        redis_client.ping()
        logger.info("✅ Redis accessible")
    except Exception as e:
        logger.warning(f"⚠️  Redis non accessible: {e}")
        logger.warning("L'API fonctionnera en mode dégradé sans Redis")
    
    # Test PostgreSQL
    async def test_postgres():
        try:
            conn = await asyncpg.connect(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT')),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            await conn.close()
            logger.info("✅ PostgreSQL accessible")
            return True
        except Exception as e:
            logger.error(f"❌ PostgreSQL non accessible: {e}")
            return False
    
    try:
        postgres_ok = asyncio.run(test_postgres())
        if not postgres_ok:
            logger.error("PostgreSQL est requis pour le fonctionnement de l'API")
            return False
    except Exception as e:
        logger.error(f"Erreur lors du test PostgreSQL: {e}")
        return False
    
    return True

def print_startup_info():
    """Afficher les informations de démarrage"""
    
    print("\n" + "=" * 60)
    print("🏥 API de Rappels - Hôpital Général de Douala")
    print("📅 Phase 4: API callbacks et planification")
    print("=" * 60)
    print(f"🌍 Environnement: {config.environment}")
    print(f"🕐 Timezone: {config.timezone}")
    print(f"🌐 API: http://{config.api.host}:{config.api.port}")
    print(f"📊 Docs: http://{config.api.host}:{config.api.port}/docs")
    print(f"🔧 Redis: {config.redis.host}:{config.redis.port}")
    print(f"📝 Log level: {config.api.log_level}")
    print("=" * 60)
    print("\n🚀 Fonctionnalités disponibles:")
    print("   ✅ Création de rappels programmés")
    print("   ✅ Envoi de rappels immédiats")
    print("   ✅ Gestion des files d'attente Redis")
    print("   ✅ Planificateur automatique avec retry")
    print("   ✅ Tracking des statuts de livraison")
    print("   ✅ Webhooks Twilio")
    print("   ✅ Métriques et monitoring")
    print("   ✅ API de gestion et administration")
    print("\n📋 Endpoints principaux:")
    print("   POST /reminders - Créer un rappel")
    print("   GET  /reminders - Lister les rappels")
    print("   POST /reminders/immediate - Envoi immédiat")
    print("   POST /reminders/batch - Création en lot")
    print("   GET  /reminders/stats - Statistiques")
    print("   POST /webhook/twilio/status - Webhook Twilio")
    print("   GET  /health - État de santé")
    print("   GET  /metrics - Métriques détaillées")
    print("\n" + "=" * 60)

def main():
    """Point d'entrée principal"""
    
    print("Initialisation de l'API de rappels...")
    
    # Configuration de l'environnement
    if not setup_environment():
        logger.error("Échec de la configuration de l'environnement")
        sys.exit(1)
    
    # Vérification des dépendances
    if not check_dependencies():
        sys.exit(1)
    
    # Vérification des services
    if not check_services():
        logger.error("Impossible de démarrer l'API sans les services requis")
        sys.exit(1)
    
    # Affichage des informations
    print_startup_info()
    
    # Configuration d'uvicorn
    uvicorn_config = {
        "app": "reminder_api:app",
        "host": config.api.host,
        "port": config.api.port,
        "log_level": config.api.log_level,
        "reload": config.api.reload and config.is_development,
        "workers": 1 if config.api.reload else config.api.workers,
        "access_log": True,
        "use_colors": True
    }
    
    # Démarrage du serveur
    try:
        logger.info(f"Démarrage du serveur sur {config.api.host}:{config.api.port}")
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        logger.info("Arrêt du serveur demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du serveur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()