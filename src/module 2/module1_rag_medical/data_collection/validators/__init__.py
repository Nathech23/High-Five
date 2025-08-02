#!/usr/bin/env python3
"""
Package des validateurs médicaux

Ce package contient les outils pour valider l'exactitude et la qualité des contenus médicaux.
"""

from .medical_validator import MedicalValidator, ValidationResult, MedicalFact

__all__ = [
    'MedicalValidator',
    'ValidationResult',
    'MedicalFact'
]