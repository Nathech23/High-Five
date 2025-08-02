#!/usr/bin/env python3
"""
Package des collecteurs de données médicales

Ce package contient les collecteurs pour différentes sources de données médicales:
- WHO (Organisation Mondiale de la Santé)
- CDC (Centers for Disease Control)
- Autres sources médicales publiques
"""

from .who_collector import WHOCollector, MedicalDocument as WHOMedicalDocument
from .cdc_collector import CDCCollector, CDCDocument

__all__ = [
    'WHOCollector',
    'WHOMedicalDocument',
    'CDCCollector',
    'CDCDocument'
]