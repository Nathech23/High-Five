#!/usr/bin/env python3
"""
Système de Récupération de Contexte Pertinent pour RAG Médical

Ce module implémente un système avancé de récupération et fusion de contexte
optimisé pour les applications médicales avec RAG (Retrieval-Augmented Generation).
"""

import logging
import time
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from collections import defaultdict, Counter
import re
import json
from datetime import datetime
from enum import Enum
import math

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextType(Enum):
    """Types de contexte pour la récupération"""
    PRIMARY = "primary"          # Contexte principal directement pertinent
    SUPPORTING = "supporting"    # Contexte de support
    BACKGROUND = "background"    # Contexte de fond
    CONTRADICTORY = "contradictory"  # Contexte contradictoire
    RELATED = "related"          # Contexte connexe

class FusionStrategy(Enum):
    """Stratégies de fusion des résultats"""
    CONCATENATION = "concatenation"  # Concaténation simple
    WEIGHTED_MERGE = "weighted_merge"  # Fusion pondérée
    HIERARCHICAL = "hierarchical"    # Fusion hiérarchique
    SEMANTIC_CLUSTERING = "semantic_clustering"  # Clustering sémantique
    MEDICAL_PRIORITY = "medical_priority"  # Priorité médicale

@dataclass
class ContextChunk:
    """Chunk de contexte avec métadonnées enrichies"""
    chunk_id: str
    content: str
    relevance_score: float
    context_type: ContextType
    source_document: str
    medical_domain: str
    confidence_score: float
    position_in_document: int
    word_count: int
    medical_entities: List[str] = field(default_factory=list)
    key_concepts: List[str] = field(default_factory=list)
    relationships: Dict[str, float] = field(default_factory=dict)
    temporal_info: Optional[str] = None
    evidence_level: str = "unknown"
    source_credibility: float = 1.0

@dataclass
class RetrievalQuery:
    """Requête de récupération de contexte"""
    text: str
    medical_specialty: Optional[str] = None
    context_types: List[ContextType] = field(default_factory=lambda: [ContextType.PRIMARY, ContextType.SUPPORTING])
    max_chunks: int = 10
    max_total_words: int = 2000
    min_relevance: float = 0.3
    diversity_threshold: float = 0.8
    temporal_preference: Optional[str] = None  # "recent", "historical", None
    evidence_level_preference: List[str] = field(default_factory=lambda: ["high", "medium", "low"])

@dataclass
class FusedContext:
    """Contexte fusionné prêt pour la génération"""
    fused_content: str
    total_chunks: int
    total_words: int
    fusion_strategy: FusionStrategy
    context_distribution: Dict[ContextType, int]
    confidence_score: float
    medical_domains: List[str]
    key_entities: List[str]
    source_documents: List[str]
    fusion_metadata: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, float] = field(default_factory=dict)

class MedicalContextRetriever:
    """
    Système de récupération de contexte pertinent pour RAG médical
    
    Fonctionnalités:
    - Récupération multi-critères de contexte
    - Classification automatique du type de contexte
    - Fusion intelligente des chunks
    - Optimisation pour la cohérence médicale
    - Gestion de la diversité et de la redondance
    """
    
    def __init__(self,
                 semantic_search_system=None,
                 medical_knowledge_base: Optional[Dict[str, Any]] = None,
                 language: str = "fr"):
        """
        Initialise le système de récupération de contexte
        
        Args:
            semantic_search_system: Système de recherche sémantique
            medical_knowledge_base: Base de connaissances médicales
            language: Langue des documents
        """
        self.search_system = semantic_search_system
        self.medical_kb = medical_knowledge_base or {}
        self.language = language
        
        # Cache des contextes récupérés
        self.context_cache = {}
        
        # Patterns médicaux pour l'analyse de contexte
        self._init_medical_patterns()
        
        # Statistiques de récupération
        self.retrieval_stats = {
            'total_retrievals': 0,
            'avg_retrieval_time': 0.0,
            'avg_chunks_retrieved': 0.0,
            'fusion_strategies_used': defaultdict(int),
            'context_types_retrieved': defaultdict(int)
        }
        
        logger.info(f"Système de récupération de contexte initialisé (langue: {language})")
    
    def _init_medical_patterns(self):
        """Initialise les patterns médicaux pour l'analyse de contexte"""
        # Patterns pour identifier les types de contexte médical
        self.context_patterns = {
            ContextType.PRIMARY: [
                re.compile(r'\b(diagnostic|traitement|symptôme|cause)\b', re.IGNORECASE),
                re.compile(r'\b(thérapie|médication|posologie)\b', re.IGNORECASE)
            ],
            ContextType.SUPPORTING: [
                re.compile(r'\b(étude|recherche|essai clinique)\b', re.IGNORECASE),
                re.compile(r'\b(statistique|prévalence|incidence)\b', re.IGNORECASE)
            ],
            ContextType.BACKGROUND: [
                re.compile(r'\b(historique|contexte|introduction)\b', re.IGNORECASE),
                re.compile(r'\b(définition|description|généralité)\b', re.IGNORECASE)
            ]
        }
        
        # Indicateurs de niveau de preuve
        self.evidence_indicators = {
            'high': ['méta-analyse', 'essai randomisé', 'étude contrôlée', 'revue systématique'],
            'medium': ['étude de cohorte', 'étude cas-témoin', 'série de cas'],
            'low': ['rapport de cas', 'opinion d\'expert', 'consensus']
        }
        
        # Relations médicales importantes
        self.medical_relationships = {
            'causal': ['cause', 'provoque', 'entraîne', 'induit'],
            'temporal': ['avant', 'après', 'pendant', 'simultané'],
            'conditional': ['si', 'lorsque', 'en cas de', 'selon'],
            'comparative': ['plus', 'moins', 'similaire', 'différent']
        }
    
    def retrieve_context(self, query: Union[str, RetrievalQuery]) -> List[ContextChunk]:
        """
        Récupère le contexte pertinent pour une requête
        
        Args:
            query: Requête de récupération (string ou RetrievalQuery)
            
        Returns:
            Liste des chunks de contexte triés par pertinence
        """
        # Conversion en RetrievalQuery si nécessaire
        if isinstance(query, str):
            query = RetrievalQuery(text=query)
        
        logger.info(f"Récupération de contexte pour: '{query.text}'")
        start_time = time.time()
        
        # Vérification du cache
        cache_key = self._generate_cache_key(query)
        if cache_key in self.context_cache:
            logger.info("Contexte récupéré depuis le cache")
            return self.context_cache[cache_key]
        
        # Récupération des chunks candidats
        candidate_chunks = self._retrieve_candidate_chunks(query)
        
        # Classification des types de contexte
        classified_chunks = self._classify_context_types(candidate_chunks, query)
        
        # Enrichissement avec métadonnées médicales
        enriched_chunks = self._enrich_medical_metadata(classified_chunks)
        
        # Calcul des relations entre chunks
        related_chunks = self._calculate_chunk_relationships(enriched_chunks)
        
        # Filtrage et sélection finale
        final_chunks = self._select_optimal_chunks(related_chunks, query)
        
        # Mise en cache
        self.context_cache[cache_key] = final_chunks
        
        # Mise à jour des statistiques
        retrieval_time = time.time() - start_time
        self._update_retrieval_stats(final_chunks, retrieval_time)
        
        logger.info(f"Contexte récupéré: {len(final_chunks)} chunks en {retrieval_time:.3f}s")
        return final_chunks
    
    def _retrieve_candidate_chunks(self, query: RetrievalQuery) -> List[ContextChunk]:
        """Récupère les chunks candidats depuis le système de recherche"""
        if not self.search_system:
            logger.warning("Système de recherche non disponible")
            return []
        
        # Configuration de la recherche étendue
        from .semantic_search import SearchQuery, SearchType
        
        search_query = SearchQuery(
            text=query.text,
            search_types=[SearchType.HYBRID, SearchType.SEMANTIC],
            max_results=query.max_chunks * 3,  # Récupérer plus pour le filtrage
            min_relevance=query.min_relevance * 0.7,  # Seuil plus bas pour la récupération
            medical_context=query.medical_specialty
        )
        
        search_results = self.search_system.search(search_query)
        
        # Conversion en ContextChunk
        candidate_chunks = []
        for result in search_results:
            chunk = ContextChunk(
                chunk_id=result.chunk_id,
                content=result.content,
                relevance_score=result.relevance_score,
                context_type=ContextType.PRIMARY,  # Sera reclassifié
                source_document=result.document_id,
                medical_domain=result.metadata.get('medical_domain', 'general'),
                confidence_score=result.relevance_score,
                position_in_document=result.metadata.get('chunk_index', 0),
                word_count=len(result.content.split()),
                source_credibility=result.metadata.get('source_credibility', 1.0)
            )
            candidate_chunks.append(chunk)
        
        return candidate_chunks
    
    def _classify_context_types(self, chunks: List[ContextChunk], query: RetrievalQuery) -> List[ContextChunk]:
        """Classifie les chunks selon leur type de contexte"""
        for chunk in chunks:
            # Analyse du contenu pour déterminer le type de contexte
            content_lower = chunk.content.lower()
            query_lower = query.text.lower()
            
            # Scores pour chaque type de contexte
            type_scores = {}
            
            for context_type, patterns in self.context_patterns.items():
                score = 0.0
                for pattern in patterns:
                    matches = len(pattern.findall(chunk.content))
                    score += matches * 0.1
                type_scores[context_type] = score
            
            # Classification basée sur la pertinence directe
            direct_relevance = self._calculate_direct_relevance(chunk.content, query.text)
            
            if direct_relevance > 0.8:
                chunk.context_type = ContextType.PRIMARY
            elif direct_relevance > 0.6:
                chunk.context_type = ContextType.SUPPORTING
            elif direct_relevance > 0.4:
                chunk.context_type = ContextType.RELATED
            else:
                # Utiliser les scores de patterns
                best_type = max(type_scores.items(), key=lambda x: x[1])[0]
                chunk.context_type = best_type if type_scores[best_type] > 0 else ContextType.BACKGROUND
            
            # Détection de contexte contradictoire
            if self._detect_contradiction(chunk.content, query.text):
                chunk.context_type = ContextType.CONTRADICTORY
        
        return chunks
    
    def _enrich_medical_metadata(self, chunks: List[ContextChunk]) -> List[ContextChunk]:
        """Enrichit les chunks avec des métadonnées médicales"""
        for chunk in chunks:
            # Extraction des entités médicales
            chunk.medical_entities = self._extract_medical_entities(chunk.content)
            
            # Extraction des concepts clés
            chunk.key_concepts = self._extract_key_concepts(chunk.content)
            
            # Détermination du niveau de preuve
            chunk.evidence_level = self._determine_evidence_level(chunk.content)
            
            # Extraction d'informations temporelles
            chunk.temporal_info = self._extract_temporal_info(chunk.content)
            
            # Ajustement du score de confiance basé sur les métadonnées
            chunk.confidence_score = self._adjust_confidence_score(chunk)
        
        return chunks
    
    def _calculate_chunk_relationships(self, chunks: List[ContextChunk]) -> List[ContextChunk]:
        """Calcule les relations entre les chunks"""
        for i, chunk in enumerate(chunks):
            relationships = {}
            
            for j, other_chunk in enumerate(chunks):
                if i != j:
                    # Similarité sémantique
                    semantic_sim = self._calculate_semantic_similarity(
                        chunk.content, other_chunk.content
                    )
                    
                    # Chevauchement d'entités médicales
                    entity_overlap = self._calculate_entity_overlap(
                        chunk.medical_entities, other_chunk.medical_entities
                    )
                    
                    # Relation temporelle
                    temporal_relation = self._detect_temporal_relation(
                        chunk.content, other_chunk.content
                    )
                    
                    # Score de relation combiné
                    relation_score = (
                        semantic_sim * 0.4 + 
                        entity_overlap * 0.4 + 
                        temporal_relation * 0.2
                    )
                    
                    if relation_score > 0.3:
                        relationships[other_chunk.chunk_id] = relation_score
            
            chunk.relationships = relationships
        
        return chunks
    
    def _select_optimal_chunks(self, chunks: List[ContextChunk], query: RetrievalQuery) -> List[ContextChunk]:
        """Sélectionne les chunks optimaux selon les critères de la requête"""
        # Filtrage par types de contexte demandés
        filtered_chunks = [
            chunk for chunk in chunks 
            if chunk.context_type in query.context_types
        ]
        
        # Filtrage par niveau de preuve
        if query.evidence_level_preference:
            evidence_filtered = []
            for level in query.evidence_level_preference:
                level_chunks = [c for c in filtered_chunks if c.evidence_level == level]
                evidence_filtered.extend(level_chunks)
            filtered_chunks = evidence_filtered or filtered_chunks
        
        # Tri par pertinence et diversité
        selected_chunks = self._select_diverse_chunks(
            filtered_chunks, query.max_chunks, query.diversity_threshold
        )
        
        # Limitation par nombre de mots total
        final_chunks = self._limit_by_word_count(selected_chunks, query.max_total_words)
        
        return final_chunks
    
    def _select_diverse_chunks(self, chunks: List[ContextChunk], max_chunks: int, diversity_threshold: float) -> List[ContextChunk]:
        """Sélectionne des chunks diversifiés pour éviter la redondance"""
        if not chunks:
            return []
        
        # Tri par score de pertinence
        sorted_chunks = sorted(chunks, key=lambda x: x.relevance_score, reverse=True)
        
        selected = [sorted_chunks[0]]  # Toujours prendre le meilleur
        
        for chunk in sorted_chunks[1:]:
            if len(selected) >= max_chunks:
                break
            
            # Vérifier la diversité avec les chunks déjà sélectionnés
            is_diverse = True
            for selected_chunk in selected:
                similarity = self._calculate_semantic_similarity(
                    chunk.content, selected_chunk.content
                )
                if similarity > diversity_threshold:
                    is_diverse = False
                    break
            
            if is_diverse:
                selected.append(chunk)
        
        return selected
    
    def _limit_by_word_count(self, chunks: List[ContextChunk], max_words: int) -> List[ContextChunk]:
        """Limite les chunks par nombre total de mots"""
        total_words = 0
        limited_chunks = []
        
        for chunk in chunks:
            if total_words + chunk.word_count <= max_words:
                limited_chunks.append(chunk)
                total_words += chunk.word_count
            else:
                # Tronquer le dernier chunk si nécessaire
                remaining_words = max_words - total_words
                if remaining_words > 50:  # Minimum viable
                    words = chunk.content.split()
                    truncated_content = ' '.join(words[:remaining_words])
                    
                    truncated_chunk = ContextChunk(
                        chunk_id=chunk.chunk_id + "_truncated",
                        content=truncated_content,
                        relevance_score=chunk.relevance_score * 0.9,  # Pénalité pour troncature
                        context_type=chunk.context_type,
                        source_document=chunk.source_document,
                        medical_domain=chunk.medical_domain,
                        confidence_score=chunk.confidence_score * 0.9,
                        position_in_document=chunk.position_in_document,
                        word_count=remaining_words,
                        medical_entities=chunk.medical_entities,
                        key_concepts=chunk.key_concepts,
                        evidence_level=chunk.evidence_level
                    )
                    
                    limited_chunks.append(truncated_chunk)
                break
        
        return limited_chunks
    
    def fuse_context(self, chunks: List[ContextChunk], strategy: FusionStrategy = FusionStrategy.MEDICAL_PRIORITY) -> FusedContext:
        """
        Fusionne les chunks de contexte selon la stratégie spécifiée
        
        Args:
            chunks: Liste des chunks à fusionner
            strategy: Stratégie de fusion
            
        Returns:
            Contexte fusionné
        """
        if not chunks:
            return FusedContext(
                fused_content="",
                total_chunks=0,
                total_words=0,
                fusion_strategy=strategy,
                context_distribution={},
                confidence_score=0.0,
                medical_domains=[],
                key_entities=[],
                source_documents=[]
            )
        
        logger.info(f"Fusion de {len(chunks)} chunks avec stratégie {strategy.value}")
        
        if strategy == FusionStrategy.CONCATENATION:
            fused_content = self._concatenate_chunks(chunks)
        elif strategy == FusionStrategy.WEIGHTED_MERGE:
            fused_content = self._weighted_merge_chunks(chunks)
        elif strategy == FusionStrategy.HIERARCHICAL:
            fused_content = self._hierarchical_merge_chunks(chunks)
        elif strategy == FusionStrategy.SEMANTIC_CLUSTERING:
            fused_content = self._semantic_cluster_merge_chunks(chunks)
        elif strategy == FusionStrategy.MEDICAL_PRIORITY:
            fused_content = self._medical_priority_merge_chunks(chunks)
        else:
            fused_content = self._concatenate_chunks(chunks)  # Fallback
        
        # Calcul des métadonnées de fusion
        context_distribution = Counter(chunk.context_type for chunk in chunks)
        total_words = sum(chunk.word_count for chunk in chunks)
        confidence_score = np.mean([chunk.confidence_score for chunk in chunks])
        
        medical_domains = list(set(chunk.medical_domain for chunk in chunks))
        key_entities = list(set(
            entity for chunk in chunks for entity in chunk.medical_entities
        ))
        source_documents = list(set(chunk.source_document for chunk in chunks))
        
        # Calcul des métriques de qualité
        quality_metrics = self._calculate_fusion_quality_metrics(chunks, fused_content)
        
        # Mise à jour des statistiques
        self.retrieval_stats['fusion_strategies_used'][strategy.value] += 1
        
        return FusedContext(
            fused_content=fused_content,
            total_chunks=len(chunks),
            total_words=total_words,
            fusion_strategy=strategy,
            context_distribution=dict(context_distribution),
            confidence_score=confidence_score,
            medical_domains=medical_domains,
            key_entities=key_entities,
            source_documents=source_documents,
            quality_metrics=quality_metrics
        )
    
    def _concatenate_chunks(self, chunks: List[ContextChunk]) -> str:
        """Concaténation simple des chunks"""
        # Tri par type de contexte et pertinence
        type_priority = {
            ContextType.PRIMARY: 0,
            ContextType.SUPPORTING: 1,
            ContextType.RELATED: 2,
            ContextType.BACKGROUND: 3,
            ContextType.CONTRADICTORY: 4
        }
        
        sorted_chunks = sorted(
            chunks,
            key=lambda x: (type_priority.get(x.context_type, 5), -x.relevance_score)
        )
        
        content_parts = []
        for chunk in sorted_chunks:
            content_parts.append(f"[{chunk.context_type.value.upper()}] {chunk.content}")
        
        return "\n\n".join(content_parts)
    
    def _weighted_merge_chunks(self, chunks: List[ContextChunk]) -> str:
        """Fusion pondérée basée sur les scores de pertinence"""
        # Groupement par type de contexte
        grouped_chunks = defaultdict(list)
        for chunk in chunks:
            grouped_chunks[chunk.context_type].append(chunk)
        
        content_parts = []
        
        # Traitement par ordre de priorité
        for context_type in [ContextType.PRIMARY, ContextType.SUPPORTING, ContextType.RELATED, ContextType.BACKGROUND]:
            if context_type in grouped_chunks:
                type_chunks = sorted(
                    grouped_chunks[context_type],
                    key=lambda x: x.relevance_score,
                    reverse=True
                )
                
                section_content = []
                for chunk in type_chunks:
                    weight_indicator = "★" * min(3, int(chunk.relevance_score * 3) + 1)
                    section_content.append(f"{weight_indicator} {chunk.content}")
                
                if section_content:
                    content_parts.append(
                        f"=== {context_type.value.upper()} ===\n" + "\n\n".join(section_content)
                    )
        
        return "\n\n".join(content_parts)
    
    def _hierarchical_merge_chunks(self, chunks: List[ContextChunk]) -> str:
        """Fusion hiérarchique basée sur les relations entre chunks"""
        # Construction d'un graphe de relations
        chunk_graph = {}
        for chunk in chunks:
            chunk_graph[chunk.chunk_id] = {
                'chunk': chunk,
                'children': [],
                'parents': []
            }
        
        # Ajout des relations
        for chunk in chunks:
            for related_id, relation_score in chunk.relationships.items():
                if related_id in chunk_graph and relation_score > 0.5:
                    chunk_graph[chunk.chunk_id]['children'].append(related_id)
                    chunk_graph[related_id]['parents'].append(chunk.chunk_id)
        
        # Identification des chunks racines (peu de parents)
        root_chunks = [
            chunk_id for chunk_id, data in chunk_graph.items()
            if len(data['parents']) <= 1
        ]
        
        # Construction hiérarchique
        content_parts = []
        visited = set()
        
        def build_hierarchy(chunk_id, level=0):
            if chunk_id in visited:
                return
            visited.add(chunk_id)
            
            chunk = chunk_graph[chunk_id]['chunk']
            indent = "  " * level
            content_parts.append(f"{indent}• {chunk.content}")
            
            # Traitement des enfants
            for child_id in chunk_graph[chunk_id]['children']:
                if child_id not in visited:
                    build_hierarchy(child_id, level + 1)
        
        # Construction de la hiérarchie
        for root_id in sorted(root_chunks, key=lambda x: chunk_graph[x]['chunk'].relevance_score, reverse=True):
            build_hierarchy(root_id)
        
        return "\n\n".join(content_parts)
    
    def _semantic_cluster_merge_chunks(self, chunks: List[ContextChunk]) -> str:
        """Fusion basée sur le clustering sémantique"""
        if len(chunks) <= 2:
            return self._concatenate_chunks(chunks)
        
        # Clustering simple basé sur la similarité
        clusters = []
        unassigned = chunks.copy()
        
        while unassigned:
            # Prendre le chunk avec le meilleur score comme centre de cluster
            center = max(unassigned, key=lambda x: x.relevance_score)
            cluster = [center]
            unassigned.remove(center)
            
            # Ajouter les chunks similaires au cluster
            to_remove = []
            for chunk in unassigned:
                similarity = self._calculate_semantic_similarity(center.content, chunk.content)
                if similarity > 0.6:
                    cluster.append(chunk)
                    to_remove.append(chunk)
            
            for chunk in to_remove:
                unassigned.remove(chunk)
            
            clusters.append(cluster)
        
        # Fusion par cluster
        content_parts = []
        for i, cluster in enumerate(clusters):
            cluster_content = []
            for chunk in sorted(cluster, key=lambda x: x.relevance_score, reverse=True):
                cluster_content.append(chunk.content)
            
            if cluster_content:
                content_parts.append(
                    f"=== THÈME {i+1} ===\n" + "\n\n".join(cluster_content)
                )
        
        return "\n\n".join(content_parts)
    
    def _medical_priority_merge_chunks(self, chunks: List[ContextChunk]) -> str:
        """Fusion avec priorité médicale (stratégie optimisée pour le domaine médical)"""
        # Classification médicale des chunks
        medical_categories = {
            'diagnostic': [],
            'treatment': [],
            'symptoms': [],
            'prevention': [],
            'complications': [],
            'general': []
        }
        
        for chunk in chunks:
            category = self._classify_medical_category(chunk.content)
            medical_categories[category].append(chunk)
        
        # Ordre de priorité médicale
        priority_order = ['diagnostic', 'symptoms', 'treatment', 'complications', 'prevention', 'general']
        
        content_parts = []
        
        for category in priority_order:
            if medical_categories[category]:
                # Tri par niveau de preuve et pertinence
                evidence_priority = {'high': 0, 'medium': 1, 'low': 2, 'unknown': 3}
                
                sorted_chunks = sorted(
                    medical_categories[category],
                    key=lambda x: (evidence_priority.get(x.evidence_level, 3), -x.relevance_score)
                )
                
                category_content = []
                for chunk in sorted_chunks:
                    evidence_marker = {
                        'high': '🔬',
                        'medium': '📊',
                        'low': '📝',
                        'unknown': ''
                    }.get(chunk.evidence_level, '')
                    
                    category_content.append(f"{evidence_marker} {chunk.content}")
                
                if category_content:
                    category_title = {
                        'diagnostic': 'DIAGNOSTIC',
                        'treatment': 'TRAITEMENT',
                        'symptoms': 'SYMPTÔMES',
                        'prevention': 'PRÉVENTION',
                        'complications': 'COMPLICATIONS',
                        'general': 'INFORMATIONS GÉNÉRALES'
                    }[category]
                    
                    content_parts.append(
                        f"=== {category_title} ===\n" + "\n\n".join(category_content)
                    )
        
        return "\n\n".join(content_parts)
    
    def _calculate_direct_relevance(self, content: str, query: str) -> float:
        """Calcule la pertinence directe entre le contenu et la requête"""
        content_words = set(content.lower().split())
        query_words = set(query.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = content_words.intersection(query_words)
        return len(intersection) / len(query_words)
    
    def _detect_contradiction(self, content: str, query: str) -> bool:
        """Détecte si le contenu contredit la requête"""
        contradiction_indicators = [
            'contrairement', 'cependant', 'néanmoins', 'toutefois',
            'mais', 'non', 'pas', 'aucun', 'jamais'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in contradiction_indicators)
    
    def _extract_medical_entities(self, content: str) -> List[str]:
        """Extrait les entités médicales du contenu"""
        # Simulation d'extraction d'entités médicales
        # En pratique, utiliserait un modèle NER spécialisé
        medical_terms = [
            'paludisme', 'fièvre', 'diagnostic', 'traitement', 'médicament',
            'symptôme', 'maladie', 'infection', 'virus', 'bactérie',
            'antibiotique', 'vaccin', 'prévention', 'thérapie'
        ]
        
        content_lower = content.lower()
        found_entities = []
        
        for term in medical_terms:
            if term in content_lower:
                found_entities.append(term)
        
        return found_entities
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extrait les concepts clés du contenu"""
        # Simulation d'extraction de concepts
        words = content.lower().split()
        
        # Filtrage des mots importants (simulation)
        important_words = []
        for word in words:
            if len(word) > 4 and word.isalpha():
                important_words.append(word)
        
        # Retourner les plus fréquents
        word_counts = Counter(important_words)
        return [word for word, count in word_counts.most_common(5)]
    
    def _determine_evidence_level(self, content: str) -> str:
        """Détermine le niveau de preuve du contenu"""
        content_lower = content.lower()
        
        for level, indicators in self.evidence_indicators.items():
            for indicator in indicators:
                if indicator in content_lower:
                    return level
        
        return 'unknown'
    
    def _extract_temporal_info(self, content: str) -> Optional[str]:
        """Extrait les informations temporelles du contenu"""
        temporal_patterns = [
            r'\b(\d{4})\b',  # Années
            r'\b(récent|récemment|actuellement)\b',
            r'\b(historique|passé|ancien)\b'
        ]
        
        for pattern in temporal_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _adjust_confidence_score(self, chunk: ContextChunk) -> float:
        """Ajuste le score de confiance basé sur les métadonnées"""
        base_score = chunk.confidence_score
        
        # Bonus pour niveau de preuve élevé
        evidence_bonus = {
            'high': 0.2,
            'medium': 0.1,
            'low': 0.0,
            'unknown': -0.1
        }.get(chunk.evidence_level, 0)
        
        # Bonus pour crédibilité de la source
        credibility_bonus = (chunk.source_credibility - 0.5) * 0.2
        
        # Bonus pour richesse en entités médicales
        entity_bonus = min(0.1, len(chunk.medical_entities) * 0.02)
        
        adjusted_score = base_score + evidence_bonus + credibility_bonus + entity_bonus
        return min(1.0, max(0.0, adjusted_score))
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité sémantique entre deux textes"""
        # Simulation de similarité sémantique
        # En pratique, utiliserait des embeddings
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _calculate_entity_overlap(self, entities1: List[str], entities2: List[str]) -> float:
        """Calcule le chevauchement d'entités médicales"""
        if not entities1 or not entities2:
            return 0.0
        
        set1 = set(entities1)
        set2 = set(entities2)
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _detect_temporal_relation(self, text1: str, text2: str) -> float:
        """Détecte les relations temporelles entre deux textes"""
        # Simulation de détection de relations temporelles
        temporal_words = ['avant', 'après', 'pendant', 'simultané', 'puis', 'ensuite']
        
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        score = 0.0
        for word in temporal_words:
            if word in text1_lower or word in text2_lower:
                score += 0.1
        
        return min(1.0, score)
    
    def _classify_medical_category(self, content: str) -> str:
        """Classifie le contenu selon les catégories médicales"""
        content_lower = content.lower()
        
        category_keywords = {
            'diagnostic': ['diagnostic', 'diagnose', 'examen', 'test', 'analyse'],
            'treatment': ['traitement', 'thérapie', 'médicament', 'posologie', 'cure'],
            'symptoms': ['symptôme', 'signe', 'manifestation', 'douleur', 'fièvre'],
            'prevention': ['prévention', 'prophylaxie', 'vaccination', 'mesure préventive'],
            'complications': ['complication', 'séquelle', 'effet secondaire', 'risque']
        }
        
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            category_scores[category] = score
        
        best_category = max(category_scores.items(), key=lambda x: x[1])
        return best_category[0] if best_category[1] > 0 else 'general'
    
    def _calculate_fusion_quality_metrics(self, chunks: List[ContextChunk], fused_content: str) -> Dict[str, float]:
        """Calcule les métriques de qualité de la fusion"""
        metrics = {}
        
        # Diversité du contenu
        unique_entities = set()
        for chunk in chunks:
            unique_entities.update(chunk.medical_entities)
        metrics['entity_diversity'] = len(unique_entities)
        
        # Cohérence temporelle
        temporal_consistency = 1.0  # Simulation
        metrics['temporal_consistency'] = temporal_consistency
        
        # Couverture des types de contexte
        context_types = set(chunk.context_type for chunk in chunks)
        metrics['context_type_coverage'] = len(context_types) / len(ContextType)
        
        # Qualité moyenne des sources
        avg_credibility = np.mean([chunk.source_credibility for chunk in chunks])
        metrics['average_source_credibility'] = avg_credibility
        
        # Longueur appropriée
        word_count = len(fused_content.split())
        optimal_length = 1000  # Longueur optimale estimée
        length_score = 1.0 - abs(word_count - optimal_length) / optimal_length
        metrics['length_appropriateness'] = max(0.0, length_score)
        
        return metrics
    
    def _generate_cache_key(self, query: RetrievalQuery) -> str:
        """Génère une clé de cache pour la requête"""
        key_components = [
            query.text,
            str(sorted([ct.value for ct in query.context_types])),
            str(query.max_chunks),
            str(query.min_relevance),
            query.medical_specialty or ""
        ]
        return "|".join(key_components)
    
    def _update_retrieval_stats(self, chunks: List[ContextChunk], retrieval_time: float):
        """Met à jour les statistiques de récupération"""
        self.retrieval_stats['total_retrievals'] += 1
        
        # Temps moyen
        total_retrievals = self.retrieval_stats['total_retrievals']
        current_avg = self.retrieval_stats['avg_retrieval_time']
        self.retrieval_stats['avg_retrieval_time'] = (
            (current_avg * (total_retrievals - 1) + retrieval_time) / total_retrievals
        )
        
        # Nombre moyen de chunks
        current_avg_chunks = self.retrieval_stats['avg_chunks_retrieved']
        self.retrieval_stats['avg_chunks_retrieved'] = (
            (current_avg_chunks * (total_retrievals - 1) + len(chunks)) / total_retrievals
        )
        
        # Types de contexte
        for chunk in chunks:
            self.retrieval_stats['context_types_retrieved'][chunk.context_type.value] += 1
    
    def get_retrieval_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de récupération"""
        return {
            'retrieval_stats': self.retrieval_stats.copy(),
            'cache_size': len(self.context_cache),
            'medical_kb_size': len(self.medical_kb),
            'supported_context_types': [ct.value for ct in ContextType],
            'supported_fusion_strategies': [fs.value for fs in FusionStrategy]
        }

def main():
    """Fonction de test du système de récupération de contexte"""
    # Simulation d'un système de recherche
    class MockSearchSystem:
        def search(self, query):
            # Simulation de résultats de recherche
            from .semantic_search import SearchResult, SearchType
            
            mock_results = [
                SearchResult(
                    document_id="doc1",
                    chunk_id="chunk1",
                    content="Le paludisme est diagnostiqué par examen microscopique du sang.",
                    relevance_score=0.9,
                    search_type=SearchType.SEMANTIC,
                    metadata={'medical_domain': 'infectious_diseases', 'source_credibility': 0.9}
                ),
                SearchResult(
                    document_id="doc2",
                    chunk_id="chunk2",
                    content="Les symptômes du paludisme incluent fièvre, frissons et maux de tête.",
                    relevance_score=0.8,
                    search_type=SearchType.SEMANTIC,
                    metadata={'medical_domain': 'infectious_diseases', 'source_credibility': 0.8}
                )
            ]
            return mock_results
    
    # Initialisation du système
    mock_search = MockSearchSystem()
    retriever = MedicalContextRetriever(
        semantic_search_system=mock_search,
        language="fr"
    )
    
    # Test de récupération de contexte
    query = RetrievalQuery(
        text="diagnostic du paludisme",
        medical_specialty="infectious_diseases",
        max_chunks=5
    )
    
    context_chunks = retriever.retrieve_context(query)
    
    print("\n=== RÉCUPÉRATION DE CONTEXTE ===")
    print(f"Requête: {query.text}")
    print(f"Chunks récupérés: {len(context_chunks)}")
    
    for i, chunk in enumerate(context_chunks, 1):
        print(f"\n{i}. Type: {chunk.context_type.value}")
        print(f"   Score: {chunk.relevance_score:.3f}")
        print(f"   Contenu: {chunk.content}")
        print(f"   Entités: {chunk.medical_entities}")
    
    # Test de fusion
    if context_chunks:
        fused_context = retriever.fuse_context(
            context_chunks, 
            FusionStrategy.MEDICAL_PRIORITY
        )
        
        print(f"\n=== CONTEXTE FUSIONNÉ ===")
        print(f"Stratégie: {fused_context.fusion_strategy.value}")
        print(f"Total chunks: {fused_context.total_chunks}")
        print(f"Total mots: {fused_context.total_words}")
        print(f"Score de confiance: {fused_context.confidence_score:.3f}")
        print(f"\nContenu fusionné:\n{fused_context.fused_content}")
    
    # Statistiques
    stats = retriever.get_retrieval_statistics()
    print(f"\n=== STATISTIQUES ===")
    print(f"Récupérations totales: {stats['retrieval_stats']['total_retrievals']}")
    print(f"Temps moyen: {stats['retrieval_stats']['avg_retrieval_time']:.3f}s")

if __name__ == "__main__":
    main()