#!/usr/bin/env python3
"""
RAG Multilingue et Contextuel

Objectifs 11-18: RAG multilingue et contextuel

Ce package implémente un système RAG avancé avec support multilingue,
traduction automatique, recherche cross-linguale et optimisations
spécifiques pour le contexte médical camerounais.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métadonnées du package
__version__ = "2.0.0"
__author__ = "Équipe Hackathon HGD"
__description__ = "RAG Multilingue et Contextuel pour l'Hôpital Général de Douala"

# Objectifs couverts par ce package
OBJECTIVES = {
    11: "Implémenter embeddings multilingues",
    12: "Créer système de traduction automatique", 
    13: "Développer recherche cross-linguale",
    14: "Optimiser chunking pour différentes langues",
    15: "Implémenter re-ranking des résultats",
    16: "Créer fusion intelligente sources multiples",
    17: "Ajouter filtrage par pertinence médicale",
    18: "Tester précision recherche sur 200 requêtes"
}

# Langues supportées
SUPPORTED_LANGUAGES = {
    "fr": "Français",
    "en": "Anglais", 
    "ff": "Fulfulde",
    "ewondo": "Ewondo",
    "duala": "Duala",
    "bamileke": "Bamiléké",
    "ha": "Hausa",
    "ar": "Arabe"
}

# Configuration par défaut
DEFAULT_CONFIG = {
    "primary_language": "fr",
    "fallback_language": "en",
    "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "translation_service": "google",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "max_results": 10,
    "similarity_threshold": 0.7,
    "rerank_top_k": 20,
    "medical_boost_factor": 1.5
}

# Composants du package
COMPONENTS = {
    "multilingual_embeddings": "Embeddings multilingues optimisés",
    "translation_system": "Système de traduction automatique", 
    "cross_lingual_search": "Recherche cross-linguale",
    "language_chunker": "Chunking optimisé par langue",
    "result_reranker": "Re-ranking intelligent des résultats",
    "source_fusion": "Fusion de sources multiples",
    "medical_filter": "Filtrage par pertinence médicale",
    "evaluation_system": "Système d'évaluation sur 200 requêtes"
}

def get_package_info() -> Dict[str, Any]:
    """
    Retourne les informations du package
    
    Returns:
        Dict[str, Any]: Informations du package
    """
    return {
        "name": "multilingual_rag",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "objectives": OBJECTIVES,
        "supported_languages": SUPPORTED_LANGUAGES,
        "components": COMPONENTS,
        "default_config": DEFAULT_CONFIG
    }

def get_objectives_status() -> Dict[int, str]:
    """
    Retourne le statut des objectifs
    
    Returns:
        Dict[int, str]: Statut de chaque objectif
    """
    return {
        11: "✅ Implémenté - Embeddings multilingues avec sentence-transformers",
        12: "✅ Implémenté - Traduction automatique Google/DeepL",
        13: "✅ Implémenté - Recherche cross-linguale avec mapping",
        14: "✅ Implémenté - Chunking adaptatif par langue",
        15: "✅ Implémenté - Re-ranking avec scores multiples",
        16: "✅ Implémenté - Fusion intelligente avec pondération",
        17: "✅ Implémenté - Filtrage médical avec terminologie",
        18: "✅ Implémenté - Évaluation sur 200 requêtes test"
    }

def create_multilingual_rag_system(config: Optional[Dict[str, Any]] = None) -> 'MultilingualRAGSystem':
    """
    Crée une instance du système RAG multilingue
    
    Args:
        config: Configuration optionnelle
    
    Returns:
        MultilingualRAGSystem: Instance du système RAG
    """
    try:
        from .multilingual_rag_system import MultilingualRAGSystem
        
        # Fusionner avec la configuration par défaut
        final_config = DEFAULT_CONFIG.copy()
        if config:
            final_config.update(config)
        
        system = MultilingualRAGSystem(final_config)
        logger.info("Système RAG multilingue créé avec succès")
        return system
    
    except ImportError as e:
        logger.error(f"Erreur d'import: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création du système RAG: {e}")
        raise

def validate_language_support(language: str) -> bool:
    """
    Valide si une langue est supportée
    
    Args:
        language: Code de langue à valider
    
    Returns:
        bool: True si la langue est supportée
    """
    return language.lower() in SUPPORTED_LANGUAGES

def get_language_name(language_code: str) -> str:
    """
    Retourne le nom complet d'une langue
    
    Args:
        language_code: Code de langue
    
    Returns:
        str: Nom complet de la langue
    """
    return SUPPORTED_LANGUAGES.get(language_code.lower(), "Langue inconnue")

def list_available_components() -> List[str]:
    """
    Liste les composants disponibles
    
    Returns:
        List[str]: Liste des composants
    """
    return list(COMPONENTS.keys())

# Imports conditionnels pour éviter les erreurs de dépendances
try:
    from .multilingual_embeddings import MultilingualEmbeddings
    from .translation_system import TranslationSystem
    from .cross_lingual_search import CrossLingualSearch
    from .language_chunker import LanguageChunker
    from .result_reranker import ResultReranker
    from .source_fusion import SourceFusion
    from .medical_filter import MedicalFilter
    from .evaluation_system import EvaluationSystem
    from .multilingual_rag_system import MultilingualRAGSystem
    
    __all__ = [
        "MultilingualEmbeddings",
        "TranslationSystem", 
        "CrossLingualSearch",
        "LanguageChunker",
        "ResultReranker",
        "SourceFusion",
        "MedicalFilter",
        "EvaluationSystem",
        "MultilingualRAGSystem",
        "get_package_info",
        "get_objectives_status",
        "create_multilingual_rag_system",
        "validate_language_support",
        "get_language_name",
        "list_available_components",
        "SUPPORTED_LANGUAGES",
        "DEFAULT_CONFIG",
        "OBJECTIVES"
    ]
    
except ImportError as e:
    logger.warning(f"Certains composants ne sont pas disponibles: {e}")
    __all__ = [
        "get_package_info",
        "get_objectives_status", 
        "validate_language_support",
        "get_language_name",
        "list_available_components",
        "SUPPORTED_LANGUAGES",
        "DEFAULT_CONFIG",
        "OBJECTIVES"
    ]

# Message d'initialisation
logger.info(f"Package RAG Multilingue v{__version__} initialisé")
logger.info(f"Langues supportées: {', '.join(SUPPORTED_LANGUAGES.values())}")
logger.info(f"Objectifs couverts: {len(OBJECTIVES)} objectifs (11-18)")