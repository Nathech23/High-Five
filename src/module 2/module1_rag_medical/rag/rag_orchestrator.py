#!/usr/bin/env python3
"""
Orchestrateur Principal du Système RAG Médical

Ce module coordonne tous les composants du système RAG médical :
- Chunking intelligent des documents
- Pipeline d'embeddings
- Recherche sémantique
- Récupération de contexte
- Fusion des résultats
- Évaluation et optimisation
"""

import logging
import time
import json
import asyncio
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import numpy as np
from datetime import datetime
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle

# Imports des composants RAG
try:
    from .intelligent_chunker import MedicalDocumentChunker, IntelligentChunk
    from .embedding_pipeline import MedicalEmbeddingPipeline, ProcessedEmbedding
    from .semantic_search import MedicalSemanticSearch, SearchResult, SearchQuery
    from .context_retrieval import MedicalContextRetriever, FusedContext
    from .rag_evaluation import RAGEvaluationSuite, EvaluationResult
    from .chunk_optimizer import MedicalChunkOptimizer, OptimizationResult
except ImportError:
    # Fallback pour les imports directs
    from intelligent_chunker import MedicalDocumentChunker, IntelligentChunk
    from embedding_pipeline import MedicalEmbeddingPipeline, ProcessedEmbedding
    from semantic_search import MedicalSemanticSearch, SearchResult, SearchQuery
    from context_retrieval import MedicalContextRetriever, FusedContext
    from rag_evaluation import RAGEvaluationSuite, EvaluationResult
    from chunk_optimizer import MedicalChunkOptimizer, OptimizationResult

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RAGConfiguration:
    """Configuration complète du système RAG"""
    # Configuration du chunking
    chunk_size: int = 800
    chunk_overlap: int = 160
    preserve_sentences: bool = True
    medical_boundary_aware: bool = True
    
    # Configuration des embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    batch_size: int = 32
    normalize_embeddings: bool = True
    
    # Configuration de la recherche
    search_strategy: str = "hybrid"  # semantic, keyword, hybrid, medical_entity
    max_results: int = 10
    similarity_threshold: float = 0.7
    diversity_threshold: float = 0.8
    
    # Configuration de la récupération de contexte
    fusion_strategy: str = "medical_priority"  # concatenation, weighted_merge, hierarchical, semantic_clustering, medical_priority
    max_context_chunks: int = 8
    context_window_size: int = 4000
    
    # Configuration de l'évaluation
    enable_evaluation: bool = True
    evaluation_queries_path: Optional[str] = None
    optimization_enabled: bool = False
    
    # Chemins et stockage
    data_directory: str = "./rag_data"
    cache_directory: str = "./rag_cache"
    models_directory: str = "./rag_models"
    
    # Performance
    use_gpu: bool = False
    max_workers: int = 4
    enable_caching: bool = True
    
    # Langue et domaine
    language: str = "fr"
    medical_domain: str = "general"

@dataclass
class RAGResponse:
    """Réponse complète du système RAG"""
    query: str
    retrieved_chunks: List[IntelligentChunk]
    fused_context: FusedContext
    search_results: List[SearchResult]
    confidence_score: float
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RAGMetrics:
    """Métriques de performance du système RAG"""
    total_queries: int = 0
    avg_processing_time: float = 0.0
    avg_confidence_score: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    last_optimization: Optional[datetime] = None
    performance_history: List[Dict[str, Any]] = field(default_factory=list)

class MedicalRAGOrchestrator:
    """
    Orchestrateur principal du système RAG médical
    
    Fonctionnalités:
    - Coordination de tous les composants RAG
    - Pipeline de traitement complet
    - Optimisation automatique des paramètres
    - Évaluation continue de la performance
    - Gestion du cache et de la persistance
    - Interface unifiée pour les requêtes
    """
    
    def __init__(self, config: RAGConfiguration = None):
        """
        Initialise l'orchestrateur RAG
        
        Args:
            config: Configuration du système RAG
        """
        self.config = config or RAGConfiguration()
        
        # Initialisation des composants
        self.chunker: Optional[MedicalDocumentChunker] = None
        self.embedding_pipeline: Optional[MedicalEmbeddingPipeline] = None
        self.semantic_search: Optional[MedicalSemanticSearch] = None
        self.context_retriever: Optional[MedicalContextRetriever] = None
        self.evaluation_suite: Optional[RAGEvaluationSuite] = None
        self.chunk_optimizer: Optional[MedicalChunkOptimizer] = None
        
        # État du système
        self.is_initialized = False
        self.indexed_documents: List[Dict[str, Any]] = []
        self.metrics = RAGMetrics()
        
        # Cache et persistance
        self.cache = {}
        self.cache_directory = Path(self.config.cache_directory)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        
        # Executor pour le traitement parallèle
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        logger.info("Orchestrateur RAG médical initialisé")
    
    async def initialize(self) -> None:
        """
        Initialise tous les composants du système RAG
        """
        if self.is_initialized:
            logger.info("Système RAG déjà initialisé")
            return
        
        logger.info("Initialisation du système RAG médical...")
        start_time = time.time()
        
        try:
            # 1. Initialisation du chunker
            logger.info("Initialisation du chunker intelligent...")
            self.chunker = MedicalDocumentChunker(
                chunk_size=self.config.chunk_size,
                overlap_size=self.config.chunk_overlap,
                preserve_sentences=self.config.preserve_sentences,
                medical_boundary_aware=self.config.medical_boundary_aware,
                language=self.config.language
            )
            
            # 2. Initialisation du pipeline d'embeddings
            logger.info("Initialisation du pipeline d'embeddings...")
            self.embedding_pipeline = MedicalEmbeddingPipeline(
                model_name=self.config.embedding_model,
                batch_size=self.config.batch_size,
                normalize=self.config.normalize_embeddings,
                use_gpu=self.config.use_gpu,
                cache_dir=str(self.cache_directory / "embeddings")
            )
            
            # 3. Initialisation de la recherche sémantique
            logger.info("Initialisation de la recherche sémantique...")
            self.semantic_search = MedicalSemanticSearch(
                embedding_model=self.embedding_pipeline.model,
                language=self.config.language
            )
            
            # 4. Initialisation de la récupération de contexte
            logger.info("Initialisation de la récupération de contexte...")
            self.context_retriever = MedicalContextRetriever(
                semantic_search=self.semantic_search,
                language=self.config.language
            )
            
            # 5. Initialisation de l'évaluation (si activée)
            if self.config.enable_evaluation:
                logger.info("Initialisation de la suite d'évaluation...")
                self.evaluation_suite = RAGEvaluationSuite(
                    rag_system=self,
                    evaluation_data_path=self.config.evaluation_queries_path,
                    output_dir=str(self.cache_directory / "evaluation")
                )
            
            # 6. Initialisation de l'optimiseur (si activé)
            if self.config.optimization_enabled:
                logger.info("Initialisation de l'optimiseur de chunks...")
                self.chunk_optimizer = MedicalChunkOptimizer(
                    language=self.config.language
                )
            
            # Chargement du cache existant
            await self._load_cache()
            
            self.is_initialized = True
            initialization_time = time.time() - start_time
            
            logger.info(f"Système RAG initialisé avec succès en {initialization_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du système RAG: {e}")
            raise
    
    async def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Indexe une collection de documents médicaux
        
        Args:
            documents: Liste de documents avec 'id', 'content', et métadonnées
        """
        if not self.is_initialized:
            await self.initialize()
        
        logger.info(f"Indexation de {len(documents)} documents...")
        start_time = time.time()
        
        try:
            # 1. Chunking des documents
            logger.info("Chunking des documents...")
            all_chunks = []
            
            for doc in documents:
                doc_chunks = await self._process_document_chunks(doc)
                all_chunks.extend(doc_chunks)
            
            logger.info(f"Généré {len(all_chunks)} chunks")
            
            # 2. Génération des embeddings
            logger.info("Génération des embeddings...")
            chunk_texts = [chunk.content for chunk in all_chunks]
            embeddings = await self._generate_embeddings_batch(chunk_texts)
            
            # 3. Indexation dans le système de recherche
            logger.info("Indexation dans le système de recherche...")
            indexed_docs = []
            
            for chunk, embedding in zip(all_chunks, embeddings):
                indexed_doc = {
                    'id': chunk.chunk_id,
                    'content': chunk.content,
                    'embedding': embedding,
                    'metadata': chunk.metadata,
                    'source_document': chunk.source_document
                }
                indexed_docs.append(indexed_doc)
            
            # Ajout à l'index de recherche
            await self._add_to_search_index(indexed_docs)
            
            # Mise à jour de la liste des documents indexés
            self.indexed_documents.extend(indexed_docs)
            
            # Sauvegarde du cache
            await self._save_cache()
            
            indexing_time = time.time() - start_time
            logger.info(f"Indexation terminée en {indexing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation: {e}")
            raise
    
    async def query(self, 
                   query_text: str,
                   max_results: Optional[int] = None,
                   search_strategy: Optional[str] = None,
                   fusion_strategy: Optional[str] = None) -> RAGResponse:
        """
        Exécute une requête complète sur le système RAG
        
        Args:
            query_text: Texte de la requête
            max_results: Nombre maximum de résultats
            search_strategy: Stratégie de recherche à utiliser
            fusion_strategy: Stratégie de fusion à utiliser
            
        Returns:
            Réponse complète du système RAG
        """
        if not self.is_initialized:
            await self.initialize()
        
        if not self.indexed_documents:
            raise ValueError("Aucun document indexé. Veuillez d'abord indexer des documents.")
        
        logger.info(f"Exécution de la requête: '{query_text[:100]}...'")
        start_time = time.time()
        
        try:
            # Vérification du cache
            cache_key = self._generate_cache_key(query_text, max_results, search_strategy, fusion_strategy)
            
            if self.config.enable_caching and cache_key in self.cache:
                logger.info("Résultat trouvé dans le cache")
                cached_response = self.cache[cache_key]
                self._update_metrics(cached_response, from_cache=True)
                return cached_response
            
            # Configuration des paramètres
            max_results = max_results or self.config.max_results
            search_strategy = search_strategy or self.config.search_strategy
            fusion_strategy = fusion_strategy or self.config.fusion_strategy
            
            # 1. Recherche sémantique
            logger.debug("Exécution de la recherche sémantique...")
            search_query = SearchQuery(
                text=query_text,
                max_results=max_results,
                search_type=search_strategy,
                similarity_threshold=self.config.similarity_threshold,
                diversity_threshold=self.config.diversity_threshold
            )
            
            search_results = await self._execute_search(search_query)
            
            # 2. Récupération des chunks correspondants
            logger.debug("Récupération des chunks...")
            retrieved_chunks = await self._retrieve_chunks_from_results(search_results)
            
            # 3. Fusion du contexte
            logger.debug("Fusion du contexte...")
            fused_context = await self._fuse_context(
                query_text, retrieved_chunks, fusion_strategy
            )
            
            # 4. Calcul du score de confiance
            confidence_score = self._calculate_confidence_score(
                search_results, fused_context
            )
            
            processing_time = time.time() - start_time
            
            # Construction de la réponse
            response = RAGResponse(
                query=query_text,
                retrieved_chunks=retrieved_chunks,
                fused_context=fused_context,
                search_results=search_results,
                confidence_score=confidence_score,
                processing_time=processing_time,
                metadata={
                    'search_strategy': search_strategy,
                    'fusion_strategy': fusion_strategy,
                    'num_indexed_docs': len(self.indexed_documents),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Mise en cache
            if self.config.enable_caching:
                self.cache[cache_key] = response
            
            # Mise à jour des métriques
            self._update_metrics(response)
            
            logger.info(f"Requête traitée en {processing_time:.2f}s (confiance: {confidence_score:.3f})")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête: {e}")
            self.metrics.error_rate = (self.metrics.error_rate * self.metrics.total_queries + 1) / (self.metrics.total_queries + 1)
            raise
    
    async def _process_document_chunks(self, document: Dict[str, Any]) -> List[IntelligentChunk]:
        """Traite un document et génère ses chunks"""
        content = document.get('content', '')
        doc_id = document.get('id', 'unknown')
        
        if not content:
            return []
        
        # Utilisation du chunker intelligent
        chunks = self.chunker.chunk_document(
            text=content,
            document_id=doc_id,
            metadata=document.get('metadata', {})
        )
        
        return chunks
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Génère les embeddings pour un batch de textes"""
        if not texts:
            return []
        
        # Traitement par batch pour optimiser la performance
        embeddings = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embedding_pipeline.process_texts(batch_texts)
            
            for embedding_result in batch_embeddings:
                embeddings.append(embedding_result.embedding)
        
        return embeddings
    
    async def _add_to_search_index(self, indexed_docs: List[Dict[str, Any]]) -> None:
        """Ajoute les documents à l'index de recherche"""
        # Conversion au format attendu par le système de recherche
        search_docs = []
        
        for doc in indexed_docs:
            search_doc = {
                'id': doc['id'],
                'content': doc['content'],
                'embedding': doc['embedding'],
                'metadata': doc['metadata']
            }
            search_docs.append(search_doc)
        
        # Indexation dans le système de recherche sémantique
        self.semantic_search.index_documents(search_docs)
    
    async def _execute_search(self, search_query: SearchQuery) -> List[SearchResult]:
        """Exécute une recherche sémantique"""
        return self.semantic_search.search(
            query=search_query.text,
            search_type=search_query.search_type,
            max_results=search_query.max_results,
            similarity_threshold=search_query.similarity_threshold,
            filters=search_query.filters
        )
    
    async def _retrieve_chunks_from_results(self, search_results: List[SearchResult]) -> List[IntelligentChunk]:
        """Récupère les chunks correspondant aux résultats de recherche"""
        chunks = []
        
        for result in search_results:
            # Recherche du chunk dans les documents indexés
            for doc in self.indexed_documents:
                if doc['id'] == result.document_id:
                    # Reconstruction du chunk
                    chunk = IntelligentChunk(
                        chunk_id=doc['id'],
                        content=doc['content'],
                        start_char=0,  # À améliorer avec les vraies positions
                        end_char=len(doc['content']),
                        source_document=doc.get('source_document', 'unknown'),
                        metadata=doc['metadata']
                    )
                    chunks.append(chunk)
                    break
        
        return chunks
    
    async def _fuse_context(self, 
                          query: str, 
                          chunks: List[IntelligentChunk], 
                          fusion_strategy: str) -> FusedContext:
        """Fusionne le contexte des chunks récupérés"""
        # Conversion des chunks au format attendu par le context retriever
        context_chunks = []
        
        for chunk in chunks:
            context_chunk = {
                'id': chunk.chunk_id,
                'content': chunk.content,
                'metadata': chunk.metadata,
                'source': chunk.source_document
            }
            context_chunks.append(context_chunk)
        
        # Utilisation du context retriever pour la fusion
        retrieval_query = {
            'text': query,
            'max_chunks': self.config.max_context_chunks,
            'fusion_strategy': fusion_strategy,
            'context_window_size': self.config.context_window_size
        }
        
        fused_context = self.context_retriever.retrieve_and_fuse_context(
            query=retrieval_query,
            available_chunks=context_chunks
        )
        
        return fused_context
    
    def _calculate_confidence_score(self, 
                                  search_results: List[SearchResult], 
                                  fused_context: FusedContext) -> float:
        """Calcule un score de confiance pour la réponse"""
        if not search_results:
            return 0.0
        
        factors = []
        
        # Facteur 1: Score de similarité moyen des résultats
        avg_similarity = np.mean([result.score for result in search_results])
        factors.append(avg_similarity)
        
        # Facteur 2: Nombre de résultats pertinents
        num_results = len(search_results)
        result_factor = min(1.0, num_results / 5.0)  # Optimal autour de 5 résultats
        factors.append(result_factor)
        
        # Facteur 3: Qualité du contexte fusionné
        if hasattr(fused_context, 'quality_score'):
            factors.append(fused_context.quality_score)
        else:
            factors.append(0.8)  # Score par défaut
        
        # Facteur 4: Diversité des sources
        unique_sources = len(set(result.document_id for result in search_results))
        diversity_factor = min(1.0, unique_sources / 3.0)
        factors.append(diversity_factor)
        
        return np.mean(factors)
    
    def _generate_cache_key(self, 
                          query: str, 
                          max_results: Optional[int], 
                          search_strategy: Optional[str], 
                          fusion_strategy: Optional[str]) -> str:
        """Génère une clé de cache pour une requête"""
        key_data = {
            'query': query,
            'max_results': max_results,
            'search_strategy': search_strategy,
            'fusion_strategy': fusion_strategy,
            'config_hash': hash(str(asdict(self.config)))
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _update_metrics(self, response: RAGResponse, from_cache: bool = False) -> None:
        """Met à jour les métriques de performance"""
        self.metrics.total_queries += 1
        
        # Temps de traitement moyen
        total_time = (self.metrics.avg_processing_time * (self.metrics.total_queries - 1) + 
                     response.processing_time)
        self.metrics.avg_processing_time = total_time / self.metrics.total_queries
        
        # Score de confiance moyen
        total_confidence = (self.metrics.avg_confidence_score * (self.metrics.total_queries - 1) + 
                           response.confidence_score)
        self.metrics.avg_confidence_score = total_confidence / self.metrics.total_queries
        
        # Taux de cache hit
        if from_cache:
            cache_hits = self.metrics.cache_hit_rate * (self.metrics.total_queries - 1) + 1
            self.metrics.cache_hit_rate = cache_hits / self.metrics.total_queries
        else:
            self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * 
                                         (self.metrics.total_queries - 1)) / self.metrics.total_queries
        
        # Historique de performance
        self.metrics.performance_history.append({
            'timestamp': datetime.now().isoformat(),
            'processing_time': response.processing_time,
            'confidence_score': response.confidence_score,
            'from_cache': from_cache
        })
        
        # Limiter l'historique
        if len(self.metrics.performance_history) > 1000:
            self.metrics.performance_history = self.metrics.performance_history[-1000:]
    
    async def _load_cache(self) -> None:
        """Charge le cache depuis le disque"""
        cache_file = self.cache_directory / "rag_cache.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
                logger.info(f"Cache chargé: {len(self.cache)} entrées")
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du cache: {e}")
                self.cache = {}
    
    async def _save_cache(self) -> None:
        """Sauvegarde le cache sur le disque"""
        if not self.config.enable_caching:
            return
        
        cache_file = self.cache_directory / "rag_cache.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.debug(f"Cache sauvegardé: {len(self.cache)} entrées")
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du cache: {e}")
    
    async def optimize_system(self, 
                            test_documents: List[Dict[str, Any]] = None,
                            test_queries: List[str] = None) -> Dict[str, Any]:
        """
        Optimise automatiquement les paramètres du système RAG
        
        Args:
            test_documents: Documents de test pour l'optimisation
            test_queries: Requêtes de test pour l'évaluation
            
        Returns:
            Résultats de l'optimisation
        """
        if not self.config.optimization_enabled or not self.chunk_optimizer:
            logger.warning("Optimisation non activée")
            return {}
        
        logger.info("Début de l'optimisation du système RAG...")
        start_time = time.time()
        
        try:
            # Utilisation des documents indexés si aucun document de test fourni
            if not test_documents and self.indexed_documents:
                test_documents = [
                    {
                        'id': doc['id'],
                        'content': doc['content'],
                        'metadata': doc['metadata']
                    }
                    for doc in self.indexed_documents[:50]  # Limiter pour l'optimisation
                ]
            
            if not test_documents:
                raise ValueError("Aucun document disponible pour l'optimisation")
            
            # Optimisation des chunks
            logger.info("Optimisation de la configuration des chunks...")
            chunk_optimization = self.chunk_optimizer.optimize_chunk_configuration(
                documents=[doc['content'] for doc in test_documents],
                test_queries=test_queries
            )
            
            # Mise à jour de la configuration
            self.config.chunk_size = chunk_optimization.optimal_chunk_size
            self.config.chunk_overlap = chunk_optimization.optimal_overlap_size
            
            # Réinitialisation du chunker avec les nouveaux paramètres
            self.chunker = MedicalDocumentChunker(
                chunk_size=self.config.chunk_size,
                overlap_size=self.config.chunk_overlap,
                preserve_sentences=self.config.preserve_sentences,
                medical_boundary_aware=self.config.medical_boundary_aware,
                language=self.config.language
            )
            
            # Évaluation du système optimisé
            evaluation_results = {}
            if self.evaluation_suite and test_queries:
                logger.info("Évaluation du système optimisé...")
                evaluation_results = self.evaluation_suite.evaluate_rag_system(
                    max_queries=min(20, len(test_queries))
                )
            
            optimization_time = time.time() - start_time
            self.metrics.last_optimization = datetime.now()
            
            optimization_summary = {
                'chunk_optimization': asdict(chunk_optimization),
                'evaluation_results': evaluation_results,
                'optimization_time': optimization_time,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Optimisation terminée en {optimization_time:.2f}s")
            return optimization_summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {e}")
            raise
    
    async def evaluate_performance(self, 
                                 test_queries: List[str] = None,
                                 max_queries: int = 50) -> Dict[str, Any]:
        """
        Évalue la performance du système RAG
        
        Args:
            test_queries: Requêtes de test spécifiques
            max_queries: Nombre maximum de requêtes à évaluer
            
        Returns:
            Résultats de l'évaluation
        """
        if not self.evaluation_suite:
            logger.warning("Suite d'évaluation non disponible")
            return {}
        
        logger.info("Évaluation de la performance du système RAG...")
        
        try:
            # Chargement des requêtes d'évaluation
            if not test_queries:
                self.evaluation_suite.load_evaluation_queries()
            
            # Exécution de l'évaluation
            evaluation_results = self.evaluation_suite.evaluate_rag_system(
                max_queries=max_queries
            )
            
            # Génération du rapport
            report_path = self.evaluation_suite.generate_evaluation_report()
            
            evaluation_summary = {
                'metrics': evaluation_results,
                'report_path': report_path,
                'system_metrics': asdict(self.metrics),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("Évaluation terminée avec succès")
            return evaluation_summary
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation: {e}")
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retourne le statut actuel du système RAG"""
        return {
            'is_initialized': self.is_initialized,
            'indexed_documents_count': len(self.indexed_documents),
            'configuration': asdict(self.config),
            'metrics': asdict(self.metrics),
            'cache_size': len(self.cache),
            'components_status': {
                'chunker': self.chunker is not None,
                'embedding_pipeline': self.embedding_pipeline is not None,
                'semantic_search': self.semantic_search is not None,
                'context_retriever': self.context_retriever is not None,
                'evaluation_suite': self.evaluation_suite is not None,
                'chunk_optimizer': self.chunk_optimizer is not None
            }
        }
    
    async def cleanup(self) -> None:
        """Nettoie les ressources du système"""
        logger.info("Nettoyage du système RAG...")
        
        # Sauvegarde finale du cache
        await self._save_cache()
        
        # Fermeture de l'executor
        self.executor.shutdown(wait=True)
        
        # Nettoyage des composants
        if self.embedding_pipeline:
            # Nettoyage du pipeline d'embeddings si nécessaire
            pass
        
        logger.info("Nettoyage terminé")

def main():
    """Fonction de test de l'orchestrateur RAG"""
    import asyncio
    
    async def test_orchestrator():
        # Configuration de test
        config = RAGConfiguration(
            chunk_size=600,
            chunk_overlap=120,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            search_strategy="hybrid",
            fusion_strategy="medical_priority",
            enable_evaluation=True,
            optimization_enabled=True,
            max_workers=2
        )
        
        # Initialisation de l'orchestrateur
        orchestrator = MedicalRAGOrchestrator(config)
        
        try:
            print("\n=== ORCHESTRATEUR RAG MÉDICAL ===")
            print("Initialisation...")
            await orchestrator.initialize()
            
            # Documents de test
            test_documents = [
                {
                    'id': 'doc_001',
                    'content': """
                    Le diabète de type 2 est une maladie chronique caractérisée par une résistance à l'insuline.
                    Les symptômes incluent une soif excessive, une miction fréquente, et une fatigue.
                    Le diagnostic se fait par mesure de la glycémie à jeun (>126 mg/dL) ou HbA1c (>6.5%).
                    Le traitement comprend des modifications du mode de vie et des médicaments comme la metformine.
                    """,
                    'metadata': {'specialty': 'endocrinology', 'language': 'fr'}
                },
                {
                    'id': 'doc_002',
                    'content': """
                    L'hypertension artérielle est définie par une pression systolique ≥140 mmHg ou diastolique ≥90 mmHg.
                    Les facteurs de risque incluent l'âge, l'obésité, le tabagisme, et les antécédents familiaux.
                    Le traitement de première ligne inclut les diurétiques thiazidiques et les IEC.
                    Le suivi implique des contrôles réguliers de la tension et des examens biologiques.
                    """,
                    'metadata': {'specialty': 'cardiology', 'language': 'fr'}
                }
            ]
            
            # Indexation des documents
            print("\nIndexation des documents...")
            await orchestrator.index_documents(test_documents)
            
            # Requêtes de test
            test_queries = [
                "Comment diagnostiquer le diabète ?",
                "Quel est le traitement de l'hypertension ?",
                "Quels sont les symptômes du diabète ?"
            ]
            
            # Test des requêtes
            print("\n=== TEST DES REQUÊTES ===")
            for query in test_queries:
                print(f"\nRequête: {query}")
                response = await orchestrator.query(query)
                
                print(f"Temps de traitement: {response.processing_time:.3f}s")
                print(f"Score de confiance: {response.confidence_score:.3f}")
                print(f"Chunks récupérés: {len(response.retrieved_chunks)}")
                print(f"Résultats de recherche: {len(response.search_results)}")
            
            # Statut du système
            print("\n=== STATUT DU SYSTÈME ===")
            status = orchestrator.get_system_status()
            print(f"Documents indexés: {status['indexed_documents_count']}")
            print(f"Requêtes traitées: {status['metrics']['total_queries']}")
            print(f"Temps moyen: {status['metrics']['avg_processing_time']:.3f}s")
            print(f"Confiance moyenne: {status['metrics']['avg_confidence_score']:.3f}")
            print(f"Taux de cache: {status['metrics']['cache_hit_rate']:.3f}")
            
            # Test d'optimisation
            print("\n=== TEST D'OPTIMISATION ===")
            optimization_results = await orchestrator.optimize_system(
                test_documents=test_documents,
                test_queries=test_queries
            )
            
            if optimization_results:
                chunk_opt = optimization_results['chunk_optimization']
                print(f"Taille optimale: {chunk_opt['optimal_chunk_size']}")
                print(f"Overlap optimal: {chunk_opt['optimal_overlap_size']}")
                print(f"Score de qualité: {chunk_opt['quality_score']:.3f}")
            
            # Test d'évaluation
            print("\n=== TEST D'ÉVALUATION ===")
            evaluation_results = await orchestrator.evaluate_performance(
                test_queries=test_queries,
                max_queries=3
            )
            
            if evaluation_results:
                metrics = evaluation_results['metrics']
                print(f"Précision@5: {metrics.get('avg_precision_at_5', 0):.3f}")
                print(f"Rappel@5: {metrics.get('avg_recall_at_5', 0):.3f}")
                print(f"MAP: {metrics.get('avg_map', 0):.3f}")
            
        finally:
            # Nettoyage
            await orchestrator.cleanup()
            print("\n=== NETTOYAGE TERMINÉ ===")
    
    # Exécution du test
    asyncio.run(test_orchestrator())

if __name__ == "__main__":
    main()