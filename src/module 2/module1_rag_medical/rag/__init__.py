#!/usr/bin/env python3
"""
Module RAG Médical - Système de Récupération et Génération Augmentée

Ce package implémente un système RAG complet spécialisé pour le domaine médical,
incluant le chunking intelligent, les embeddings, la recherche sémantique,
la récupération de contexte, l'évaluation et l'optimisation.
"""

__version__ = "1.0.0"
__author__ = "Équipe Hackathon Hôpital Général de Douala"
__description__ = "Système RAG médical avec chunking intelligent et recherche sémantique"

# Imports des composants principaux
try:
    from .intelligent_chunker import (
        MedicalDocumentChunker,
        IntelligentChunk,
        ChunkMetadata
    )
    from .embedding_pipeline import (
        MedicalEmbeddingPipeline,
        ProcessedEmbedding,
        EmbeddingMetadata
    )
    from .semantic_search import (
        MedicalSemanticSearch,
        SearchResult,
        SearchQuery,
        SearchType,
        RelevanceMethod
    )
    from .context_retrieval import (
        MedicalContextRetriever,
        ContextChunk,
        FusedContext,
        RetrievalQuery,
        ContextType,
        FusionStrategy
    )
    from .rag_evaluation import (
        RAGEvaluationSuite,
        EvaluationQuery,
        EvaluationResult,
        OptimizationConfig
    )
    from .chunk_optimizer import (
        MedicalChunkOptimizer,
        ChunkConfiguration,
        ChunkQualityMetrics,
        OptimizationResult
    )
    from .rag_orchestrator import (
        MedicalRAGOrchestrator,
        RAGConfiguration,
        RAGResponse,
        RAGMetrics
    )
except ImportError as e:
    import warnings
    warnings.warn(f"Certains composants RAG ne sont pas disponibles: {e}")
    # Définition des imports de base pour éviter les erreurs
    MedicalRAGOrchestrator = None
    RAGConfiguration = None

# Informations du module
__all__ = [
    # Chunking
    'MedicalDocumentChunker',
    'IntelligentChunk',
    'ChunkMetadata',
    
    # Embeddings
    'MedicalEmbeddingPipeline',
    'ProcessedEmbedding',
    'EmbeddingMetadata',
    
    # Recherche sémantique
    'MedicalSemanticSearch',
    'SearchResult',
    'SearchQuery',
    'SearchType',
    'RelevanceMethod',
    
    # Récupération de contexte
    'MedicalContextRetriever',
    'ContextChunk',
    'FusedContext',
    'RetrievalQuery',
    'ContextType',
    'FusionStrategy',
    
    # Évaluation
    'RAGEvaluationSuite',
    'EvaluationQuery',
    'EvaluationResult',
    'OptimizationConfig',
    
    # Optimisation
    'MedicalChunkOptimizer',
    'ChunkConfiguration',
    'ChunkQualityMetrics',
    'OptimizationResult',
    
    # Orchestrateur principal
    'MedicalRAGOrchestrator',
    'RAGConfiguration',
    'RAGResponse',
    'RAGMetrics',
    
    # Fonctions utilitaires
    'create_default_rag_system',
    'get_module_info',
    'get_version'
]

def get_version() -> str:
    """Retourne la version du module RAG"""
    return __version__

def get_module_info() -> dict:
    """Retourne les informations du module RAG"""
    return {
        'name': 'rag_medical',
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'components': [
            'intelligent_chunker',
            'embedding_pipeline', 
            'semantic_search',
            'context_retrieval',
            'rag_evaluation',
            'chunk_optimizer',
            'rag_orchestrator'
        ]
    }

def create_default_rag_system(language: str = "fr", 
                             medical_domain: str = "general") -> 'MedicalRAGOrchestrator':
    """
    Crée un système RAG médical avec une configuration par défaut
    
    Args:
        language: Langue des documents (fr, en)
        medical_domain: Domaine médical spécialisé
        
    Returns:
        Instance de MedicalRAGOrchestrator configurée
    """
    if MedicalRAGOrchestrator is None:
        raise ImportError("MedicalRAGOrchestrator n'est pas disponible")
    
    if RAGConfiguration is None:
        raise ImportError("RAGConfiguration n'est pas disponible")
    
    # Configuration par défaut optimisée pour le contexte médical
    config = RAGConfiguration(
        # Chunking optimisé pour les documents médicaux
        chunk_size=800,
        chunk_overlap=160,
        preserve_sentences=True,
        medical_boundary_aware=True,
        
        # Embeddings avec modèle multilingue
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=32,
        normalize_embeddings=True,
        
        # Recherche hybride pour meilleure précision
        search_strategy="hybrid",
        max_results=10,
        similarity_threshold=0.7,
        diversity_threshold=0.8,
        
        # Fusion prioritaire médicale
        fusion_strategy="medical_priority",
        max_context_chunks=8,
        context_window_size=4000,
        
        # Évaluation et optimisation activées
        enable_evaluation=True,
        optimization_enabled=True,
        
        # Configuration spécifique
        language=language,
        medical_domain=medical_domain,
        
        # Performance
        use_gpu=False,  # Compatible avec la plupart des environnements
        max_workers=4,
        enable_caching=True
    )
    
    return MedicalRAGOrchestrator(config)

# Configuration du logging pour le module
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Message d'information lors de l'import
if __name__ != "__main__":
    logger = logging.getLogger(__name__)
    logger.info(f"Module RAG Médical v{__version__} chargé avec succès")