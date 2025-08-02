#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Objectif 15: Implémenter fusion avancée sources multiples
Système de fusion avancée pour combiner intelligemment les résultats de sources multiples

Fonctionnalités:
- Fusion multi-sources intelligente
- Détection et résolution de conflits
- Pondération dynamique des sources
- Consensus et validation croisée
- Métriques de cohérence
- Traçabilité des sources
"""

import json
import logging
import math
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
import statistics
import hashlib
from difflib import SequenceMatcher

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Types de sources"""
    MEDICAL_DATABASE = "medical_database"
    CLINICAL_GUIDELINE = "clinical_guideline"
    RESEARCH_PAPER = "research_paper"
    EXPERT_SYSTEM = "expert_system"
    KNOWLEDGE_BASE = "knowledge_base"
    REAL_TIME_DATA = "real_time_data"
    USER_GENERATED = "user_generated"

class ConflictType(Enum):
    """Types de conflits entre sources"""
    CONTRADICTION = "contradiction"  # Informations contradictoires
    INCONSISTENCY = "inconsistency"  # Incohérences mineures
    OUTDATED = "outdated"           # Information obsolète
    INCOMPLETE = "incomplete"       # Information incomplète
    DUPLICATE = "duplicate"         # Doublons
    BIAS = "bias"                   # Biais détecté

class FusionStrategy(Enum):
    """Stratégies de fusion"""
    WEIGHTED_AVERAGE = "weighted_average"
    CONSENSUS_BASED = "consensus_based"
    AUTHORITY_BASED = "authority_based"
    EVIDENCE_BASED = "evidence_based"
    TEMPORAL_BASED = "temporal_based"
    HYBRID = "hybrid"

class ConfidenceLevel(Enum):
    """Niveaux de confiance"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95

@dataclass
class SourceInfo:
    """Informations sur une source"""
    id: str
    name: str
    type: SourceType
    authority_score: float  # 0-1
    reliability_score: float  # 0-1
    recency_score: float  # 0-1
    bias_score: float  # 0-1 (0 = pas de biais)
    coverage_domains: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SourceResult:
    """Résultat d'une source"""
    source_info: SourceInfo
    content: str
    confidence: float
    relevance_score: float
    evidence_quality: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    supporting_evidence: List[str] = field(default_factory=list)

@dataclass
class ConflictDetection:
    """Détection de conflit entre sources"""
    conflict_type: ConflictType
    sources_involved: List[str]
    severity: float  # 0-1
    description: str
    resolution_suggestion: str
    confidence: float
    detected_at: datetime = field(default_factory=datetime.now)

@dataclass
class FusionResult:
    """Résultat de fusion"""
    fused_content: str
    confidence: float
    consensus_level: float
    sources_used: List[str]
    source_weights: Dict[str, float]
    conflicts_detected: List[ConflictDetection]
    fusion_strategy: FusionStrategy
    quality_metrics: Dict[str, float]
    provenance: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class FusionMetrics:
    """Métriques de fusion"""
    total_fusions: int = 0
    avg_consensus_level: float = 0.0
    avg_confidence: float = 0.0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    source_utilization: Dict[str, int] = field(default_factory=dict)
    fusion_latency_ms: float = 0.0
    quality_improvement: float = 0.0

class ConflictDetector:
    """Détecteur de conflits entre sources"""
    
    def __init__(self):
        self.contradiction_keywords = {
            'positive': ['efficace', 'recommandé', 'bénéfique', 'améliore', 'guérit'],
            'negative': ['inefficace', 'déconseillé', 'dangereux', 'aggrave', 'contre-indiqué'],
            'uncertainty': ['peut-être', 'possiblement', 'incertain', 'débat', 'controverse']
        }
        
    def detect_conflicts(self, results: List[SourceResult], query: str) -> List[ConflictDetection]:
        """Détecter les conflits entre les résultats de sources"""
        conflicts = []
        
        # Détecter les contradictions
        contradictions = self._detect_contradictions(results)
        conflicts.extend(contradictions)
        
        # Détecter les incohérences
        inconsistencies = self._detect_inconsistencies(results)
        conflicts.extend(inconsistencies)
        
        # Détecter les informations obsolètes
        outdated = self._detect_outdated_info(results)
        conflicts.extend(outdated)
        
        # Détecter les doublons
        duplicates = self._detect_duplicates(results)
        conflicts.extend(duplicates)
        
        # Détecter les biais
        biases = self._detect_bias(results)
        conflicts.extend(biases)
        
        return conflicts
    
    def _detect_contradictions(self, results: List[SourceResult]) -> List[ConflictDetection]:
        """Détecter les contradictions directes"""
        conflicts = []
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                contradiction_score = self._calculate_contradiction_score(result1.content, result2.content)
                
                if contradiction_score > 0.7:  # Seuil de contradiction
                    conflict = ConflictDetection(
                        conflict_type=ConflictType.CONTRADICTION,
                        sources_involved=[result1.source_info.id, result2.source_info.id],
                        severity=contradiction_score,
                        description=f"Contradiction détectée entre {result1.source_info.name} et {result2.source_info.name}",
                        resolution_suggestion=self._suggest_contradiction_resolution(result1, result2),
                        confidence=0.8
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _calculate_contradiction_score(self, content1: str, content2: str) -> float:
        """Calculer le score de contradiction entre deux contenus"""
        # Analyser la polarité des contenus
        polarity1 = self._analyze_polarity(content1)
        polarity2 = self._analyze_polarity(content2)
        
        # Si les polarités sont opposées, c'est une contradiction
        if (polarity1 > 0.3 and polarity2 < -0.3) or (polarity1 < -0.3 and polarity2 > 0.3):
            return abs(polarity1 - polarity2)
        
        return 0.0
    
    def _analyze_polarity(self, content: str) -> float:
        """Analyser la polarité d'un contenu (-1 à 1)"""
        content_lower = content.lower()
        
        positive_count = sum(1 for word in self.contradiction_keywords['positive'] if word in content_lower)
        negative_count = sum(1 for word in self.contradiction_keywords['negative'] if word in content_lower)
        uncertainty_count = sum(1 for word in self.contradiction_keywords['uncertainty'] if word in content_lower)
        
        total_words = len(content_lower.split())
        if total_words == 0:
            return 0.0
        
        # Calculer la polarité
        polarity = (positive_count - negative_count) / total_words
        
        # Réduire la confiance si beaucoup d'incertitude
        uncertainty_factor = 1 - (uncertainty_count / total_words)
        
        return polarity * uncertainty_factor
    
    def _detect_inconsistencies(self, results: List[SourceResult]) -> List[ConflictDetection]:
        """Détecter les incohérences mineures"""
        conflicts = []
        
        # Analyser les valeurs numériques pour les incohérences
        numeric_values = self._extract_numeric_values(results)
        
        for metric, values in numeric_values.items():
            if len(values) > 1:
                variance = statistics.variance([v['value'] for v in values])
                mean_val = statistics.mean([v['value'] for v in values])
                
                # Coefficient de variation élevé indique une incohérence
                if mean_val > 0 and (variance / mean_val) > 0.5:
                    sources_involved = [v['source'] for v in values]
                    
                    conflict = ConflictDetection(
                        conflict_type=ConflictType.INCONSISTENCY,
                        sources_involved=sources_involved,
                        severity=min(variance / mean_val, 1.0),
                        description=f"Incohérence dans les valeurs de {metric}",
                        resolution_suggestion="Vérifier les méthodologies et unités de mesure",
                        confidence=0.7
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _extract_numeric_values(self, results: List[SourceResult]) -> Dict[str, List[Dict]]:
        """Extraire les valeurs numériques des résultats"""
        import re
        
        numeric_patterns = {
            'percentage': r'(\d+(?:\.\d+)?)\s*%',
            'dosage': r'(\d+(?:\.\d+)?)\s*(?:mg|g|ml|l)',
            'duration': r'(\d+(?:\.\d+)?)\s*(?:jour|semaine|mois|année)s?',
            'efficacy': r'efficacité.*?(\d+(?:\.\d+)?)\s*%'
        }
        
        extracted_values = defaultdict(list)
        
        for result in results:
            content = result.content.lower()
            
            for metric, pattern in numeric_patterns.items():
                matches = re.findall(pattern, content)
                for match in matches:
                    extracted_values[metric].append({
                        'value': float(match),
                        'source': result.source_info.id,
                        'content': content
                    })
        
        return extracted_values
    
    def _detect_outdated_info(self, results: List[SourceResult]) -> List[ConflictDetection]:
        """Détecter les informations obsolètes"""
        conflicts = []
        current_time = datetime.now()
        
        for result in results:
            # Calculer l'âge de l'information
            age_days = (current_time - result.timestamp).days
            
            # Seuils d'obsolescence par type de source
            obsolescence_thresholds = {
                SourceType.CLINICAL_GUIDELINE: 365 * 3,  # 3 ans
                SourceType.RESEARCH_PAPER: 365 * 5,      # 5 ans
                SourceType.MEDICAL_DATABASE: 365 * 2,    # 2 ans
                SourceType.REAL_TIME_DATA: 30,           # 30 jours
                SourceType.EXPERT_SYSTEM: 365,          # 1 an
            }
            
            threshold = obsolescence_thresholds.get(result.source_info.type, 365 * 2)
            
            if age_days > threshold:
                severity = min(age_days / threshold - 1, 1.0)
                
                conflict = ConflictDetection(
                    conflict_type=ConflictType.OUTDATED,
                    sources_involved=[result.source_info.id],
                    severity=severity,
                    description=f"Information potentiellement obsolète ({age_days} jours)",
                    resolution_suggestion="Rechercher des sources plus récentes",
                    confidence=0.6
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _detect_duplicates(self, results: List[SourceResult]) -> List[ConflictDetection]:
        """Détecter les doublons"""
        conflicts = []
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                similarity = SequenceMatcher(None, result1.content, result2.content).ratio()
                
                if similarity > 0.8:  # Seuil de similarité pour duplication
                    conflict = ConflictDetection(
                        conflict_type=ConflictType.DUPLICATE,
                        sources_involved=[result1.source_info.id, result2.source_info.id],
                        severity=similarity,
                        description=f"Contenu dupliqué détecté (similarité: {similarity:.1%})",
                        resolution_suggestion="Conserver la source la plus fiable",
                        confidence=0.9
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _detect_bias(self, results: List[SourceResult]) -> List[ConflictDetection]:
        """Détecter les biais potentiels"""
        conflicts = []
        
        for result in results:
            bias_score = result.source_info.bias_score
            
            if bias_score > 0.6:  # Seuil de biais
                conflict = ConflictDetection(
                    conflict_type=ConflictType.BIAS,
                    sources_involved=[result.source_info.id],
                    severity=bias_score,
                    description=f"Biais potentiel détecté (score: {bias_score:.2f})",
                    resolution_suggestion="Croiser avec des sources neutres",
                    confidence=0.7
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _suggest_contradiction_resolution(self, result1: SourceResult, result2: SourceResult) -> str:
        """Suggérer une résolution pour une contradiction"""
        # Comparer l'autorité des sources
        if result1.source_info.authority_score > result2.source_info.authority_score + 0.2:
            return f"Privilégier {result1.source_info.name} (autorité supérieure)"
        elif result2.source_info.authority_score > result1.source_info.authority_score + 0.2:
            return f"Privilégier {result2.source_info.name} (autorité supérieure)"
        
        # Comparer la récence
        if result1.source_info.recency_score > result2.source_info.recency_score + 0.2:
            return f"Privilégier {result1.source_info.name} (plus récent)"
        elif result2.source_info.recency_score > result1.source_info.recency_score + 0.2:
            return f"Privilégier {result2.source_info.name} (plus récent)"
        
        return "Rechercher des sources additionnelles pour arbitrer"

class SourceWeightCalculator:
    """Calculateur de poids pour les sources"""
    
    def __init__(self):
        self.base_weights = {
            SourceType.CLINICAL_GUIDELINE: 0.9,
            SourceType.MEDICAL_DATABASE: 0.8,
            SourceType.RESEARCH_PAPER: 0.7,
            SourceType.EXPERT_SYSTEM: 0.6,
            SourceType.KNOWLEDGE_BASE: 0.5,
            SourceType.REAL_TIME_DATA: 0.4,
            SourceType.USER_GENERATED: 0.2
        }
    
    def calculate_weights(self, results: List[SourceResult], 
                         conflicts: List[ConflictDetection],
                         query_context: Dict[str, Any] = None) -> Dict[str, float]:
        """Calculer les poids dynamiques pour chaque source"""
        query_context = query_context or {}
        weights = {}
        
        for result in results:
            # Poids de base selon le type de source
            base_weight = self.base_weights.get(result.source_info.type, 0.5)
            
            # Facteurs d'ajustement
            authority_factor = result.source_info.authority_score
            reliability_factor = result.source_info.reliability_score
            recency_factor = result.source_info.recency_score
            bias_penalty = 1 - result.source_info.bias_score
            relevance_factor = result.relevance_score
            evidence_factor = result.evidence_quality
            
            # Pénalités pour conflits
            conflict_penalty = self._calculate_conflict_penalty(result.source_info.id, conflicts)
            
            # Bonus contextuel
            context_bonus = self._calculate_context_bonus(result, query_context)
            
            # Calcul du poids final
            final_weight = (
                base_weight * 
                authority_factor * 
                reliability_factor * 
                recency_factor * 
                bias_penalty * 
                relevance_factor * 
                evidence_factor * 
                conflict_penalty * 
                context_bonus
            )
            
            weights[result.source_info.id] = max(0.01, min(1.0, final_weight))
        
        # Normaliser les poids
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def _calculate_conflict_penalty(self, source_id: str, conflicts: List[ConflictDetection]) -> float:
        """Calculer la pénalité due aux conflits"""
        penalty = 1.0
        
        for conflict in conflicts:
            if source_id in conflict.sources_involved:
                # Pénalité basée sur la sévérité et le type de conflit
                conflict_penalties = {
                    ConflictType.CONTRADICTION: 0.5,
                    ConflictType.INCONSISTENCY: 0.8,
                    ConflictType.OUTDATED: 0.7,
                    ConflictType.DUPLICATE: 0.9,
                    ConflictType.BIAS: 0.6
                }
                
                base_penalty = conflict_penalties.get(conflict.conflict_type, 0.8)
                severity_penalty = 1 - (conflict.severity * (1 - base_penalty))
                penalty *= severity_penalty
        
        return penalty
    
    def _calculate_context_bonus(self, result: SourceResult, query_context: Dict[str, Any]) -> float:
        """Calculer le bonus contextuel"""
        bonus = 1.0
        
        # Bonus pour urgence
        if query_context.get('urgency') == 'high':
            if result.source_info.type in [SourceType.CLINICAL_GUIDELINE, SourceType.EXPERT_SYSTEM]:
                bonus *= 1.2
        
        # Bonus pour recherche
        if query_context.get('context_type') == 'research':
            if result.source_info.type == SourceType.RESEARCH_PAPER:
                bonus *= 1.3
        
        # Bonus pour domaine de spécialité
        specialty = query_context.get('medical_specialty')
        if specialty and specialty in result.source_info.coverage_domains:
            bonus *= 1.1
        
        return bonus

class MultisourceFusion:
    """Système principal de fusion multi-sources"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'fusion_strategy': FusionStrategy.HYBRID,
            'min_consensus_threshold': 0.6,
            'max_sources_per_fusion': 10,
            'conflict_resolution_enabled': True,
            'quality_threshold': 0.5,
            'enable_provenance_tracking': True
        }
        
        self.conflict_detector = ConflictDetector()
        self.weight_calculator = SourceWeightCalculator()
        self.metrics = FusionMetrics()
        self.fusion_history = []
        
        logger.info("MultisourceFusion initialisé")
    
    def fuse_sources(self, results: List[SourceResult], query: str, 
                    query_context: Dict[str, Any] = None) -> FusionResult:
        """Fusionner les résultats de sources multiples"""
        start_time = time.time()
        query_context = query_context or {}
        
        # Filtrer les résultats de qualité insuffisante
        filtered_results = [r for r in results if r.confidence >= self.config['quality_threshold']]
        
        if not filtered_results:
            return self._create_empty_fusion_result("Aucun résultat de qualité suffisante")
        
        # Limiter le nombre de sources
        if len(filtered_results) > self.config['max_sources_per_fusion']:
            # Trier par qualité et garder les meilleures
            filtered_results = sorted(filtered_results, 
                                    key=lambda r: r.confidence * r.relevance_score * r.evidence_quality, 
                                    reverse=True)[:self.config['max_sources_per_fusion']]
        
        # Détecter les conflits
        conflicts = self.conflict_detector.detect_conflicts(filtered_results, query)
        
        # Calculer les poids des sources
        source_weights = self.weight_calculator.calculate_weights(filtered_results, conflicts, query_context)
        
        # Appliquer la stratégie de fusion
        fusion_result = self._apply_fusion_strategy(filtered_results, source_weights, conflicts, query, query_context)
        
        # Calculer les métriques de qualité
        quality_metrics = self._calculate_quality_metrics(filtered_results, fusion_result, conflicts)
        fusion_result.quality_metrics = quality_metrics
        
        # Traçabilité
        if self.config['enable_provenance_tracking']:
            fusion_result.provenance = self._create_provenance_record(filtered_results, conflicts, query_context)
        
        # Mettre à jour les métriques
        processing_time = (time.time() - start_time) * 1000
        self._update_metrics(fusion_result, processing_time)
        
        # Enregistrer dans l'historique
        self.fusion_history.append({
            'query': query,
            'timestamp': datetime.now(),
            'sources_count': len(filtered_results),
            'conflicts_count': len(conflicts),
            'consensus_level': fusion_result.consensus_level,
            'confidence': fusion_result.confidence
        })
        
        return fusion_result
    
    def _apply_fusion_strategy(self, results: List[SourceResult], weights: Dict[str, float],
                              conflicts: List[ConflictDetection], query: str, 
                              query_context: Dict[str, Any]) -> FusionResult:
        """Appliquer la stratégie de fusion choisie"""
        strategy = self.config['fusion_strategy']
        
        if strategy == FusionStrategy.WEIGHTED_AVERAGE:
            return self._weighted_average_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.CONSENSUS_BASED:
            return self._consensus_based_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.AUTHORITY_BASED:
            return self._authority_based_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.EVIDENCE_BASED:
            return self._evidence_based_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.TEMPORAL_BASED:
            return self._temporal_based_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.HYBRID:
            return self._hybrid_fusion(results, weights, conflicts, query_context)
        else:
            return self._weighted_average_fusion(results, weights, conflicts)
    
    def _weighted_average_fusion(self, results: List[SourceResult], weights: Dict[str, float],
                                conflicts: List[ConflictDetection]) -> FusionResult:
        """Fusion par moyenne pondérée"""
        # Combiner les contenus avec pondération
        content_segments = []
        total_weight = 0
        confidence_sum = 0
        
        for result in results:
            weight = weights.get(result.source_info.id, 0)
            if weight > 0:
                content_segments.append({
                    'content': result.content,
                    'weight': weight,
                    'source': result.source_info.name
                })
                total_weight += weight
                confidence_sum += result.confidence * weight
        
        # Créer le contenu fusionné
        fused_content = self._merge_content_segments(content_segments)
        
        # Calculer la confiance moyenne pondérée
        avg_confidence = confidence_sum / total_weight if total_weight > 0 else 0
        
        # Calculer le niveau de consensus
        consensus_level = self._calculate_consensus_level(results, weights)
        
        return FusionResult(
            fused_content=fused_content,
            confidence=avg_confidence,
            consensus_level=consensus_level,
            sources_used=[r.source_info.id for r in results],
            source_weights=weights,
            conflicts_detected=conflicts,
            fusion_strategy=FusionStrategy.WEIGHTED_AVERAGE,
            quality_metrics={},
            provenance={}
        )
    
    def _consensus_based_fusion(self, results: List[SourceResult], weights: Dict[str, float],
                               conflicts: List[ConflictDetection]) -> FusionResult:
        """Fusion basée sur le consensus"""
        # Identifier les points de consensus
        consensus_points = self._identify_consensus_points(results)
        
        # Construire le contenu basé sur le consensus
        fused_content = self._build_consensus_content(consensus_points, results, weights)
        
        # Calculer la confiance basée sur le consensus
        consensus_level = len(consensus_points) / max(len(results), 1)
        confidence = consensus_level * 0.9  # Légèrement réduite car basée sur consensus
        
        return FusionResult(
            fused_content=fused_content,
            confidence=confidence,
            consensus_level=consensus_level,
            sources_used=[r.source_info.id for r in results],
            source_weights=weights,
            conflicts_detected=conflicts,
            fusion_strategy=FusionStrategy.CONSENSUS_BASED,
            quality_metrics={},
            provenance={}
        )
    
    def _authority_based_fusion(self, results: List[SourceResult], weights: Dict[str, float],
                               conflicts: List[ConflictDetection]) -> FusionResult:
        """Fusion basée sur l'autorité des sources"""
        # Trier par autorité
        sorted_results = sorted(results, key=lambda r: r.source_info.authority_score, reverse=True)
        
        # Privilégier les sources les plus autoritaires
        primary_result = sorted_results[0]
        supporting_results = sorted_results[1:3]  # 2 sources de support max
        
        # Construire le contenu en privilégiant l'autorité
        fused_content = primary_result.content
        
        # Ajouter des informations complémentaires des sources de support
        for result in supporting_results:
            if result.source_info.authority_score > 0.7:
                additional_info = self._extract_complementary_info(primary_result.content, result.content)
                if additional_info:
                    fused_content += f"\n\nInformation complémentaire ({result.source_info.name}): {additional_info}"
        
        confidence = primary_result.confidence * primary_result.source_info.authority_score
        consensus_level = self._calculate_consensus_level(results, weights)
        
        return FusionResult(
            fused_content=fused_content,
            confidence=confidence,
            consensus_level=consensus_level,
            sources_used=[r.source_info.id for r in [primary_result] + supporting_results],
            source_weights=weights,
            conflicts_detected=conflicts,
            fusion_strategy=FusionStrategy.AUTHORITY_BASED,
            quality_metrics={},
            provenance={}
        )
    
    def _evidence_based_fusion(self, results: List[SourceResult], weights: Dict[str, float],
                              conflicts: List[ConflictDetection]) -> FusionResult:
        """Fusion basée sur la qualité de l'évidence"""
        # Trier par qualité de l'évidence
        sorted_results = sorted(results, key=lambda r: r.evidence_quality, reverse=True)
        
        # Construire le contenu en privilégiant l'évidence
        evidence_levels = defaultdict(list)
        
        for result in sorted_results:
            evidence_level = result.metadata.get('evidence_level', 'Unknown')
            evidence_levels[evidence_level].append(result)
        
        # Commencer par les niveaux d'évidence les plus élevés
        fused_content = ""
        confidence_sum = 0
        weight_sum = 0
        
        for level in ['I', 'II', 'III', 'IV', 'V', 'Unknown']:
            if level in evidence_levels:
                level_results = evidence_levels[level]
                if level_results:
                    best_result = max(level_results, key=lambda r: r.evidence_quality)
                    
                    if fused_content:
                        fused_content += f"\n\nÉvidence niveau {level}: "
                    fused_content += best_result.content
                    
                    weight = weights.get(best_result.source_info.id, 0)
                    confidence_sum += best_result.confidence * weight
                    weight_sum += weight
        
        confidence = confidence_sum / weight_sum if weight_sum > 0 else 0
        consensus_level = self._calculate_consensus_level(results, weights)
        
        return FusionResult(
            fused_content=fused_content,
            confidence=confidence,
            consensus_level=consensus_level,
            sources_used=[r.source_info.id for r in sorted_results],
            source_weights=weights,
            conflicts_detected=conflicts,
            fusion_strategy=FusionStrategy.EVIDENCE_BASED,
            quality_metrics={},
            provenance={}
        )
    
    def _temporal_based_fusion(self, results: List[SourceResult], weights: Dict[str, float],
                              conflicts: List[ConflictDetection]) -> FusionResult:
        """Fusion basée sur la temporalité"""
        # Trier par récence
        sorted_results = sorted(results, key=lambda r: r.timestamp, reverse=True)
        
        # Privilégier les informations les plus récentes
        recent_results = sorted_results[:3]  # 3 sources les plus récentes
        
        fused_content = ""
        confidence_sum = 0
        weight_sum = 0
        
        for i, result in enumerate(recent_results):
            # Pondération décroissante avec l'âge
            temporal_weight = 1.0 / (i + 1)
            source_weight = weights.get(result.source_info.id, 0)
            combined_weight = temporal_weight * source_weight
            
            if i == 0:
                fused_content = result.content
            else:
                additional_info = self._extract_complementary_info(fused_content, result.content)
                if additional_info:
                    age_days = (datetime.now() - result.timestamp).days
                    fused_content += f"\n\nMise à jour ({age_days} jours): {additional_info}"
            
            confidence_sum += result.confidence * combined_weight
            weight_sum += combined_weight
        
        confidence = confidence_sum / weight_sum if weight_sum > 0 else 0
        consensus_level = self._calculate_consensus_level(results, weights)
        
        return FusionResult(
            fused_content=fused_content,
            confidence=confidence,
            consensus_level=consensus_level,
            sources_used=[r.source_info.id for r in recent_results],
            source_weights=weights,
            conflicts_detected=conflicts,
            fusion_strategy=FusionStrategy.TEMPORAL_BASED,
            quality_metrics={},
            provenance={}
        )
    
    def _hybrid_fusion(self, results: List[SourceResult], weights: Dict[str, float],
                      conflicts: List[ConflictDetection], query_context: Dict[str, Any]) -> FusionResult:
        """Fusion hybride combinant plusieurs stratégies"""
        # Analyser le contexte pour choisir la meilleure approche
        context_type = query_context.get('context_type', 'general')
        urgency = query_context.get('urgency', 'normal')
        
        # Choisir la stratégie principale selon le contexte
        if urgency == 'high':
            primary_strategy = FusionStrategy.AUTHORITY_BASED
        elif context_type == 'research':
            primary_strategy = FusionStrategy.EVIDENCE_BASED
        elif len(conflicts) > 0:
            primary_strategy = FusionStrategy.CONSENSUS_BASED
        else:
            primary_strategy = FusionStrategy.WEIGHTED_AVERAGE
        
        # Appliquer la stratégie principale
        primary_result = self._apply_fusion_strategy_specific(results, weights, conflicts, primary_strategy)
        
        # Enrichir avec des informations d'autres stratégies
        if primary_strategy != FusionStrategy.TEMPORAL_BASED:
            temporal_info = self._extract_temporal_insights(results)
            if temporal_info:
                primary_result.fused_content += f"\n\nÉvolution temporelle: {temporal_info}"
        
        if primary_strategy != FusionStrategy.CONSENSUS_BASED and len(results) > 2:
            consensus_info = self._extract_consensus_insights(results)
            if consensus_info:
                primary_result.fused_content += f"\n\nConsensus: {consensus_info}"
        
        primary_result.fusion_strategy = FusionStrategy.HYBRID
        return primary_result
    
    def _apply_fusion_strategy_specific(self, results: List[SourceResult], weights: Dict[str, float],
                                       conflicts: List[ConflictDetection], strategy: FusionStrategy) -> FusionResult:
        """Appliquer une stratégie spécifique"""
        if strategy == FusionStrategy.AUTHORITY_BASED:
            return self._authority_based_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.EVIDENCE_BASED:
            return self._evidence_based_fusion(results, weights, conflicts)
        elif strategy == FusionStrategy.CONSENSUS_BASED:
            return self._consensus_based_fusion(results, weights, conflicts)
        else:
            return self._weighted_average_fusion(results, weights, conflicts)
    
    def _merge_content_segments(self, segments: List[Dict]) -> str:
        """Fusionner les segments de contenu"""
        if not segments:
            return ""
        
        # Trier par poids décroissant
        sorted_segments = sorted(segments, key=lambda s: s['weight'], reverse=True)
        
        # Commencer par le segment le plus important
        merged_content = sorted_segments[0]['content']
        
        # Ajouter les autres segments en évitant la redondance
        for segment in sorted_segments[1:]:
            additional_info = self._extract_complementary_info(merged_content, segment['content'])
            if additional_info:
                merged_content += f"\n\nSource {segment['source']}: {additional_info}"
        
        return merged_content
    
    def _extract_complementary_info(self, main_content: str, additional_content: str) -> str:
        """Extraire les informations complémentaires non redondantes"""
        # Simplification: chercher des phrases uniques dans le contenu additionnel
        main_sentences = set(main_content.split('.'))
        additional_sentences = additional_content.split('.')
        
        unique_sentences = []
        for sentence in additional_sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 20:  # Ignorer les phrases trop courtes
                # Vérifier si la phrase apporte une information nouvelle
                is_unique = True
                for main_sentence in main_sentences:
                    similarity = SequenceMatcher(None, sentence.lower(), main_sentence.lower()).ratio()
                    if similarity > 0.7:
                        is_unique = False
                        break
                
                if is_unique:
                    unique_sentences.append(sentence)
        
        return '. '.join(unique_sentences[:2])  # Limiter à 2 phrases
    
    def _identify_consensus_points(self, results: List[SourceResult]) -> List[str]:
        """Identifier les points de consensus entre les sources"""
        # Extraire les concepts clés de chaque source
        all_concepts = []
        for result in results:
            concepts = self._extract_key_concepts(result.content)
            all_concepts.append(concepts)
        
        # Trouver les concepts présents dans au moins 50% des sources
        concept_counts = Counter()
        for concepts in all_concepts:
            for concept in concepts:
                concept_counts[concept] += 1
        
        min_sources = max(2, len(results) // 2)
        consensus_points = [concept for concept, count in concept_counts.items() 
                           if count >= min_sources]
        
        return consensus_points
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extraire les concepts clés d'un contenu"""
        # Simplification: extraire les mots médicaux importants
        medical_keywords = [
            'traitement', 'diagnostic', 'symptôme', 'médicament', 'posologie',
            'efficacité', 'effet', 'indication', 'contre-indication', 'dosage',
            'paludisme', 'malaria', 'artemether', 'lumefantrine', 'tuberculose',
            'vih', 'pneumonie', 'hypertension', 'diabète'
        ]
        
        content_lower = content.lower()
        found_concepts = []
        
        for keyword in medical_keywords:
            if keyword in content_lower:
                found_concepts.append(keyword)
        
        return found_concepts
    
    def _build_consensus_content(self, consensus_points: List[str], 
                                results: List[SourceResult], weights: Dict[str, float]) -> str:
        """Construire le contenu basé sur le consensus"""
        if not consensus_points:
            return "Aucun consensus clair identifié entre les sources."
        
        content_parts = []
        content_parts.append(f"Consensus identifié sur {len(consensus_points)} points clés:")
        
        for concept in consensus_points[:5]:  # Limiter à 5 concepts
            # Trouver la meilleure explication pour ce concept
            best_explanation = self._find_best_explanation(concept, results, weights)
            if best_explanation:
                content_parts.append(f"\n• {concept.title()}: {best_explanation}")
        
        return '\n'.join(content_parts)
    
    def _find_best_explanation(self, concept: str, results: List[SourceResult], 
                              weights: Dict[str, float]) -> str:
        """Trouver la meilleure explication pour un concept"""
        explanations = []
        
        for result in results:
            if concept.lower() in result.content.lower():
                # Extraire la phrase contenant le concept
                sentences = result.content.split('.')
                for sentence in sentences:
                    if concept.lower() in sentence.lower():
                        weight = weights.get(result.source_info.id, 0)
                        explanations.append({
                            'text': sentence.strip(),
                            'weight': weight,
                            'quality': result.evidence_quality
                        })
                        break
        
        if explanations:
            # Choisir la meilleure explication
            best = max(explanations, key=lambda e: e['weight'] * e['quality'])
            return best['text']
        
        return ""
    
    def _calculate_consensus_level(self, results: List[SourceResult], weights: Dict[str, float]) -> float:
        """Calculer le niveau de consensus"""
        if len(results) < 2:
            return 1.0
        
        # Calculer la similarité moyenne entre toutes les paires
        similarities = []
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                similarity = SequenceMatcher(None, result1.content, result2.content).ratio()
                weight1 = weights.get(result1.source_info.id, 0)
                weight2 = weights.get(result2.source_info.id, 0)
                weighted_similarity = similarity * (weight1 + weight2) / 2
                similarities.append(weighted_similarity)
        
        return statistics.mean(similarities) if similarities else 0.0
    
    def _extract_temporal_insights(self, results: List[SourceResult]) -> str:
        """Extraire des insights temporels"""
        if len(results) < 2:
            return ""
        
        # Analyser l'évolution temporelle
        sorted_results = sorted(results, key=lambda r: r.timestamp)
        oldest = sorted_results[0]
        newest = sorted_results[-1]
        
        time_span = (newest.timestamp - oldest.timestamp).days
        
        if time_span > 365:  # Plus d'un an
            return f"Évolution sur {time_span} jours: informations mises à jour régulièrement"
        elif time_span > 30:  # Plus d'un mois
            return f"Informations récentes ({time_span} jours)"
        else:
            return "Informations très récentes"
    
    def _extract_consensus_insights(self, results: List[SourceResult]) -> str:
        """Extraire des insights de consensus"""
        consensus_points = self._identify_consensus_points(results)
        
        if len(consensus_points) >= len(results) * 0.7:  # 70% de consensus
            return f"Fort consensus sur {len(consensus_points)} points"
        elif len(consensus_points) >= len(results) * 0.5:  # 50% de consensus
            return f"Consensus modéré sur {len(consensus_points)} points"
        else:
            return "Consensus limité, sources divergentes"
    
    def _calculate_quality_metrics(self, results: List[SourceResult], 
                                  fusion_result: FusionResult, 
                                  conflicts: List[ConflictDetection]) -> Dict[str, float]:
        """Calculer les métriques de qualité"""
        metrics = {}
        
        # Diversité des sources
        source_types = set(r.source_info.type for r in results)
        metrics['source_diversity'] = len(source_types) / len(SourceType)
        
        # Qualité moyenne des sources
        avg_authority = statistics.mean([r.source_info.authority_score for r in results])
        avg_reliability = statistics.mean([r.source_info.reliability_score for r in results])
        metrics['avg_source_quality'] = (avg_authority + avg_reliability) / 2
        
        # Impact des conflits
        conflict_severity = statistics.mean([c.severity for c in conflicts]) if conflicts else 0
        metrics['conflict_impact'] = 1 - conflict_severity
        
        # Cohérence du contenu fusionné
        metrics['content_coherence'] = fusion_result.consensus_level
        
        # Score de qualité global
        metrics['overall_quality'] = (
            metrics['source_diversity'] * 0.2 +
            metrics['avg_source_quality'] * 0.4 +
            metrics['conflict_impact'] * 0.2 +
            metrics['content_coherence'] * 0.2
        )
        
        return metrics
    
    def _create_provenance_record(self, results: List[SourceResult], 
                                 conflicts: List[ConflictDetection],
                                 query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Créer un enregistrement de traçabilité"""
        return {
            'fusion_timestamp': datetime.now().isoformat(),
            'sources_metadata': [
                {
                    'id': r.source_info.id,
                    'name': r.source_info.name,
                    'type': r.source_info.type.value,
                    'authority_score': r.source_info.authority_score,
                    'reliability_score': r.source_info.reliability_score,
                    'timestamp': r.timestamp.isoformat()
                } for r in results
            ],
            'conflicts_summary': [
                {
                    'type': c.conflict_type.value,
                    'severity': c.severity,
                    'sources_involved': c.sources_involved
                } for c in conflicts
            ],
            'query_context': query_context,
            'fusion_strategy': self.config['fusion_strategy'].value
        }
    
    def _create_empty_fusion_result(self, reason: str) -> FusionResult:
        """Créer un résultat de fusion vide"""
        return FusionResult(
            fused_content=f"Fusion impossible: {reason}",
            confidence=0.0,
            consensus_level=0.0,
            sources_used=[],
            source_weights={},
            conflicts_detected=[],
            fusion_strategy=self.config['fusion_strategy'],
            quality_metrics={'overall_quality': 0.0},
            provenance={}
        )
    
    def _update_metrics(self, fusion_result: FusionResult, processing_time: float):
        """Mettre à jour les métriques du système"""
        self.metrics.total_fusions += 1
        
        # Moyennes mobiles
        total = self.metrics.total_fusions
        self.metrics.avg_consensus_level = (
            (self.metrics.avg_consensus_level * (total - 1) + fusion_result.consensus_level) / total
        )
        self.metrics.avg_confidence = (
            (self.metrics.avg_confidence * (total - 1) + fusion_result.confidence) / total
        )
        self.metrics.fusion_latency_ms = (
            (self.metrics.fusion_latency_ms * (total - 1) + processing_time) / total
        )
        
        # Compteurs
        self.metrics.conflicts_detected += len(fusion_result.conflicts_detected)
        
        # Utilisation des sources
        for source_id in fusion_result.sources_used:
            self.metrics.source_utilization[source_id] = (
                self.metrics.source_utilization.get(source_id, 0) + 1
            )
    
    def get_metrics(self) -> FusionMetrics:
        """Obtenir les métriques du système"""
        return self.metrics
    
    def export_data(self, filename: str = "multisource_fusion_export.json"):
        """Exporter les données du système"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'fusion_strategy': self.config['fusion_strategy'].value,
                    'min_consensus_threshold': self.config['min_consensus_threshold'],
                    'conflict_resolution_enabled': self.config['conflict_resolution_enabled']
                },
                'metrics': asdict(self.metrics),
                'fusion_history': self.fusion_history[-100:],  # 100 dernières fusions
                'source_utilization_summary': {
                    'total_sources': len(self.metrics.source_utilization),
                    'most_used_sources': sorted(self.metrics.source_utilization.items(), 
                                               key=lambda x: x[1], reverse=True)[:10]
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Données exportées vers {filename}")
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")

def main():
    """Fonction principale de démonstration"""
    print("🔗 Multisource Fusion - Objectif 15")
    print("Fusion avancée de sources multiples")
    print("=" * 45)
    
    # Configuration du système
    config = {
        'fusion_strategy': FusionStrategy.HYBRID,
        'min_consensus_threshold': 0.6,
        'max_sources_per_fusion': 8,
        'conflict_resolution_enabled': True,
        'quality_threshold': 0.4,
        'enable_provenance_tracking': True
    }
    
    fusion_system = MultisourceFusion(config)
    
    # Créer des sources de test
    sources = [
        SourceInfo(
            id="who_guidelines",
            name="OMS Guidelines",
            type=SourceType.CLINICAL_GUIDELINE,
            authority_score=0.95,
            reliability_score=0.9,
            recency_score=0.8,
            bias_score=0.1,
            coverage_domains=["paludisme", "maladies_tropicales"]
        ),
        SourceInfo(
            id="pubmed_research",
            name="PubMed Research",
            type=SourceType.RESEARCH_PAPER,
            authority_score=0.8,
            reliability_score=0.85,
            recency_score=0.9,
            bias_score=0.2,
            coverage_domains=["paludisme", "pharmacologie"]
        ),
        SourceInfo(
            id="cochrane_review",
            name="Cochrane Review",
            type=SourceType.MEDICAL_DATABASE,
            authority_score=0.9,
            reliability_score=0.95,
            recency_score=0.7,
            bias_score=0.1,
            coverage_domains=["evidence_based_medicine"]
        ),
        SourceInfo(
            id="expert_system",
            name="Expert Medical System",
            type=SourceType.EXPERT_SYSTEM,
            authority_score=0.7,
            reliability_score=0.8,
            recency_score=0.95,
            bias_score=0.3,
            coverage_domains=["diagnostic", "traitement"]
        ),
        SourceInfo(
            id="outdated_source",
            name="Source Obsolète",
            type=SourceType.RESEARCH_PAPER,
            authority_score=0.6,
            reliability_score=0.7,
            recency_score=0.2,  # Très ancien
            bias_score=0.4,
            coverage_domains=["paludisme"]
        )
    ]
    
    # Créer des résultats de test avec des conflits potentiels
    test_results = [
        SourceResult(
            source_info=sources[0],
            content="L'artemether-lumefantrine est le traitement de première ligne pour le paludisme non compliqué chez l'enfant. Posologie: 20mg/120mg deux fois par jour pendant 3 jours. Efficacité: 95% de guérison.",
            confidence=0.9,
            relevance_score=0.95,
            evidence_quality=0.9,
            metadata={'evidence_level': 'I', 'study_type': 'guideline'}
        ),
        SourceResult(
            source_info=sources[1],
            content="Étude RCT sur artemether-lumefantrine: efficacité de 92% dans le traitement du paludisme pédiatrique. Posologie recommandée: 20mg/120mg BID pendant 3 jours. Effets secondaires mineurs observés.",
            confidence=0.85,
            relevance_score=0.9,
            evidence_quality=0.8,
            metadata={'evidence_level': 'II', 'study_type': 'rct'}
        ),
        SourceResult(
            source_info=sources[2],
            content="Méta-analyse de 15 études: artemether-lumefantrine montre une efficacité de 94% ± 3% pour le paludisme non compliqué. Recommandation forte (Grade A).",
            confidence=0.95,
            relevance_score=0.9,
            evidence_quality=0.95,
            metadata={'evidence_level': 'I', 'study_type': 'meta-analysis'}
        ),
        SourceResult(
            source_info=sources[3],
            content="Système expert recommande artemether-lumefantrine pour paludisme pédiatrique. Algorithme de diagnostic intégré. Surveillance des effets secondaires recommandée.",
            confidence=0.75,
            relevance_score=0.8,
            evidence_quality=0.7,
            metadata={'evidence_level': 'IV', 'study_type': 'expert_system'}
        ),
        SourceResult(
            source_info=sources[4],
            content="Ancienne étude: chloroquine reste efficace pour le paludisme. Résistance limitée observée. Traitement de choix économique.",  # Information obsolète/contradictoire
            confidence=0.6,
            relevance_score=0.7,
            evidence_quality=0.4,
            metadata={'evidence_level': 'III', 'study_type': 'cohort'},
            timestamp=datetime(2015, 1, 1)  # Très ancien
        )
    ]
    
    # Test de fusion avec différents contextes
    test_scenarios = [
        {
            'query': 'traitement paludisme enfant artemether-lumefantrine',
            'context': {'context_type': 'clinical', 'urgency': 'normal', 'medical_specialty': 'pediatrie'},
            'description': 'Contexte clinique normal'
        },
        {
            'query': 'efficacité artemether-lumefantrine méta-analyse',
            'context': {'context_type': 'research', 'urgency': 'low', 'medical_specialty': 'pharmacologie'},
            'description': 'Contexte recherche'
        },
        {
            'query': 'traitement urgent paludisme grave',
            'context': {'context_type': 'emergency', 'urgency': 'high', 'medical_specialty': 'urgences'},
            'description': 'Contexte urgence'
        }
    ]
    
    print("\n🔍 Test de fusion multi-sources...")
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n--- Scénario {i+1}: {scenario['description']} ---")
        print(f"Requête: {scenario['query']}")
        
        start_time = time.time()
        fusion_result = fusion_system.fuse_sources(test_results, scenario['query'], scenario['context'])
        fusion_time = (time.time() - start_time) * 1000
        
        print(f"⏱️ Temps de fusion: {fusion_time:.1f}ms")
        print(f"🎯 Confiance: {fusion_result.confidence:.1%}")
        print(f"🤝 Consensus: {fusion_result.consensus_level:.1%}")
        print(f"📊 Stratégie: {fusion_result.fusion_strategy.value}")
        print(f"🔗 Sources utilisées: {len(fusion_result.sources_used)}")
        print(f"⚠️ Conflits détectés: {len(fusion_result.conflicts_detected)}")
        
        # Afficher les conflits détectés
        if fusion_result.conflicts_detected:
            print("\n🚨 Conflits identifiés:")
            for conflict in fusion_result.conflicts_detected[:3]:  # Top 3
                print(f"  • {conflict.conflict_type.value}: {conflict.description}")
                print(f"    Sévérité: {conflict.severity:.1%} | Résolution: {conflict.resolution_suggestion}")
        
        # Afficher un extrait du contenu fusionné
        content_preview = fusion_result.fused_content[:200] + "..." if len(fusion_result.fused_content) > 200 else fusion_result.fused_content
        print(f"\n📄 Contenu fusionné (extrait):\n{content_preview}")
        
        # Métriques de qualité
        quality = fusion_result.quality_metrics.get('overall_quality', 0)
        print(f"\n✨ Qualité globale: {quality:.1%}")
    
    # Test de différentes stratégies
    print("\n🔄 Comparaison des stratégies de fusion...")
    test_query = "traitement paludisme artemether-lumefantrine"
    strategies = [FusionStrategy.WEIGHTED_AVERAGE, FusionStrategy.CONSENSUS_BASED, 
                 FusionStrategy.AUTHORITY_BASED, FusionStrategy.EVIDENCE_BASED]
    
    for strategy in strategies:
        fusion_system.config['fusion_strategy'] = strategy
        result = fusion_system.fuse_sources(test_results[:4], test_query)  # Exclure la source obsolète
        print(f"  {strategy.value}: Confiance {result.confidence:.1%}, Consensus {result.consensus_level:.1%}")
    
    # Métriques globales
    print("\n📈 Métriques du système:")
    metrics = fusion_system.get_metrics()
    print(f"  Fusions totales: {metrics.total_fusions}")
    print(f"  Confiance moyenne: {metrics.avg_confidence:.1%}")
    print(f"  Consensus moyen: {metrics.avg_consensus_level:.1%}")
    print(f"  Conflits détectés: {metrics.conflicts_detected}")
    print(f"  Latence moyenne: {metrics.fusion_latency_ms:.1f}ms")
    
    # Sources les plus utilisées
    if metrics.source_utilization:
        print("\n🏆 Sources les plus utilisées:")
        sorted_sources = sorted(metrics.source_utilization.items(), key=lambda x: x[1], reverse=True)
        for source_id, count in sorted_sources[:3]:
            print(f"  {source_id}: {count} utilisations")
    
    # Export des données
    print("\n💾 Export des données...")
    fusion_system.export_data()
    
    # Évaluation finale
    print("\n🎯 Évaluation finale:")
    avg_confidence = metrics.avg_confidence
    avg_consensus = metrics.avg_consensus_level
    avg_latency = metrics.fusion_latency_ms
    
    if avg_confidence >= 0.8 and avg_consensus >= 0.7 and avg_latency <= 100:
        print("✅ Objectif 15 ATTEINT - Fusion multi-sources excellente!")
    elif avg_confidence >= 0.7 and avg_consensus >= 0.6 and avg_latency <= 200:
        print("✅ Objectif 15 LARGEMENT ATTEINT - Performance très bonne!")
    else:
        print("⚠️ Objectif 15 PARTIELLEMENT ATTEINT - Optimisations possibles")
    
    print(f"🎯 Confiance moyenne: {avg_confidence:.1%}")
    print(f"🤝 Consensus moyen: {avg_consensus:.1%}")
    print(f"⚡ Latence moyenne: {avg_latency:.1f}ms")
    print(f"🔗 Système de fusion multi-sources opérationnel")
    print(f"🛡️ Détection et résolution de conflits activée")
    print(f"📊 {len(strategies)} stratégies de fusion disponibles")

if __name__ == "__main__":
    main()