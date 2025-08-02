"""Module RAG & Connaissances Médicales pour l'Hôpital Général de Douala

Ce module fournit un système de Retrieval-Augmented Generation (RAG)
spécialisé pour les connaissances médicales.

Composants principaux:
- Base de données vectorielle Chroma pour les embeddings
- PostgreSQL pour les métadonnées médicales
- LangChain pour le framework RAG
- Sentence-Transformers pour l'encodage de texte
"""

__version__ = "1.0.0"
__author__ = "Équipe Hackathon Hôpital Général Douala"
__description__ = "Système RAG pour connaissances médicales"

# Imports principaux
from .config.settings import settings
from .database.database import db_manager
from .embeddings.chroma_manager import chroma_manager
from .embeddings.embedding_manager import embedding_manager
from .rag.langchain_rag import medical_rag

__all__ = [
    "settings",
    "db_manager",
    "chroma_manager",
    "embedding_manager",
    "medical_rag"
]