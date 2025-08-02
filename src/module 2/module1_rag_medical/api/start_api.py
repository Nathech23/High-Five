#!/usr/bin/env python3
"""
Script de Démarrage pour l'API RAG Médical

Script pour démarrer facilement l'API FastAPI avec configuration optimisée.

Objectifs Hackathon:
25. ✅ Créer API FastAPI pour service RAG
26. ✅ Implémenter endpoints de recherche de connaissances
27. ✅ Valider pipeline complet : query → embeddings → search → context
28. ✅ Documenter architecture RAG

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 1 - RAG & Medical Knowledge
Version: 1.0.0
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_header(title: str, char: str = "=", width: int = 60) -> None:
    """Affiche un en-tête formaté"""
    print("\n" + char * width)
    print(f"    {title}")
    print(char * width)

def print_info(message: str) -> None:
    """Affiche une information"""
    print(f"ℹ️  {message}")

def print_success(message: str) -> None:
    """Affiche un message de succès"""
    print(f"✅ {message}")

def print_error(message: str) -> None:
    """Affiche une erreur"""
    print(f"❌ {message}")

def print_warning(message: str) -> None:
    """Affiche un avertissement"""
    print(f"⚠️  {message}")

def check_dependencies():
    """Vérifie les dépendances nécessaires"""
    print_info("Vérification des dépendances...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"Package '{package}' disponible")
        except ImportError:
            missing_packages.append(package)
            print_error(f"Package '{package}' manquant")
    
    if missing_packages:
        print_error(f"Packages manquants: {', '.join(missing_packages)}")
        print_info("Installez les dépendances avec:")
        print_info("pip install fastapi uvicorn pydantic requests")
        return False
    
    print_success("Toutes les dépendances sont disponibles")
    return True

def check_rag_system():
    """Vérifie que le système RAG est disponible"""
    print_info("Vérification du système RAG...")
    
    try:
        # Ajouter le chemin parent pour les imports
        parent_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(parent_dir))
        
        from rag import get_module_info
        module_info = get_module_info()
        
        print_success(f"Système RAG disponible - Version: {module_info.get('version', 'N/A')}")
        return True
        
    except ImportError as e:
        print_error(f"Système RAG non disponible: {e}")
        print_info("Assurez-vous que le module RAG est correctement installé")
        return False

def start_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True, 
                    log_level: str = "info", workers: int = 1):
    """Démarre le serveur API"""
    try:
        import uvicorn
        from main import app
        
        print_header("DÉMARRAGE DE L'API RAG MÉDICAL")
        print_info(f"Host: {host}")
        print_info(f"Port: {port}")
        print_info(f"Reload: {reload}")
        print_info(f"Log Level: {log_level}")
        print_info(f"Workers: {workers}")
        
        print_info("\n🌐 URLs disponibles:")
        print_info(f"  • API: http://{host}:{port}")
        print_info(f"  • Documentation: http://{host}:{port}/docs")
        print_info(f"  • Architecture: http://{host}:{port}/docs-architecture")
        print_info(f"  • Santé: http://{host}:{port}/health")
        
        print_info("\n🎯 Endpoints principaux:")
        print_info("  • POST /query - Requête RAG complète")
        print_info("  • POST /search - Recherche sémantique")
        print_info("  • POST /validate-pipeline - Validation pipeline")
        print_info("  • POST /evaluate - Évaluation performance")
        
        print_success("\nDémarrage du serveur...")
        print_warning("Appuyez sur Ctrl+C pour arrêter le serveur")
        
        # Configuration uvicorn
        config = {
            "app": "main:app",
            "host": host,
            "port": port,
            "reload": reload,
            "log_level": log_level,
            "access_log": True
        }
        
        if workers > 1 and not reload:
            config["workers"] = workers
        
        uvicorn.run(**config)
        
    except KeyboardInterrupt:
        print_warning("\nArrêt du serveur demandé par l'utilisateur")
        print_success("Serveur arrêté proprement")
    except Exception as e:
        print_error(f"Erreur lors du démarrage du serveur: {e}")
        logger.error(f"Erreur détaillée: {e}", exc_info=True)
        return False
    
    return True

def run_quick_test(api_url: str):
    """Lance un test rapide de l'API"""
    print_info("Lancement d'un test rapide...")
    
    try:
        import requests
        import time
        
        # Attendre que l'API soit prête
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"{api_url}/health", timeout=2)
                if response.status_code == 200:
                    print_success("API accessible")
                    break
            except:
                if i < max_retries - 1:
                    print_info(f"Tentative {i+1}/{max_retries} - Attente de l'API...")
                    time.sleep(2)
                else:
                    print_error("API non accessible après plusieurs tentatives")
                    return False
        
        # Test de requête simple
        test_query = {
            "query": "Qu'est-ce que le diabète ?",
            "language": "fr",
            "max_results": 3
        }
        
        response = requests.post(f"{api_url}/query", json=test_query, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Test réussi - Confiance: {result.get('confidence_score', 0):.3f}")
            print_info(f"Temps de traitement: {result.get('processing_time', 0):.3f}s")
            return True
        else:
            print_error(f"Test échoué - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur lors du test: {e}")
        return False

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Démarrage de l'API RAG Médical",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python start_api.py                    # Démarrage standard
  python start_api.py --port 8080        # Port personnalisé
  python start_api.py --no-reload        # Sans rechargement automatique
  python start_api.py --workers 4        # Plusieurs workers (production)
  python start_api.py --test-only        # Test uniquement

Objectifs Hackathon:
  ✅ 25. Créer API FastAPI pour service RAG
  ✅ 26. Implémenter endpoints de recherche de connaissances
  ✅ 27. Valider pipeline complet : query → embeddings → search → context
  ✅ 28. Documenter architecture RAG
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Adresse d'écoute (défaut: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port d'écoute (défaut: 8000)"
    )
    
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Désactiver le rechargement automatique"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="Niveau de log (défaut: info)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Nombre de workers (défaut: 1)"
    )
    
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Lancer uniquement les tests sans démarrer le serveur"
    )
    
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Ignorer les vérifications de dépendances"
    )
    
    args = parser.parse_args()
    
    print_header("API RAG MÉDICAL - HÔPITAL GÉNÉRAL DE DOUALA")
    print_info("Hackathon 2024 - Module 1: RAG & Medical Knowledge")
    print_info("Objectifs 25-28: API RAG et validation")
    
    # Vérifications préliminaires
    if not args.skip_checks:
        if not check_dependencies():
            return 1
        
        if not check_rag_system():
            return 1
    
    # Mode test uniquement
    if args.test_only:
        api_url = f"http://{args.host}:{args.port}"
        success = run_quick_test(api_url)
        return 0 if success else 1
    
    # Démarrage du serveur
    try:
        success = start_api_server(
            host=args.host,
            port=args.port,
            reload=not args.no_reload,
            log_level=args.log_level,
            workers=args.workers
        )
        
        return 0 if success else 1
        
    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())