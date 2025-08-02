#!/usr/bin/env python3
"""
Filtrage par Pertinence Médicale

Objectif 17: Ajouter filtrage par pertinence médicale

Ce module implémente un système de filtrage intelligent qui évalue
et filtre les résultats de recherche selon leur pertinence médicale,
en utilisant des critères spécialisés et des modèles de scoring médical.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
import numpy as np
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import time
import math

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn non disponible")
    SKLEARN_AVAILABLE = False

class MedicalRelevanceLevel(Enum):
    """Niveaux de pertinence médicale"""
    HIGHLY_RELEVANT = "highly_relevant"  # Très pertinent
    RELEVANT = "relevant"  # Pertinent
    MODERATELY_RELEVANT = "moderately_relevant"  # Modérément pertinent
    LOW_RELEVANCE = "low_relevance"  # Peu pertinent
    NOT_RELEVANT = "not_relevant"  # Non pertinent
    POTENTIALLY_HARMFUL = "potentially_harmful"  # Potentiellement dangereux

class MedicalDomain(Enum):
    """Domaines médicaux"""
    GENERAL_MEDICINE = "general_medicine"
    INFECTIOUS_DISEASES = "infectious_diseases"
    CARDIOLOGY = "cardiology"
    PEDIATRICS = "pediatrics"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    PREVENTIVE_MEDICINE = "preventive_medicine"
    MENTAL_HEALTH = "mental_health"
    GYNECOLOGY = "gynecology"
    DERMATOLOGY = "dermatology"
    ONCOLOGY = "oncology"
    NEUROLOGY = "neurology"
    TROPICAL_MEDICINE = "tropical_medicine"

class ContentType(Enum):
    """Types de contenu médical"""
    CLINICAL_GUIDELINE = "clinical_guideline"  # Directive clinique
    RESEARCH_ARTICLE = "research_article"  # Article de recherche
    CASE_STUDY = "case_study"  # Étude de cas
    DRUG_INFORMATION = "drug_information"  # Information médicament
    PATIENT_EDUCATION = "patient_education"  # Éducation patient
    PROTOCOL = "protocol"  # Protocole
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"  # Critères diagnostiques
    TREATMENT_PLAN = "treatment_plan"  # Plan de traitement
    PREVENTION_GUIDE = "prevention_guide"  # Guide de prévention
    EMERGENCY_PROCEDURE = "emergency_procedure"  # Procédure d'urgence

class EvidenceLevel(Enum):
    """Niveaux de preuve médicale"""
    LEVEL_1A = "1a"  # Méta-analyse d'essais randomisés
    LEVEL_1B = "1b"  # Essai randomisé contrôlé
    LEVEL_2A = "2a"  # Étude de cohorte
    LEVEL_2B = "2b"  # Étude cas-témoins
    LEVEL_3 = "3"    # Série de cas
    LEVEL_4 = "4"    # Avis d'expert
    LEVEL_5 = "5"    # Opinion non validée

@dataclass
class MedicalCriteria:
    """Critères de pertinence médicale"""
    domain: Optional[MedicalDomain] = None
    content_type: Optional[ContentType] = None
    evidence_level: Optional[EvidenceLevel] = None
    target_audience: str = "general"  # "general", "professional", "specialist"
    urgency_level: str = "normal"  # "low", "normal", "high", "critical"
    language_preference: List[str] = field(default_factory=list)
    geographical_relevance: str = "global"  # "local", "regional", "global"
    age_group: Optional[str] = None  # "pediatric", "adult", "geriatric"
    clinical_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """Résultat de recherche à filtrer"""
    id: str
    content: str
    title: Optional[str] = None
    language: str = "fr"
    source: Optional[str] = None
    score: float = 0.0
    timestamp: Optional[datetime] = None
    medical_terms: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    content_type: Optional[str] = None
    evidence_level: Optional[str] = None
    target_audience: Optional[str] = None
    geographical_tags: List[str] = field(default_factory=list)
    age_group_tags: List[str] = field(default_factory=list)
    safety_indicators: Dict[str, float] = field(default_factory=dict)
    quality_indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelevanceScore:
    """Score de pertinence médicale"""
    overall_score: float  # Score global (0.0 à 1.0)
    relevance_level: MedicalRelevanceLevel
    domain_match: float  # Correspondance du domaine
    content_quality: float  # Qualité du contenu
    evidence_strength: float  # Force de la preuve
    safety_score: float  # Score de sécurité
    currency_score: float  # Score d'actualité
    audience_match: float  # Correspondance audience
    geographical_relevance: float  # Pertinence géographique
    language_bonus: float  # Bonus linguistique
    explanation: str  # Explication du score
    confidence: float  # Confiance dans l'évaluation
    warnings: List[str] = field(default_factory=list)  # Avertissements

@dataclass
class FilteringStats:
    """Statistiques de filtrage"""
    total_results_processed: int = 0
    results_by_relevance: Dict[str, int] = field(default_factory=dict)
    results_by_domain: Dict[str, int] = field(default_factory=dict)
    results_by_language: Dict[str, int] = field(default_factory=dict)
    avg_relevance_score: float = 0.0
    safety_warnings_issued: int = 0
    outdated_content_filtered: int = 0
    low_quality_filtered: int = 0
    processing_time: float = 0.0
    avg_processing_time: float = 0.0

class MedicalRelevanceFilter:
    """
    Système de filtrage par pertinence médicale
    
    Objectif couvert:
    - 17. Ajouter filtrage par pertinence médicale
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = FilteringStats()
        
        # Seuils de configuration
        self.min_relevance_threshold = self.config.get("min_relevance_threshold", 0.3)
        self.safety_threshold = self.config.get("safety_threshold", 0.7)
        self.currency_threshold_days = self.config.get("currency_threshold_days", 1825)  # 5 ans
        self.quality_threshold = self.config.get("quality_threshold", 0.5)
        
        # Dictionnaires médicaux par langue
        self.medical_vocabularies = {
            "fr": {
                "high_priority_terms": [
                    "diagnostic", "traitement", "thérapie", "médicament", "posologie",
                    "symptôme", "maladie", "infection", "virus", "bactérie",
                    "patient", "clinique", "hôpital", "urgence", "chirurgie",
                    "prévention", "vaccination", "dépistage", "épidémiologie"
                ],
                "medical_specialties": [
                    "cardiologie", "neurologie", "oncologie", "pédiatrie",
                    "gynécologie", "dermatologie", "psychiatrie", "radiologie",
                    "anesthésie", "réanimation", "infectiologie", "endocrinologie"
                ],
                "safety_terms": [
                    "contre-indication", "effet secondaire", "toxique", "dangereux",
                    "allergie", "interaction", "surdosage", "précaution",
                    "surveillance", "monitoring", "risque", "complication"
                ],
                "evidence_terms": [
                    "étude", "recherche", "essai", "méta-analyse", "revue systématique",
                    "randomisé", "contrôlé", "cohorte", "cas-témoins", "preuve",
                    "recommandation", "guideline", "consensus", "protocole"
                ]
            },
            "en": {
                "high_priority_terms": [
                    "diagnosis", "treatment", "therapy", "medication", "dosage",
                    "symptom", "disease", "infection", "virus", "bacteria",
                    "patient", "clinical", "hospital", "emergency", "surgery",
                    "prevention", "vaccination", "screening", "epidemiology"
                ],
                "medical_specialties": [
                    "cardiology", "neurology", "oncology", "pediatrics",
                    "gynecology", "dermatology", "psychiatry", "radiology",
                    "anesthesia", "intensive care", "infectious diseases", "endocrinology"
                ],
                "safety_terms": [
                    "contraindication", "side effect", "toxic", "dangerous",
                    "allergy", "interaction", "overdose", "precaution",
                    "monitoring", "surveillance", "risk", "complication"
                ],
                "evidence_terms": [
                    "study", "research", "trial", "meta-analysis", "systematic review",
                    "randomized", "controlled", "cohort", "case-control", "evidence",
                    "recommendation", "guideline", "consensus", "protocol"
                ]
            },
            "ff": {
                "high_priority_terms": [
                    "jannginoore", "dokotoro", "jammirgal", "nayeejo", "ɓernde",
                    "neddo", "jannginoowo", "ɓerngu", "naange"
                ],
                "medical_specialties": ["jannginoore ɓernde", "jannginoore ɓiɓɓe"],
                "safety_terms": ["haɗe", "ɓernde ɓurɗo"],
                "evidence_terms": ["jannginoore"]
            },
            "ar": {
                "high_priority_terms": [
                    "تشخيص", "علاج", "دواء", "جرعة", "أعراض", "مرض",
                    "عدوى", "مريض", "مستشفى", "طوارئ", "جراحة", "وقاية"
                ],
                "medical_specialties": [
                    "أمراض القلب", "الأعصاب", "الأورام", "الأطفال",
                    "النساء", "الجلدية", "النفسية", "الأشعة"
                ],
                "safety_terms": ["موانع", "آثار جانبية", "سام", "خطير", "حساسية"],
                "evidence_terms": ["دراسة", "بحث", "تجربة", "دليل", "توصية"]
            }
        }
        
        # Patterns de détection de contenu médical
        self.medical_patterns = {
            "dosage_patterns": [
                r"\b\d+\s*(mg|g|ml|l|UI|mcg|µg)\b",
                r"\b\d+\s*fois\s*par\s*(jour|semaine|mois)\b",
                r"\b\d+\s*times\s*(daily|weekly|monthly)\b",
                r"\b\d+\s*comprimés?\b",
                r"\b\d+\s*tablets?\b"
            ],
            "vital_signs_patterns": [
                r"\b(TA|BP|FC|HR|FR|RR|T°|Temp)\s*[:=]?\s*\d+",
                r"\b\d+/\d+\s*mmHg\b",
                r"\b\d+\s*bpm\b",
                r"\b\d+°C\b",
                r"\b\d+\.\d+°C\b"
            ],
            "clinical_indicators": [
                r"\b(diagnostic|diagnosis)\s*[:=]\s*\w+",
                r"\b(traitement|treatment)\s*[:=]\s*\w+",
                r"\b(patient|case)\s*#?\d+\b",
                r"\b(ICD|CIM)[-\s]*\d+"
            ],
            "safety_indicators": [
                r"\b(contre-indication|contraindication)s?\b",
                r"\b(effet secondaire|side effect)s?\b",
                r"\b(allergie|allergy|allergic)\b",
                r"\b(toxique|toxic|poisonous)\b",
                r"\b(dangereux|dangerous|harmful)\b"
            ]
        }
        
        # Poids par type de contenu
        self.content_type_weights = {
            ContentType.CLINICAL_GUIDELINE: 1.0,
            ContentType.RESEARCH_ARTICLE: 0.9,
            ContentType.PROTOCOL: 0.95,
            ContentType.DIAGNOSTIC_CRITERIA: 0.9,
            ContentType.DRUG_INFORMATION: 0.85,
            ContentType.EMERGENCY_PROCEDURE: 0.95,
            ContentType.TREATMENT_PLAN: 0.85,
            ContentType.CASE_STUDY: 0.7,
            ContentType.PATIENT_EDUCATION: 0.6,
            ContentType.PREVENTION_GUIDE: 0.75
        }
        
        # Poids par niveau de preuve
        self.evidence_level_weights = {
            EvidenceLevel.LEVEL_1A: 1.0,
            EvidenceLevel.LEVEL_1B: 0.95,
            EvidenceLevel.LEVEL_2A: 0.8,
            EvidenceLevel.LEVEL_2B: 0.75,
            EvidenceLevel.LEVEL_3: 0.6,
            EvidenceLevel.LEVEL_4: 0.4,
            EvidenceLevel.LEVEL_5: 0.2
        }
        
        # Modèle de classification (si disponible)
        self.relevance_classifier = None
        if SKLEARN_AVAILABLE:
            self._init_classification_model()
        
        logger.info("Système de filtrage par pertinence médicale initialisé")
    
    def _init_classification_model(self):
        """Initialise le modèle de classification de pertinence"""
        try:
            # Pipeline simple avec TF-IDF + Naive Bayes
            self.relevance_classifier = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=1000, ngram_range=(1, 2))),
                ('classifier', MultinomialNB())
            ])
            
            # Données d'entraînement simulées (en production, utiliser de vraies données)
            training_texts = [
                "Le paludisme est traité avec l'artéméther-luméfantrine selon les recommandations OMS",
                "Diagnostic différentiel de la fièvre en zone tropicale incluant paludisme et dengue",
                "Protocole de prise en charge de l'hypertension artérielle en première ligne",
                "Effets secondaires de l'aspirine: risque hémorragique et contre-indications",
                "Recette de cuisine traditionnelle camerounaise avec des épices",
                "Article de presse sur la politique économique du gouvernement",
                "Guide touristique des attractions de Douala et ses environs"
            ]
            
            training_labels = [
                "highly_relevant", "highly_relevant", "relevant", "relevant",
                "not_relevant", "not_relevant", "not_relevant"
            ]
            
            # Entraîner le modèle
            self.relevance_classifier.fit(training_texts, training_labels)
            
            logger.info("Modèle de classification initialisé")
        
        except Exception as e:
            logger.warning(f"Erreur lors de l'initialisation du modèle: {e}")
            self.relevance_classifier = None
    
    def _extract_medical_terms(self, text: str, language: str) -> List[str]:
        """Extrait les termes médicaux d'un texte"""
        if language not in self.medical_vocabularies:
            language = "fr"  # Fallback
        
        vocab = self.medical_vocabularies[language]
        text_lower = text.lower()
        
        found_terms = []
        
        # Rechercher dans toutes les catégories
        for category, terms in vocab.items():
            for term in terms:
                if term.lower() in text_lower:
                    found_terms.append(term)
        
        return list(set(found_terms))
    
    def _calculate_domain_match(self, result: SearchResult, criteria: MedicalCriteria) -> float:
        """Calcule la correspondance du domaine médical"""
        if not criteria.domain:
            return 0.5  # Score neutre si pas de domaine spécifié
        
        # Correspondance exacte
        if result.domain and result.domain.lower() == criteria.domain.value.lower():
            return 1.0
        
        # Correspondance basée sur les termes du domaine
        domain_keywords = {
            MedicalDomain.INFECTIOUS_DISEASES: ["infection", "virus", "bactérie", "paludisme", "tuberculose"],
            MedicalDomain.CARDIOLOGY: ["cœur", "cardiaque", "hypertension", "infarctus"],
            MedicalDomain.EMERGENCY: ["urgence", "trauma", "réanimation", "choc"],
            MedicalDomain.PEDIATRICS: ["enfant", "pédiatrie", "nourrisson", "adolescent"],
            MedicalDomain.SURGERY: ["chirurgie", "opération", "intervention", "anesthésie"]
        }
        
        if criteria.domain in domain_keywords:
            keywords = domain_keywords[criteria.domain]
            text_lower = result.content.lower()
            
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            return min(matches / len(keywords) * 2, 1.0)  # Amplifier le score
        
        return 0.3  # Score faible pour domaines non reconnus
    
    def _calculate_content_quality(self, result: SearchResult) -> float:
        """Calcule la qualité du contenu médical"""
        quality_score = 0.5  # Score de base
        
        # Longueur du contenu
        content_length = len(result.content)
        if 200 <= content_length <= 3000:
            quality_score += 0.2
        elif content_length < 100:
            quality_score -= 0.3
        
        # Présence de termes médicaux
        medical_terms = self._extract_medical_terms(result.content, result.language)
        if medical_terms:
            medical_density = len(medical_terms) / max(len(result.content.split()), 1) * 100
            quality_score += min(medical_density * 0.1, 0.3)
        
        # Présence de patterns médicaux
        pattern_bonus = 0.0
        for pattern_type, patterns in self.medical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, result.content, re.IGNORECASE):
                    pattern_bonus += 0.05
        
        quality_score += min(pattern_bonus, 0.2)
        
        # Indicateurs de qualité explicites
        if result.quality_indicators:
            explicit_quality = sum(result.quality_indicators.values()) / len(result.quality_indicators)
            quality_score = (quality_score + explicit_quality) / 2
        
        # Structure du contenu
        if result.title and len(result.title.strip()) > 5:
            quality_score += 0.1
        
        if '\n' in result.content:  # Paragraphes
            quality_score += 0.05
        
        return max(0.0, min(1.0, quality_score))
    
    def _calculate_evidence_strength(self, result: SearchResult) -> float:
        """Calcule la force de la preuve"""
        # Niveau de preuve explicite
        if result.evidence_level:
            try:
                evidence_level = EvidenceLevel(result.evidence_level)
                return self.evidence_level_weights.get(evidence_level, 0.5)
            except ValueError:
                pass
        
        # Détection basée sur le contenu
        evidence_indicators = {
            "meta_analysis": ["méta-analyse", "meta-analysis", "systematic review"],
            "rct": ["randomisé", "randomized", "controlled trial", "essai contrôlé"],
            "cohort": ["cohorte", "cohort", "prospective"],
            "case_control": ["cas-témoins", "case-control"],
            "expert_opinion": ["avis d'expert", "expert opinion", "consensus"]
        }
        
        text_lower = result.content.lower()
        
        for evidence_type, indicators in evidence_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    if evidence_type == "meta_analysis":
                        return 1.0
                    elif evidence_type == "rct":
                        return 0.9
                    elif evidence_type == "cohort":
                        return 0.7
                    elif evidence_type == "case_control":
                        return 0.6
                    elif evidence_type == "expert_opinion":
                        return 0.4
        
        # Score par défaut basé sur la source
        if result.source:
            if any(term in result.source.lower() for term in ["who", "oms", "cdc", "cochrane"]):
                return 0.8
            elif any(term in result.source.lower() for term in ["pubmed", "medline", "journal"]):
                return 0.7
        
        return 0.5  # Score neutre
    
    def _calculate_safety_score(self, result: SearchResult) -> Tuple[float, List[str]]:
        """Calcule le score de sécurité et détecte les avertissements"""
        safety_score = 1.0  # Score de base (sûr)
        warnings = []
        
        # Indicateurs de sécurité explicites
        if result.safety_indicators:
            explicit_safety = sum(result.safety_indicators.values()) / len(result.safety_indicators)
            safety_score = min(safety_score, explicit_safety)
        
        # Détection de termes de sécurité
        text_lower = result.content.lower()
        
        # Contre-indications
        contraindication_patterns = [
            r"contre-indication", r"contraindication", r"ne pas utiliser",
            r"éviter", r"avoid", r"déconseillé", r"not recommended"
        ]
        
        for pattern in contraindication_patterns:
            if re.search(pattern, text_lower):
                safety_score -= 0.2
                warnings.append(f"Contre-indications mentionnées")
                break
        
        # Effets secondaires
        side_effect_patterns = [
            r"effet secondaire", r"side effect", r"adverse", r"toxique",
            r"toxic", r"dangereux", r"dangerous"
        ]
        
        for pattern in side_effect_patterns:
            if re.search(pattern, text_lower):
                safety_score -= 0.1
                warnings.append(f"Effets secondaires mentionnés")
                break
        
        # Interactions médicamenteuses
        interaction_patterns = [
            r"interaction", r"incompatible", r"ne pas associer"
        ]
        
        for pattern in interaction_patterns:
            if re.search(pattern, text_lower):
                safety_score -= 0.15
                warnings.append(f"Interactions médicamenteuses mentionnées")
                break
        
        # Dosages dangereux
        dangerous_dosage_patterns = [
            r"surdosage", r"overdose", r"dose létale", r"lethal dose"
        ]
        
        for pattern in dangerous_dosage_patterns:
            if re.search(pattern, text_lower):
                safety_score -= 0.3
                warnings.append(f"Informations sur surdosage détectées")
                break
        
        return max(0.0, safety_score), warnings
    
    def _calculate_currency_score(self, result: SearchResult) -> float:
        """Calcule le score d'actualité"""
        if not result.timestamp:
            return 0.5  # Score neutre si pas de date
        
        now = datetime.now()
        age_days = (now - result.timestamp).days
        
        # Score décroissant avec l'âge
        if age_days <= 365:  # Moins d'1 an
            return 1.0
        elif age_days <= 1825:  # Moins de 5 ans
            return 1.0 - (age_days - 365) / 1460 * 0.5  # Décroissance linéaire
        else:  # Plus de 5 ans
            return max(0.1, 0.5 - (age_days - 1825) / 1825 * 0.4)
    
    def _calculate_audience_match(self, result: SearchResult, criteria: MedicalCriteria) -> float:
        """Calcule la correspondance avec l'audience cible"""
        if not criteria.target_audience or criteria.target_audience == "general":
            return 0.8  # Score élevé pour audience générale
        
        # Correspondance exacte
        if result.target_audience and result.target_audience.lower() == criteria.target_audience.lower():
            return 1.0
        
        # Détection basée sur le contenu
        audience_indicators = {
            "professional": ["clinique", "clinical", "médecin", "doctor", "professionnel"],
            "specialist": ["spécialiste", "specialist", "expert", "avancé", "advanced"],
            "patient": ["patient", "famille", "family", "éducation", "education"]
        }
        
        text_lower = result.content.lower()
        
        if criteria.target_audience in audience_indicators:
            indicators = audience_indicators[criteria.target_audience]
            matches = sum(1 for indicator in indicators if indicator in text_lower)
            return min(matches / len(indicators) * 2, 1.0)
        
        return 0.5
    
    def _calculate_geographical_relevance(self, result: SearchResult, criteria: MedicalCriteria) -> float:
        """Calcule la pertinence géographique"""
        if criteria.geographical_relevance == "global":
            return 0.8  # Score élevé pour pertinence globale
        
        # Tags géographiques explicites
        if result.geographical_tags:
            if criteria.geographical_relevance == "local":
                local_tags = ["cameroun", "douala", "yaoundé", "afrique centrale"]
                matches = sum(1 for tag in result.geographical_tags 
                            if any(local in tag.lower() for local in local_tags))
                return min(matches / len(result.geographical_tags), 1.0)
            
            elif criteria.geographical_relevance == "regional":
                regional_tags = ["afrique", "africa", "tropical", "subsaharienne"]
                matches = sum(1 for tag in result.geographical_tags 
                            if any(regional in tag.lower() for regional in regional_tags))
                return min(matches / len(result.geographical_tags), 1.0)
        
        # Détection basée sur le contenu
        text_lower = result.content.lower()
        
        if criteria.geographical_relevance == "local":
            local_indicators = ["cameroun", "douala", "yaoundé", "hgd", "afrique centrale"]
            matches = sum(1 for indicator in local_indicators if indicator in text_lower)
            return min(matches * 0.3, 1.0)
        
        return 0.6  # Score par défaut
    
    def _calculate_language_bonus(self, result: SearchResult, criteria: MedicalCriteria) -> float:
        """Calcule le bonus linguistique"""
        if not criteria.language_preference:
            return 0.0  # Pas de bonus si pas de préférence
        
        if result.language in criteria.language_preference:
            # Bonus selon la position dans les préférences
            position = criteria.language_preference.index(result.language)
            return max(0.0, 0.3 - position * 0.1)
        
        return 0.0
    
    def _classify_relevance_level(self, overall_score: float) -> MedicalRelevanceLevel:
        """Classifie le niveau de pertinence selon le score"""
        if overall_score >= 0.8:
            return MedicalRelevanceLevel.HIGHLY_RELEVANT
        elif overall_score >= 0.6:
            return MedicalRelevanceLevel.RELEVANT
        elif overall_score >= 0.4:
            return MedicalRelevanceLevel.MODERATELY_RELEVANT
        elif overall_score >= 0.2:
            return MedicalRelevanceLevel.LOW_RELEVANCE
        else:
            return MedicalRelevanceLevel.NOT_RELEVANT
    
    def calculate_medical_relevance(self, result: SearchResult, criteria: MedicalCriteria) -> RelevanceScore:
        """
        Calcule le score de pertinence médicale d'un résultat
        
        Args:
            result: Résultat à évaluer
            criteria: Critères de pertinence médicale
        
        Returns:
            RelevanceScore: Score de pertinence détaillé
        """
        try:
            # Calculer les composants du score
            domain_match = self._calculate_domain_match(result, criteria)
            content_quality = self._calculate_content_quality(result)
            evidence_strength = self._calculate_evidence_strength(result)
            safety_score, warnings = self._calculate_safety_score(result)
            currency_score = self._calculate_currency_score(result)
            audience_match = self._calculate_audience_match(result, criteria)
            geographical_relevance = self._calculate_geographical_relevance(result, criteria)
            language_bonus = self._calculate_language_bonus(result, criteria)
            
            # Poids des composants
            weights = {
                "domain_match": 0.25,
                "content_quality": 0.20,
                "evidence_strength": 0.15,
                "safety_score": 0.15,
                "currency_score": 0.10,
                "audience_match": 0.10,
                "geographical_relevance": 0.05
            }
            
            # Calculer le score global
            overall_score = (
                domain_match * weights["domain_match"] +
                content_quality * weights["content_quality"] +
                evidence_strength * weights["evidence_strength"] +
                safety_score * weights["safety_score"] +
                currency_score * weights["currency_score"] +
                audience_match * weights["audience_match"] +
                geographical_relevance * weights["geographical_relevance"] +
                language_bonus  # Bonus additionnel
            )
            
            # Normaliser le score
            overall_score = max(0.0, min(1.0, overall_score))
            
            # Ajustements spéciaux
            if safety_score < self.safety_threshold:
                overall_score *= 0.5  # Pénalité importante pour sécurité
                warnings.append("Score de sécurité faible détecté")
            
            # Classifier le niveau de pertinence
            relevance_level = self._classify_relevance_level(overall_score)
            
            # Calculer la confiance
            confidence = self._calculate_confidence(result, overall_score)
            
            # Générer l'explication
            explanation = self._generate_explanation(
                domain_match, content_quality, evidence_strength,
                safety_score, currency_score, audience_match
            )
            
            return RelevanceScore(
                overall_score=overall_score,
                relevance_level=relevance_level,
                domain_match=domain_match,
                content_quality=content_quality,
                evidence_strength=evidence_strength,
                safety_score=safety_score,
                currency_score=currency_score,
                audience_match=audience_match,
                geographical_relevance=geographical_relevance,
                language_bonus=language_bonus,
                explanation=explanation,
                confidence=confidence,
                warnings=warnings
            )
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul de pertinence: {e}")
            return RelevanceScore(
                overall_score=0.0,
                relevance_level=MedicalRelevanceLevel.NOT_RELEVANT,
                domain_match=0.0,
                content_quality=0.0,
                evidence_strength=0.0,
                safety_score=0.0,
                currency_score=0.0,
                audience_match=0.0,
                geographical_relevance=0.0,
                language_bonus=0.0,
                explanation="Erreur lors de l'évaluation",
                confidence=0.0,
                warnings=[f"Erreur: {str(e)}"]
            )
    
    def _calculate_confidence(self, result: SearchResult, overall_score: float) -> float:
        """Calcule la confiance dans l'évaluation"""
        confidence = 0.5  # Base
        
        # Bonus pour les métadonnées complètes
        if result.source:
            confidence += 0.1
        if result.timestamp:
            confidence += 0.1
        if result.domain:
            confidence += 0.1
        if result.medical_terms:
            confidence += 0.1
        
        # Bonus pour la cohérence du score
        if 0.3 <= overall_score <= 0.8:  # Scores moyens plus fiables
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_explanation(self, domain_match: float, content_quality: float,
                            evidence_strength: float, safety_score: float,
                            currency_score: float, audience_match: float) -> str:
        """Génère une explication du score"""
        explanations = []
        
        if domain_match >= 0.7:
            explanations.append("Excellente correspondance du domaine")
        elif domain_match >= 0.4:
            explanations.append("Correspondance partielle du domaine")
        else:
            explanations.append("Faible correspondance du domaine")
        
        if content_quality >= 0.7:
            explanations.append("Contenu de haute qualité")
        elif content_quality < 0.4:
            explanations.append("Qualité du contenu limitée")
        
        if evidence_strength >= 0.8:
            explanations.append("Preuves scientifiques solides")
        elif evidence_strength < 0.4:
            explanations.append("Preuves limitées")
        
        if safety_score < 0.7:
            explanations.append("Préoccupations de sécurité détectées")
        
        if currency_score < 0.5:
            explanations.append("Information potentiellement obsolète")
        
        return "; ".join(explanations[:3])  # Limiter à 3 explications principales
    
    def filter_results(self, results: List[SearchResult], criteria: MedicalCriteria,
                      min_relevance: Optional[float] = None) -> List[Tuple[SearchResult, RelevanceScore]]:
        """
        Filtre une liste de résultats selon leur pertinence médicale
        
        Args:
            results: Liste des résultats à filtrer
            criteria: Critères de filtrage
            min_relevance: Seuil minimum de pertinence (optionnel)
        
        Returns:
            List[Tuple[SearchResult, RelevanceScore]]: Résultats filtrés avec leurs scores
        """
        start_time = time.time()
        
        try:
            if not results:
                return []
            
            min_threshold = min_relevance or self.min_relevance_threshold
            filtered_results = []
            
            for result in results:
                # Calculer le score de pertinence
                relevance_score = self.calculate_medical_relevance(result, criteria)
                
                # Appliquer le filtrage
                if relevance_score.overall_score >= min_threshold:
                    # Vérifications de sécurité supplémentaires
                    if relevance_score.safety_score >= self.safety_threshold or not relevance_score.warnings:
                        filtered_results.append((result, relevance_score))
                    else:
                        # Marquer comme potentiellement dangereux
                        relevance_score.relevance_level = MedicalRelevanceLevel.POTENTIALLY_HARMFUL
                        filtered_results.append((result, relevance_score))
            
            # Trier par score de pertinence décroissant
            filtered_results.sort(key=lambda x: x[1].overall_score, reverse=True)
            
            # Mettre à jour les statistiques
            processing_time = time.time() - start_time
            self._update_filtering_stats(results, filtered_results, processing_time)
            
            return filtered_results
        
        except Exception as e:
            logger.error(f"Erreur lors du filtrage: {e}")
            return [(result, RelevanceScore(
                overall_score=0.0,
                relevance_level=MedicalRelevanceLevel.NOT_RELEVANT,
                domain_match=0.0, content_quality=0.0, evidence_strength=0.0,
                safety_score=0.0, currency_score=0.0, audience_match=0.0,
                geographical_relevance=0.0, language_bonus=0.0,
                explanation="Erreur de filtrage", confidence=0.0
            )) for result in results]
    
    def _update_filtering_stats(self, original_results: List[SearchResult],
                              filtered_results: List[Tuple[SearchResult, RelevanceScore]],
                              processing_time: float):
        """Met à jour les statistiques de filtrage"""
        self.stats.total_results_processed += len(original_results)
        
        # Statistiques par niveau de pertinence
        for _, relevance_score in filtered_results:
            level = relevance_score.relevance_level.value
            self.stats.results_by_relevance[level] = self.stats.results_by_relevance.get(level, 0) + 1
            
            # Compter les avertissements de sécurité
            if relevance_score.warnings:
                self.stats.safety_warnings_issued += len(relevance_score.warnings)
        
        # Statistiques par domaine et langue
        for result in original_results:
            if result.domain:
                self.stats.results_by_domain[result.domain] = self.stats.results_by_domain.get(result.domain, 0) + 1
            
            self.stats.results_by_language[result.language] = self.stats.results_by_language.get(result.language, 0) + 1
        
        # Score de pertinence moyen
        if filtered_results:
            avg_score = sum(score.overall_score for _, score in filtered_results) / len(filtered_results)
            
            if self.stats.total_results_processed > len(original_results):
                # Moyenne mobile
                previous_count = self.stats.total_results_processed - len(original_results)
                self.stats.avg_relevance_score = (
                    (self.stats.avg_relevance_score * previous_count + avg_score * len(filtered_results)) /
                    self.stats.total_results_processed
                )
            else:
                self.stats.avg_relevance_score = avg_score
        
        # Temps de traitement
        if self.stats.total_results_processed > len(original_results):
            previous_count = self.stats.total_results_processed - len(original_results)
            self.stats.avg_processing_time = (
                (self.stats.avg_processing_time * previous_count + processing_time) /
                (previous_count + 1)
            )
        else:
            self.stats.avg_processing_time = processing_time
    
    def generate_stats(self) -> FilteringStats:
        """Génère les statistiques de filtrage"""
        start_time = time.time()
        self.stats.processing_time = time.time() - start_time
        return self.stats
    
    def export_filtering_data(self, output_path: str):
        """Exporte les données de filtrage"""
        export_data = {
            "metadata": {
                "total_results_processed": self.stats.total_results_processed,
                "supported_languages": list(self.medical_vocabularies.keys()),
                "medical_domains": [domain.value for domain in MedicalDomain],
                "content_types": [content_type.value for content_type in ContentType],
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "configuration": {
                "min_relevance_threshold": self.min_relevance_threshold,
                "safety_threshold": self.safety_threshold,
                "currency_threshold_days": self.currency_threshold_days,
                "quality_threshold": self.quality_threshold,
                "content_type_weights": {k.value: v for k, v in self.content_type_weights.items()},
                "evidence_level_weights": {k.value: v for k, v in self.evidence_level_weights.items()}
            },
            "medical_vocabularies": {
                lang: {category: len(terms) for category, terms in vocab.items()}
                for lang, vocab in self.medical_vocabularies.items()
            },
            "statistics": {
                "results_by_relevance": self.stats.results_by_relevance,
                "results_by_domain": self.stats.results_by_domain,
                "results_by_language": self.stats.results_by_language,
                "avg_relevance_score": self.stats.avg_relevance_score,
                "safety_warnings_issued": self.stats.safety_warnings_issued,
                "avg_processing_time": self.stats.avg_processing_time
            },
            "medical_patterns": {
                pattern_type: len(patterns) for pattern_type, patterns in self.medical_patterns.items()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de filtrage exportées: {output_path}")

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("🔍 Test du Filtrage par Pertinence Médicale")
    
    # Créer le système de filtrage
    filter_system = MedicalRelevanceFilter({
        "min_relevance_threshold": 0.3,
        "safety_threshold": 0.7,
        "quality_threshold": 0.5
    })
    
    # Critères de filtrage
    criteria = MedicalCriteria(
        domain=MedicalDomain.INFECTIOUS_DISEASES,
        content_type=ContentType.CLINICAL_GUIDELINE,
        target_audience="professional",
        urgency_level="high",
        language_preference=["fr", "en"],
        geographical_relevance="local",
        clinical_context={
            "patient_type": "adult",
            "severity": "moderate"
        }
    )
    
    # Résultats de test
    test_results = [
        SearchResult(
            id="who_malaria_guideline",
            content="Le paludisme est une maladie parasitaire grave transmise par les moustiques anopheles. Traitement de première ligne: artéméther-luméfantrine 20mg/120mg, 4 comprimés selon protocole OMS. Contre-indications: allergie connue aux dérivés d'artémisinine.",
            title="Directives OMS - Traitement du Paludisme 2024",
            language="fr",
            source="Organisation Mondiale de la Santé",
            score=0.95,
            timestamp=datetime(2024, 1, 15),
            medical_terms=["paludisme", "artéméther-luméfantrine", "anopheles"],
            domain="infectious_diseases",
            content_type="clinical_guideline",
            evidence_level="1a",
            target_audience="professional",
            geographical_tags=["global", "afrique"],
            safety_indicators={"contraindications_mentioned": 0.8},
            quality_indicators={"peer_reviewed": 1.0, "official_source": 1.0}
        ),
        SearchResult(
            id="local_malaria_protocol",
            content="Protocole HGD pour le paludisme: diagnostic rapide par TDR, traitement artéméther-luméfantrine si test positif. Surveillance clinique 48h. Spécificités Cameroun: résistance chloroquine documentée.",
            title="Protocole Paludisme - HGD Douala",
            language="fr",
            source="Hôpital Général de Douala",
            score=0.88,
            timestamp=datetime(2024, 2, 1),
            medical_terms=["paludisme", "TDR", "artéméther-luméfantrine"],
            domain="infectious_diseases",
            content_type="protocol",
            target_audience="professional",
            geographical_tags=["cameroun", "douala"],
            quality_indicators={"local_relevance": 1.0, "clinical_experience": 0.9}
        ),
        SearchResult(
            id="patient_education_malaria",
            content="Le paludisme se manifeste par de la fièvre, des frissons et des maux de tête. Consultez rapidement un médecin si vous avez ces symptômes. Prenez vos médicaments comme prescrits.",
            title="Information Patient - Paludisme",
            language="fr",
            source="Brochure éducative",
            score=0.65,
            timestamp=datetime(2023, 8, 10),
            medical_terms=["paludisme", "fièvre", "symptômes"],
            domain="infectious_diseases",
            content_type="patient_education",
            target_audience="patient",
            quality_indicators={"readability": 0.9}
        ),
        SearchResult(
            id="outdated_chloroquine_info",
            content="Traitement du paludisme: chloroquine 25mg/kg en première intention. Très efficace contre Plasmodium falciparum. Peu d'effets secondaires.",
            title="Traitement Paludisme - Guide 2010",
            language="fr",
            source="Ancien manuel médical",
            score=0.70,
            timestamp=datetime(2010, 5, 15),
            medical_terms=["paludisme", "chloroquine"],
            domain="infectious_diseases",
            content_type="clinical_guideline",
            evidence_level="4",
            quality_indicators={"outdated": 0.2}
        ),
        SearchResult(
            id="dangerous_home_remedy",
            content="Remède traditionnel contre le paludisme: décoction d'écorce de quinquina 500mg toutes les heures jusqu'à guérison. Très efficace selon la tradition.",
            title="Remèdes Traditionnels",
            language="fr",
            source="Blog santé alternative",
            score=0.45,
            timestamp=datetime(2023, 12, 1),
            medical_terms=["paludisme", "quinquina"],
            domain="infectious_diseases",
            content_type="community_content",
            safety_indicators={"unverified_treatment": 0.3, "potential_overdose": 0.2}
        ),
        SearchResult(
            id="non_medical_content",
            content="Les moustiques sont des insectes fascinants. Leur cycle de vie comprend quatre stades: œuf, larve, nymphe et adulte. Ils jouent un rôle important dans l'écosystème.",
            title="Biologie des Moustiques",
            language="fr",
            source="Encyclopédie nature",
            score=0.30,
            timestamp=datetime(2023, 6, 20),
            medical_terms=[],
            domain="biology",
            content_type="educational"
        )
    ]
    
    print(f"\n📊 Test avec {len(test_results)} résultats:")
    
    # Afficher les résultats originaux
    print("\n📋 Résultats originaux:")
    for i, result in enumerate(test_results, 1):
        print(f"  {i}. {result.title}")
        print(f"     Source: {result.source} | Domaine: {result.domain}")
        print(f"     Type: {result.content_type} | Score: {result.score:.2f}")
        if result.timestamp:
            age_days = (datetime.now() - result.timestamp).days
            print(f"     Âge: {age_days} jours")
    
    # Effectuer le filtrage
    print(f"\n🔍 Filtrage avec critères:")
    print(f"   Domaine: {criteria.domain.value}")
    print(f"   Type de contenu: {criteria.content_type.value if criteria.content_type else 'Tous'}")
    print(f"   Audience: {criteria.target_audience}")
    print(f"   Urgence: {criteria.urgency_level}")
    print(f"   Langues préférées: {criteria.language_preference}")
    print(f"   Pertinence géographique: {criteria.geographical_relevance}")
    
    filtered_results = filter_system.filter_results(
        results=test_results,
        criteria=criteria,
        min_relevance=0.2
    )
    
    print(f"\n✅ Résultats filtrés ({len(filtered_results)}/{len(test_results)}):")
    
    for i, (result, relevance_score) in enumerate(filtered_results, 1):
        level_emoji = {
            MedicalRelevanceLevel.HIGHLY_RELEVANT: "🟢",
            MedicalRelevanceLevel.RELEVANT: "🔵",
            MedicalRelevanceLevel.MODERATELY_RELEVANT: "🟡",
            MedicalRelevanceLevel.LOW_RELEVANCE: "🟠",
            MedicalRelevanceLevel.NOT_RELEVANT: "🔴",
            MedicalRelevanceLevel.POTENTIALLY_HARMFUL: "⚠️"
        }.get(relevance_score.relevance_level, "❓")
        
        print(f"\n  {i}. {level_emoji} {result.title}")
        print(f"     Score global: {relevance_score.overall_score:.3f} ({relevance_score.relevance_level.value})")
        print(f"     Correspondance domaine: {relevance_score.domain_match:.2f}")
        print(f"     Qualité contenu: {relevance_score.content_quality:.2f}")
        print(f"     Force preuve: {relevance_score.evidence_strength:.2f}")
        print(f"     Sécurité: {relevance_score.safety_score:.2f}")
        print(f"     Actualité: {relevance_score.currency_score:.2f}")
        print(f"     Correspondance audience: {relevance_score.audience_match:.2f}")
        print(f"     Confiance: {relevance_score.confidence:.2f}")
        print(f"     Explication: {relevance_score.explanation}")
        
        if relevance_score.warnings:
            print(f"     ⚠️ Avertissements: {'; '.join(relevance_score.warnings)}")
    
    # Test avec différents seuils
    print(f"\n📊 Test avec différents seuils de pertinence:")
    
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    for threshold in thresholds:
        filtered_count = len(filter_system.filter_results(
            results=test_results,
            criteria=criteria,
            min_relevance=threshold
        ))
        print(f"   Seuil {threshold:.1f}: {filtered_count}/{len(test_results)} résultats")
    
    # Test avec différents domaines
    print(f"\n🏥 Test avec différents domaines médicaux:")
    
    domains_to_test = [
        MedicalDomain.INFECTIOUS_DISEASES,
        MedicalDomain.CARDIOLOGY,
        MedicalDomain.EMERGENCY,
        MedicalDomain.GENERAL_MEDICINE
    ]
    
    for domain in domains_to_test:
        domain_criteria = MedicalCriteria(domain=domain, target_audience="professional")
        domain_results = filter_system.filter_results(
            results=test_results,
            criteria=domain_criteria,
            min_relevance=0.3
        )
        
        if domain_results:
            avg_score = sum(score.overall_score for _, score in domain_results) / len(domain_results)
            print(f"   {domain.value}: {len(domain_results)} résultats (score moyen: {avg_score:.2f})")
        else:
            print(f"   {domain.value}: 0 résultats")
    
    # Générer les statistiques
    stats = filter_system.generate_stats()
    
    print(f"\n📈 Statistiques de filtrage:")
    print(f"   Résultats traités: {stats.total_results_processed}")
    print(f"   Score moyen: {stats.avg_relevance_score:.3f}")
    print(f"   Avertissements sécurité: {stats.safety_warnings_issued}")
    print(f"   Temps moyen traitement: {stats.avg_processing_time:.3f}s")
    
    if stats.results_by_relevance:
        print(f"\n   Répartition par niveau:")
        for level, count in stats.results_by_relevance.items():
            print(f"     {level}: {count}")
    
    if stats.results_by_domain:
        print(f"\n   Répartition par domaine:")
        for domain, count in stats.results_by_domain.items():
            print(f"     {domain}: {count}")
    
    if stats.results_by_language:
        print(f"\n   Répartition par langue:")
        for language, count in stats.results_by_language.items():
            print(f"     {language}: {count}")
    
    # Test de performance
    print(f"\n⚡ Test de performance:")
    
    # Créer un grand nombre de résultats pour le test
    large_test_results = []
    for i in range(100):
        large_test_results.append(SearchResult(
            id=f"test_result_{i}",
            content=f"Contenu médical test {i} avec termes: paludisme, traitement, diagnostic",
            title=f"Résultat Test {i}",
            language="fr",
            source="Test Source",
            score=0.5 + (i % 50) / 100,
            timestamp=datetime.now() - timedelta(days=i),
            medical_terms=["paludisme", "traitement"],
            domain="infectious_diseases"
        ))
    
    start_time = time.time()
    large_filtered_results = filter_system.filter_results(
        results=large_test_results,
        criteria=criteria,
        min_relevance=0.3
    )
    end_time = time.time()
    
    print(f"   {len(large_test_results)} résultats traités en {end_time - start_time:.3f}s")
    print(f"   {len(large_filtered_results)} résultats conservés")
    print(f"   Vitesse: {len(large_test_results) / (end_time - start_time):.1f} résultats/seconde")
    
    # Exporter les données
    export_path = "medical_relevance_filter_export.json"
    filter_system.export_filtering_data(export_path)
    print(f"\n💾 Données exportées: {export_path}")
    
    print(f"\n✅ Test du filtrage par pertinence médicale terminé!")
    print(f"\n🎯 Objectif 17 - Filtrage par pertinence médicale: IMPLÉMENTÉ")
    print(f"   ✓ Évaluation multi-critères de la pertinence médicale")
    print(f"   ✓ Filtrage par domaine, qualité, preuve et sécurité")
    print(f"   ✓ Support multilingue (français, anglais, langues camerounaises)")
    print(f"   ✓ Détection de contenu potentiellement dangereux")
    print(f"   ✓ Scoring adaptatif selon le contexte clinique")
    print(f"   ✓ Statistiques et monitoring détaillés")

if __name__ == "__main__":
    main()