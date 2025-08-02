#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Objectif 13: Système de pre-fetching prédictif
Créer système de pre-fetching prédictif pour optimiser les performances RAG

Fonctionnalités:
- Analyse des patterns de requêtes
- Prédiction des requêtes futures
- Pre-fetching intelligent
- Cache prédictif
- Optimisation des ressources
- Métriques de performance
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionModel(Enum):
    """Types de modèles de prédiction"""
    FREQUENCY = "frequency"  # Basé sur la fréquence
    SEQUENCE = "sequence"    # Basé sur les séquences
    TIME_BASED = "time_based" # Basé sur le temps
    SIMILARITY = "similarity" # Basé sur la similarité
    HYBRID = "hybrid"        # Modèle hybride

class PrefetchStrategy(Enum):
    """Stratégies de pre-fetching"""
    AGGRESSIVE = "aggressive"   # Pre-fetch agressif
    CONSERVATIVE = "conservative" # Pre-fetch conservateur
    ADAPTIVE = "adaptive"       # Pre-fetch adaptatif
    SMART = "smart"            # Pre-fetch intelligent

class PrefetchPriority(Enum):
    """Priorités de pre-fetching"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class QueryPattern:
    """Pattern de requête identifié"""
    pattern_id: str
    query_template: str
    frequency: int = 0
    last_seen: datetime = field(default_factory=datetime.now)
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    related_patterns: List[str] = field(default_factory=list)
    time_distribution: Dict[int, int] = field(default_factory=dict)  # heure -> fréquence

@dataclass
class PredictionResult:
    """Résultat de prédiction"""
    query: str
    confidence: float
    priority: PrefetchPriority
    estimated_time: datetime
    model_used: PredictionModel
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PrefetchRequest:
    """Requête de pre-fetching"""
    query: str
    priority: PrefetchPriority
    predicted_time: datetime
    confidence: float
    model_used: PredictionModel
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    cache_key: Optional[str] = None

@dataclass
class PrefetchMetrics:
    """Métriques de pre-fetching"""
    total_predictions: int = 0
    successful_prefetches: int = 0
    cache_hits_from_prefetch: int = 0
    total_queries: int = 0
    avg_prediction_accuracy: float = 0.0
    avg_prefetch_time: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    time_saved: float = 0.0  # temps économisé en ms

class QueryAnalyzer:
    """Analyseur de patterns de requêtes"""
    
    def __init__(self):
        self.query_history = deque(maxlen=10000)
        self.patterns = {}
        self.sequence_patterns = defaultdict(list)
        self.time_patterns = defaultdict(list)
        
    def add_query(self, query: str, timestamp: datetime, response_time: float, success: bool):
        """Ajouter une requête à l'historique"""
        self.query_history.append({
            'query': query,
            'timestamp': timestamp,
            'response_time': response_time,
            'success': success,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday()
        })
        
        # Analyser les patterns
        self._analyze_patterns(query, timestamp, response_time, success)
    
    def _analyze_patterns(self, query: str, timestamp: datetime, response_time: float, success: bool):
        """Analyser les patterns dans les requêtes"""
        # Pattern basé sur la fréquence
        pattern_id = self._extract_pattern(query)
        
        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = QueryPattern(
                pattern_id=pattern_id,
                query_template=self._generalize_query(query)
            )
        
        pattern = self.patterns[pattern_id]
        pattern.frequency += 1
        pattern.last_seen = timestamp
        pattern.avg_response_time = (
            (pattern.avg_response_time * (pattern.frequency - 1) + response_time) / pattern.frequency
        )
        pattern.success_rate = (
            (pattern.success_rate * (pattern.frequency - 1) + (1.0 if success else 0.0)) / pattern.frequency
        )
        
        # Distribution temporelle
        hour = timestamp.hour
        pattern.time_distribution[hour] = pattern.time_distribution.get(hour, 0) + 1
        
        # Patterns de séquence
        if len(self.query_history) >= 2:
            prev_query = self.query_history[-2]['query']
            prev_pattern = self._extract_pattern(prev_query)
            self.sequence_patterns[prev_pattern].append(pattern_id)
    
    def _extract_pattern(self, query: str) -> str:
        """Extraire un pattern d'une requête"""
        # Simplification: utiliser un hash des mots-clés principaux
        words = query.lower().split()
        # Garder seulement les mots médicaux importants
        medical_keywords = [w for w in words if len(w) > 3 and w.isalpha()]
        pattern = ' '.join(sorted(medical_keywords[:3]))  # Top 3 mots-clés
        return hashlib.md5(pattern.encode()).hexdigest()[:8]
    
    def _generalize_query(self, query: str) -> str:
        """Généraliser une requête en template"""
        # Remplacer les valeurs spécifiques par des placeholders
        import re
        generalized = query
        # Remplacer les nombres
        generalized = re.sub(r'\d+', '[NUMBER]', generalized)
        # Remplacer les dates
        generalized = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '[DATE]', generalized)
        return generalized
    
    def get_frequent_patterns(self, min_frequency: int = 3) -> List[QueryPattern]:
        """Obtenir les patterns fréquents"""
        return [p for p in self.patterns.values() if p.frequency >= min_frequency]
    
    def get_time_based_patterns(self, current_hour: int) -> List[QueryPattern]:
        """Obtenir les patterns basés sur l'heure"""
        relevant_patterns = []
        for pattern in self.patterns.values():
            if current_hour in pattern.time_distribution:
                freq_at_hour = pattern.time_distribution[current_hour]
                if freq_at_hour > 0:
                    relevant_patterns.append(pattern)
        return sorted(relevant_patterns, key=lambda p: p.time_distribution.get(current_hour, 0), reverse=True)

class PredictionEngine:
    """Moteur de prédiction des requêtes futures"""
    
    def __init__(self, analyzer: QueryAnalyzer):
        self.analyzer = analyzer
        self.models = {
            PredictionModel.FREQUENCY: self._predict_by_frequency,
            PredictionModel.SEQUENCE: self._predict_by_sequence,
            PredictionModel.TIME_BASED: self._predict_by_time,
            PredictionModel.SIMILARITY: self._predict_by_similarity,
            PredictionModel.HYBRID: self._predict_hybrid
        }
    
    def predict_next_queries(self, 
                           current_query: Optional[str] = None,
                           model: PredictionModel = PredictionModel.HYBRID,
                           max_predictions: int = 10) -> List[PredictionResult]:
        """Prédire les prochaines requêtes avec algorithmes améliorés"""
        if model in self.models:
            predictions = self.models[model](current_query, max_predictions)
            # Filtrer et améliorer les prédictions
            filtered_predictions = []
            for pred in predictions:
                # Améliorer la confiance basée sur des facteurs additionnels
                enhanced_confidence = self._enhance_prediction_confidence(pred, current_query)
                pred.confidence = enhanced_confidence
                if pred.confidence >= 0.3:  # Seuil de qualité
                    filtered_predictions.append(pred)
            return sorted(filtered_predictions, key=lambda x: x.confidence, reverse=True)[:max_predictions]
        return []
    
    def _analyze_query_context(self, query: str) -> Dict[str, Any]:
        """Analyser le contexte d'une requête"""
        context = {
            'medical_domain': '',
            'query_type': 'general',
            'complexity': 'simple',
            'keywords': [],
            'entities': []
        }
        
        query_lower = query.lower()
        
        # Détection du domaine médical
        medical_domains = {
            'paludisme': ['malaria', 'paludisme', 'artemether', 'lumefantrine'],
            'tuberculose': ['tuberculose', 'tb', 'bacille'],
            'vih': ['vih', 'sida', 'antirétroviral'],
            'diabète': ['diabète', 'glycémie', 'insuline'],
            'hypertension': ['hypertension', 'tension', 'artérielle']
        }
        
        for domain, keywords in medical_domains.items():
            if any(keyword in query_lower for keyword in keywords):
                context['medical_domain'] = domain
                break
        
        # Type de requête
        if any(word in query_lower for word in ['traitement', 'thérapie', 'médicament']):
            context['query_type'] = 'treatment'
        elif any(word in query_lower for word in ['diagnostic', 'symptôme', 'signe']):
            context['query_type'] = 'diagnostic'
        elif any(word in query_lower for word in ['prévention', 'vaccination', 'prophylaxie']):
            context['query_type'] = 'prevention'
        
        # Complexité
        if len(query.split()) > 5 or any(word in query_lower for word in ['complexe', 'compliqué', 'sévère']):
            context['complexity'] = 'complex'
        elif len(query.split()) > 3:
            context['complexity'] = 'medium'
        
        # Extraction des mots-clés
        context['keywords'] = [word for word in query.split() if len(word) > 3]
        
        return context
    
    def _normalize_query(self, query: str) -> str:
        """Normaliser une requête pour la comparaison"""
        # Supprimer la ponctuation et normaliser les espaces
        import re
        normalized = re.sub(r'[^\w\s]', '', query.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _is_contextually_related(self, query1: str, context: str) -> bool:
        """Vérifier si une requête est liée au contexte"""
        query_lower = query1.lower()
        context_lower = context.lower()
        
        # Recherche de mots-clés du contexte dans la requête
        context_words = context_lower.split()
        query_words = query_lower.split()
        
        common_words = set(context_words) & set(query_words)
        return len(common_words) > 0
    
    def _predict_by_frequency(self, current_query: Optional[str], max_predictions: int) -> List[PredictionResult]:
        """Prédiction basée sur la fréquence avec améliorations"""
        patterns = self.analyzer.get_frequent_patterns(min_frequency=1)  # Seuil plus bas
        predictions = []
        
        for pattern in patterns[:max_predictions * 2]:  # Plus de candidats
            # Calcul de confiance amélioré
            base_confidence = min(pattern.frequency / 20.0, 0.8)  # Normalisation ajustée
            
            # Bonus pour les patterns récents
            recency_bonus = 0.0
            if pattern.last_seen and (datetime.now() - pattern.last_seen).total_seconds() < 3600:
                recency_bonus = 0.2
            
            # Bonus pour le taux de succès
            success_bonus = pattern.success_rate * 0.1
            
            # Bonus pour la similarité avec la requête actuelle si disponible
            similarity_bonus = 0.0
            if current_query:
                similarity_bonus = self._calculate_query_similarity(current_query, pattern.query_template) * 0.15
            
            final_confidence = min(0.95, base_confidence + recency_bonus + success_bonus + similarity_bonus)
            priority = self._calculate_priority(final_confidence, pattern.success_rate)
            
            if final_confidence >= 0.25:  # Seuil de qualité plus bas
                predictions.append(PredictionResult(
                    query=pattern.query_template,
                    confidence=final_confidence,
                    priority=priority,
                    estimated_time=datetime.now() + timedelta(minutes=3),
                    model_used=PredictionModel.FREQUENCY,
                    context={'frequency': pattern.frequency, 'avg_time': pattern.avg_response_time, 'recency_bonus': recency_bonus}
                ))
        
        return sorted(predictions, key=lambda p: p.confidence, reverse=True)[:max_predictions]
    
    def _predict_by_frequency_enhanced(self, current_query: str, query_context: Dict, num_predictions: int) -> List[PredictionResult]:
        """Prédictions basées sur la fréquence avec contexte amélioré"""
        predictions = []
        
        # Obtenir les patterns les plus fréquents avec filtrage contextuel
        frequent_patterns = self.analyzer.get_frequent_patterns(min_frequency=1)  # Seuil plus bas
        
        # Filtrer par contexte médical si disponible
        medical_context = query_context.get('medical_domain', '')
        if medical_context:
            frequent_patterns = [p for p in frequent_patterns 
                               if self._is_contextually_related(p.query_template, medical_context)]
        
        for pattern in frequent_patterns[:num_predictions * 2]:  # Plus de candidats
            # Calcul de confiance amélioré
            base_confidence = min(0.8, pattern.frequency / 5.0)  # Normalisation ajustée
            
            # Bonus pour les patterns récents
            recency_bonus = 0.0
            if pattern.last_seen and (datetime.now() - pattern.last_seen).total_seconds() < 3600:
                recency_bonus = 0.2
            
            # Bonus pour le taux de succès
            success_bonus = pattern.success_rate * 0.1
            
            # Bonus pour la similarité avec la requête actuelle
            similarity_bonus = self._calculate_query_similarity(current_query, pattern.query_template) * 0.15
            
            final_confidence = min(0.95, base_confidence + recency_bonus + success_bonus + similarity_bonus)
            
            if final_confidence >= 0.3:  # Seuil de qualité
                prediction = PredictionResult(
                    query=pattern.query_template,
                    confidence=final_confidence,
                    priority=self._determine_priority(final_confidence),
                    estimated_time=datetime.now() + timedelta(minutes=2),  # Plus rapide
                    model_used=PredictionModel.FREQUENCY,
                    context={'pattern_frequency': pattern.frequency, 'success_rate': pattern.success_rate}
                )
                predictions.append(prediction)
        
        return predictions[:num_predictions]
    
    def _determine_priority(self, confidence: float) -> PrefetchPriority:
        """Déterminer la priorité basée sur la confiance"""
        if confidence >= 0.8:
            return PrefetchPriority.CRITICAL
        elif confidence >= 0.6:
            return PrefetchPriority.HIGH
        elif confidence >= 0.4:
            return PrefetchPriority.MEDIUM
        else:
            return PrefetchPriority.LOW
    
    def _predict_by_sequence(self, current_query: Optional[str], max_predictions: int) -> List[PredictionResult]:
        """Prédiction basée sur les séquences avec analyse améliorée"""
        if not current_query:
            return []
        
        current_pattern = self.analyzer._extract_pattern(current_query)
        next_patterns = self.analyzer.sequence_patterns.get(current_pattern, [])
        
        predictions = []
        pattern_counts = defaultdict(int)
        
        # Compter les occurrences des patterns suivants
        for pattern_id in next_patterns:
            pattern_counts[pattern_id] += 1
        
        total_sequences = len(next_patterns)
        if total_sequences == 0:
            # Si pas de séquence exacte, chercher des patterns similaires
            for pattern_id, similar_patterns in self.analyzer.sequence_patterns.items():
                if self._patterns_are_similar(current_pattern, pattern_id):
                    for next_pattern in similar_patterns:
                        pattern_counts[next_pattern] += 0.5  # Poids réduit pour similarité
                    total_sequences += len(similar_patterns) * 0.5
        
        if total_sequences == 0:
            return []
        
        for pattern_id, count in pattern_counts.items():
            if pattern_id in self.analyzer.patterns:
                pattern = self.analyzer.patterns[pattern_id]
                base_confidence = count / total_sequences
                
                # Bonus pour les séquences fréquentes
                frequency_bonus = min(0.2, pattern.frequency / 10.0)
                
                # Bonus pour la cohérence médicale
                medical_bonus = 0.0
                if self._is_medical_sequence_coherent(current_query, pattern.query_template):
                    medical_bonus = 0.15
                
                final_confidence = min(0.95, base_confidence + frequency_bonus + medical_bonus)
                priority = self._calculate_priority(final_confidence, pattern.success_rate)
                
                if final_confidence >= 0.2:  # Seuil plus bas
                    predictions.append(PredictionResult(
                        query=pattern.query_template,
                        confidence=final_confidence,
                        priority=priority,
                        estimated_time=datetime.now() + timedelta(minutes=1),
                        model_used=PredictionModel.SEQUENCE,
                        context={'sequence_probability': base_confidence, 'pattern_frequency': pattern.frequency}
                    ))
        
        return sorted(predictions, key=lambda p: p.confidence, reverse=True)[:max_predictions]
    
    def _predict_by_sequence_enhanced(self, current_query: str, query_context: Dict, num_predictions: int) -> List[PredictionResult]:
        """Prédictions basées sur les séquences avec analyse contextuelle"""
        predictions = []
        
        # Chercher des séquences contenant la requête actuelle ou similaire
        current_normalized = self._normalize_query(current_query)
        current_pattern = self.analyzer._extract_pattern(current_query)
        next_patterns = self.analyzer.sequence_patterns.get(current_pattern, [])
        
        pattern_counts = defaultdict(int)
        
        # Compter les occurrences des patterns suivants
        for pattern_id in next_patterns:
            pattern_counts[pattern_id] += 1
        
        total_sequences = len(next_patterns)
        
        for pattern_id, count in pattern_counts.items():
            if pattern_id in self.analyzer.patterns:
                pattern = self.analyzer.patterns[pattern_id]
                
                # Calcul de confiance amélioré
                base_confidence = min(0.85, count / max(1, total_sequences))  # Éviter division par zéro
                
                # Bonus pour les séquences fréquentes
                frequency_bonus = min(0.1, pattern.frequency / 10.0)
                
                # Bonus pour la cohérence médicale
                medical_bonus = 0.0
                if self._is_medical_sequence_coherent(current_query, pattern.query_template):
                    medical_bonus = 0.15
                
                final_confidence = min(0.95, base_confidence + frequency_bonus + medical_bonus)
                
                if final_confidence >= 0.4:  # Seuil de qualité
                    prediction = PredictionResult(
                        query=pattern.query_template,
                        confidence=final_confidence,
                        priority=self._determine_priority(final_confidence),
                        estimated_time=datetime.now() + timedelta(minutes=1),  # Très rapide pour séquences
                        model_used=PredictionModel.SEQUENCE,
                        context={'sequence_count': count, 'pattern_frequency': pattern.frequency}
                    )
                    predictions.append(prediction)
        
        # Éliminer les doublons et trier par confiance
        unique_predictions = {}
        for pred in predictions:
            if pred.query not in unique_predictions or pred.confidence > unique_predictions[pred.query].confidence:
                unique_predictions[pred.query] = pred
        
        return sorted(unique_predictions.values(), key=lambda x: x.confidence, reverse=True)[:num_predictions]
    
    def _predict_by_time(self, current_query: Optional[str], max_predictions: int) -> List[PredictionResult]:
        """Prédiction basée sur le temps"""
        current_hour = datetime.now().hour
        time_patterns = self.analyzer.get_time_based_patterns(current_hour)
        
        predictions = []
        for pattern in time_patterns[:max_predictions]:
            freq_at_hour = pattern.time_distribution.get(current_hour, 0)
            total_freq = pattern.frequency
            confidence = freq_at_hour / total_freq if total_freq > 0 else 0
            
            priority = self._calculate_priority(confidence, pattern.success_rate)
            
            predictions.append(PredictionResult(
                query=pattern.query_template,
                confidence=confidence,
                priority=priority,
                estimated_time=datetime.now() + timedelta(minutes=10),
                model_used=PredictionModel.TIME_BASED,
                context={'hour_frequency': freq_at_hour, 'total_frequency': total_freq}
            ))
        
        return predictions
    
    def _predict_by_similarity(self, current_query: Optional[str], max_predictions: int) -> List[PredictionResult]:
        """Prédiction basée sur la similarité"""
        if not current_query:
            return []
        
        # Simulation de similarité basée sur les mots-clés communs
        current_words = set(current_query.lower().split())
        predictions = []
        
        for pattern in self.analyzer.patterns.values():
            pattern_words = set(pattern.query_template.lower().split())
            similarity = len(current_words & pattern_words) / len(current_words | pattern_words)
            
            if similarity > 0.3:  # Seuil de similarité
                confidence = similarity * (pattern.frequency / 100.0)
                priority = self._calculate_priority(confidence, pattern.success_rate)
                
                predictions.append(PredictionResult(
                    query=pattern.query_template,
                    confidence=confidence,
                    priority=priority,
                    estimated_time=datetime.now() + timedelta(minutes=3),
                    model_used=PredictionModel.SIMILARITY,
                    context={'similarity': similarity, 'common_words': len(current_words & pattern_words)}
                ))
        
        return sorted(predictions, key=lambda p: p.confidence, reverse=True)[:max_predictions]
    
    def _predict_hybrid(self, current_query: Optional[str], max_predictions: int) -> List[PredictionResult]:
        """Prédiction hybride combinant plusieurs modèles"""
        all_predictions = []
        
        # Combiner les prédictions de différents modèles
        freq_predictions = self._predict_by_frequency(current_query, max_predictions // 2)
        seq_predictions = self._predict_by_sequence(current_query, max_predictions // 4)
        time_predictions = self._predict_by_time(current_query, max_predictions // 4)
        
        # Pondérer les prédictions
        for pred in freq_predictions:
            pred.confidence *= 0.4  # 40% de poids
            all_predictions.append(pred)
        
        for pred in seq_predictions:
            pred.confidence *= 0.3  # 30% de poids
            all_predictions.append(pred)
        
        for pred in time_predictions:
            pred.confidence *= 0.3  # 30% de poids
            all_predictions.append(pred)
        
        # Déduplication et tri
        unique_predictions = {}
        for pred in all_predictions:
            if pred.query not in unique_predictions or pred.confidence > unique_predictions[pred.query].confidence:
                unique_predictions[pred.query] = pred
        
        # Améliorer les prédictions hybrides avec des facteurs contextuels
        enhanced_predictions = []
        for pred in unique_predictions.values():
            # Appliquer des améliorations contextuelles
            enhanced_confidence = self._apply_contextual_enhancements(pred, current_query)
            pred.confidence = enhanced_confidence
            if pred.confidence >= 0.25:  # Seuil adaptatif
                enhanced_predictions.append(pred)
        
        return sorted(enhanced_predictions, key=lambda p: p.confidence, reverse=True)[:max_predictions]
    
    def _predict_by_semantic_similarity(self, current_query: str, query_context: Dict, num_predictions: int) -> List[PredictionResult]:
        """Prédictions basées sur la similarité sémantique"""
        predictions = []
        
        # Utiliser la méthode de similarité existante mais avec contexte
        similarity_predictions = self._predict_by_similarity(current_query, num_predictions)
        
        # Améliorer avec le contexte
        for pred in similarity_predictions:
            # Bonus pour la cohérence contextuelle
            context_bonus = 0.0
            if query_context.get('medical_domain'):
                if self._is_contextually_related(pred.query, query_context['medical_domain']):
                    context_bonus = 0.1
            
            pred.confidence = min(0.95, pred.confidence + context_bonus)
            predictions.append(pred)
        
        return predictions[:num_predictions]
    
    def _predict_by_temporal_patterns(self, current_query: str, query_context: Dict, num_predictions: int) -> List[PredictionResult]:
        """Prédictions basées sur les patterns temporels améliorés"""
        predictions = []
        
        # Utiliser la méthode temporelle existante
        time_predictions = self._predict_by_time(current_query, num_predictions)
        
        # Améliorer avec des patterns temporels plus sophistiqués
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        for pred in time_predictions:
            # Bonus pour les heures de pointe médicales
            time_bonus = 0.0
            if 8 <= current_hour <= 18:  # Heures de travail
                time_bonus = 0.1
            elif 0 <= current_day <= 4:  # Jours de semaine
                time_bonus = 0.05
            
            pred.confidence = min(0.95, pred.confidence + time_bonus)
            predictions.append(pred)
        
        return predictions[:num_predictions]
    
    def _predict_by_pattern_learning(self, current_query: str, query_context: Dict, num_predictions: int) -> List[PredictionResult]:
        """Prédictions basées sur l'apprentissage de patterns simples"""
        predictions = []
        
        # Apprentissage simple basé sur les co-occurrences
        query_words = set(current_query.lower().split())
        
        # Analyser les patterns de co-occurrence dans l'historique
        cooccurrence_scores = defaultdict(float)
        
        for entry in list(self.analyzer.query_history)[-100:]:  # 100 dernières requêtes
            entry_words = set(entry['query'].lower().split())
            overlap = len(query_words & entry_words)
            
            if overlap > 0:
                # Score basé sur le chevauchement et le succès
                score = (overlap / len(query_words | entry_words)) * (1.0 if entry['success'] else 0.5)
                cooccurrence_scores[entry['query']] += score
        
        # Créer des prédictions basées sur les scores
        for query, score in sorted(cooccurrence_scores.items(), key=lambda x: x[1], reverse=True)[:num_predictions]:
            if score > 0.3:  # Seuil minimum
                prediction = PredictionResult(
                    query=query,
                    confidence=min(0.8, score),
                    priority=self._determine_priority(score),
                    estimated_time=datetime.now() + timedelta(minutes=5),
                    model_used=PredictionModel.HYBRID,
                    context={'cooccurrence_score': score}
                )
                predictions.append(prediction)
        
        return predictions[:num_predictions]
    
    def _calculate_priority(self, confidence: float, success_rate: float) -> PrefetchPriority:
        """Calculer la priorité basée sur la confiance et le taux de succès"""
        score = confidence * success_rate
        
        if score >= 0.7:
            return PrefetchPriority.CRITICAL
        elif score >= 0.5:
            return PrefetchPriority.HIGH
        elif score >= 0.3:
            return PrefetchPriority.MEDIUM
        else:
            return PrefetchPriority.LOW
    
    def _enhance_prediction_confidence(self, prediction: PredictionResult, current_query: Optional[str]) -> float:
        """Améliorer la confiance d'une prédiction avec des facteurs contextuels"""
        enhanced_confidence = prediction.confidence
        
        # Bonus pour les requêtes médicales cohérentes
        if current_query and self._is_medical_sequence_coherent(current_query, prediction.query):
            enhanced_confidence += 0.1
        
        # Bonus pour les patterns temporels
        current_hour = datetime.now().hour
        if 8 <= current_hour <= 18:  # Heures de travail
            enhanced_confidence += 0.05
        
        return min(0.95, enhanced_confidence)
    
    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculer la similarité entre deux requêtes"""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _patterns_are_similar(self, pattern1: str, pattern2: str) -> bool:
        """Vérifier si deux patterns sont similaires"""
        return pattern1[:4] == pattern2[:4]  # Similarité basée sur les premiers caractères
    
    def _is_medical_sequence_coherent(self, query1: str, query2: str) -> bool:
        """Vérifier si deux requêtes forment une séquence médicale cohérente"""
        medical_keywords = {
            'diagnostic': ['traitement', 'symptômes', 'prévention'],
            'traitement': ['dosage', 'effets', 'suivi'],
            'symptômes': ['diagnostic', 'traitement'],
            'prévention': ['vaccination', 'hygiène']
        }
        
        for keyword, related in medical_keywords.items():
            if keyword in query1.lower():
                for rel in related:
                    if rel in query2.lower():
                        return True
        return False
    
    def _apply_contextual_enhancements(self, prediction: PredictionResult, current_query: Optional[str]) -> float:
        """Appliquer des améliorations contextuelles à une prédiction"""
        enhanced_confidence = prediction.confidence
        
        # Bonus pour les modèles de séquence (plus fiables)
        if prediction.model_used == PredictionModel.SEQUENCE:
            enhanced_confidence *= 1.2
        
        # Bonus pour les prédictions récentes
        time_diff = (prediction.estimated_time - datetime.now()).total_seconds()
        if time_diff < 300:  # Moins de 5 minutes
            enhanced_confidence += 0.1
        
        return min(0.95, enhanced_confidence)
    
    def _merge_predictions_enhanced(self, predictions: List[PredictionResult], current_query: str) -> List[PredictionResult]:
        """Fusionner et améliorer les prédictions"""
        # Grouper par requête et garder la meilleure confiance
        unique_predictions = {}
        
        for pred in predictions:
            query_key = pred.query.lower().strip()
            
            if query_key not in unique_predictions:
                unique_predictions[query_key] = pred
            else:
                # Garder la prédiction avec la meilleure confiance
                if pred.confidence > unique_predictions[query_key].confidence:
                    unique_predictions[query_key] = pred
                # Ou combiner les confidences si elles sont proches
                elif abs(pred.confidence - unique_predictions[query_key].confidence) < 0.1:
                    # Moyenne pondérée
                    combined_confidence = (pred.confidence + unique_predictions[query_key].confidence) / 2
                    unique_predictions[query_key].confidence = min(0.95, combined_confidence * 1.1)
        
        # Appliquer des améliorations contextuelles
        enhanced_predictions = []
        for pred in unique_predictions.values():
            # Améliorer la confiance avec des facteurs contextuels
            enhanced_confidence = self._apply_contextual_boost(pred, current_query)
            pred.confidence = enhanced_confidence
            
            if pred.confidence >= 0.25:  # Seuil de qualité
                enhanced_predictions.append(pred)
        
        return sorted(enhanced_predictions, key=lambda x: x.confidence, reverse=True)
    
    def _apply_contextual_boost(self, prediction: PredictionResult, current_query: str) -> float:
        """Appliquer un boost contextuel à une prédiction"""
        boosted_confidence = prediction.confidence
        
        # Boost pour les requêtes médicales cohérentes
        if self._is_medical_sequence_coherent(current_query, prediction.query):
            boosted_confidence += 0.1
        
        # Boost pour les modèles plus fiables
        model_boost = {
            PredictionModel.SEQUENCE: 0.15,
            PredictionModel.FREQUENCY: 0.1,
            PredictionModel.HYBRID: 0.05,
            PredictionModel.SIMILARITY: 0.05,
            PredictionModel.TIME_BASED: 0.02
        }
        
        boosted_confidence += model_boost.get(prediction.model_used, 0.0)
        
        # Boost pour les priorités élevées
        if prediction.priority in [PrefetchPriority.HIGH, PrefetchPriority.CRITICAL]:
            boosted_confidence += 0.05
        
        return min(0.95, boosted_confidence)

class PredictivePrefetcher:
    """Système de pre-fetching prédictif principal"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'max_prefetch_requests': 50,
            'prefetch_strategy': PrefetchStrategy.ADAPTIVE,
            'min_confidence_threshold': 0.3,
            'max_concurrent_prefetches': 5,
            'cache_ttl_minutes': 30,
            'resource_limit_cpu': 0.7,
            'resource_limit_memory': 0.8
        }
        
        self.analyzer = QueryAnalyzer()
        self.prediction_engine = PredictionEngine(self.analyzer)
        self.prefetch_queue = deque()
        self.active_prefetches = {}
        self.prefetch_cache = {}
        self.metrics = PrefetchMetrics()
        self.executor = ThreadPoolExecutor(max_workers=self.config['max_concurrent_prefetches'])
        self.running = False
        self.prefetch_thread = None
        
        logger.info("PredictivePrefetcher initialisé")
    
    def start(self):
        """Démarrer le système de pre-fetching"""
        self.running = True
        self.prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
        self.prefetch_thread.start()
        logger.info("Système de pre-fetching démarré")
    
    def stop(self):
        """Arrêter le système de pre-fetching"""
        self.running = False
        if self.prefetch_thread:
            self.prefetch_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logger.info("Système de pre-fetching arrêté")
    
    def process_query(self, query: str, response_time: float = None, success: bool = True) -> Any:
        """Traiter une requête et déclencher les prédictions"""
        timestamp = datetime.now()
        
        # Ajouter à l'historique pour l'analyse
        self.analyzer.add_query(query, timestamp, response_time or 0.0, success)
        self.metrics.total_queries += 1
        
        # Vérifier si la requête était dans le cache de pre-fetching
        cache_key = self._generate_cache_key(query)
        if cache_key in self.prefetch_cache:
            self.metrics.cache_hits_from_prefetch += 1
            cached_result = self.prefetch_cache[cache_key]
            self.metrics.time_saved += cached_result.get('original_time', 0)
            logger.info(f"Cache hit pour requête pre-fetchée: {query[:50]}...")
            return cached_result['result']
        
        # Générer des prédictions pour les prochaines requêtes
        self._trigger_predictions(query)
        
        # Simuler le traitement de la requête
        result = self._simulate_query_processing(query)
        return result
    
    def _trigger_predictions(self, current_query: str):
        """Déclencher les prédictions et ajouter au queue de pre-fetching"""
        predictions = self.prediction_engine.predict_next_queries(
            current_query=current_query,
            model=PredictionModel.HYBRID,
            max_predictions=10
        )
        
        for prediction in predictions:
            if prediction.confidence >= self.config['min_confidence_threshold']:
                prefetch_request = PrefetchRequest(
                    query=prediction.query,
                    priority=prediction.priority,
                    predicted_time=prediction.estimated_time,
                    confidence=prediction.confidence,
                    model_used=prediction.model_used,
                    cache_key=self._generate_cache_key(prediction.query)
                )
                
                # Éviter les doublons
                if not any(req.cache_key == prefetch_request.cache_key for req in self.prefetch_queue):
                    self.prefetch_queue.append(prefetch_request)
                    self.metrics.total_predictions += 1
    
    def _is_high_quality_prediction(self, prediction: PredictionResult, current_query: str) -> bool:
        """Vérifier si une prédiction est de haute qualité"""
        # Critères de qualité
        min_confidence = self.config.get('min_confidence_threshold', 0.3)
        
        # Vérifications de base
        if prediction.confidence < min_confidence:
            return False
        
        # Éviter les prédictions identiques à la requête actuelle
        if prediction.query.lower().strip() == current_query.lower().strip():
            return False
        
        # Vérifier la longueur minimale
        if len(prediction.query.strip()) < 5:
            return False
        
        return True
    
    def _prefetch_worker(self):
        """Worker thread pour le pre-fetching"""
        while self.running:
            try:
                if self.prefetch_queue and len(self.active_prefetches) < self.config['max_concurrent_prefetches']:
                    # Trier par priorité et confiance
                    sorted_queue = sorted(self.prefetch_queue, 
                                        key=lambda x: (x.priority.value, x.confidence), 
                                        reverse=True)
                    
                    if sorted_queue:
                        request = sorted_queue[0]
                        self.prefetch_queue.remove(request)
                        
                        # Vérifier les ressources
                        if self._check_resource_availability():
                            future = self.executor.submit(self._execute_prefetch, request)
                            self.active_prefetches[request.cache_key] = future
                
                # Nettoyer les prefetches terminés
                self._cleanup_completed_prefetches()
                
                # Nettoyer le cache expiré
                self._cleanup_expired_cache()
                
                time.sleep(0.1)  # Éviter la surcharge CPU
                
            except Exception as e:
                logger.error(f"Erreur dans prefetch worker: {e}")
                time.sleep(1)
    
    def _execute_prefetch(self, request: PrefetchRequest) -> bool:
        """Exécuter une requête de pre-fetching"""
        try:
            request.status = "processing"
            start_time = time.time()
            
            # Simuler le traitement de la requête
            result = self._simulate_query_processing(request.query)
            
            processing_time = (time.time() - start_time) * 1000  # en ms
            
            # Stocker dans le cache
            self.prefetch_cache[request.cache_key] = {
                'result': result,
                'timestamp': datetime.now(),
                'original_time': processing_time,
                'request': request
            }
            
            request.status = "completed"
            request.completed_at = datetime.now()
            
            self.metrics.successful_prefetches += 1
            self.metrics.avg_prefetch_time = (
                (self.metrics.avg_prefetch_time * (self.metrics.successful_prefetches - 1) + processing_time) /
                self.metrics.successful_prefetches
            )
            
            logger.info(f"Pre-fetch réussi: {request.query[:50]}... ({processing_time:.1f}ms)")
            return True
            
        except Exception as e:
            request.status = "failed"
            logger.error(f"Erreur pre-fetch: {e}")
            return False
    
    def _simulate_query_processing(self, query: str) -> Dict[str, Any]:
        """Simuler le traitement d'une requête RAG"""
        # Simulation réaliste du traitement
        processing_time = 50 + len(query) * 2  # Temps basé sur la longueur
        time.sleep(processing_time / 1000)  # Simuler le délai
        
        return {
            'query': query,
            'results': [f"Résultat {i+1} pour: {query[:30]}..." for i in range(3)],
            'processing_time_ms': processing_time,
            'timestamp': datetime.now().isoformat(),
            'confidence': 0.85
        }
    
    def _generate_cache_key(self, query: str) -> str:
        """Générer une clé de cache pour une requête"""
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def _check_resource_availability(self) -> bool:
        """Vérifier la disponibilité des ressources"""
        # Simulation de vérification des ressources
        import psutil
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent / 100
            
            self.metrics.resource_usage = {
                'cpu': cpu_usage / 100,
                'memory': memory_usage
            }
            
            return (cpu_usage / 100 < self.config['resource_limit_cpu'] and 
                   memory_usage < self.config['resource_limit_memory'])
        except:
            # Si psutil n'est pas disponible, autoriser le pre-fetching
            return True
    
    def _cleanup_completed_prefetches(self):
        """Nettoyer les pre-fetches terminés"""
        completed_keys = []
        for key, future in self.active_prefetches.items():
            if future.done():
                completed_keys.append(key)
        
        for key in completed_keys:
            del self.active_prefetches[key]
    
    def _cleanup_expired_cache(self):
        """Nettoyer le cache expiré"""
        current_time = datetime.now()
        ttl = timedelta(minutes=self.config['cache_ttl_minutes'])
        
        expired_keys = []
        for key, cached_item in self.prefetch_cache.items():
            if current_time - cached_item['timestamp'] > ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.prefetch_cache[key]
    
    def get_metrics(self) -> PrefetchMetrics:
        """Obtenir les métriques de performance"""
        # Calculer la précision des prédictions
        if self.metrics.total_predictions > 0:
            self.metrics.avg_prediction_accuracy = (
                self.metrics.cache_hits_from_prefetch / self.metrics.total_predictions
            )
        
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Obtenir le statut du système"""
        return {
            'running': self.running,
            'queue_size': len(self.prefetch_queue),
            'active_prefetches': len(self.active_prefetches),
            'cache_size': len(self.prefetch_cache),
            'metrics': asdict(self.get_metrics()),
            'config': self.config
        }
    
    def export_data(self, filename: str = "predictive_prefetcher_export.json"):
        """Exporter les données du système"""
        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'status': self.get_status(),
                'patterns': {pid: asdict(pattern) for pid, pattern in self.analyzer.patterns.items()},
                'sequence_patterns': dict(self.analyzer.sequence_patterns),
                'recent_queries': list(self.analyzer.query_history)[-100:],  # 100 dernières requêtes
                'cache_summary': {
                    'total_entries': len(self.prefetch_cache),
                    'cache_keys': list(self.prefetch_cache.keys())
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Données exportées vers {filename}")
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")

def main():
    """Fonction principale de démonstration"""
    print("🔮 Predictive Prefetcher - Objectif 13")
    print("Système de pre-fetching prédictif")
    print("=" * 50)
    
    # Configuration du système
    config = {
        'max_prefetch_requests': 20,
        'prefetch_strategy': PrefetchStrategy.ADAPTIVE,
        'min_confidence_threshold': 0.4,
        'max_concurrent_prefetches': 3,
        'cache_ttl_minutes': 15,
        'resource_limit_cpu': 0.8,
        'resource_limit_memory': 0.9
    }
    
    prefetcher = PredictivePrefetcher(config)
    prefetcher.start()
    
    try:
        # Simuler des requêtes médicales typiques
        medical_queries = [
            "traitement paludisme enfant",
            "diagnostic malaria rapide",
            "artemether lumefantrine dosage",
            "paludisme grave symptômes",
            "prévention paludisme grossesse",
            "traitement paludisme enfant",  # Répétition pour pattern
            "diagnostic tuberculose pulmonaire",
            "traitement VIH antirétroviral",
            "vaccination enfant calendrier",
            "diagnostic malaria rapide",  # Répétition
            "hypertension artérielle traitement",
            "diabète type 2 gestion",
            "traitement paludisme enfant",  # Répétition
            "pneumonie enfant antibiotique",
            "diarrhée aiguë réhydratation"
        ]
        
        print("\n🔍 Simulation de requêtes médicales...")
        
        # Traiter les requêtes avec des délais réalistes
        for i, query in enumerate(medical_queries):
            print(f"\nRequête {i+1}: {query}")
            
            start_time = time.time()
            result = prefetcher.process_query(query, response_time=80 + i*5, success=True)
            processing_time = (time.time() - start_time) * 1000
            
            print(f"  ⏱️ Temps de traitement: {processing_time:.1f}ms")
            
            # Attendre un peu pour simuler l'utilisation réelle
            time.sleep(0.5)
            
            # Afficher le statut périodiquement
            if (i + 1) % 5 == 0:
                status = prefetcher.get_status()
                print(f"\n📊 Statut après {i+1} requêtes:")
                print(f"  Queue: {status['queue_size']} requêtes")
                print(f"  Cache: {status['cache_size']} entrées")
                print(f"  Pre-fetches actifs: {status['active_prefetches']}")
        
        # Attendre que les pre-fetches se terminent
        print("\n⏳ Attente des pre-fetches en cours...")
        time.sleep(3)
        
        # Tester quelques requêtes pour voir les cache hits
        print("\n🎯 Test des cache hits...")
        test_queries = [
            "traitement paludisme enfant",
            "diagnostic malaria rapide",
            "artemether lumefantrine dosage"
        ]
        
        for query in test_queries:
            start_time = time.time()
            result = prefetcher.process_query(query)
            processing_time = (time.time() - start_time) * 1000
            print(f"  {query}: {processing_time:.1f}ms")
        
        # Afficher les métriques finales
        print("\n📈 Métriques de performance:")
        metrics = prefetcher.get_metrics()
        print(f"  Requêtes totales: {metrics.total_queries}")
        print(f"  Prédictions générées: {metrics.total_predictions}")
        print(f"  Pre-fetches réussis: {metrics.successful_prefetches}")
        print(f"  Cache hits: {metrics.cache_hits_from_prefetch}")
        print(f"  Précision prédictions: {metrics.avg_prediction_accuracy:.1%}")
        print(f"  Temps moyen pre-fetch: {metrics.avg_prefetch_time:.1f}ms")
        print(f"  Temps économisé: {metrics.time_saved:.1f}ms")
        
        # Analyser les patterns découverts
        print("\n🔍 Patterns découverts:")
        frequent_patterns = prefetcher.analyzer.get_frequent_patterns(min_frequency=2)
        for pattern in frequent_patterns[:5]:
            print(f"  Pattern: {pattern.query_template[:50]}...")
            print(f"    Fréquence: {pattern.frequency}")
            print(f"    Taux de succès: {pattern.success_rate:.1%}")
            print(f"    Temps moyen: {pattern.avg_response_time:.1f}ms")
        
        # Export des données
        print("\n💾 Export des données...")
        prefetcher.export_data()
        
        # Évaluation finale
        final_status = prefetcher.get_status()
        hit_rate = metrics.cache_hits_from_prefetch / metrics.total_queries if metrics.total_queries > 0 else 0
        
        print("\n🎯 Évaluation finale:")
        if hit_rate >= 0.2 and metrics.avg_prediction_accuracy >= 0.3:
            print("✅ Objectif 13 ATTEINT - Pre-fetching prédictif performant!")
        else:
            print("⚠️ Objectif 13 PARTIELLEMENT ATTEINT - Optimisations nécessaires")
        
        print(f"📊 Taux de cache hit: {hit_rate:.1%}")
        print(f"🎯 Précision prédictions: {metrics.avg_prediction_accuracy:.1%}")
        print(f"⚡ Temps économisé total: {metrics.time_saved:.1f}ms")
        print(f"🔮 Système prédictif opérationnel avec {len(frequent_patterns)} patterns")
        
    finally:
        prefetcher.stop()

if __name__ == "__main__":
    main()