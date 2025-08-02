#!/usr/bin/env python3
"""
Package des traducteurs médicaux

Ce package contient les outils pour traduire les contenus médicaux vers les langues locales.
"""

from .medical_translator import MedicalTranslator, TranslationResult, MedicalTerm

__all__ = [
    'MedicalTranslator',
    'TranslationResult',
    'MedicalTerm'
]