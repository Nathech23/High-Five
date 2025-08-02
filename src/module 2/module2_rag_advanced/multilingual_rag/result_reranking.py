#!/usr/bin/env python3
"""
Re-ranking des Résultats

Objectif 15: Implémenter re-ranking des résultats

Ce module implémente un système de re-ranking intelligent pour améliorer
la pertinence des résultats de recherche en utilisant plusieurs critères
de scoring et des modèles de re-ranking avancés.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
import numpy as np
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from collections import defaultdict, Counter
import time
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import MinMaxScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn non disponible")
    SKLEARN_AVAILABLE = False

try:
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    logger.warning("SciPy non disponible")
    SCIPY_AVAILABLE = False

class RerankingStrategy(Enum):
    """Stratégies de re-ranking"""
    SIMILARITY_BASED = "similarity_based"  # Basé sur la similarité
    MEDICAL_RELEVANCE = "medical_relevance"  # Pertinence médicale
    LANGUAGE_PREFERENCE = "language_preference"  # Préférence linguistique
    TEMPORAL_RELEVANCE = "temporal_relevance"  # Pertinence temporelle
    SOURCE_AUTHORITY = "source_authority"  # Autorité de la source
    USER_CONTEXT = "user_context"  # Contexte utilisateur
    HYBRID_SCORING = "hybrid_scoring"  # Scoring hybride
    LEARNING_TO_RANK = "learning_to_rank"  # Apprentissage du ranking

class ScoringCriterion(Enum):
    """Critères de scoring"""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    KEYWORD_MATCH = "keyword_match"
    MEDICAL_TERM_DENSITY = "medical_term_density"
    LANGUAGE_MATCH = "language_match"
    DOCUMENT_QUALITY = "document_quality"
    RECENCY = "recency"
    SOURCE_RELIABILITY = "source_reliability"
    USER_PREFERENCE = "user_preference"
    CLINICAL_RELEVANCE = "clinical_relevance"
    READABILITY = "readability"

class MedicalDomain(Enum):
    """Domaines médicaux"""
    GENERAL = "general"
    CARDIOLOGY = "cardiology"
    INFECTIOUS_DISEASES = "infectious_diseases"
    PEDIATRICS = "pediatrics"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    PREVENTIVE = "preventive"
    MENTAL_HEALTH = "mental_health"
    GYNECOLOGY = "gynecology"
    DERMATOLOGY = "dermatology"

@dataclass
class SearchResult:
    """Résultat de recherche à re-ranker"""
    id: str
    content: str
    title: Optional[str] = None
    language: str = "fr"
    original_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    medical_terms: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    source: Optional[str] = None
    created_date: Optional[datetime] = None
    author: Optional[str] = None
    document_type: Optional[str] = None
    quality_indicators: Dict[str, float] = field(default_factory=dict)

@dataclass
class RerankingQuery:
    """Requête pour le re-ranking"""
    text: str
    language: str = "fr"
    domain: Optional[MedicalDomain] = None
    user_context: Dict[str, Any] = field(default_factory=dict)
    preferred_languages: List[str] = field(default_factory=list)
    temporal_preference: Optional[str] = None  # "recent", "classic", "any"
    source_preferences: List[str] = field(default_factory=list)
    clinical_context: Dict[str, Any] = field(default_factory=dict)
    boost_factors: Dict[str, float] = field(default_factory=dict)

@dataclass
class ScoringFeatures:
    """Features pour le scoring"""
    semantic_similarity: float = 0.0
    keyword_overlap: float = 0.0
    medical_term_match: float = 0.0
    language_bonus: float = 0.0
    domain_relevance: float = 0.0
    source_authority: float = 0.0
    recency_score: float = 0.0
    quality_score: float = 0.0
    readability_score: float = 0.0
    clinical_relevance: float = 0.0
    user_preference: float = 0.0
    cross_lingual_penalty: float = 0.0

@dataclass
class RerankingResult:
    """Résultat du re-ranking"""
    result: SearchResult
    original_rank: int
    new_rank: int
    original_score: float
    reranked_score: float
    score_breakdown: ScoringFeatures
    explanation: str
    confidence: float
    boost_applied: Dict[str, float] = field(default_factory=dict)
    penalties_applied: Dict[str, float] = field(default_factory=dict)

@dataclass
class RerankingStats:
    """Statistiques de re-ranking"""
    total_rerankings: int = 0
    avg_score_improvement: float = 0.0
    avg_rank_changes: float = 0.0
    strategy_usage: Dict[str, int] = field(default_factory=dict)
    domain_performance: Dict[str, float] = field(default_factory=dict)
    language_performance: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    avg_processing_time: float = 0.0

class ResultReranking:
    """
    Système de re-ranking des résultats
    
    Objectif couvert:
    - 15. Implémenter re-ranking des résultats
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = RerankingStats()
        
        # Configuration des poids par défaut
        self.default_weights = {
            ScoringCriterion.SEMANTIC_SIMILARITY: 0.25,
            ScoringCriterion.KEYWORD_MATCH: 0.15,
            ScoringCriterion.MEDICAL_TERM_DENSITY: 0.20,
            ScoringCriterion.LANGUAGE_MATCH: 0.10,
            ScoringCriterion.DOCUMENT_QUALITY: 0.10,
            ScoringCriterion.RECENCY: 0.05,
            ScoringCriterion.SOURCE_RELIABILITY: 0.10,
            ScoringCriterion.CLINICAL_RELEVANCE: 0.05
        }
        
        # Poids par domaine médical
        self.domain_weights = {
            MedicalDomain.EMERGENCY: {
                ScoringCriterion.CLINICAL_RELEVANCE: 0.35,
                ScoringCriterion.RECENCY: 0.15,
                ScoringCriterion.SOURCE_RELIABILITY: 0.20
            },
            MedicalDomain.INFECTIOUS_DISEASES: {
                ScoringCriterion.MEDICAL_TERM_DENSITY: 0.30,
                ScoringCriterion.RECENCY: 0.10,
                ScoringCriterion.SOURCE_RELIABILITY: 0.15
            },
            MedicalDomain.PREVENTIVE: {
                ScoringCriterion.READABILITY: 0.20,
                ScoringCriterion.LANGUAGE_MATCH: 0.15,
                ScoringCriterion.USER_PREFERENCE: 0.10
            }
        }
        
        # Autorité des sources
        self.source_authority = {
            "WHO": 1.0,
            "CDC": 0.95,
            "OMS": 1.0,
            "Ministère Santé Cameroun": 0.90,
            "HGD": 0.85,
            "PubMed": 0.90,
            "Cochrane": 0.95,
            "UpToDate": 0.85,
            "Medscape": 0.75,
            "Wikipedia": 0.50,
            "Blog médical": 0.30,
            "Forum": 0.20
        }
        
        # Termes médicaux par domaine
        self.domain_terms = {
            MedicalDomain.INFECTIOUS_DISEASES: {
                "fr": ["infection", "virus", "bactérie", "paludisme", "tuberculose", "VIH", "antibiotique"],
                "en": ["infection", "virus", "bacteria", "malaria", "tuberculosis", "HIV", "antibiotic"],
                "ff": ["nayeejo", "ɓernde", "paludisme"],
                "ar": ["عدوى", "فيروس", "بكتيريا", "ملاريا"]
            },
            MedicalDomain.CARDIOLOGY: {
                "fr": ["cœur", "cardiaque", "hypertension", "infarctus", "arythmie"],
                "en": ["heart", "cardiac", "hypertension", "infarction", "arrhythmia"],
                "ff": ["ɓernde buurde", "hypertension"],
                "ar": ["قلب", "قلبي", "ارتفاع ضغط الدم"]
            },
            MedicalDomain.EMERGENCY: {
                "fr": ["urgence", "trauma", "réanimation", "choc", "hémorragie"],
                "en": ["emergency", "trauma", "resuscitation", "shock", "hemorrhage"],
                "ff": ["gaggal", "ɓernde ɓurɗo"],
                "ar": ["طوارئ", "صدمة", "إنعاش"]
            }
        }
        
        # Cache de features
        self.features_cache: Dict[str, ScoringFeatures] = {}
        self.max_cache_size = self.config.get("max_cache_size", 1000)
        
        # Modèles de scoring
        self.tfidf_vectorizer = None
        self.scaler = MinMaxScaler() if SKLEARN_AVAILABLE else None
        
        # Initialiser les composants
        self._init_scoring_models()
        
        logger.info("Système de re-ranking initialisé")
    
    def _init_scoring_models(self):
        """Initialise les modèles de scoring"""
        if SKLEARN_AVAILABLE:
            # Vectoriseur TF-IDF pour la similarité textuelle
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,  # Géré manuellement pour le multilingue
                ngram_range=(1, 2),
                lowercase=True
            )
            
            logger.info("Modèles de scoring TF-IDF initialisés")
    
    def _get_cache_key(self, query: RerankingQuery, result: SearchResult) -> str:
        """Génère une clé de cache pour les features"""
        content = f"{query.text}_{result.id}_{query.language}_{query.domain}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _extract_keywords(self, text: str, language: str) -> List[str]:
        """Extrait les mots-clés d'un texte"""
        # Mots vides par langue
        stopwords = {
            "fr": {"le", "la", "les", "de", "du", "des", "et", "est", "une", "un", "dans", "pour", "avec", "sur", "par", "ce", "cette", "que", "qui"},
            "en": {"the", "and", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by", "a", "an", "this", "that"},
            "ff": {"ko", "e", "o", "ɗo", "ɓe", "mo", "no", "wo"},
            "ar": {"في", "من", "إلى", "على", "هذا", "هذه"}
        }
        
        # Nettoyer et diviser le texte
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrer les mots vides
        lang_stopwords = stopwords.get(language, set())
        keywords = [word for word in words if len(word) > 2 and word not in lang_stopwords]
        
        return keywords
    
    def _calculate_semantic_similarity(self, query_text: str, result_content: str) -> float:
        """Calcule la similarité sémantique entre la requête et le résultat"""
        if not SKLEARN_AVAILABLE:
            # Fallback: similarité basée sur les mots communs
            query_words = set(self._extract_keywords(query_text, "fr"))
            result_words = set(self._extract_keywords(result_content, "fr"))
            
            if not query_words or not result_words:
                return 0.0
            
            intersection = query_words & result_words
            union = query_words | result_words
            
            return len(intersection) / len(union) if union else 0.0
        
        try:
            # Utiliser TF-IDF pour la similarité
            texts = [query_text, result_content]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            return float(similarity_matrix[0, 1])
        
        except Exception as e:
            logger.warning(f"Erreur calcul similarité sémantique: {e}")
            return 0.0
    
    def _calculate_keyword_overlap(self, query: RerankingQuery, result: SearchResult) -> float:
        """Calcule le chevauchement de mots-clés"""
        query_keywords = set(self._extract_keywords(query.text, query.language))
        result_keywords = set(self._extract_keywords(result.content, result.language))
        
        if not query_keywords:
            return 0.0
        
        # Intersection pondérée
        intersection = query_keywords & result_keywords
        overlap_score = len(intersection) / len(query_keywords)
        
        # Bonus pour les mots-clés dans le titre
        if result.title:
            title_keywords = set(self._extract_keywords(result.title, result.language))
            title_intersection = query_keywords & title_keywords
            title_bonus = len(title_intersection) / len(query_keywords) * 0.5
            overlap_score += title_bonus
        
        return min(overlap_score, 1.0)
    
    def _calculate_medical_term_match(self, query: RerankingQuery, result: SearchResult) -> float:
        """Calcule la correspondance des termes médicaux"""
        if not query.domain:
            return 0.5  # Score neutre si pas de domaine spécifié
        
        domain_terms = self.domain_terms.get(query.domain, {})
        query_lang_terms = set(domain_terms.get(query.language, []))
        result_lang_terms = set(domain_terms.get(result.language, []))
        
        # Termes médicaux dans la requête
        query_text_lower = query.text.lower()
        query_medical_terms = {term for term in query_lang_terms if term in query_text_lower}
        
        # Termes médicaux dans le résultat
        result_text_lower = result.content.lower()
        result_medical_terms = {term for term in result_lang_terms if term in result_text_lower}
        
        # Ajouter les termes médicaux explicites du résultat
        if result.medical_terms:
            result_medical_terms.update(term.lower() for term in result.medical_terms)
        
        if not query_medical_terms and not result_medical_terms:
            return 0.5  # Score neutre
        
        if not query_medical_terms:
            return 0.3  # Pénalité légère si pas de termes médicaux dans la requête
        
        # Calculer la correspondance
        intersection = query_medical_terms & result_medical_terms
        match_score = len(intersection) / len(query_medical_terms)
        
        # Bonus pour la densité de termes médicaux
        density_bonus = len(result_medical_terms) / max(len(result.content.split()), 1) * 10
        density_bonus = min(density_bonus, 0.3)
        
        return min(match_score + density_bonus, 1.0)
    
    def _calculate_language_bonus(self, query: RerankingQuery, result: SearchResult) -> float:
        """Calcule le bonus de langue"""
        # Bonus pour la correspondance exacte de langue
        if result.language == query.language:
            return 1.0
        
        # Bonus pour les langues préférées
        if query.preferred_languages and result.language in query.preferred_languages:
            preference_index = query.preferred_languages.index(result.language)
            return 1.0 - (preference_index * 0.1)  # Diminution de 10% par rang
        
        # Bonus pour les familles de langues
        language_families = {
            "romance": {"fr", "es", "it"},
            "germanic": {"en", "de", "nl"},
            "niger_congo": {"ff", "ewondo", "duala", "bamileke"},
            "afroasiatic": {"ar", "ha"}
        }
        
        for family, languages in language_families.items():
            if query.language in languages and result.language in languages:
                return 0.7  # Bonus pour la même famille
        
        # Pénalité pour les langues très différentes
        return 0.3
    
    def _calculate_domain_relevance(self, query: RerankingQuery, result: SearchResult) -> float:
        """Calcule la pertinence du domaine"""
        if not query.domain:
            return 0.5  # Score neutre
        
        # Correspondance exacte du domaine
        if result.domain and result.domain.lower() == query.domain.value.lower():
            return 1.0
        
        # Correspondance partielle basée sur les termes du domaine
        domain_terms = self.domain_terms.get(query.domain, {})
        all_domain_terms = set()
        for lang_terms in domain_terms.values():
            all_domain_terms.update(term.lower() for term in lang_terms)
        
        result_text_lower = result.content.lower()
        matching_terms = sum(1 for term in all_domain_terms if term in result_text_lower)
        
        if all_domain_terms:
            relevance = matching_terms / len(all_domain_terms)
            return min(relevance * 2, 1.0)  # Amplifier le score
        
        return 0.5
    
    def _calculate_source_authority(self, result: SearchResult) -> float:
        """Calcule l'autorité de la source"""
        if not result.source:
            return 0.5  # Score neutre
        
        # Recherche exacte
        if result.source in self.source_authority:
            return self.source_authority[result.source]
        
        # Recherche partielle
        source_lower = result.source.lower()
        for auth_source, score in self.source_authority.items():
            if auth_source.lower() in source_lower or source_lower in auth_source.lower():
                return score
        
        # Score par défaut pour les sources inconnues
        return 0.4
    
    def _calculate_recency_score(self, result: SearchResult, temporal_preference: Optional[str] = None) -> float:
        """Calcule le score de récence"""
        if not result.created_date:
            return 0.5  # Score neutre si pas de date
        
        now = datetime.now()
        age_days = (now - result.created_date).days
        
        if temporal_preference == "recent":
            # Préférence pour les documents récents
            if age_days <= 30:
                return 1.0
            elif age_days <= 365:
                return 1.0 - (age_days - 30) / 335 * 0.5  # Décroissance linéaire
            else:
                return 0.5 - min((age_days - 365) / 1825, 0.4)  # Décroissance plus lente
        
        elif temporal_preference == "classic":
            # Préférence pour les documents établis
            if age_days >= 365:
                return 1.0
            else:
                return 0.5 + (age_days / 365) * 0.5
        
        else:
            # Pas de préférence temporelle forte
            if age_days <= 1825:  # 5 ans
                return 1.0 - (age_days / 1825) * 0.3
            else:
                return 0.7
    
    def _calculate_quality_score(self, result: SearchResult) -> float:
        """Calcule le score de qualité du document"""
        quality_score = 0.5  # Score de base
        
        # Indicateurs de qualité explicites
        if result.quality_indicators:
            explicit_quality = sum(result.quality_indicators.values()) / len(result.quality_indicators)
            quality_score = (quality_score + explicit_quality) / 2
        
        # Longueur du contenu (ni trop court ni trop long)
        content_length = len(result.content)
        if 200 <= content_length <= 2000:
            length_bonus = 0.2
        elif 100 <= content_length <= 5000:
            length_bonus = 0.1
        else:
            length_bonus = -0.1
        
        quality_score += length_bonus
        
        # Présence d'un titre
        if result.title and len(result.title.strip()) > 5:
            quality_score += 0.1
        
        # Présence de métadonnées
        if result.metadata:
            metadata_bonus = min(len(result.metadata) * 0.02, 0.1)
            quality_score += metadata_bonus
        
        # Présence de termes médicaux
        if result.medical_terms:
            medical_bonus = min(len(result.medical_terms) * 0.05, 0.2)
            quality_score += medical_bonus
        
        return min(max(quality_score, 0.0), 1.0)
    
    def _calculate_readability_score(self, result: SearchResult) -> float:
        """Calcule le score de lisibilité"""
        content = result.content
        
        # Métriques de base
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = re.findall(r'\b\w+\b', content)
        
        if not sentences or not words:
            return 0.5
        
        # Longueur moyenne des phrases
        avg_sentence_length = len(words) / len(sentences)
        
        # Longueur moyenne des mots
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Score basé sur des valeurs optimales
        optimal_sentence_length = 15  # mots par phrase
        optimal_word_length = 5  # caractères par mot
        
        sentence_score = 1.0 - abs(avg_sentence_length - optimal_sentence_length) / optimal_sentence_length
        word_score = 1.0 - abs(avg_word_length - optimal_word_length) / optimal_word_length
        
        # Normaliser
        sentence_score = max(0.0, min(1.0, sentence_score))
        word_score = max(0.0, min(1.0, word_score))
        
        # Bonus pour la structure (listes, paragraphes)
        structure_bonus = 0.0
        if '\n' in content:  # Paragraphes
            structure_bonus += 0.1
        if re.search(r'^\s*[-•*]', content, re.MULTILINE):  # Listes
            structure_bonus += 0.1
        
        readability = (sentence_score + word_score) / 2 + structure_bonus
        return min(readability, 1.0)
    
    def _calculate_clinical_relevance(self, query: RerankingQuery, result: SearchResult) -> float:
        """Calcule la pertinence clinique"""
        clinical_indicators = {
            "fr": ["diagnostic", "traitement", "symptôme", "patient", "clinique", "thérapie", "médication", "posologie"],
            "en": ["diagnosis", "treatment", "symptom", "patient", "clinical", "therapy", "medication", "dosage"],
            "ff": ["jannginoore", "jammirgal", "neddo", "dokotoro"],
            "ar": ["تشخيص", "علاج", "أعراض", "مريض", "سريري"]
        }
        
        # Contexte clinique de la requête
        clinical_context = query.clinical_context
        if clinical_context:
            context_score = 0.0
            
            # Urgence
            if clinical_context.get("urgency") == "high":
                context_score += 0.3
            
            # Type de patient
            patient_type = clinical_context.get("patient_type")
            if patient_type and patient_type.lower() in result.content.lower():
                context_score += 0.2
            
            # Spécialité
            specialty = clinical_context.get("specialty")
            if specialty and specialty.lower() in result.content.lower():
                context_score += 0.2
            
            return min(context_score, 0.7)
        
        # Score basé sur les indicateurs cliniques
        query_lang = query.language
        indicators = clinical_indicators.get(query_lang, clinical_indicators["fr"])
        
        query_text_lower = query.text.lower()
        result_text_lower = result.content.lower()
        
        query_clinical_terms = sum(1 for indicator in indicators if indicator in query_text_lower)
        result_clinical_terms = sum(1 for indicator in indicators if indicator in result_text_lower)
        
        if query_clinical_terms == 0:
            return 0.5  # Score neutre
        
        clinical_match = result_clinical_terms / len(indicators)
        query_clinical_ratio = query_clinical_terms / len(indicators)
        
        relevance = (clinical_match + query_clinical_ratio) / 2
        return min(relevance * 2, 1.0)  # Amplifier le score
    
    def _calculate_user_preference(self, query: RerankingQuery, result: SearchResult) -> float:
        """Calcule le score de préférence utilisateur"""
        user_context = query.user_context
        if not user_context:
            return 0.5
        
        preference_score = 0.5
        
        # Préférences de langue
        preferred_langs = user_context.get("preferred_languages", [])
        if preferred_langs and result.language in preferred_langs:
            lang_index = preferred_langs.index(result.language)
            preference_score += 0.3 * (1 - lang_index * 0.1)
        
        # Préférences de source
        preferred_sources = user_context.get("preferred_sources", [])
        if preferred_sources and result.source:
            for pref_source in preferred_sources:
                if pref_source.lower() in result.source.lower():
                    preference_score += 0.2
                    break
        
        # Niveau d'expertise
        expertise_level = user_context.get("expertise_level", "general")
        if expertise_level == "expert" and result.document_type == "research":
            preference_score += 0.2
        elif expertise_level == "general" and result.document_type == "patient_info":
            preference_score += 0.2
        
        # Préférences de domaine
        preferred_domains = user_context.get("preferred_domains", [])
        if preferred_domains and result.domain:
            if result.domain in preferred_domains:
                preference_score += 0.3
        
        return min(preference_score, 1.0)
    
    def _extract_features(self, query: RerankingQuery, result: SearchResult) -> ScoringFeatures:
        """Extrait toutes les features de scoring"""
        # Vérifier le cache
        cache_key = self._get_cache_key(query, result)
        if cache_key in self.features_cache:
            return self.features_cache[cache_key]
        
        # Calculer les features
        features = ScoringFeatures(
            semantic_similarity=self._calculate_semantic_similarity(query.text, result.content),
            keyword_overlap=self._calculate_keyword_overlap(query, result),
            medical_term_match=self._calculate_medical_term_match(query, result),
            language_bonus=self._calculate_language_bonus(query, result),
            domain_relevance=self._calculate_domain_relevance(query, result),
            source_authority=self._calculate_source_authority(result),
            recency_score=self._calculate_recency_score(result, query.temporal_preference),
            quality_score=self._calculate_quality_score(result),
            readability_score=self._calculate_readability_score(result),
            clinical_relevance=self._calculate_clinical_relevance(query, result),
            user_preference=self._calculate_user_preference(query, result),
            cross_lingual_penalty=0.0 if result.language == query.language else 0.1
        )
        
        # Mettre en cache
        if len(self.features_cache) < self.max_cache_size:
            self.features_cache[cache_key] = features
        
        return features
    
    def _get_scoring_weights(self, query: RerankingQuery, strategy: RerankingStrategy) -> Dict[ScoringCriterion, float]:
        """Récupère les poids de scoring selon la stratégie et le domaine"""
        weights = self.default_weights.copy()
        
        # Ajuster selon le domaine
        if query.domain and query.domain in self.domain_weights:
            domain_adjustments = self.domain_weights[query.domain]
            for criterion, adjustment in domain_adjustments.items():
                weights[criterion] = adjustment
        
        # Ajuster selon la stratégie
        if strategy == RerankingStrategy.MEDICAL_RELEVANCE:
            weights[ScoringCriterion.MEDICAL_TERM_DENSITY] *= 2.0
            weights[ScoringCriterion.CLINICAL_RELEVANCE] *= 2.0
            weights[ScoringCriterion.SOURCE_RELIABILITY] *= 1.5
        
        elif strategy == RerankingStrategy.LANGUAGE_PREFERENCE:
            weights[ScoringCriterion.LANGUAGE_MATCH] *= 3.0
            weights[ScoringCriterion.READABILITY] *= 1.5
        
        elif strategy == RerankingStrategy.TEMPORAL_RELEVANCE:
            weights[ScoringCriterion.RECENCY] *= 3.0
        
        elif strategy == RerankingStrategy.SOURCE_AUTHORITY:
            weights[ScoringCriterion.SOURCE_RELIABILITY] *= 2.5
            weights[ScoringCriterion.DOCUMENT_QUALITY] *= 1.5
        
        elif strategy == RerankingStrategy.USER_CONTEXT:
            weights[ScoringCriterion.USER_PREFERENCE] *= 2.0
            weights[ScoringCriterion.LANGUAGE_MATCH] *= 1.5
        
        # Normaliser les poids
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def _calculate_final_score(self, features: ScoringFeatures, weights: Dict[ScoringCriterion, float],
                             query: RerankingQuery) -> Tuple[float, str]:
        """Calcule le score final et génère une explication"""
        score_components = {
            ScoringCriterion.SEMANTIC_SIMILARITY: features.semantic_similarity,
            ScoringCriterion.KEYWORD_MATCH: features.keyword_overlap,
            ScoringCriterion.MEDICAL_TERM_DENSITY: features.medical_term_match,
            ScoringCriterion.LANGUAGE_MATCH: features.language_bonus,
            ScoringCriterion.DOCUMENT_QUALITY: features.quality_score,
            ScoringCriterion.RECENCY: features.recency_score,
            ScoringCriterion.SOURCE_RELIABILITY: features.source_authority,
            ScoringCriterion.CLINICAL_RELEVANCE: features.clinical_relevance,
            ScoringCriterion.READABILITY: features.readability_score,
            ScoringCriterion.USER_PREFERENCE: features.user_preference
        }
        
        # Calculer le score pondéré
        final_score = 0.0
        explanation_parts = []
        
        for criterion, weight in weights.items():
            if criterion in score_components:
                component_score = score_components[criterion]
                weighted_score = component_score * weight
                final_score += weighted_score
                
                if weight > 0.05:  # Inclure dans l'explication si poids significatif
                    explanation_parts.append(
                        f"{criterion.value}: {component_score:.2f} (poids: {weight:.2f})"
                    )
        
        # Appliquer les boosts personnalisés
        boost_total = 0.0
        if query.boost_factors:
            for boost_type, boost_value in query.boost_factors.items():
                if boost_type in ["medical", "clinical"] and features.medical_term_match > 0.7:
                    boost_total += boost_value
                elif boost_type == "language" and features.language_bonus > 0.8:
                    boost_total += boost_value
                elif boost_type == "quality" and features.quality_score > 0.8:
                    boost_total += boost_value
        
        final_score += boost_total
        
        # Appliquer la pénalité cross-linguale
        final_score -= features.cross_lingual_penalty
        
        # Normaliser le score
        final_score = max(0.0, min(1.0, final_score))
        
        # Générer l'explication
        explanation = "; ".join(explanation_parts[:3])  # Top 3 composants
        if boost_total > 0:
            explanation += f"; Boost appliqué: +{boost_total:.2f}"
        if features.cross_lingual_penalty > 0:
            explanation += f"; Pénalité cross-linguale: -{features.cross_lingual_penalty:.2f}"
        
        return final_score, explanation
    
    def rerank_results(self, query: RerankingQuery, results: List[SearchResult],
                      strategy: RerankingStrategy = RerankingStrategy.HYBRID_SCORING,
                      max_results: Optional[int] = None) -> List[RerankingResult]:
        """
        Re-ranke une liste de résultats de recherche
        
        Args:
            query: Requête de re-ranking
            results: Liste des résultats à re-ranker
            strategy: Stratégie de re-ranking
            max_results: Nombre maximum de résultats à retourner
        
        Returns:
            List[RerankingResult]: Résultats re-rankés
        """
        start_time = time.time()
        
        try:
            if not results:
                return []
            
            # Récupérer les poids de scoring
            weights = self._get_scoring_weights(query, strategy)
            
            # Calculer les scores pour chaque résultat
            reranked_results = []
            
            for i, result in enumerate(results):
                # Extraire les features
                features = self._extract_features(query, result)
                
                # Calculer le score final
                final_score, explanation = self._calculate_final_score(features, weights, query)
                
                # Calculer la confiance
                confidence = self._calculate_confidence(features, weights)
                
                # Créer le résultat re-ranké
                reranked_result = RerankingResult(
                    result=result,
                    original_rank=i + 1,
                    new_rank=0,  # Sera mis à jour après le tri
                    original_score=result.original_score,
                    reranked_score=final_score,
                    score_breakdown=features,
                    explanation=explanation,
                    confidence=confidence,
                    boost_applied=query.boost_factors.copy() if query.boost_factors else {},
                    penalties_applied={"cross_lingual": features.cross_lingual_penalty} if features.cross_lingual_penalty > 0 else {}
                )
                
                reranked_results.append(reranked_result)
            
            # Trier par score décroissant
            reranked_results.sort(key=lambda x: x.reranked_score, reverse=True)
            
            # Mettre à jour les nouveaux rangs
            for i, result in enumerate(reranked_results):
                result.new_rank = i + 1
            
            # Limiter le nombre de résultats si spécifié
            if max_results:
                reranked_results = reranked_results[:max_results]
            
            # Mettre à jour les statistiques
            processing_time = time.time() - start_time
            self._update_reranking_stats(query, reranked_results, strategy, processing_time)
            
            return reranked_results
        
        except Exception as e:
            logger.error(f"Erreur lors du re-ranking: {e}")
            # Retourner les résultats originaux en cas d'erreur
            return [
                RerankingResult(
                    result=result,
                    original_rank=i + 1,
                    new_rank=i + 1,
                    original_score=result.original_score,
                    reranked_score=result.original_score,
                    score_breakdown=ScoringFeatures(),
                    explanation="Erreur de re-ranking",
                    confidence=0.0
                )
                for i, result in enumerate(results)
            ]
    
    def _calculate_confidence(self, features: ScoringFeatures, weights: Dict[ScoringCriterion, float]) -> float:
        """Calcule la confiance dans le score de re-ranking"""
        # Variance des scores de features
        feature_scores = [
            features.semantic_similarity,
            features.keyword_overlap,
            features.medical_term_match,
            features.language_bonus,
            features.quality_score,
            features.source_authority
        ]
        
        if not feature_scores:
            return 0.5
        
        # Calculer la variance
        mean_score = sum(feature_scores) / len(feature_scores)
        variance = sum((score - mean_score) ** 2 for score in feature_scores) / len(feature_scores)
        
        # Confiance inversement proportionnelle à la variance
        confidence = 1.0 / (1.0 + variance * 2)
        
        # Ajuster selon la qualité des features
        if features.semantic_similarity > 0.8 and features.medical_term_match > 0.7:
            confidence += 0.2
        
        if features.source_authority > 0.8:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _update_reranking_stats(self, query: RerankingQuery, results: List[RerankingResult],
                              strategy: RerankingStrategy, processing_time: float):
        """Met à jour les statistiques de re-ranking"""
        self.stats.total_rerankings += 1
        
        # Amélioration moyenne du score
        if results:
            score_improvements = [r.reranked_score - r.original_score for r in results]
            avg_improvement = sum(score_improvements) / len(score_improvements)
            
            if self.stats.total_rerankings > 1:
                self.stats.avg_score_improvement = (
                    (self.stats.avg_score_improvement * (self.stats.total_rerankings - 1) + avg_improvement) /
                    self.stats.total_rerankings
                )
            else:
                self.stats.avg_score_improvement = avg_improvement
            
            # Changements de rang moyens
            rank_changes = [abs(r.new_rank - r.original_rank) for r in results]
            avg_rank_change = sum(rank_changes) / len(rank_changes)
            
            if self.stats.total_rerankings > 1:
                self.stats.avg_rank_changes = (
                    (self.stats.avg_rank_changes * (self.stats.total_rerankings - 1) + avg_rank_change) /
                    self.stats.total_rerankings
                )
            else:
                self.stats.avg_rank_changes = avg_rank_change
        
        # Usage des stratégies
        self.stats.strategy_usage[strategy.value] = self.stats.strategy_usage.get(strategy.value, 0) + 1
        
        # Performance par domaine
        if query.domain:
            domain_key = query.domain.value
            if results:
                avg_confidence = sum(r.confidence for r in results) / len(results)
                if domain_key in self.stats.domain_performance:
                    current_perf = self.stats.domain_performance[domain_key]
                    self.stats.domain_performance[domain_key] = (current_perf + avg_confidence) / 2
                else:
                    self.stats.domain_performance[domain_key] = avg_confidence
        
        # Performance par langue
        if results:
            for result in results:
                lang = result.result.language
                if lang in self.stats.language_performance:
                    current_perf = self.stats.language_performance[lang]
                    self.stats.language_performance[lang] = (current_perf + result.confidence) / 2
                else:
                    self.stats.language_performance[lang] = result.confidence
        
        # Temps de traitement
        if self.stats.total_rerankings > 1:
            self.stats.avg_processing_time = (
                (self.stats.avg_processing_time * (self.stats.total_rerankings - 1) + processing_time) /
                self.stats.total_rerankings
            )
        else:
            self.stats.avg_processing_time = processing_time
    
    def generate_stats(self) -> RerankingStats:
        """Génère les statistiques de re-ranking"""
        start_time = time.time()
        self.stats.processing_time = time.time() - start_time
        return self.stats
    
    def export_reranking_data(self, output_path: str):
        """Exporte les données de re-ranking"""
        export_data = {
            "metadata": {
                "total_rerankings": self.stats.total_rerankings,
                "supported_strategies": [s.value for s in RerankingStrategy],
                "scoring_criteria": [c.value for c in ScoringCriterion],
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "configuration": {
                "default_weights": {k.value: v for k, v in self.default_weights.items()},
                "source_authority": self.source_authority,
                "domain_weights": {
                    domain.value: {k.value: v for k, v in weights.items()}
                    for domain, weights in self.domain_weights.items()
                },
                "max_cache_size": self.max_cache_size
            },
            "statistics": {
                "avg_score_improvement": self.stats.avg_score_improvement,
                "avg_rank_changes": self.stats.avg_rank_changes,
                "strategy_usage": self.stats.strategy_usage,
                "domain_performance": self.stats.domain_performance,
                "language_performance": self.stats.language_performance,
                "avg_processing_time": self.stats.avg_processing_time
            },
            "domain_terms": {
                domain.value: terms for domain, terms in self.domain_terms.items()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de re-ranking exportées: {output_path}")

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("🔄 Test du Re-ranking des Résultats")
    
    # Créer le système de re-ranking
    reranking_system = ResultReranking({
        "max_cache_size": 500
    })
    
    # Requête de test
    query = RerankingQuery(
        text="paludisme fièvre traitement",
        language="fr",
        domain=MedicalDomain.INFECTIOUS_DISEASES,
        preferred_languages=["fr", "en"],
        temporal_preference="recent",
        clinical_context={
            "urgency": "high",
            "patient_type": "adult",
            "specialty": "infectiologie"
        },
        boost_factors={
            "medical": 0.2,
            "clinical": 0.1
        }
    )
    
    # Résultats de test
    test_results = [
        SearchResult(
            id="result_1",
            content="Le paludisme est une maladie parasitaire grave transmise par les moustiques. Le traitement standard inclut l'artéméther-luméfantrine pour les cas non compliqués.",
            title="Paludisme - Traitement standard",
            language="fr",
            original_score=0.85,
            medical_terms=["paludisme", "traitement", "artéméther-luméfantrine"],
            domain="infectious_diseases",
            source="OMS",
            created_date=datetime(2024, 1, 15),
            document_type="clinical_guideline",
            quality_indicators={"peer_reviewed": 1.0, "official_source": 1.0}
        ),
        SearchResult(
            id="result_2",
            content="Malaria is a serious parasitic disease. Treatment with artemether-lumefantrine is recommended for uncomplicated cases. Early diagnosis is crucial.",
            title="Malaria Treatment Guidelines",
            language="en",
            original_score=0.75,
            medical_terms=["malaria", "treatment", "artemether-lumefantrine"],
            domain="infectious_diseases",
            source="CDC",
            created_date=datetime(2023, 12, 10),
            document_type="clinical_guideline",
            quality_indicators={"peer_reviewed": 1.0, "official_source": 0.95}
        ),
        SearchResult(
            id="result_3",
            content="Nayeejo paludisme ko nayeejo ɓurɗo mo anopheles ɗon haɓa. Jannginoore artéméther-luméfantrine ena waɗi.",
            title="Paludisme - Jannginoore",
            language="ff",
            original_score=0.60,
            medical_terms=["nayeejo paludisme", "jannginoore"],
            domain="infectious_diseases",
            source="Ministère Santé Cameroun",
            created_date=datetime(2024, 2, 1),
            document_type="patient_info",
            quality_indicators={"official_source": 0.9, "local_relevance": 1.0}
        ),
        SearchResult(
            id="result_4",
            content="La fièvre peut avoir plusieurs causes. Il est important de consulter un médecin pour un diagnostic approprié.",
            title="Fièvre - Information générale",
            language="fr",
            original_score=0.45,
            medical_terms=["fièvre", "diagnostic"],
            domain="general",
            source="Blog médical",
            created_date=datetime(2022, 6, 15),
            document_type="blog_post",
            quality_indicators={"readability": 0.8}
        ),
        SearchResult(
            id="result_5",
            content="الملاريا مرض طفيلي خطير. العلاج بالأرتيميثر-لوميفانترين فعال للحالات غير المعقدة.",
            title="الملاريا - العلاج",
            language="ar",
            original_score=0.70,
            medical_terms=["الملاريا", "العلاج"],
            domain="infectious_diseases",
            source="WHO",
            created_date=datetime(2024, 1, 20),
            document_type="clinical_guideline",
            quality_indicators={"peer_reviewed": 1.0, "official_source": 1.0}
        )
    ]
    
    # Stratégies à tester
    strategies = [
        RerankingStrategy.SIMILARITY_BASED,
        RerankingStrategy.MEDICAL_RELEVANCE,
        RerankingStrategy.LANGUAGE_PREFERENCE,
        RerankingStrategy.HYBRID_SCORING
    ]
    
    print(f"\n📊 Test avec {len(test_results)} résultats et {len(strategies)} stratégies:")
    
    # Afficher les résultats originaux
    print("\n📋 Résultats originaux:")
    for i, result in enumerate(test_results, 1):
        print(f"  {i}. {result.title} ({result.language}) - Score: {result.original_score:.3f}")
        print(f"     Source: {result.source} | Domaine: {result.domain}")
    
    # Tester chaque stratégie
    for strategy in strategies:
        print(f"\n🔄 Stratégie: {strategy.value.upper()}")
        
        reranked_results = reranking_system.rerank_results(
            query=query,
            results=test_results,
            strategy=strategy,
            max_results=5
        )
        
        print(f"   Résultats re-rankés:")
        for result in reranked_results:
            rank_change = result.new_rank - result.original_rank
            rank_indicator = "📈" if rank_change < 0 else "📉" if rank_change > 0 else "➡️"
            
            print(f"     {result.new_rank}. {result.result.title} ({result.result.language})")
            print(f"        Score: {result.original_score:.3f} → {result.reranked_score:.3f} {rank_indicator}")
            print(f"        Rang: {result.original_rank} → {result.new_rank} (Δ{rank_change:+d})")
            print(f"        Confiance: {result.confidence:.3f}")
            print(f"        Explication: {result.explanation[:80]}...")
            
            if result.boost_applied:
                print(f"        Boosts: {result.boost_applied}")
    
    # Test avec contexte utilisateur
    print("\n👤 Test avec contexte utilisateur spécialisé:")
    expert_query = RerankingQuery(
        text="artemether lumefantrine dosage pediatric",
        language="en",
        domain=MedicalDomain.PEDIATRICS,
        user_context={
            "expertise_level": "expert",
            "preferred_languages": ["en", "fr"],
            "preferred_sources": ["WHO", "CDC", "Cochrane"],
            "preferred_domains": ["pediatrics", "infectious_diseases"]
        },
        boost_factors={
            "quality": 0.3,
            "medical": 0.2
        }
    )
    
    expert_results = reranking_system.rerank_results(
        query=expert_query,
        results=test_results,
        strategy=RerankingStrategy.USER_CONTEXT
    )
    
    print("   Résultats pour expert:")
    for i, result in enumerate(expert_results[:3], 1):
        print(f"     {i}. {result.result.title} - Score: {result.reranked_score:.3f}")
        print(f"        Préférence utilisateur: {result.score_breakdown.user_preference:.3f}")
    
    # Générer les statistiques
    stats = reranking_system.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"   Re-rankings totaux: {stats.total_rerankings}")
    print(f"   Amélioration score moyenne: {stats.avg_score_improvement:.3f}")
    print(f"   Changements rang moyens: {stats.avg_rank_changes:.1f}")
    print(f"   Temps traitement moyen: {stats.avg_processing_time:.3f}s")
    
    print(f"\n🔧 Usage des stratégies:")
    for strategy, count in stats.strategy_usage.items():
        print(f"   {strategy}: {count} utilisations")
    
    print(f"\n🌐 Performance par langue:")
    for lang, performance in stats.language_performance.items():
        print(f"   {lang}: {performance:.3f} confiance moyenne")
    
    # Exporter les données
    reranking_system.export_reranking_data("result_reranking_export.json")
    print("\n✅ Données exportées: result_reranking_export.json")

if __name__ == "__main__":
    main()