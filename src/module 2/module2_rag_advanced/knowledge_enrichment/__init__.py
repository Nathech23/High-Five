#!/usr/bin/env python3
"""
Package d'Enrichissement de la Base de Connaissances

Objectifs 1-10: Enrichissement base de connaissances
1. Intégrer 500+ articles médicaux validés
2. Créer sections par spécialités médicales
3. Ajouter contenu en français et langues camerounaises
4. Structurer informations par niveau de complexité
5. Créer glossaire médical multilingue
6. Intégrer protocoles de soins DGH
7. Ajouter FAQ courantes patients
8. Valider exactitude avec sources officielles
9. Créer liens entre concepts médicaux
10. Organiser par parcours de soins patient

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Équipe Hackathon Hôpital Général de Douala"
__description__ = "Enrichissement avancé de la base de connaissances médicales"

# Imports des composants
try:
    from .medical_knowledge_enricher import MedicalKnowledgeEnricher
    from .specialty_organizer import SpecialtyOrganizer
    from .multilingual_glossary import MultilingualGlossary
    from .protocol_integrator import ProtocolIntegrator
    from .faq_manager import FAQManager
    from .concept_linker import ConceptLinker
    from .care_pathway_organizer import CarePathwayOrganizer
    from .complexity_structurer import ComplexityStructurer
except ImportError:
    # Imports optionnels
    pass

# Exports
__all__ = [
    "MedicalKnowledgeEnricher",
    "SpecialtyOrganizer",
    "MultilingualGlossary", 
    "ProtocolIntegrator",
    "FAQManager",
    "ConceptLinker",
    "CarePathwayOrganizer",
    "ComplexityStructurer",
    "get_enrichment_info"
]

def get_enrichment_info():
    """
    Retourne les informations sur l'enrichissement
    
    Returns:
        dict: Informations sur les composants d'enrichissement
    """
    return {
        "package": "knowledge_enrichment",
        "version": __version__,
        "objectives_covered": list(range(1, 11)),
        "components": {
            "medical_knowledge_enricher": "Intégration 500+ articles médicaux",
            "specialty_organizer": "Organisation par spécialités médicales",
            "multilingual_glossary": "Glossaire médical multilingue",
            "protocol_integrator": "Protocoles de soins DGH",
            "faq_manager": "FAQ courantes patients",
            "concept_linker": "Liens entre concepts médicaux",
            "care_pathway_organizer": "Parcours de soins patient",
            "complexity_structurer": "Niveaux de complexité"
        },
        "languages": ["français", "fulfulde", "ewondo", "duala"],
        "specialties": [
            "cardiologie", "endocrinologie", "infectiologie",
            "pneumologie", "neurologie", "pédiatrie"
        ]
    }

print(f"📚 Knowledge Enrichment v{__version__} - Objectifs 1-10")