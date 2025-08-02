#!/usr/bin/env python3
"""
Package des processeurs de données médicales

Ce package contient les outils pour traiter et nettoyer les données médicales collectées.
"""

from .data_processor import MedicalDataProcessor, ProcessedDocument

__all__ = [
    'MedicalDataProcessor',
    'ProcessedDocument'
]