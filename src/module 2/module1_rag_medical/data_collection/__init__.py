#!/usr/bin/env python3
"""
Module 2: Collecte et Préparation des Données Médicales

Ce module fournit un système complet pour:
- Collecter 200+ documents médicaux publics depuis des sources fiables (WHO, CDC, etc.)
- Créer un corpus français sur les maladies courantes
- Structurer les données par catégories (diagnostics, traitements, médicaments)
- Nettoyer et formater les textes pour les embeddings
- Créer des fiches explicatives en langage simple
- Valider l'exactitude médicale des sources
- Traduire les contenus essentiels en langues locales
- Organiser une hiérarchie thématique des connaissances

Auteur: Assistant IA
Version: 1.0.0
Date: 2024
"""

__version__ = "1.0.0"
__author__ = "Assistant IA"
__description__ = "Module de collecte et préparation des données médicales pour l'Hôpital Général de Douala"

# Imports principaux
from .main_orchestrator import DataCollectionOrchestrator

# Imports des collecteurs
from .collectors.who_collector import WHOCollector
from .collectors.cdc_collector import CDCCollector

# Imports des processeurs
from .processors.data_processor import MedicalDataProcessor, ProcessedDocument

# Imports des validateurs
from .validators.medical_validator import MedicalValidator, ValidationResult

# Imports des traducteurs
from .translators.medical_translator import MedicalTranslator, TranslationResult

# Imports des organisateurs
from .organizers.knowledge_organizer import KnowledgeOrganizer, KnowledgeHierarchy

# Configuration
from .config import settings

__all__ = [
    # Orchestrateur principal
    'DataCollectionOrchestrator',
    
    # Collecteurs
    'WHOCollector',
    'CDCCollector',
    
    # Processeurs
    'MedicalDataProcessor',
    'ProcessedDocument',
    
    # Validateurs
    'MedicalValidator',
    'ValidationResult',
    
    # Traducteurs
    'MedicalTranslator',
    'TranslationResult',
    
    # Organisateurs
    'KnowledgeOrganizer',
    'KnowledgeHierarchy',
    
    # Configuration
    'settings'
]

# Informations du module
MODULE_INFO = {
    'name': 'Module 2: Collecte et Préparation des Données Médicales',
    'version': __version__,
    'description': __description__,
    'author': __author__,
    'capabilities': [
        'Collecte automatisée de documents médicaux',
        'Traitement et nettoyage des données',
        'Validation médicale des contenus',
        'Traduction multilingue (français, anglais, langues locales)',
        'Organisation hiérarchique des connaissances',
        'Génération de fiches explicatives simplifiées',
        'Rapports de qualité et statistiques'
    ],
    'supported_sources': [
        'WHO (Organisation Mondiale de la Santé)',
        'CDC (Centers for Disease Control)',
        'Sources médicales publiques'
    ],
    'supported_languages': [
        'Français (fr)',
        'Anglais (en)',
        'Fulfulde (ff)',
        'Ewondo (ewo)',
        'Duala (dua)'
    ],
    'output_formats': [
        'JSON (données structurées)',
        'CSV (analyse)',
        'HTML (rapports)',
        'TXT (hiérarchie lisible)'
    ]
}

def get_module_info():
    """Retourne les informations du module"""
    return MODULE_INFO

def get_version():
    """Retourne la version du module"""
    return __version__

def create_orchestrator(config=None):
    """Crée une instance de l'orchestrateur avec configuration par défaut"""
    if config is None:
        config = {
            'processing': {
                'min_content_length': 300,
                'max_content_length': 50000,
                'target_summary_length': 200
            },
            'validation': {
                'min_confidence_threshold': 0.7,
                'min_source_credibility': 0.6
            },
            'translation': {},
            'organization': {
                'max_hierarchy_depth': 4,
                'min_documents_per_node': 3,
                'max_documents_per_node': 20
            }
        }
    
    return DataCollectionOrchestrator(config)

# Message de bienvenue
print(f"📚 {MODULE_INFO['name']} v{__version__} chargé avec succès")
print(f"🎯 Prêt pour la collecte et préparation de données médicales")