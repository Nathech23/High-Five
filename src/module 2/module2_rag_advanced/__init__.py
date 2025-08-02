#!/usr/bin/env python3
"""
Module 2: RAG Avancé & Multilingue

Module avancé pour le système RAG médical avec support multilingue,
enrichissement de la base de connaissances et validation médicale.

Objectifs Module 2 (29-56):
- Enrichissement base de connaissances (1-10)
- RAG multilingue et contextuel (11-18)
- API enrichie et caching (19-24)
- Validation médicale (25-28)

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Équipe Hackathon Hôpital Général de Douala"
__description__ = "Module RAG avancé avec support multilingue et validation médicale"

# Imports principaux
try:
    from .knowledge_enrichment import (
        MedicalKnowledgeEnricher,
        SpecialtyOrganizer,
        MultilingualGlossary,
        ProtocolIntegrator
    )
    from .multilingual_rag import (
        MultilingualRAGSystem,
        CrossLingualSearch,
        IntelligentReranker,
        SourceFusion
    )
    from .advanced_api import (
        AdvancedMedicalAPI,
        IntelligentCache,
        RecommendationEngine,
        PerformanceOptimizer
    )
    from .medical_validation import (
        ExpertValidationSystem,
        SourceReliabilityScorer,
        KnowledgeUpdater,
        EvidenceDocumenter
    )
except ImportError:
    # Imports optionnels pour éviter les erreurs lors de l'installation
    pass

# Métadonnées du module
__all__ = [
    # Enrichissement base de connaissances
    "MedicalKnowledgeEnricher",
    "SpecialtyOrganizer", 
    "MultilingualGlossary",
    "ProtocolIntegrator",
    
    # RAG multilingue
    "MultilingualRAGSystem",
    "CrossLingualSearch",
    "IntelligentReranker",
    "SourceFusion",
    
    # API avancée
    "AdvancedMedicalAPI",
    "IntelligentCache",
    "RecommendationEngine",
    "PerformanceOptimizer",
    
    # Validation médicale
    "ExpertValidationSystem",
    "SourceReliabilityScorer",
    "KnowledgeUpdater",
    "EvidenceDocumenter",
    
    # Fonctions utilitaires
    "get_module_info",
    "create_advanced_rag_system"
]

def get_module_info():
    """
    Retourne les informations sur le module
    
    Returns:
        dict: Informations sur le module
    """
    return {
        "name": "RAG Avancé & Multilingue",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "components": [
            "knowledge_enrichment",
            "multilingual_rag", 
            "advanced_api",
            "medical_validation"
        ],
        "objectives": {
            "enrichissement_connaissances": list(range(1, 11)),
            "rag_multilingue": list(range(11, 19)),
            "api_enrichie": list(range(19, 25)),
            "validation_medicale": list(range(25, 29))
        },
        "languages_supported": [
            "français", "anglais", "fulfulde", "ewondo", "duala"
        ],
        "medical_specialties": [
            "cardiologie", "endocrinologie", "infectiologie",
            "pneumologie", "neurologie", "pédiatrie",
            "gynécologie", "chirurgie", "médecine_générale"
        ]
    }

def create_advanced_rag_system(config=None):
    """
    Crée un système RAG avancé avec configuration par défaut
    
    Args:
        config (dict, optional): Configuration personnalisée
    
    Returns:
        MultilingualRAGSystem: Système RAG avancé configuré
    """
    default_config = {
        "languages": ["fr", "en", "ff", "ew", "du"],
        "medical_domain": "general",
        "enable_caching": True,
        "enable_recommendations": True,
        "performance_target_ms": 200,
        "validation_level": "expert"
    }
    
    if config:
        default_config.update(config)
    
    try:
        return MultilingualRAGSystem(config=default_config)
    except NameError:
        print("⚠️  Système RAG avancé non disponible - Installation requise")
        return None

# Informations du module
print(f"🚀 Module 2: RAG Avancé & Multilingue v{__version__}")
print(f"🏥 Hôpital Général de Douala - Hackathon 2024")
print(f"🎯 Objectifs: 28 fonctionnalités avancées")