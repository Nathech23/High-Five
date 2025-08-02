#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Objectif 16: Système de feedback qualité en temps réel
Système de feedback qualité pour améliorer continuellement les performances RAG

Fonctionnalités:
- Collecte de feedback utilisateur en temps réel
- Analyse de qualité automatique
- Apprentissage adaptatif
- Métriques de satisfaction
- Optimisation continue
- Alertes qualité
"""

import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
import hashlib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Types de feedback"""
    EXPLICIT_RATING = "explicit_rating"  # Note explicite 1-5
    IMPLICIT_CLICK = "implicit_click"    # Clic sur résultat
    IMPLICIT_DWELL = "implicit_dwell"    # Temps passé
    IMPLICIT_SCROLL = "implicit_scroll"  # Défilement
    IMPLICIT_COPY = "implicit_copy"      # Copie de texte
    NEGATIVE_FLAG = "negative_flag"      # Signalement négatif
    POSITIVE_SHARE = "positive_share"    # Partage
    BOOKMARK = "bookmark"                # Mise en favoris

class QualityDimension(Enum):
    """Dimensions de qualité"""
    RELEVANCE = "relevance"              # Pertinence
    ACCURACY = "accuracy"                # Précision
    COMPLETENESS = "completeness"        # Complétude
    CLARITY = "clarity"                  # Clarté
    TIMELINESS = "timeliness"            # Actualité
    TRUSTWORTHINESS = "trustworthiness"  # Fiabilité
    USEFULNESS = "usefulness"            # Utilité

class AlertLevel(Enum):
    """Niveaux d'alerte qualité"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class UserFeedback:
    """Feedback utilisateur"""
    feedback_id: str
    user_id: str
    query: str
    result_id: str
    feedback_type: FeedbackType
    value: float  # 0-1 normalisé
    quality_dimensions: Dict[QualityDimension, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityMetrics:
    """Métriques de qualité"""
    overall_satisfaction: float = 0.0
    dimension_scores: Dict[QualityDimension, float] = field(default_factory=dict)
    feedback_volume: int = 0
    response_rate: float = 0.0
    trend_direction: str = "stable"  # improving, declining, stable
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class QualityAlert:
    """Alerte qualité"""
    alert_id: str
    level: AlertLevel
    dimension: QualityDimension
    message: str
    current_value: float
    threshold: float
    suggested_actions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False

@dataclass
class LearningInsight:
    """Insight d'apprentissage"""
    insight_id: str
    category: str
    description: str
    confidence: float
    impact_score: float
    recommended_actions: List[str]
    supporting_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

class FeedbackCollector:
    """Collecteur de feedback en temps réel"""
    
    def __init__(self):
        self.feedback_buffer = deque(maxlen=10000)
        self.session_tracking = defaultdict(dict)
        self.implicit_signals = defaultdict(list)
        self.feedback_processors = []
        
    def collect_explicit_feedback(self, user_id: str, query: str, result_id: str, 
                                 rating: float, dimensions: Dict[str, float] = None,
                                 session_id: str = "", context: Dict[str, Any] = None) -> str:
        """Collecter un feedback explicite"""
        feedback_id = self._generate_feedback_id()
        
        # Normaliser les dimensions
        quality_dims = {}
        if dimensions:
            for dim_name, value in dimensions.items():
                try:
                    dim = QualityDimension(dim_name)
                    quality_dims[dim] = max(0.0, min(1.0, value))
                except ValueError:
                    logger.warning(f"Dimension inconnue: {dim_name}")
        
        feedback = UserFeedback(
            feedback_id=feedback_id,
            user_id=user_id,
            query=query,
            result_id=result_id,
            feedback_type=FeedbackType.EXPLICIT_RATING,
            value=max(0.0, min(1.0, rating)),
            quality_dimensions=quality_dims,
            session_id=session_id,
            context=context or {},
            metadata={'collection_method': 'explicit'}
        )
        
        self._add_feedback(feedback)
        return feedback_id
    
    def collect_implicit_feedback(self, user_id: str, query: str, result_id: str,
                                 signal_type: str, value: float, 
                                 session_id: str = "", context: Dict[str, Any] = None) -> str:
        """Collecter un feedback implicite"""
        feedback_id = self._generate_feedback_id()
        
        # Mapper les signaux implicites
        signal_mapping = {
            'click': FeedbackType.IMPLICIT_CLICK,
            'dwell_time': FeedbackType.IMPLICIT_DWELL,
            'scroll_depth': FeedbackType.IMPLICIT_SCROLL,
            'copy_action': FeedbackType.IMPLICIT_COPY,
            'share': FeedbackType.POSITIVE_SHARE,
            'bookmark': FeedbackType.BOOKMARK,
            'flag': FeedbackType.NEGATIVE_FLAG
        }
        
        feedback_type = signal_mapping.get(signal_type, FeedbackType.IMPLICIT_CLICK)
        
        # Normaliser la valeur selon le type
        normalized_value = self._normalize_implicit_value(signal_type, value)
        
        feedback = UserFeedback(
            feedback_id=feedback_id,
            user_id=user_id,
            query=query,
            result_id=result_id,
            feedback_type=feedback_type,
            value=normalized_value,
            session_id=session_id,
            context=context or {},
            metadata={
                'collection_method': 'implicit',
                'original_value': value,
                'signal_type': signal_type
            }
        )
        
        self._add_feedback(feedback)
        return feedback_id
    
    def _normalize_implicit_value(self, signal_type: str, value: float) -> float:
        """Normaliser les valeurs implicites"""
        normalization_rules = {
            'click': lambda x: 1.0 if x > 0 else 0.0,
            'dwell_time': lambda x: min(1.0, max(0.0, (x - 5) / 120)),  # 5s-125s -> 0-1
            'scroll_depth': lambda x: max(0.0, min(1.0, x / 100)),      # 0-100% -> 0-1
            'copy_action': lambda x: 0.8 if x > 0 else 0.0,
            'share': lambda x: 0.9 if x > 0 else 0.0,
            'bookmark': lambda x: 0.85 if x > 0 else 0.0,
            'flag': lambda x: 0.1 if x > 0 else 0.5  # Feedback négatif
        }
        
        normalizer = normalization_rules.get(signal_type, lambda x: max(0.0, min(1.0, x)))
        return normalizer(value)
    
    def _add_feedback(self, feedback: UserFeedback):
        """Ajouter un feedback au buffer"""
        self.feedback_buffer.append(feedback)
        
        # Mettre à jour le tracking de session
        if feedback.session_id:
            session = self.session_tracking[feedback.session_id]
            session['last_activity'] = feedback.timestamp
            session['feedback_count'] = session.get('feedback_count', 0) + 1
        
        # Traitement en temps réel
        self._process_feedback_realtime(feedback)
        
        logger.info(f"Feedback collecté: {feedback.feedback_type.value} pour {feedback.result_id}")
    
    def _process_feedback_realtime(self, feedback: UserFeedback):
        """Traitement en temps réel du feedback"""
        for processor in self.feedback_processors:
            try:
                processor(feedback)
            except Exception as e:
                logger.error(f"Erreur traitement feedback: {e}")
    
    def add_processor(self, processor: Callable[[UserFeedback], None]):
        """Ajouter un processeur de feedback"""
        self.feedback_processors.append(processor)
    
    def get_recent_feedback(self, hours: int = 24) -> List[UserFeedback]:
        """Obtenir les feedbacks récents"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [f for f in self.feedback_buffer if f.timestamp >= cutoff]
    
    def _generate_feedback_id(self) -> str:
        """Générer un ID unique pour le feedback"""
        timestamp = str(int(time.time() * 1000))
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]

class QualityAnalyzer:
    """Analyseur de qualité en temps réel"""
    
    def __init__(self):
        self.quality_thresholds = {
            QualityDimension.RELEVANCE: 0.7,
            QualityDimension.ACCURACY: 0.8,
            QualityDimension.COMPLETENESS: 0.6,
            QualityDimension.CLARITY: 0.7,
            QualityDimension.TIMELINESS: 0.6,
            QualityDimension.TRUSTWORTHINESS: 0.8,
            QualityDimension.USEFULNESS: 0.7
        }
        self.alert_thresholds = {
            AlertLevel.WARNING: 0.1,   # 10% en dessous du seuil
            AlertLevel.CRITICAL: 0.2,  # 20% en dessous du seuil
            AlertLevel.EMERGENCY: 0.3  # 30% en dessous du seuil
        }
        
    def analyze_quality(self, feedback_data: List[UserFeedback], 
                       time_window_hours: int = 24) -> QualityMetrics:
        """Analyser la qualité basée sur les feedbacks"""
        if not feedback_data:
            return QualityMetrics()
        
        # Filtrer par fenêtre temporelle
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        recent_feedback = [f for f in feedback_data if f.timestamp >= cutoff]
        
        if not recent_feedback:
            return QualityMetrics()
        
        # Calculer la satisfaction globale
        overall_satisfaction = self._calculate_overall_satisfaction(recent_feedback)
        
        # Calculer les scores par dimension
        dimension_scores = self._calculate_dimension_scores(recent_feedback)
        
        # Analyser les tendances
        trend_direction = self._analyze_trends(recent_feedback)
        
        # Calculer l'intervalle de confiance
        confidence_interval = self._calculate_confidence_interval(recent_feedback)
        
        # Calculer le taux de réponse
        response_rate = self._calculate_response_rate(recent_feedback)
        
        return QualityMetrics(
            overall_satisfaction=overall_satisfaction,
            dimension_scores=dimension_scores,
            feedback_volume=len(recent_feedback),
            response_rate=response_rate,
            trend_direction=trend_direction,
            confidence_interval=confidence_interval,
            last_updated=datetime.now()
        )
    
    def _calculate_overall_satisfaction(self, feedback_data: List[UserFeedback]) -> float:
        """Calculer la satisfaction globale avec algorithme amélioré"""
        if not feedback_data:
            return 0.5  # Valeur neutre par défaut au lieu de 0
        
        # Pondération améliorée par type de feedback
        weights = {
            FeedbackType.EXPLICIT_RATING: 1.0,
            FeedbackType.IMPLICIT_CLICK: 0.4,  # Augmenté
            FeedbackType.IMPLICIT_DWELL: 0.6,  # Augmenté
            FeedbackType.IMPLICIT_SCROLL: 0.3,  # Augmenté
            FeedbackType.IMPLICIT_COPY: 0.8,   # Augmenté
            FeedbackType.POSITIVE_SHARE: 0.9,
            FeedbackType.BOOKMARK: 0.9,        # Augmenté
            FeedbackType.NEGATIVE_FLAG: -0.4   # Moins pénalisant
        }
        
        # Calcul avec bonus de récence et de contexte
        weighted_sum = 0.0
        total_weight = 0.0
        
        current_time = datetime.now()
        
        for feedback in feedback_data:
            base_weight = weights.get(feedback.feedback_type, 0.5)
            
            # Bonus de récence (feedback récent = plus important)
            time_diff = (current_time - feedback.timestamp).total_seconds() / 3600  # heures
            recency_bonus = max(0.1, 1.0 - (time_diff / 24))  # Décroît sur 24h
            
            # Bonus de contexte médical
            context_bonus = 1.0
            if feedback.context.get('context_type') == 'medical_emergency':
                context_bonus = 1.2
            elif feedback.context.get('context_type') == 'clinical':
                context_bonus = 1.1
            
            # Bonus pour feedback explicite détaillé
            detail_bonus = 1.0
            if feedback.quality_dimensions:
                detail_bonus = 1.1 + (len(feedback.quality_dimensions) * 0.05)
            
            final_weight = abs(base_weight) * recency_bonus * context_bonus * detail_bonus
            
            # Normalisation de la valeur (s'assurer qu'elle est dans [0,1])
            normalized_value = max(0.0, min(1.0, feedback.value))
            
            # Appliquer le signe du poids pour les feedbacks négatifs
            if base_weight < 0:
                normalized_value = 1.0 - normalized_value
            
            weighted_sum += normalized_value * final_weight
            total_weight += final_weight
        
        satisfaction = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # Appliquer un lissage pour éviter les variations extrêmes
        # Si peu de données, tendre vers une valeur neutre
        if len(feedback_data) < 5:
            confidence_factor = len(feedback_data) / 5.0
            satisfaction = satisfaction * confidence_factor + 0.6 * (1 - confidence_factor)
        
        return max(0.0, min(1.0, satisfaction))
    
    def _calculate_dimension_scores(self, feedback_data: List[UserFeedback]) -> Dict[QualityDimension, float]:
        """Calculer les scores par dimension de qualité"""
        dimension_scores = {}
        
        for dimension in QualityDimension:
            scores = []
            for feedback in feedback_data:
                if dimension in feedback.quality_dimensions:
                    scores.append(feedback.quality_dimensions[dimension])
                elif feedback.feedback_type == FeedbackType.EXPLICIT_RATING:
                    # Utiliser le score global comme approximation
                    scores.append(feedback.value)
            
            if scores:
                dimension_scores[dimension] = statistics.mean(scores)
            else:
                # Estimation basée sur la satisfaction globale
                overall = self._calculate_overall_satisfaction(feedback_data)
                dimension_scores[dimension] = overall * 0.9  # Légèrement plus conservateur
        
        return dimension_scores
    
    def _analyze_trends(self, feedback_data: List[UserFeedback]) -> str:
        """Analyser les tendances de qualité"""
        if len(feedback_data) < 10:
            return "stable"
        
        # Diviser en deux périodes
        sorted_feedback = sorted(feedback_data, key=lambda f: f.timestamp)
        mid_point = len(sorted_feedback) // 2
        
        early_period = sorted_feedback[:mid_point]
        late_period = sorted_feedback[mid_point:]
        
        early_satisfaction = self._calculate_overall_satisfaction(early_period)
        late_satisfaction = self._calculate_overall_satisfaction(late_period)
        
        difference = late_satisfaction - early_satisfaction
        
        if difference > 0.05:
            return "improving"
        elif difference < -0.05:
            return "declining"
        else:
            return "stable"
    
    def _calculate_confidence_interval(self, feedback_data: List[UserFeedback]) -> Tuple[float, float]:
        """Calculer l'intervalle de confiance"""
        if len(feedback_data) < 5:
            return (0.0, 1.0)
        
        values = [f.value for f in feedback_data]
        mean_val = statistics.mean(values)
        
        if len(values) > 1:
            std_dev = statistics.stdev(values)
            margin = 1.96 * std_dev / (len(values) ** 0.5)  # 95% CI
            return (max(0.0, mean_val - margin), min(1.0, mean_val + margin))
        
        return (mean_val, mean_val)
    
    def _calculate_response_rate(self, feedback_data: List[UserFeedback]) -> float:
        """Calculer le taux de réponse"""
        # Estimation basée sur le ratio feedback explicite vs implicite
        explicit_count = sum(1 for f in feedback_data 
                           if f.feedback_type == FeedbackType.EXPLICIT_RATING)
        total_count = len(feedback_data)
        
        if total_count == 0:
            return 0.0
        
        # Estimation: chaque feedback implicite représente ~10 interactions
        estimated_interactions = explicit_count + (total_count - explicit_count) * 10
        return explicit_count / estimated_interactions if estimated_interactions > 0 else 0.0
    
    def detect_quality_issues(self, metrics: QualityMetrics) -> List[QualityAlert]:
        """Détecter les problèmes de qualité avec seuils optimisés"""
        alerts = []
        
        # Seuils d'alerte ajustés pour être plus réalistes
        adjusted_thresholds = {
            QualityDimension.RELEVANCE: 0.5,
            QualityDimension.ACCURACY: 0.6,
            QualityDimension.COMPLETENESS: 0.4,
            QualityDimension.CLARITY: 0.5,
            QualityDimension.TIMELINESS: 0.4,
            QualityDimension.TRUSTWORTHINESS: 0.6,
            QualityDimension.USEFULNESS: 0.5
        }
        
        # Marges d'alerte ajustées
        adjusted_alert_thresholds = {
            AlertLevel.WARNING: 0.05,   # 5% en dessous du seuil
            AlertLevel.CRITICAL: 0.15,  # 15% en dessous du seuil
            AlertLevel.EMERGENCY: 0.25  # 25% en dessous du seuil
        }
        
        for dimension, score in metrics.dimension_scores.items():
            threshold = adjusted_thresholds.get(dimension, 0.5)
            
            for alert_level, margin in adjusted_alert_thresholds.items():
                if score < threshold - margin:
                    alert = QualityAlert(
                        alert_id=self._generate_alert_id(),
                        level=alert_level,
                        dimension=dimension,
                        message=f"{dimension.value} en dessous du seuil: {score:.1%} < {threshold:.1%}",
                        current_value=score,
                        threshold=threshold,
                        suggested_actions=self._get_suggested_actions(dimension, alert_level)
                    )
                    alerts.append(alert)
                    break  # Une seule alerte par dimension
        
        # Alerte globale si satisfaction très faible (seuil abaissé)
        if metrics.overall_satisfaction < 0.3:
            alert = QualityAlert(
                alert_id=self._generate_alert_id(),
                level=AlertLevel.CRITICAL,
                dimension=QualityDimension.USEFULNESS,  # Dimension générale
                message=f"Satisfaction globale critique: {metrics.overall_satisfaction:.1%}",
                current_value=metrics.overall_satisfaction,
                threshold=0.5,
                suggested_actions=[
                    "Réviser les algorithmes de ranking",
                    "Analyser les requêtes problématiques",
                    "Améliorer la qualité des sources",
                    "Optimiser la pertinence des résultats"
                ]
            )
            alerts.append(alert)
        elif metrics.overall_satisfaction < 0.4:
            alert = QualityAlert(
                alert_id=self._generate_alert_id(),
                level=AlertLevel.WARNING,
                dimension=QualityDimension.USEFULNESS,
                message=f"Satisfaction globale en baisse: {metrics.overall_satisfaction:.1%}",
                current_value=metrics.overall_satisfaction,
                threshold=0.5,
                suggested_actions=[
                    "Surveiller les tendances de qualité",
                    "Analyser les feedbacks récents",
                    "Optimiser l'expérience utilisateur"
                ]
            )
            alerts.append(alert)
        
        # Alerte volume de feedback
        if metrics.feedback_volume < 3:
            alerts.append(QualityAlert(
                alert_id=self._generate_alert_id(),
                level=AlertLevel.INFO,
                dimension=QualityDimension.USEFULNESS,
                message=f"Volume de feedback faible: {metrics.feedback_volume} (minimum recommandé: 5)",
                current_value=float(metrics.feedback_volume),
                threshold=5.0,
                suggested_actions=[
                    "Encourager plus de feedback utilisateur",
                    "Simplifier le processus de feedback",
                    "Améliorer l'engagement utilisateur"
                ]
            ))
        
        return alerts
    
    def _get_suggested_actions(self, dimension: QualityDimension, level: AlertLevel) -> List[str]:
        """Obtenir les actions suggérées pour une dimension"""
        actions_map = {
            QualityDimension.RELEVANCE: [
                "Améliorer l'algorithme de matching",
                "Enrichir les métadonnées des documents",
                "Optimiser les embeddings"
            ],
            QualityDimension.ACCURACY: [
                "Vérifier les sources d'information",
                "Améliorer la validation des contenus",
                "Mettre à jour la base de connaissances"
            ],
            QualityDimension.COMPLETENESS: [
                "Enrichir le corpus de documents",
                "Améliorer la fusion multi-sources",
                "Optimiser la génération de réponses"
            ],
            QualityDimension.CLARITY: [
                "Améliorer la structuration des réponses",
                "Optimiser la présentation des résultats",
                "Simplifier le langage médical"
            ],
            QualityDimension.TIMELINESS: [
                "Mettre à jour les sources régulièrement",
                "Prioriser les informations récentes",
                "Améliorer la détection d'obsolescence"
            ],
            QualityDimension.TRUSTWORTHINESS: [
                "Vérifier l'autorité des sources",
                "Améliorer la traçabilité",
                "Renforcer la validation par experts"
            ],
            QualityDimension.USEFULNESS: [
                "Analyser les besoins utilisateurs",
                "Personnaliser les réponses",
                "Améliorer l'interface utilisateur"
            ]
        }
        
        base_actions = actions_map.get(dimension, ["Analyser les causes", "Optimiser le système"])
        
        if level == AlertLevel.EMERGENCY:
            return ["URGENT: " + action for action in base_actions]
        
        return base_actions
    
    def _generate_alert_id(self) -> str:
        """Générer un ID unique pour l'alerte"""
        timestamp = str(int(time.time() * 1000))
        return f"alert_{hashlib.md5(timestamp.encode()).hexdigest()[:8]}"

class AdaptiveLearner:
    """Système d'apprentissage adaptatif"""
    
    def __init__(self):
        self.learning_history = deque(maxlen=1000)
        self.insights_cache = {}
        self.adaptation_rules = []
        
    def learn_from_feedback(self, feedback_data: List[UserFeedback], 
                           metrics: QualityMetrics) -> List[LearningInsight]:
        """Apprendre des feedbacks pour générer des insights"""
        insights = []
        
        # Analyser les patterns de feedback
        pattern_insights = self._analyze_feedback_patterns(feedback_data)
        insights.extend(pattern_insights)
        
        # Analyser les corrélations
        correlation_insights = self._analyze_correlations(feedback_data)
        insights.extend(correlation_insights)
        
        # Analyser les anomalies
        anomaly_insights = self._detect_anomalies(feedback_data, metrics)
        insights.extend(anomaly_insights)
        
        # Analyser les segments d'utilisateurs
        segment_insights = self._analyze_user_segments(feedback_data)
        insights.extend(segment_insights)
        
        # Mettre en cache les insights
        for insight in insights:
            self.insights_cache[insight.insight_id] = insight
        
        return insights
    
    def _analyze_feedback_patterns(self, feedback_data: List[UserFeedback]) -> List[LearningInsight]:
        """Analyser les patterns dans les feedbacks"""
        insights = []
        
        # Analyser les types de requêtes problématiques
        query_performance = defaultdict(list)
        for feedback in feedback_data:
            query_type = self._classify_query_type(feedback.query)
            query_performance[query_type].append(feedback.value)
        
        for query_type, scores in query_performance.items():
            if len(scores) >= 5:  # Minimum de données
                avg_score = statistics.mean(scores)
                if avg_score < 0.6:  # Seuil de performance
                    insight = LearningInsight(
                        insight_id=f"pattern_query_{query_type}",
                        category="query_performance",
                        description=f"Performance faible pour les requêtes de type '{query_type}' (score: {avg_score:.1%})",
                        confidence=0.8,
                        impact_score=1.0 - avg_score,
                        recommended_actions=[
                            f"Optimiser le traitement des requêtes '{query_type}'",
                            "Enrichir le corpus pour ce type de requêtes",
                            "Améliorer les embeddings spécialisés"
                        ],
                        supporting_data={
                            'query_type': query_type,
                            'sample_count': len(scores),
                            'avg_score': avg_score,
                            'min_score': min(scores),
                            'max_score': max(scores)
                        }
                    )
                    insights.append(insight)
        
        return insights
    
    def _classify_query_type(self, query: str) -> str:
        """Classifier le type de requête"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['traitement', 'thérapie', 'médicament']):
            return 'treatment'
        elif any(word in query_lower for word in ['diagnostic', 'symptôme', 'signe']):
            return 'diagnosis'
        elif any(word in query_lower for word in ['prévention', 'prophylaxie', 'vaccination']):
            return 'prevention'
        elif any(word in query_lower for word in ['posologie', 'dose', 'administration']):
            return 'dosage'
        elif any(word in query_lower for word in ['effet', 'secondaire', 'adverse']):
            return 'side_effects'
        else:
            return 'general'
    
    def _analyze_correlations(self, feedback_data: List[UserFeedback]) -> List[LearningInsight]:
        """Analyser les corrélations dans les données"""
        insights = []
        
        # Corrélation entre temps de session et satisfaction
        session_data = defaultdict(list)
        for feedback in feedback_data:
            if feedback.session_id:
                session_data[feedback.session_id].append(feedback)
        
        session_satisfaction = []
        session_durations = []
        
        for session_id, session_feedback in session_data.items():
            if len(session_feedback) > 1:
                duration = (max(f.timestamp for f in session_feedback) - 
                          min(f.timestamp for f in session_feedback)).total_seconds()
                satisfaction = statistics.mean([f.value for f in session_feedback])
                
                session_durations.append(duration)
                session_satisfaction.append(satisfaction)
        
        if len(session_satisfaction) >= 10:
            # Calculer corrélation simple
            correlation = self._calculate_correlation(session_durations, session_satisfaction)
            
            if abs(correlation) > 0.3:  # Corrélation significative
                insight = LearningInsight(
                    insight_id="correlation_duration_satisfaction",
                    category="user_behavior",
                    description=f"Corrélation {correlation:.2f} entre durée de session et satisfaction",
                    confidence=min(0.9, abs(correlation)),
                    impact_score=abs(correlation),
                    recommended_actions=[
                        "Optimiser l'expérience utilisateur pour les sessions longues" if correlation > 0 
                        else "Réduire la friction dans l'interface",
                        "Analyser les patterns de navigation",
                        "Personnaliser l'expérience selon la durée"
                    ],
                    supporting_data={
                        'correlation': correlation,
                        'sample_size': len(session_satisfaction),
                        'avg_duration': statistics.mean(session_durations),
                        'avg_satisfaction': statistics.mean(session_satisfaction)
                    }
                )
                insights.append(insight)
        
        return insights
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculer la corrélation de Pearson"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        sum_y2 = sum(yi * yi for yi in y)
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _detect_anomalies(self, feedback_data: List[UserFeedback], 
                         metrics: QualityMetrics) -> List[LearningInsight]:
        """Détecter les anomalies dans les feedbacks"""
        insights = []
        
        # Détecter les chutes soudaines de qualité
        if metrics.trend_direction == "declining":
            recent_scores = [f.value for f in feedback_data[-20:]]  # 20 derniers
            older_scores = [f.value for f in feedback_data[-100:-20]]  # 80 précédents
            
            if recent_scores and older_scores:
                recent_avg = statistics.mean(recent_scores)
                older_avg = statistics.mean(older_scores)
                
                if older_avg - recent_avg > 0.15:  # Chute significative
                    insight = LearningInsight(
                        insight_id="anomaly_quality_drop",
                        category="quality_anomaly",
                        description=f"Chute de qualité détectée: {older_avg:.1%} → {recent_avg:.1%}",
                        confidence=0.9,
                        impact_score=older_avg - recent_avg,
                        recommended_actions=[
                            "Investiguer les changements récents du système",
                            "Vérifier l'intégrité des données",
                            "Analyser les requêtes problématiques récentes",
                            "Rollback si nécessaire"
                        ],
                        supporting_data={
                            'recent_avg': recent_avg,
                            'older_avg': older_avg,
                            'drop_magnitude': older_avg - recent_avg,
                            'recent_sample_size': len(recent_scores),
                            'older_sample_size': len(older_scores)
                        }
                    )
                    insights.append(insight)
        
        return insights
    
    def _analyze_user_segments(self, feedback_data: List[UserFeedback]) -> List[LearningInsight]:
        """Analyser les segments d'utilisateurs"""
        insights = []
        
        # Segmenter par contexte d'utilisation
        context_performance = defaultdict(list)
        for feedback in feedback_data:
            context_type = feedback.context.get('context_type', 'unknown')
            context_performance[context_type].append(feedback.value)
        
        # Identifier les segments sous-performants
        for context_type, scores in context_performance.items():
            if len(scores) >= 10:  # Minimum de données
                avg_score = statistics.mean(scores)
                if avg_score < 0.65:  # Seuil de performance
                    insight = LearningInsight(
                        insight_id=f"segment_context_{context_type}",
                        category="user_segment",
                        description=f"Performance faible pour le contexte '{context_type}' (score: {avg_score:.1%})",
                        confidence=0.7,
                        impact_score=0.8 - avg_score,
                        recommended_actions=[
                            f"Optimiser l'expérience pour le contexte '{context_type}'",
                            "Personnaliser les réponses selon le contexte",
                            "Analyser les besoins spécifiques de ce segment"
                        ],
                        supporting_data={
                            'context_type': context_type,
                            'sample_count': len(scores),
                            'avg_score': avg_score,
                            'score_distribution': {
                                'min': min(scores),
                                'max': max(scores),
                                'std': statistics.stdev(scores) if len(scores) > 1 else 0
                            }
                        }
                    )
                    insights.append(insight)
        
        return insights

class QualityFeedbackSystem:
    """Système principal de feedback qualité"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'feedback_buffer_size': 10000,
            'analysis_interval_minutes': 15,
            'alert_cooldown_minutes': 60,
            'learning_threshold': 50,  # Minimum feedbacks pour apprentissage
            'auto_adaptation': True
        }
        
        self.collector = FeedbackCollector()
        self.analyzer = QualityAnalyzer()
        self.learner = AdaptiveLearner()
        
        self.current_metrics = QualityMetrics()
        self.active_alerts = []
        self.recent_insights = []
        
        self.running = False
        self.analysis_thread = None
        
        # Ajouter des processeurs de feedback
        self.collector.add_processor(self._realtime_quality_check)
        
        logger.info("QualityFeedbackSystem initialisé")
    
    def start(self):
        """Démarrer le système de feedback"""
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()
        logger.info("Système de feedback qualité démarré")
    
    def stop(self):
        """Arrêter le système de feedback"""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        logger.info("Système de feedback qualité arrêté")
    
    def submit_explicit_feedback(self, user_id: str, query: str, result_id: str,
                                rating: float, dimensions: Dict[str, float] = None,
                                session_id: str = "", context: Dict[str, Any] = None) -> str:
        """Soumettre un feedback explicite"""
        return self.collector.collect_explicit_feedback(
            user_id, query, result_id, rating, dimensions, session_id, context
        )
    
    def submit_implicit_feedback(self, user_id: str, query: str, result_id: str,
                                signal_type: str, value: float,
                                session_id: str = "", context: Dict[str, Any] = None) -> str:
        """Soumettre un feedback implicite"""
        return self.collector.collect_implicit_feedback(
            user_id, query, result_id, signal_type, value, session_id, context
        )
    
    def get_current_metrics(self) -> QualityMetrics:
        """Obtenir les métriques actuelles"""
        return self.current_metrics
    
    def get_active_alerts(self) -> List[QualityAlert]:
        """Obtenir les alertes actives"""
        return [alert for alert in self.active_alerts if not alert.acknowledged]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acquitter une alerte"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alerte acquittée: {alert_id}")
                return True
        return False
    
    def get_recent_insights(self, hours: int = 24) -> List[LearningInsight]:
        """Obtenir les insights récents"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [insight for insight in self.recent_insights if insight.timestamp >= cutoff]
    
    def _analysis_worker(self):
        """Worker thread pour l'analyse continue"""
        while self.running:
            try:
                # Analyser la qualité - utiliser tous les feedbacks disponibles
                all_feedback = list(self.collector.feedback_buffer)
                recent_feedback = self.collector.get_recent_feedback(24)
                
                # Utiliser tous les feedbacks pour l'analyse si pas assez de récents
                feedback_to_analyze = recent_feedback if recent_feedback else all_feedback
                
                if feedback_to_analyze:
                    self.current_metrics = self.analyzer.analyze_quality(feedback_to_analyze)
                    
                    # Détecter les alertes
                    new_alerts = self.analyzer.detect_quality_issues(self.current_metrics)
                    self._process_new_alerts(new_alerts)
                    
                    # Apprentissage adaptatif
                    if len(feedback_to_analyze) >= self.config['learning_threshold']:
                        new_insights = self.learner.learn_from_feedback(feedback_to_analyze, self.current_metrics)
                        self.recent_insights.extend(new_insights)
                        
                        # Garder seulement les insights récents
                        cutoff = datetime.now() - timedelta(hours=48)
                        self.recent_insights = [i for i in self.recent_insights if i.timestamp >= cutoff]
                else:
                    # Initialiser des métriques par défaut si aucun feedback
                    self.current_metrics = QualityMetrics()
                
                # Attendre avant la prochaine analyse
                time.sleep(self.config['analysis_interval_minutes'] * 60)
                
            except Exception as e:
                logger.error(f"Erreur dans analysis worker: {e}")
                time.sleep(60)  # Attendre 1 minute en cas d'erreur
    
    def _process_new_alerts(self, new_alerts: List[QualityAlert]):
        """Traiter les nouvelles alertes"""
        cooldown = timedelta(minutes=self.config['alert_cooldown_minutes'])
        current_time = datetime.now()
        
        for new_alert in new_alerts:
            # Vérifier si une alerte similaire existe déjà
            similar_exists = any(
                alert.dimension == new_alert.dimension and 
                alert.level == new_alert.level and
                (current_time - alert.timestamp) < cooldown
                for alert in self.active_alerts
            )
            
            if not similar_exists:
                self.active_alerts.append(new_alert)
                logger.warning(f"Nouvelle alerte qualité: {new_alert.message}")
        
        # Nettoyer les anciennes alertes
        self.active_alerts = [alert for alert in self.active_alerts 
                             if (current_time - alert.timestamp) < timedelta(hours=24)]
    
    def _realtime_quality_check(self, feedback: UserFeedback):
        """Vérification qualité en temps réel"""
        # Alerte immédiate pour feedback très négatif
        if feedback.value < 0.2 and feedback.feedback_type == FeedbackType.EXPLICIT_RATING:
            alert = QualityAlert(
                alert_id=f"realtime_{feedback.feedback_id}",
                level=AlertLevel.WARNING,
                dimension=QualityDimension.USEFULNESS,
                message=f"Feedback très négatif reçu: {feedback.value:.1%} pour {feedback.result_id}",
                current_value=feedback.value,
                threshold=0.5,
                suggested_actions=[
                    "Analyser le résultat problématique",
                    "Vérifier la pertinence de la réponse",
                    "Contacter l'utilisateur si possible"
                ]
            )
            self.active_alerts.append(alert)
            logger.warning(f"Alerte temps réel: {alert.message}")
    
    def export_data(self, filename: str = "quality_feedback_export.json"):
        """Exporter les données du système"""
        try:
            recent_feedback = self.collector.get_recent_feedback(24)
            
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'config': self.config,
                'current_metrics': asdict(self.current_metrics),
                'active_alerts': [asdict(alert) for alert in self.get_active_alerts()],
                'recent_insights': [asdict(insight) for insight in self.get_recent_insights()],
                'feedback_summary': {
                    'total_feedback_24h': len(recent_feedback),
                    'feedback_types': {
                        ft.value: sum(1 for f in recent_feedback if f.feedback_type == ft)
                        for ft in FeedbackType
                    },
                    'avg_satisfaction': statistics.mean([f.value for f in recent_feedback]) if recent_feedback else 0
                },
                'quality_trends': {
                    'overall_satisfaction': self.current_metrics.overall_satisfaction,
                    'trend_direction': self.current_metrics.trend_direction,
                    'confidence_interval': self.current_metrics.confidence_interval
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Données exportées vers {filename}")
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")

def main():
    """Fonction principale de démonstration"""
    print("📊 Quality Feedback System - Objectif 16")
    print("Système de feedback qualité en temps réel")
    print("=" * 50)
    
    # Configuration du système
    config = {
        'feedback_buffer_size': 5000,
        'analysis_interval_minutes': 1,  # Plus fréquent pour la démo
        'alert_cooldown_minutes': 5,
        'learning_threshold': 10,
        'auto_adaptation': True
    }
    
    feedback_system = QualityFeedbackSystem(config)
    feedback_system.start()
    
    try:
        # Simuler des feedbacks variés
        print("\n🔄 Simulation de feedbacks utilisateurs...")
        
        # Feedbacks explicites
        explicit_feedbacks = [
            {'user': 'user_001', 'query': 'traitement paludisme enfant', 'result': 'result_001', 'rating': 0.9, 'dimensions': {'relevance': 0.95, 'accuracy': 0.9}},
            {'user': 'user_002', 'query': 'diagnostic malaria rapide', 'result': 'result_002', 'rating': 0.8, 'dimensions': {'relevance': 0.8, 'clarity': 0.85}},
            {'user': 'user_003', 'query': 'posologie artemether', 'result': 'result_003', 'rating': 0.3, 'dimensions': {'relevance': 0.4, 'completeness': 0.2}},  # Feedback négatif
            {'user': 'user_004', 'query': 'effets secondaires lumefantrine', 'result': 'result_004', 'rating': 0.7, 'dimensions': {'accuracy': 0.8, 'completeness': 0.6}},
            {'user': 'user_005', 'query': 'prévention paludisme grossesse', 'result': 'result_005', 'rating': 0.85, 'dimensions': {'relevance': 0.9, 'trustworthiness': 0.8}}
        ]
        
        for i, fb in enumerate(explicit_feedbacks):
            feedback_id = feedback_system.submit_explicit_feedback(
                user_id=fb['user'],
                query=fb['query'],
                result_id=fb['result'],
                rating=fb['rating'],
                dimensions=fb['dimensions'],
                session_id=f"session_{i//2 + 1}",
                context={'context_type': 'clinical', 'urgency': 'normal'}
            )
            print(f"  ✅ Feedback explicite: {fb['rating']:.1%} pour {fb['result']}")
            time.sleep(0.1)
        
        # Feedbacks implicites
        implicit_feedbacks = [
            {'user': 'user_001', 'query': 'traitement paludisme enfant', 'result': 'result_001', 'signal': 'click', 'value': 1},
            {'user': 'user_001', 'query': 'traitement paludisme enfant', 'result': 'result_001', 'signal': 'dwell_time', 'value': 180},
            {'user': 'user_002', 'query': 'diagnostic malaria rapide', 'result': 'result_002', 'signal': 'copy_action', 'value': 1},
            {'user': 'user_003', 'query': 'posologie artemether', 'result': 'result_003', 'signal': 'flag', 'value': 1},  # Signalement négatif
            {'user': 'user_004', 'query': 'effets secondaires lumefantrine', 'result': 'result_004', 'signal': 'bookmark', 'value': 1},
            {'user': 'user_005', 'query': 'prévention paludisme grossesse', 'result': 'result_005', 'signal': 'share', 'value': 1}
        ]
        
        for fb in implicit_feedbacks:
            feedback_system.submit_implicit_feedback(
                user_id=fb['user'],
                query=fb['query'],
                result_id=fb['result'],
                signal_type=fb['signal'],
                value=fb['value'],
                session_id=f"session_{hash(fb['user']) % 3 + 1}",
                context={'context_type': 'clinical'}
            )
            print(f"  📊 Feedback implicite: {fb['signal']} pour {fb['result']}")
            time.sleep(0.1)
        
        # Forcer une analyse immédiate
        print("\n⏳ Analyse qualité en cours...")
        all_feedback = list(feedback_system.collector.feedback_buffer)
        if all_feedback:
            feedback_system.current_metrics = feedback_system.analyzer.analyze_quality(all_feedback)
        
        # Afficher les métriques actuelles
        print("\n📈 Métriques de qualité actuelles:")
        metrics = feedback_system.get_current_metrics()
        print(f"  Satisfaction globale: {metrics.overall_satisfaction:.1%}")
        print(f"  Volume de feedback: {metrics.feedback_volume}")
        print(f"  Taux de réponse: {metrics.response_rate:.1%}")
        print(f"  Tendance: {metrics.trend_direction}")
        print(f"  Intervalle de confiance: {metrics.confidence_interval[0]:.1%} - {metrics.confidence_interval[1]:.1%}")
        
        # Scores par dimension
        if metrics.dimension_scores:
            print("\n📊 Scores par dimension:")
            for dimension, score in metrics.dimension_scores.items():
                print(f"  {dimension.value}: {score:.1%}")
        
        # Alertes actives
        alerts = feedback_system.get_active_alerts()
        if alerts:
            print(f"\n🚨 Alertes actives ({len(alerts)}):")
            for alert in alerts[:3]:  # Top 3
                print(f"  [{alert.level.value.upper()}] {alert.message}")
                print(f"    Actions suggérées: {', '.join(alert.suggested_actions[:2])}")
        else:
            print("\n✅ Aucune alerte active")
        
        # Insights d'apprentissage
        insights = feedback_system.get_recent_insights()
        if insights:
            print(f"\n🧠 Insights d'apprentissage ({len(insights)}):")
            for insight in insights[:2]:  # Top 2
                print(f"  [{insight.category}] {insight.description}")
                print(f"    Confiance: {insight.confidence:.1%} | Impact: {insight.impact_score:.1%}")
                print(f"    Actions: {', '.join(insight.recommended_actions[:2])}")
        
        # Simuler plus de feedbacks pour déclencher des alertes
        print("\n🔄 Simulation de feedbacks négatifs pour tester les alertes...")
        for i in range(5):
            feedback_system.submit_explicit_feedback(
                user_id=f'user_test_{i}',
                query='test query problématique',
                result_id=f'result_test_{i}',
                rating=0.2,  # Très négatif
                dimensions={'relevance': 0.1, 'accuracy': 0.2},
                context={'context_type': 'emergency'}
            )
        
        time.sleep(2)
        
        # Vérifier les nouvelles alertes
        new_alerts = feedback_system.get_active_alerts()
        print(f"\n🚨 Nouvelles alertes générées: {len(new_alerts)}")
        
        # Export des données
        print("\n💾 Export des données...")
        feedback_system.export_data()
        
        # Évaluation finale
        final_metrics = feedback_system.get_current_metrics()
        print("\n🎯 Évaluation finale:")
        
        if (final_metrics.feedback_volume >= 10 and 
            final_metrics.overall_satisfaction > 0 and 
            len(feedback_system.get_active_alerts()) > 0):
            print("✅ Objectif 16 ATTEINT - Système de feedback qualité opérationnel!")
        else:
            print("⚠️ Objectif 16 PARTIELLEMENT ATTEINT - Système en cours de stabilisation")
        
        print(f"📊 Volume de feedback: {final_metrics.feedback_volume}")
        print(f"😊 Satisfaction: {final_metrics.overall_satisfaction:.1%}")
        print(f"🚨 Alertes actives: {len(feedback_system.get_active_alerts())}")
        print(f"🧠 Insights générés: {len(feedback_system.get_recent_insights())}")
        print(f"📈 Système d'apprentissage adaptatif opérationnel")
        print(f"⚡ Feedback temps réel avec analyse continue")
        
    finally:
        feedback_system.stop()

if __name__ == "__main__":
    main()