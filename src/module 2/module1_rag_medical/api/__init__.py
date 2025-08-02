#!/usr/bin/env python3
"""
Package API pour le Système RAG Médical

Ce package contient l'API FastAPI complète pour le système RAG médical
développé pour l'Hôpital Général de Douala.

Objectifs Hackathon:
25. ✅ Créer API FastAPI pour service RAG
26. ✅ Implémenter endpoints de recherche de connaissances
27. ✅ Valider pipeline complet : query → embeddings → search → context
28. ✅ Documenter architecture RAG

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 1 - RAG & Medical Knowledge
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Équipe Hackathon Hôpital Général de Douala"
__description__ = "API FastAPI pour le système RAG médical"

# Imports principaux
try:
    from .main import app, api_manager
except ImportError:
    # Imports optionnels pour éviter les erreurs lors de l'installation
    app = None
    api_manager = None

# Métadonnées du module
__all__ = [
    "app",
    "api_manager",
    "get_api_info",
    "create_api_app"
]

def get_api_info():
    """
    Retourne les informations sur l'API
    
    Returns:
        dict: Informations sur l'API
    """
    return {
        "name": "API RAG Médical",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "endpoints": [
            "/health",
            "/status",
            "/info",
            "/query",
            "/search",
            "/index",
            "/evaluate",
            "/validate-pipeline",
            "/metrics",
            "/docs-architecture"
        ],
        "hackathon_objectives": [
            "25. ✅ Créer API FastAPI pour service RAG",
            "26. ✅ Implémenter endpoints de recherche de connaissances",
            "27. ✅ Valider pipeline complet : query → embeddings → search → context",
            "28. ✅ Documenter architecture RAG"
        ]
    }

def create_api_app():
    """
    Crée et configure l'application FastAPI
    
    Returns:
        FastAPI: Application configurée
    """
    from .main import app
    return app

# Informations du module
print(f"📡 API RAG Médical v{__version__} - Hôpital Général de Douala")
print(f"🎯 Objectifs Hackathon: 25-28 ✅")