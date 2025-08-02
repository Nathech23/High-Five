#!/usr/bin/env python3
"""
Validation Médicale - Module 2 RAG Avancé

Ce package implémente un système complet de validation médicale
pour garantir la qualité et la fiabilité des connaissances médicales.

Objectifs couverts (25-28):
- 25. Créer processus validation contenu par experts
- 26. Implémenter scoring fiabilité sources
- 27. Ajouter système de mise à jour connaissances
- 28. Documenter sources et niveaux de preuve

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Métadonnées du package
__version__ = "2.0.0"
__author__ = "Équipe Hackathon HGD"
__description__ = "Validation Médicale pour RAG Médical Multilingue"

# Objectifs du module
OBJECTIVES = {
    25: {
        "title": "Créer processus validation contenu par experts",
        "description": "Système de validation par comité d'experts médicaux",
        "components": ["expert_validation_system", "peer_review", "consensus_builder"],
        "status": "implemented"
    },
    26: {
        "title": "Implémenter scoring fiabilité sources",
        "description": "Système de notation automatique de la fiabilité des sources",
        "components": ["source_reliability_scorer", "credibility_analyzer", "bias_detector"],
        "status": "implemented"
    },
    27: {
        "title": "Ajouter système de mise à jour connaissances",
        "description": "Système automatique de mise à jour des connaissances médicales",
        "components": ["knowledge_updater", "change_detector", "version_manager"],
        "status": "implemented"
    },
    28: {
        "title": "Documenter sources et niveaux de preuve",
        "description": "Documentation complète des sources avec niveaux de preuve EBM",
        "components": ["evidence_documenter", "source_tracker", "citation_manager"],
        "status": "implemented"
    }
}

# Configuration par défaut
DEFAULT_CONFIG = {
    "validation": {
        "min_expert_consensus": 0.75,
        "review_timeout_days": 7,
        "auto_approve_threshold": 0.9,
        "require_peer_review": True
    },
    "reliability": {
        "min_source_score": 0.6,
        "weight_factors": {
            "journal_impact": 0.3,
            "author_credentials": 0.25,
            "peer_review_status": 0.2,
            "citation_count": 0.15,
            "recency": 0.1
        }
    },
    "updates": {
        "check_frequency_hours": 24,
        "auto_update_threshold": 0.8,
        "backup_versions": 5,
        "notification_enabled": True
    },
    "evidence": {
        "levels": ["I", "II", "III", "IV", "V"],
        "require_citations": True,
        "track_provenance": True,
        "version_control": True
    }
}

# Niveaux de preuve Evidence-Based Medicine
EVIDENCE_LEVELS = {
    "I": {
        "name": "Niveau I - Méta-analyses",
        "description": "Méta-analyses d'essais contrôlés randomisés",
        "weight": 1.0
    },
    "II": {
        "name": "Niveau II - Essais contrôlés",
        "description": "Essais contrôlés randomisés individuels",
        "weight": 0.9
    },
    "III": {
        "name": "Niveau III - Études de cohorte",
        "description": "Études de cohorte et cas-témoins",
        "weight": 0.7
    },
    "IV": {
        "name": "Niveau IV - Séries de cas",
        "description": "Séries de cas et études descriptives",
        "weight": 0.5
    },
    "V": {
        "name": "Niveau V - Opinion d'experts",
        "description": "Opinion d'experts et consensus",
        "weight": 0.3
    }
}

# Types de sources médicales
SOURCE_TYPES = {
    "journal": "Article de journal médical",
    "guideline": "Guideline clinique",
    "textbook": "Manuel médical",
    "database": "Base de données médicale",
    "conference": "Actes de conférence",
    "thesis": "Thèse médicale",
    "report": "Rapport médical",
    "website": "Site web médical"
}

# Statuts de validation
VALIDATION_STATUS = {
    "pending": "En attente de validation",
    "under_review": "En cours de révision",
    "approved": "Approuvé",
    "rejected": "Rejeté",
    "needs_revision": "Nécessite révision",
    "expired": "Expiré"
}

def get_package_info() -> Dict[str, Any]:
    """
    Retourne les informations du package
    
    Returns:
        Dict[str, Any]: Informations du package
    """
    return {
        "name": "medical_validation",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "objectives": OBJECTIVES,
        "evidence_levels": EVIDENCE_LEVELS,
        "source_types": SOURCE_TYPES,
        "validation_status": VALIDATION_STATUS
    }

def get_objectives_status() -> Dict[int, str]:
    """
    Retourne le statut des objectifs
    
    Returns:
        Dict[int, str]: Statut de chaque objectif
    """
    return {
        25: "✅ Implémenté - Processus validation par experts",
        26: "✅ Implémenté - Scoring fiabilité sources automatique",
        27: "✅ Implémenté - Système mise à jour connaissances",
        28: "✅ Implémenté - Documentation sources et preuves"
    }

def create_validation_system(config: Optional[Dict] = None) -> 'MedicalValidationSystem':
    """
    Crée le système de validation médicale
    
    Args:
        config: Configuration personnalisée
        
    Returns:
        MedicalValidationSystem: Système de validation
    """
    try:
        from .expert_validation_system import ExpertValidationSystem
        from .source_reliability_scorer import SourceReliabilityScorer
        from .knowledge_updater import KnowledgeUpdater
        from .evidence_documenter import EvidenceDocumenter
        
        # Configuration finale
        final_config = DEFAULT_CONFIG.copy()
        if config:
            final_config.update(config)
            
        # Création des composants
        expert_validator = ExpertValidationSystem(final_config["validation"])
        reliability_scorer = SourceReliabilityScorer(final_config["reliability"])
        knowledge_updater = KnowledgeUpdater(final_config["updates"])
        evidence_documenter = EvidenceDocumenter(final_config["evidence"])
        
        logger.info("Système de validation médicale créé avec succès")
        
        return MedicalValidationSystem(
            expert_validator=expert_validator,
            reliability_scorer=reliability_scorer,
            knowledge_updater=knowledge_updater,
            evidence_documenter=evidence_documenter,
            config=final_config
        )
        
    except ImportError as e:
        logger.warning(f"Composant non disponible: {e}")
        return None

def validate_config(config: Dict) -> bool:
    """
    Valide la configuration
    
    Args:
        config: Configuration à valider
        
    Returns:
        bool: True si valide
    """
    required_sections = ["validation", "reliability", "updates", "evidence"]
    return all(section in config for section in required_sections)

def get_default_config() -> Dict:
    """
    Retourne la configuration par défaut
    
    Returns:
        Dict: Configuration par défaut
    """
    return DEFAULT_CONFIG.copy()

# Classe principale du système
class MedicalValidationSystem:
    """
    Système principal de validation médicale
    """
    
    def __init__(self, expert_validator, reliability_scorer, 
                 knowledge_updater, evidence_documenter, config):
        self.expert_validator = expert_validator
        self.reliability_scorer = reliability_scorer
        self.knowledge_updater = knowledge_updater
        self.evidence_documenter = evidence_documenter
        self.config = config
        
    def validate_content(self, content: str, source_info: Dict) -> Dict:
        """
        Valide un contenu médical complet
        
        Args:
            content: Contenu à valider
            source_info: Informations sur la source
            
        Returns:
            Dict: Résultat de validation
        """
        # Validation par experts
        expert_result = self.expert_validator.validate(content)
        
        # Scoring de fiabilité
        reliability_score = self.reliability_scorer.score_source(source_info)
        
        # Documentation des preuves
        evidence_doc = self.evidence_documenter.document(content, source_info)
        
        return {
            "expert_validation": expert_result,
            "reliability_score": reliability_score,
            "evidence_documentation": evidence_doc,
            "overall_status": self._determine_status(expert_result, reliability_score)
        }
        
    def _determine_status(self, expert_result: Dict, reliability_score: float) -> str:
        """
        Détermine le statut global de validation
        """
        if (expert_result.get("consensus", 0) >= self.config["validation"]["min_expert_consensus"] and
            reliability_score >= self.config["reliability"]["min_source_score"]):
            return "approved"
        elif expert_result.get("consensus", 0) < 0.5 or reliability_score < 0.3:
            return "rejected"
        else:
            return "needs_revision"

# Initialisation du package
logger.info(f"Package medical_validation v{__version__} initialisé")
logger.info(f"Objectifs couverts: {list(OBJECTIVES.keys())}")

# Vérification des composants disponibles
try:
    from .expert_validation_system import ExpertValidationSystem
    logger.info("✓ ExpertValidationSystem disponible")
except ImportError:
    logger.warning("⚠ ExpertValidationSystem non disponible")

try:
    from .source_reliability_scorer import SourceReliabilityScorer
    logger.info("✓ SourceReliabilityScorer disponible")
except ImportError:
    logger.warning("⚠ SourceReliabilityScorer non disponible")

try:
    from .knowledge_updater import KnowledgeUpdater
    logger.info("✓ KnowledgeUpdater disponible")
except ImportError:
    logger.warning("⚠ KnowledgeUpdater non disponible")

try:
    from .evidence_documenter import EvidenceDocumenter
    logger.info("✓ EvidenceDocumenter disponible")
except ImportError:
    logger.warning("⚠ EvidenceDocumenter non disponible")

__all__ = [
    "MedicalValidationSystem",
    "get_package_info",
    "get_objectives_status",
    "create_validation_system",
    "validate_config",
    "get_default_config",
    "OBJECTIVES",
    "EVIDENCE_LEVELS",
    "SOURCE_TYPES",
    "VALIDATION_STATUS",
    "DEFAULT_CONFIG"
]