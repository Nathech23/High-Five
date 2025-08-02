#!/usr/bin/env python3
"""
Fusion Intelligente de Sources Multiples

Objectif 16: Créer fusion intelligente sources multiples

Ce module implémente un système de fusion intelligent qui combine
les résultats de recherche provenant de sources multiples en
élimininant les doublons, résolvant les conflits et synthétisant
les informations de manière cohérente.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
import numpy as np
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import time
import re
import difflib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn non disponible")
    SKLEARN_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    logger.warning("NetworkX non disponible")
    NETWORKX_AVAILABLE = False

class FusionStrategy(Enum):
    """Stratégies de fusion"""
    SIMPLE_MERGE = "simple_merge"  # Fusion simple
    WEIGHTED_FUSION = "weighted_fusion"  # Fusion pondérée
    CONSENSUS_BASED = "consensus_based"  # Basée sur le consensus
    AUTHORITY_BASED = "authority_based"  # Basée sur l'autorité
    TEMPORAL_FUSION = "temporal_fusion"  # Fusion temporelle
    SEMANTIC_CLUSTERING = "semantic_clustering"  # Clustering sémantique
    CONFLICT_RESOLUTION = "conflict_resolution"  # Résolution de conflits
    HIERARCHICAL_FUSION = "hierarchical_fusion"  # Fusion hiérarchique

class ConflictType(Enum):
    """Types de conflits"""
    CONTRADICTORY_INFO = "contradictory_info"  # Informations contradictoires
    DIFFERENT_VALUES = "different_values"  # Valeurs différentes
    MISSING_INFO = "missing_info"  # Information manquante
    OUTDATED_INFO = "outdated_info"  # Information obsolète
    LANGUAGE_VARIANT = "language_variant"  # Variante linguistique
    SOURCE_BIAS = "source_bias"  # Biais de source
    PRECISION_LEVEL = "precision_level"  # Niveau de précision différent

class SourceType(Enum):
    """Types de sources"""
    OFFICIAL_GUIDELINE = "official_guideline"  # Directive officielle
    RESEARCH_PAPER = "research_paper"  # Article de recherche
    CLINICAL_PROTOCOL = "clinical_protocol"  # Protocole clinique
    PATIENT_INFO = "patient_info"  # Information patient
    EXPERT_OPINION = "expert_opinion"  # Avis d'expert
    COMMUNITY_CONTENT = "community_content"  # Contenu communautaire
    NEWS_ARTICLE = "news_article"  # Article de presse
    REFERENCE_BOOK = "reference_book"  # Livre de référence

@dataclass
class SourceInfo:
    """Informations sur une source"""
    id: str
    name: str
    type: SourceType
    authority_score: float  # 0.0 à 1.0
    reliability_score: float  # 0.0 à 1.0
    language: str
    last_updated: Optional[datetime] = None
    domain_expertise: List[str] = field(default_factory=list)
    bias_indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """Résultat de recherche avec informations de source"""
    id: str
    content: str
    title: Optional[str] = None
    source: SourceInfo = None
    language: str = "fr"
    score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    medical_terms: List[str] = field(default_factory=list)
    key_facts: List[str] = field(default_factory=list)
    numerical_data: Dict[str, Any] = field(default_factory=dict)
    citations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConflictInfo:
    """Information sur un conflit détecté"""
    conflict_type: ConflictType
    sources: List[str]  # IDs des sources en conflit
    description: str
    severity: float  # 0.0 à 1.0
    resolution_strategy: Optional[str] = None
    resolved: bool = False
    resolution_confidence: float = 0.0

@dataclass
class FusedResult:
    """Résultat fusionné"""
    id: str
    content: str
    title: Optional[str] = None
    source_results: List[SearchResult] = field(default_factory=list)
    fusion_strategy: str = ""
    confidence_score: float = 0.0
    consensus_level: float = 0.0
    language: str = "fr"
    key_facts: List[str] = field(default_factory=list)
    numerical_data: Dict[str, Any] = field(default_factory=dict)
    source_attribution: Dict[str, float] = field(default_factory=dict)  # source_id -> contribution
    conflicts_detected: List[ConflictInfo] = field(default_factory=list)
    conflicts_resolved: List[ConflictInfo] = field(default_factory=list)
    quality_indicators: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FusionStats:
    """Statistiques de fusion"""
    total_fusions: int = 0
    total_sources_processed: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    avg_consensus_level: float = 0.0
    avg_confidence_score: float = 0.0
    fusion_strategies_used: Dict[str, int] = field(default_factory=dict)
    source_types_processed: Dict[str, int] = field(default_factory=dict)
    languages_processed: Set[str] = field(default_factory=set)
    processing_time: float = 0.0
    avg_processing_time: float = 0.0

class IntelligentFusion:
    """
    Système de fusion intelligente de sources multiples
    
    Objectif couvert:
    - 16. Créer fusion intelligente sources multiples
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = FusionStats()
        
        # Configuration des sources
        self.source_registry: Dict[str, SourceInfo] = {}
        
        # Seuils de configuration
        self.similarity_threshold = self.config.get("similarity_threshold", 0.8)
        self.conflict_threshold = self.config.get("conflict_threshold", 0.3)
        self.consensus_threshold = self.config.get("consensus_threshold", 0.6)
        self.min_sources_for_consensus = self.config.get("min_sources_for_consensus", 2)
        
        # Poids par type de source
        self.source_weights = {
            SourceType.OFFICIAL_GUIDELINE: 1.0,
            SourceType.RESEARCH_PAPER: 0.9,
            SourceType.CLINICAL_PROTOCOL: 0.95,
            SourceType.EXPERT_OPINION: 0.8,
            SourceType.REFERENCE_BOOK: 0.85,
            SourceType.PATIENT_INFO: 0.7,
            SourceType.COMMUNITY_CONTENT: 0.4,
            SourceType.NEWS_ARTICLE: 0.3
        }
        
        # Patterns de détection de conflits
        self.conflict_patterns = {
            "contradictory_terms": [
                (r"\b(ne pas|pas|non)\b", r"\b(oui|si|recommandé)\b"),
                (r"\b(contre-indiqué|déconseillé)\b", r"\b(recommandé|conseillé)\b"),
                (r"\b(inefficace|inutile)\b", r"\b(efficace|utile)\b")
            ],
            "numerical_conflicts": [
                r"(\d+(?:\.\d+)?)\s*(mg|g|ml|l|%)\b",
                r"(\d+(?:\.\d+)?)\s*fois\s*par\s*(jour|semaine|mois)\b",
                r"(\d+(?:\.\d+)?)\s*°C\b"
            ],
            "temporal_conflicts": [
                r"\b(\d{4})\b",  # Années
                r"\b(récent|ancien|nouveau|obsolète)\b"
            ]
        }
        
        # Modèles de fusion
        self.tfidf_vectorizer = None
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 2),
                stop_words=None
            )
        
        # Cache de similarité
        self.similarity_cache: Dict[str, float] = {}
        self.max_cache_size = self.config.get("max_cache_size", 1000)
        
        # Initialiser les sources par défaut
        self._init_default_sources()
        
        logger.info("Système de fusion intelligente initialisé")
    
    def _init_default_sources(self):
        """Initialise les sources par défaut"""
        default_sources = [
            SourceInfo(
                id="who",
                name="Organisation Mondiale de la Santé",
                type=SourceType.OFFICIAL_GUIDELINE,
                authority_score=1.0,
                reliability_score=1.0,
                language="fr",
                domain_expertise=["infectious_diseases", "public_health", "epidemiology"]
            ),
            SourceInfo(
                id="cdc",
                name="Centers for Disease Control",
                type=SourceType.OFFICIAL_GUIDELINE,
                authority_score=0.95,
                reliability_score=0.98,
                language="en",
                domain_expertise=["infectious_diseases", "prevention", "epidemiology"]
            ),
            SourceInfo(
                id="minsante_cm",
                name="Ministère de la Santé du Cameroun",
                type=SourceType.OFFICIAL_GUIDELINE,
                authority_score=0.90,
                reliability_score=0.85,
                language="fr",
                domain_expertise=["local_health", "tropical_diseases", "public_health"]
            ),
            SourceInfo(
                id="hgd",
                name="Hôpital Général de Douala",
                type=SourceType.CLINICAL_PROTOCOL,
                authority_score=0.85,
                reliability_score=0.90,
                language="fr",
                domain_expertise=["clinical_practice", "emergency", "surgery"]
            ),
            SourceInfo(
                id="pubmed",
                name="PubMed",
                type=SourceType.RESEARCH_PAPER,
                authority_score=0.90,
                reliability_score=0.95,
                language="en",
                domain_expertise=["research", "evidence_based", "peer_review"]
            ),
            SourceInfo(
                id="cochrane",
                name="Cochrane Library",
                type=SourceType.RESEARCH_PAPER,
                authority_score=0.95,
                reliability_score=0.98,
                language="en",
                domain_expertise=["systematic_review", "evidence_based", "meta_analysis"]
            )
        ]
        
        for source in default_sources:
            self.source_registry[source.id] = source
        
        logger.info(f"Sources par défaut initialisées: {len(default_sources)} sources")
    
    def register_source(self, source: SourceInfo):
        """Enregistre une nouvelle source"""
        self.source_registry[source.id] = source
        logger.debug(f"Source enregistrée: {source.name} ({source.id})")
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes"""
        # Créer une clé de cache
        cache_key = hashlib.md5(f"{text1[:100]}_{text2[:100]}".encode()).hexdigest()[:16]
        
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        if SKLEARN_AVAILABLE and self.tfidf_vectorizer:
            try:
                # Utiliser TF-IDF
                texts = [text1, text2]
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
                similarity_matrix = cosine_similarity(tfidf_matrix)
                similarity = float(similarity_matrix[0, 1])
            except Exception as e:
                logger.warning(f"Erreur TF-IDF: {e}")
                similarity = self._simple_similarity(text1, text2)
        else:
            similarity = self._simple_similarity(text1, text2)
        
        # Mettre en cache
        if len(self.similarity_cache) < self.max_cache_size:
            self.similarity_cache[cache_key] = similarity
        
        return similarity
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Calcule une similarité simple basée sur les mots communs"""
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _detect_duplicates(self, results: List[SearchResult]) -> List[List[int]]:
        """Détecte les doublons dans les résultats"""
        duplicate_groups = []
        processed = set()
        
        for i, result1 in enumerate(results):
            if i in processed:
                continue
            
            current_group = [i]
            
            for j, result2 in enumerate(results[i+1:], i+1):
                if j in processed:
                    continue
                
                similarity = self._calculate_similarity(result1.content, result2.content)
                
                if similarity >= self.similarity_threshold:
                    current_group.append(j)
                    processed.add(j)
            
            if len(current_group) > 1:
                duplicate_groups.append(current_group)
                processed.update(current_group)
        
        return duplicate_groups
    
    def _detect_conflicts(self, results: List[SearchResult]) -> List[ConflictInfo]:
        """Détecte les conflits entre les résultats"""
        conflicts = []
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                # Vérifier les conflits contradictoires
                contradictory_conflicts = self._check_contradictory_info(result1, result2)
                conflicts.extend(contradictory_conflicts)
                
                # Vérifier les conflits numériques
                numerical_conflicts = self._check_numerical_conflicts(result1, result2)
                conflicts.extend(numerical_conflicts)
                
                # Vérifier les conflits temporels
                temporal_conflicts = self._check_temporal_conflicts(result1, result2)
                conflicts.extend(temporal_conflicts)
        
        return conflicts
    
    def _check_contradictory_info(self, result1: SearchResult, result2: SearchResult) -> List[ConflictInfo]:
        """Vérifie les informations contradictoires"""
        conflicts = []
        
        for positive_pattern, negative_pattern in self.conflict_patterns["contradictory_terms"]:
            pos_in_1 = bool(re.search(positive_pattern, result1.content, re.IGNORECASE))
            neg_in_1 = bool(re.search(negative_pattern, result1.content, re.IGNORECASE))
            pos_in_2 = bool(re.search(positive_pattern, result2.content, re.IGNORECASE))
            neg_in_2 = bool(re.search(negative_pattern, result2.content, re.IGNORECASE))
            
            # Détecter les contradictions
            if (pos_in_1 and neg_in_2) or (neg_in_1 and pos_in_2):
                severity = 0.8 if result1.source and result2.source else 0.6
                
                conflict = ConflictInfo(
                    conflict_type=ConflictType.CONTRADICTORY_INFO,
                    sources=[result1.id, result2.id],
                    description=f"Information contradictoire détectée entre {result1.source.name if result1.source else 'source inconnue'} et {result2.source.name if result2.source else 'source inconnue'}",
                    severity=severity
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _check_numerical_conflicts(self, result1: SearchResult, result2: SearchResult) -> List[ConflictInfo]:
        """Vérifie les conflits numériques"""
        conflicts = []
        
        for pattern in self.conflict_patterns["numerical_conflicts"]:
            values1 = re.findall(pattern, result1.content, re.IGNORECASE)
            values2 = re.findall(pattern, result2.content, re.IGNORECASE)
            
            if values1 and values2:
                # Comparer les valeurs numériques
                for val1_match in values1:
                    for val2_match in values2:
                        try:
                            if isinstance(val1_match, tuple):
                                val1 = float(val1_match[0])
                                unit1 = val1_match[1] if len(val1_match) > 1 else ""
                            else:
                                val1 = float(val1_match)
                                unit1 = ""
                            
                            if isinstance(val2_match, tuple):
                                val2 = float(val2_match[0])
                                unit2 = val2_match[1] if len(val2_match) > 1 else ""
                            else:
                                val2 = float(val2_match)
                                unit2 = ""
                            
                            # Conflit si même unité mais valeurs très différentes
                            if unit1 == unit2 and abs(val1 - val2) / max(val1, val2) > 0.5:
                                conflict = ConflictInfo(
                                    conflict_type=ConflictType.DIFFERENT_VALUES,
                                    sources=[result1.id, result2.id],
                                    description=f"Valeurs numériques différentes: {val1}{unit1} vs {val2}{unit2}",
                                    severity=0.7
                                )
                                conflicts.append(conflict)
                        
                        except (ValueError, IndexError):
                            continue
        
        return conflicts
    
    def _check_temporal_conflicts(self, result1: SearchResult, result2: SearchResult) -> List[ConflictInfo]:
        """Vérifie les conflits temporels"""
        conflicts = []
        
        # Comparer les dates de création/mise à jour
        if (result1.timestamp and result2.timestamp and 
            abs((result1.timestamp - result2.timestamp).days) > 1825):  # 5 ans
            
            # Vérifier si l'information plus récente contredit l'ancienne
            newer_result = result1 if result1.timestamp > result2.timestamp else result2
            older_result = result2 if result1.timestamp > result2.timestamp else result1
            
            # Rechercher des indicateurs d'obsolescence
            obsolete_indicators = ["obsolète", "dépassé", "ancienne", "nouvelle", "récente"]
            
            for indicator in obsolete_indicators:
                if indicator in newer_result.content.lower():
                    conflict = ConflictInfo(
                        conflict_type=ConflictType.OUTDATED_INFO,
                        sources=[older_result.id, newer_result.id],
                        description=f"Information potentiellement obsolète détectée",
                        severity=0.5
                    )
                    conflicts.append(conflict)
                    break
        
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[ConflictInfo], results: List[SearchResult]) -> List[ConflictInfo]:
        """Résout les conflits détectés"""
        resolved_conflicts = []
        
        for conflict in conflicts:
            resolution_strategy = None
            resolution_confidence = 0.0
            
            # Récupérer les résultats en conflit
            conflicting_results = [r for r in results if r.id in conflict.sources]
            
            if conflict.conflict_type == ConflictType.CONTRADICTORY_INFO:
                resolution_strategy, resolution_confidence = self._resolve_contradictory_conflict(conflicting_results)
            
            elif conflict.conflict_type == ConflictType.DIFFERENT_VALUES:
                resolution_strategy, resolution_confidence = self._resolve_numerical_conflict(conflicting_results)
            
            elif conflict.conflict_type == ConflictType.OUTDATED_INFO:
                resolution_strategy, resolution_confidence = self._resolve_temporal_conflict(conflicting_results)
            
            if resolution_strategy:
                conflict.resolution_strategy = resolution_strategy
                conflict.resolution_confidence = resolution_confidence
                conflict.resolved = True
                resolved_conflicts.append(conflict)
        
        return resolved_conflicts
    
    def _resolve_contradictory_conflict(self, results: List[SearchResult]) -> Tuple[str, float]:
        """Résout un conflit contradictoire"""
        if not results:
            return None, 0.0
        
        # Prioriser par autorité de source
        best_result = max(results, key=lambda r: r.source.authority_score if r.source else 0.0)
        
        strategy = f"Résolution par autorité de source: {best_result.source.name if best_result.source else 'source inconnue'}"
        confidence = best_result.source.authority_score if best_result.source else 0.5
        
        return strategy, confidence
    
    def _resolve_numerical_conflict(self, results: List[SearchResult]) -> Tuple[str, float]:
        """Résout un conflit numérique"""
        if not results:
            return None, 0.0
        
        # Prioriser les sources officielles pour les valeurs numériques
        official_results = [r for r in results if r.source and r.source.type == SourceType.OFFICIAL_GUIDELINE]
        
        if official_results:
            best_result = max(official_results, key=lambda r: r.source.reliability_score)
            strategy = f"Résolution par source officielle: {best_result.source.name}"
            confidence = best_result.source.reliability_score
        else:
            # Utiliser la source la plus fiable
            best_result = max(results, key=lambda r: r.source.reliability_score if r.source else 0.0)
            strategy = f"Résolution par fiabilité: {best_result.source.name if best_result.source else 'source inconnue'}"
            confidence = best_result.source.reliability_score if best_result.source else 0.5
        
        return strategy, confidence
    
    def _resolve_temporal_conflict(self, results: List[SearchResult]) -> Tuple[str, float]:
        """Résout un conflit temporel"""
        if not results:
            return None, 0.0
        
        # Prioriser l'information la plus récente
        newest_result = max(results, key=lambda r: r.timestamp if r.timestamp else datetime.min)
        
        strategy = f"Résolution temporelle: information la plus récente ({newest_result.timestamp.strftime('%Y-%m-%d') if newest_result.timestamp else 'date inconnue'})"
        confidence = 0.8 if newest_result.timestamp else 0.4
        
        return strategy, confidence
    
    def _merge_duplicates(self, duplicate_groups: List[List[int]], results: List[SearchResult]) -> List[SearchResult]:
        """Fusionne les doublons"""
        merged_results = []
        processed_indices = set()
        
        # Traiter les groupes de doublons
        for group in duplicate_groups:
            if not group:
                continue
            
            group_results = [results[i] for i in group]
            
            # Sélectionner le meilleur résultat comme base
            best_result = max(group_results, key=lambda r: (
                r.source.authority_score if r.source else 0.0,
                r.score,
                len(r.content)
            ))
            
            # Enrichir avec les informations des autres résultats
            merged_content = best_result.content
            merged_medical_terms = set(best_result.medical_terms)
            merged_key_facts = set(best_result.key_facts)
            merged_citations = set(best_result.citations)
            
            for result in group_results:
                if result.id != best_result.id:
                    # Ajouter les termes médicaux uniques
                    merged_medical_terms.update(result.medical_terms)
                    merged_key_facts.update(result.key_facts)
                    merged_citations.update(result.citations)
                    
                    # Enrichir le contenu si nécessaire
                    if len(result.content) > len(merged_content):
                        merged_content = result.content
            
            # Créer le résultat fusionné
            merged_result = SearchResult(
                id=f"merged_{best_result.id}",
                content=merged_content,
                title=best_result.title,
                source=best_result.source,
                language=best_result.language,
                score=max(r.score for r in group_results),
                medical_terms=list(merged_medical_terms),
                key_facts=list(merged_key_facts),
                citations=list(merged_citations),
                confidence=sum(r.confidence for r in group_results) / len(group_results),
                metadata={
                    "merged_from": [r.id for r in group_results],
                    "merge_count": len(group_results)
                }
            )
            
            merged_results.append(merged_result)
            processed_indices.update(group)
        
        # Ajouter les résultats non dupliqués
        for i, result in enumerate(results):
            if i not in processed_indices:
                merged_results.append(result)
        
        return merged_results
    
    def _calculate_consensus(self, results: List[SearchResult]) -> float:
        """Calcule le niveau de consensus entre les résultats"""
        if len(results) < 2:
            return 1.0
        
        total_similarity = 0.0
        comparisons = 0
        
        for i, result1 in enumerate(results):
            for result2 in results[i+1:]:
                similarity = self._calculate_similarity(result1.content, result2.content)
                total_similarity += similarity
                comparisons += 1
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def _generate_fused_content(self, results: List[SearchResult], strategy: FusionStrategy) -> str:
        """Génère le contenu fusionné"""
        if not results:
            return ""
        
        if strategy == FusionStrategy.SIMPLE_MERGE:
            # Concaténation simple
            return "\n\n".join(r.content for r in results)
        
        elif strategy == FusionStrategy.WEIGHTED_FUSION:
            # Fusion pondérée par autorité de source
            weighted_contents = []
            for result in results:
                weight = result.source.authority_score if result.source else 0.5
                if weight > 0.7:  # Inclure seulement les sources fiables
                    weighted_contents.append(result.content)
            
            return "\n\n".join(weighted_contents) if weighted_contents else results[0].content
        
        elif strategy == FusionStrategy.CONSENSUS_BASED:
            # Inclure seulement le contenu avec consensus
            consensus_threshold = 0.6
            consensus_content = []
            
            for result in results:
                # Calculer le consensus pour ce résultat
                similarities = [self._calculate_similarity(result.content, other.content) 
                              for other in results if other.id != result.id]
                
                if similarities and sum(similarities) / len(similarities) >= consensus_threshold:
                    consensus_content.append(result.content)
            
            return "\n\n".join(consensus_content) if consensus_content else results[0].content
        
        elif strategy == FusionStrategy.AUTHORITY_BASED:
            # Prioriser par autorité de source
            sorted_results = sorted(results, 
                                  key=lambda r: r.source.authority_score if r.source else 0.0, 
                                  reverse=True)
            
            return "\n\n".join(r.content for r in sorted_results[:3])  # Top 3
        
        elif strategy == FusionStrategy.TEMPORAL_FUSION:
            # Prioriser l'information récente
            sorted_results = sorted(results, 
                                  key=lambda r: r.timestamp if r.timestamp else datetime.min, 
                                  reverse=True)
            
            return "\n\n".join(r.content for r in sorted_results[:3])  # 3 plus récents
        
        else:
            # Stratégie par défaut
            return results[0].content
    
    def fuse_results(self, results: List[SearchResult], 
                    strategy: FusionStrategy = FusionStrategy.WEIGHTED_FUSION,
                    resolve_conflicts: bool = True) -> FusedResult:
        """
        Fusionne une liste de résultats de recherche
        
        Args:
            results: Liste des résultats à fusionner
            strategy: Stratégie de fusion
            resolve_conflicts: Si True, résout les conflits détectés
        
        Returns:
            FusedResult: Résultat fusionné
        """
        start_time = time.time()
        
        try:
            if not results:
                return FusedResult(
                    id="empty_fusion",
                    content="",
                    fusion_strategy=strategy.value,
                    confidence_score=0.0
                )
            
            # Étape 1: Détecter et fusionner les doublons
            duplicate_groups = self._detect_duplicates(results)
            deduplicated_results = self._merge_duplicates(duplicate_groups, results)
            
            # Étape 2: Détecter les conflits
            conflicts = self._detect_conflicts(deduplicated_results)
            resolved_conflicts = []
            
            if resolve_conflicts and conflicts:
                resolved_conflicts = self._resolve_conflicts(conflicts, deduplicated_results)
            
            # Étape 3: Calculer le consensus
            consensus_level = self._calculate_consensus(deduplicated_results)
            
            # Étape 4: Générer le contenu fusionné
            fused_content = self._generate_fused_content(deduplicated_results, strategy)
            
            # Étape 5: Calculer les métriques de qualité
            confidence_score = self._calculate_fusion_confidence(
                deduplicated_results, consensus_level, len(resolved_conflicts), len(conflicts)
            )
            
            # Étape 6: Calculer l'attribution des sources
            source_attribution = self._calculate_source_attribution(deduplicated_results, strategy)
            
            # Étape 7: Extraire les faits clés et données numériques
            key_facts = self._extract_key_facts(deduplicated_results)
            numerical_data = self._extract_numerical_data(deduplicated_results)
            
            # Étape 8: Déterminer la langue principale
            main_language = self._determine_main_language(deduplicated_results)
            
            # Créer le résultat fusionné
            fused_result = FusedResult(
                id=f"fusion_{int(time.time())}_{len(results)}",
                content=fused_content,
                title=self._generate_fused_title(deduplicated_results),
                source_results=deduplicated_results,
                fusion_strategy=strategy.value,
                confidence_score=confidence_score,
                consensus_level=consensus_level,
                language=main_language,
                key_facts=key_facts,
                numerical_data=numerical_data,
                source_attribution=source_attribution,
                conflicts_detected=conflicts,
                conflicts_resolved=resolved_conflicts,
                quality_indicators={
                    "duplicate_groups_merged": len(duplicate_groups),
                    "conflicts_detected": len(conflicts),
                    "conflicts_resolved": len(resolved_conflicts),
                    "source_diversity": len(set(r.source.id for r in deduplicated_results if r.source)),
                    "language_diversity": len(set(r.language for r in deduplicated_results))
                },
                metadata={
                    "original_results_count": len(results),
                    "deduplicated_count": len(deduplicated_results),
                    "processing_time": time.time() - start_time,
                    "strategy_used": strategy.value
                }
            )
            
            # Mettre à jour les statistiques
            self._update_fusion_stats(fused_result, strategy, time.time() - start_time)
            
            return fused_result
        
        except Exception as e:
            logger.error(f"Erreur lors de la fusion: {e}")
            # Retourner un résultat de base en cas d'erreur
            return FusedResult(
                id="error_fusion",
                content=results[0].content if results else "",
                source_results=results,
                fusion_strategy=strategy.value,
                confidence_score=0.0,
                metadata={"error": str(e)}
            )
    
    def _calculate_fusion_confidence(self, results: List[SearchResult], consensus_level: float,
                                   resolved_conflicts: int, total_conflicts: int) -> float:
        """Calcule la confiance dans la fusion"""
        if not results:
            return 0.0
        
        # Score de base basé sur le consensus
        base_score = consensus_level
        
        # Bonus pour la qualité des sources
        avg_authority = sum(r.source.authority_score for r in results if r.source) / len(results)
        authority_bonus = avg_authority * 0.3
        
        # Pénalité pour les conflits non résolus
        unresolved_conflicts = total_conflicts - resolved_conflicts
        conflict_penalty = (unresolved_conflicts / max(total_conflicts, 1)) * 0.2
        
        # Bonus pour la diversité des sources
        unique_sources = len(set(r.source.id for r in results if r.source))
        diversity_bonus = min(unique_sources / len(results), 0.5) * 0.2
        
        confidence = base_score + authority_bonus + diversity_bonus - conflict_penalty
        return max(0.0, min(1.0, confidence))
    
    def _calculate_source_attribution(self, results: List[SearchResult], strategy: FusionStrategy) -> Dict[str, float]:
        """Calcule l'attribution des sources"""
        attribution = {}
        total_weight = 0.0
        
        for result in results:
            if not result.source:
                continue
            
            # Calculer le poids selon la stratégie
            if strategy == FusionStrategy.AUTHORITY_BASED:
                weight = result.source.authority_score
            elif strategy == FusionStrategy.WEIGHTED_FUSION:
                weight = (result.source.authority_score + result.source.reliability_score) / 2
            elif strategy == FusionStrategy.TEMPORAL_FUSION:
                # Poids basé sur la récence
                if result.timestamp:
                    days_old = (datetime.now() - result.timestamp).days
                    weight = max(0.1, 1.0 - (days_old / 1825))  # Décroissance sur 5 ans
                else:
                    weight = 0.5
            else:
                weight = 1.0  # Poids égal
            
            attribution[result.source.id] = weight
            total_weight += weight
        
        # Normaliser
        if total_weight > 0:
            attribution = {k: v / total_weight for k, v in attribution.items()}
        
        return attribution
    
    def _extract_key_facts(self, results: List[SearchResult]) -> List[str]:
        """Extrait les faits clés des résultats"""
        all_facts = []
        
        for result in results:
            all_facts.extend(result.key_facts)
        
        # Déduplication et tri par fréquence
        fact_counts = Counter(all_facts)
        
        # Retourner les faits les plus fréquents
        return [fact for fact, count in fact_counts.most_common(10)]
    
    def _extract_numerical_data(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extrait les données numériques des résultats"""
        numerical_data = {}
        
        # Patterns pour extraire les données numériques
        patterns = {
            "dosage": r"(\d+(?:\.\d+)?)\s*(mg|g|ml|l|UI|mcg)\b",
            "frequency": r"(\d+(?:\.\d+)?)\s*fois\s*par\s*(jour|semaine|mois)\b",
            "temperature": r"(\d+(?:\.\d+)?)\s*°C\b",
            "percentage": r"(\d+(?:\.\d+)?)\s*%\b",
            "age": r"(\d+)\s*ans?\b"
        }
        
        for result in results:
            # Ajouter les données numériques explicites
            if result.numerical_data:
                for key, value in result.numerical_data.items():
                    if key not in numerical_data:
                        numerical_data[key] = []
                    numerical_data[key].append(value)
            
            # Extraire les données du contenu
            for data_type, pattern in patterns.items():
                matches = re.findall(pattern, result.content, re.IGNORECASE)
                if matches:
                    if data_type not in numerical_data:
                        numerical_data[data_type] = []
                    numerical_data[data_type].extend(matches)
        
        return numerical_data
    
    def _determine_main_language(self, results: List[SearchResult]) -> str:
        """Détermine la langue principale des résultats"""
        if not results:
            return "fr"
        
        language_counts = Counter(r.language for r in results)
        return language_counts.most_common(1)[0][0]
    
    def _generate_fused_title(self, results: List[SearchResult]) -> str:
        """Génère un titre pour le résultat fusionné"""
        if not results:
            return "Résultat fusionné"
        
        # Utiliser le titre du résultat avec la meilleure autorité
        best_result = max(results, key=lambda r: r.source.authority_score if r.source else 0.0)
        
        if best_result.title:
            return f"{best_result.title} (Synthèse)"
        else:
            return "Synthèse de sources multiples"
    
    def _update_fusion_stats(self, fused_result: FusedResult, strategy: FusionStrategy, processing_time: float):
        """Met à jour les statistiques de fusion"""
        self.stats.total_fusions += 1
        self.stats.total_sources_processed += len(fused_result.source_results)
        self.stats.conflicts_detected += len(fused_result.conflicts_detected)
        self.stats.conflicts_resolved += len(fused_result.conflicts_resolved)
        
        # Moyennes mobiles
        if self.stats.total_fusions > 1:
            self.stats.avg_consensus_level = (
                (self.stats.avg_consensus_level * (self.stats.total_fusions - 1) + fused_result.consensus_level) /
                self.stats.total_fusions
            )
            self.stats.avg_confidence_score = (
                (self.stats.avg_confidence_score * (self.stats.total_fusions - 1) + fused_result.confidence_score) /
                self.stats.total_fusions
            )
            self.stats.avg_processing_time = (
                (self.stats.avg_processing_time * (self.stats.total_fusions - 1) + processing_time) /
                self.stats.total_fusions
            )
        else:
            self.stats.avg_consensus_level = fused_result.consensus_level
            self.stats.avg_confidence_score = fused_result.confidence_score
            self.stats.avg_processing_time = processing_time
        
        # Compteurs
        self.stats.fusion_strategies_used[strategy.value] = self.stats.fusion_strategies_used.get(strategy.value, 0) + 1
        
        for result in fused_result.source_results:
            if result.source:
                source_type = result.source.type.value
                self.stats.source_types_processed[source_type] = self.stats.source_types_processed.get(source_type, 0) + 1
            
            self.stats.languages_processed.add(result.language)
    
    def generate_stats(self) -> FusionStats:
        """Génère les statistiques de fusion"""
        start_time = time.time()
        self.stats.processing_time = time.time() - start_time
        return self.stats
    
    def export_fusion_data(self, output_path: str):
        """Exporte les données de fusion"""
        export_data = {
            "metadata": {
                "total_fusions": self.stats.total_fusions,
                "total_sources_processed": self.stats.total_sources_processed,
                "registered_sources": len(self.source_registry),
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "configuration": {
                "similarity_threshold": self.similarity_threshold,
                "conflict_threshold": self.conflict_threshold,
                "consensus_threshold": self.consensus_threshold,
                "source_weights": {k.value: v for k, v in self.source_weights.items()},
                "max_cache_size": self.max_cache_size
            },
            "sources": {
                source_id: {
                    "name": source.name,
                    "type": source.type.value,
                    "authority_score": source.authority_score,
                    "reliability_score": source.reliability_score,
                    "language": source.language,
                    "domain_expertise": source.domain_expertise
                }
                for source_id, source in self.source_registry.items()
            },
            "statistics": {
                "conflicts_detected": self.stats.conflicts_detected,
                "conflicts_resolved": self.stats.conflicts_resolved,
                "avg_consensus_level": self.stats.avg_consensus_level,
                "avg_confidence_score": self.stats.avg_confidence_score,
                "fusion_strategies_used": self.stats.fusion_strategies_used,
                "source_types_processed": self.stats.source_types_processed,
                "languages_processed": list(self.stats.languages_processed),
                "avg_processing_time": self.stats.avg_processing_time
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de fusion exportées: {output_path}")

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("🔗 Test de la Fusion Intelligente de Sources Multiples")
    
    # Créer le système de fusion
    fusion_system = IntelligentFusion({
        "similarity_threshold": 0.8,
        "conflict_threshold": 0.3,
        "consensus_threshold": 0.6
    })
    
    # Résultats de test avec sources multiples
    test_results = [
        SearchResult(
            id="who_malaria_1",
            content="Le paludisme est une maladie parasitaire grave transmise par les moustiques anopheles. Le traitement de première ligne recommandé est l'artéméther-luméfantrine 20mg/120mg, 4 comprimés selon le protocole standard.",
            title="Paludisme - Directives OMS 2024",
            source=fusion_system.source_registry["who"],
            language="fr",
            score=0.95,
            medical_terms=["paludisme", "artéméther-luméfantrine", "anopheles"],
            key_facts=["transmission par moustiques", "traitement artéméther-luméfantrine"],
            numerical_data={"dosage": "20mg/120mg", "quantity": "4 comprimés"},
            confidence=0.98
        ),
        SearchResult(
            id="cdc_malaria_1",
            content="Malaria is a serious parasitic disease transmitted by anopheles mosquitoes. First-line treatment is artemether-lumefantrine 20mg/120mg, 4 tablets according to standard protocol. Early diagnosis is crucial for effective treatment.",
            title="Malaria Treatment Guidelines - CDC 2024",
            source=fusion_system.source_registry["cdc"],
            language="en",
            score=0.92,
            medical_terms=["malaria", "artemether-lumefantrine", "anopheles"],
            key_facts=["mosquito transmission", "artemether-lumefantrine treatment", "early diagnosis important"],
            numerical_data={"dosage": "20mg/120mg", "quantity": "4 tablets"},
            confidence=0.96
        ),
        SearchResult(
            id="hgd_paludisme_1",
            content="Au HGD, nous traitons le paludisme avec l'artéméther-luméfantrine. Posologie: 20mg/120mg, 4 comprimés. Important: diagnostic rapide par test TDR. Surveillance clinique nécessaire.",
            title="Protocole Paludisme - HGD",
            source=fusion_system.source_registry["hgd"],
            language="fr",
            score=0.88,
            medical_terms=["paludisme", "artéméther-luméfantrine", "TDR"],
            key_facts=["diagnostic TDR", "surveillance clinique"],
            numerical_data={"dosage": "20mg/120mg", "quantity": "4 comprimés"},
            confidence=0.90
        ),
        SearchResult(
            id="blog_paludisme_1",
            content="Le paludisme se traite avec différents médicaments. Certains recommandent la chloroquine 25mg/kg, d'autres préfèrent l'artéméther-luméfantrine. Il faut consulter un médecin.",
            title="Traitement du paludisme - Blog santé",
            source=SourceInfo(
                id="blog_sante",
                name="Blog Santé Cameroun",
                type=SourceType.COMMUNITY_CONTENT,
                authority_score=0.3,
                reliability_score=0.4,
                language="fr"
            ),
            language="fr",
            score=0.65,
            medical_terms=["paludisme", "chloroquine", "artéméther-luméfantrine"],
            key_facts=["différents médicaments", "consulter médecin"],
            numerical_data={"chloroquine_dosage": "25mg/kg"},
            confidence=0.60
        ),
        SearchResult(
            id="old_guideline_1",
            content="Traitement du paludisme: chloroquine 25mg/kg en première intention. L'artéméther-luméfantrine est réservé aux cas résistants. Protocole de 2015.",
            title="Anciennes directives paludisme",
            source=SourceInfo(
                id="old_ministry",
                name="Ancien protocole ministériel",
                type=SourceType.OFFICIAL_GUIDELINE,
                authority_score=0.85,
                reliability_score=0.70,
                language="fr"
            ),
            language="fr",
            score=0.75,
            timestamp=datetime(2015, 6, 1),
            medical_terms=["paludisme", "chloroquine", "artéméther-luméfantrine"],
            key_facts=["chloroquine première intention", "résistance"],
            numerical_data={"chloroquine_dosage": "25mg/kg"},
            confidence=0.80
        )
    ]
    
    # Stratégies à tester
    strategies = [
        FusionStrategy.SIMPLE_MERGE,
        FusionStrategy.WEIGHTED_FUSION,
        FusionStrategy.AUTHORITY_BASED,
        FusionStrategy.CONSENSUS_BASED,
        FusionStrategy.TEMPORAL_FUSION
    ]
    
    print(f"\n📊 Test avec {len(test_results)} résultats et {len(strategies)} stratégies:")
    
    # Afficher les résultats originaux
    print("\n📋 Résultats originaux:")
    for i, result in enumerate(test_results, 1):
        source_name = result.source.name if result.source else "Source inconnue"
        authority = result.source.authority_score if result.source else 0.0
        print(f"  {i}. {result.title} ({result.language})")
        print(f"     Source: {source_name} (autorité: {authority:.2f})")
        print(f"     Score: {result.score:.2f} | Confiance: {result.confidence:.2f}")
        if result.timestamp:
            print(f"     Date: {result.timestamp.strftime('%Y-%m-%d')}")
    
    # Tester chaque stratégie
    for strategy in strategies:
        print(f"\n🔗 Stratégie: {strategy.value.upper()}")
        
        fused_result = fusion_system.fuse_results(
            results=test_results,
            strategy=strategy,
            resolve_conflicts=True
        )
        
        print(f"   Résultat fusionné:")
        print(f"     Titre: {fused_result.title}")
        print(f"     Langue: {fused_result.language}")
        print(f"     Score de confiance: {fused_result.confidence_score:.3f}")
        print(f"     Niveau de consensus: {fused_result.consensus_level:.3f}")
        print(f"     Sources utilisées: {len(fused_result.source_results)}")
        
        # Conflits détectés
        if fused_result.conflicts_detected:
            print(f"     Conflits détectés: {len(fused_result.conflicts_detected)}")
            for conflict in fused_result.conflicts_detected[:2]:  # Afficher les 2 premiers
                print(f"       - {conflict.conflict_type.value}: {conflict.description}")
                print(f"         Sévérité: {conflict.severity:.2f} | Résolu: {'Oui' if conflict.resolved else 'Non'}")
        
        # Attribution des sources
        if fused_result.source_attribution:
            print(f"     Attribution des sources:")
            for source_id, contribution in sorted(fused_result.source_attribution.items(), 
                                                key=lambda x: x[1], reverse=True):
                source_name = fusion_system.source_registry.get(source_id, {}).name if source_id in fusion_system.source_registry else source_id
                print(f"       - {source_name}: {contribution:.1%}")
        
        # Faits clés
        if fused_result.key_facts:
            print(f"     Faits clés: {', '.join(fused_result.key_facts[:3])}")
        
        # Données numériques
        if fused_result.numerical_data:
            print(f"     Données numériques: {len(fused_result.numerical_data)} types")
        
        print(f"     Contenu (extrait): {fused_result.content[:150]}...")
    
    # Test de détection de conflits spécifique
    print("\n⚠️ Test de détection de conflits:")
    
    conflict_results = [
        test_results[0],  # OMS: artéméther-luméfantrine
        test_results[4]   # Ancien: chloroquine en première intention
    ]
    
    conflict_fusion = fusion_system.fuse_results(
        results=conflict_results,
        strategy=FusionStrategy.CONFLICT_RESOLUTION,
        resolve_conflicts=True
    )
    
    print(f"   Conflits détectés: {len(conflict_fusion.conflicts_detected)}")
    print(f"   Conflits résolus: {len(conflict_fusion.conflicts_resolved)}")
    
    for conflict in conflict_fusion.conflicts_resolved:
        print(f"     Conflit: {conflict.description}")
        print(f"     Résolution: {conflict.resolution_strategy}")
        print(f"     Confiance: {conflict.resolution_confidence:.2f}")
    
    # Générer les statistiques
    stats = fusion_system.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"   Fusions totales: {stats.total_fusions}")
    print(f"   Sources traitées: {stats.total_sources_processed}")
    print(f"   Conflits détectés: {stats.conflicts_detected}")
    print(f"   Conflits résolus: {stats.conflicts_resolved}")
    print(f"   Consensus moyen: {stats.avg_consensus_level:.3f}")
    print(f"   Confiance moyenne: {stats.avg_confidence_score:.3f}")
    print(f"   Temps traitement moyen: {stats.avg_processing_time:.3f}s")
    
    print(f"\n🔧 Stratégies utilisées:")
    for strategy, count in stats.fusion_strategies_used.items():
        print(f"   {strategy}: {count} utilisations")
    
    print(f"\n📚 Types de sources traités:")
    for source_type, count in stats.source_types_processed.items():
        print(f"   {source_type}: {count} sources")
    
    print(f"\n🌐 Langues traitées: {', '.join(stats.languages_processed)}")
    
    # Exporter les données
    fusion_system.export_fusion_data("intelligent_fusion_export.json")
    print("\n✅ Données exportées: intelligent_fusion_export.json")

if __name__ == "__main__":
    main()