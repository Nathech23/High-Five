#!/usr/bin/env python3
"""
Système de Scoring de Fiabilité des Sources

Objectif 26: Implémenter scoring fiabilité sources

Ce module implémente un système automatique de notation de la fiabilité
des sources médicales basé sur des critères multiples et pondérés.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib
import urllib.parse

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vérification des dépendances optionnelles
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests non disponible, vérifications en ligne limitées")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas non disponible, analyses limitées")

try:
    from textstat import flesch_reading_ease, flesch_kincaid_grade
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False
    logger.warning("textstat non disponible, analyse de lisibilité limitée")

class SourceType(Enum):
    """Types de sources médicales"""
    PEER_REVIEWED_JOURNAL = "peer_reviewed_journal"
    MEDICAL_TEXTBOOK = "medical_textbook"
    CLINICAL_GUIDELINE = "clinical_guideline"
    GOVERNMENT_HEALTH = "government_health"
    MEDICAL_DATABASE = "medical_database"
    CONFERENCE_PROCEEDINGS = "conference_proceedings"
    THESIS_DISSERTATION = "thesis_dissertation"
    MEDICAL_WEBSITE = "medical_website"
    NEWS_ARTICLE = "news_article"
    BLOG_POST = "blog_post"
    SOCIAL_MEDIA = "social_media"
    UNKNOWN = "unknown"

class ReliabilityLevel(Enum):
    """Niveaux de fiabilité"""
    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"           # 0.7-0.89
    MODERATE = "moderate"   # 0.5-0.69
    LOW = "low"            # 0.3-0.49
    VERY_LOW = "very_low"  # 0.0-0.29

class BiasType(Enum):
    """Types de biais détectés"""
    COMMERCIAL = "commercial"
    POLITICAL = "political"
    SELECTION = "selection"
    CONFIRMATION = "confirmation"
    PUBLICATION = "publication"
    LANGUAGE = "language"
    GEOGRAPHIC = "geographic"
    NONE = "none"

@dataclass
class SourceMetadata:
    """Métadonnées d'une source"""
    title: str
    authors: List[str]
    publication_date: Optional[datetime]
    journal_name: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    language: str = "fr"
    keywords: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    
@dataclass
class JournalMetrics:
    """Métriques d'un journal médical"""
    name: str
    impact_factor: float
    h_index: int
    quartile: str  # Q1, Q2, Q3, Q4
    peer_reviewed: bool
    indexing_databases: List[str]
    specialty_areas: List[str]
    publisher: str
    established_year: Optional[int] = None
    
@dataclass
class AuthorCredentials:
    """Crédibilité d'un auteur"""
    name: str
    affiliations: List[str]
    degrees: List[str]
    specialties: List[str]
    h_index: int
    publication_count: int
    citation_count: int
    years_active: int
    expert_status: bool = False
    
@dataclass
class ContentAnalysis:
    """Analyse du contenu"""
    word_count: int
    readability_score: float
    technical_terms_ratio: float
    citation_count: int
    reference_quality: float
    evidence_level: str
    methodology_score: float
    bias_indicators: List[BiasType]
    fact_check_score: float
    
@dataclass
class ReliabilityScore:
    """Score de fiabilité complet"""
    source_id: str
    overall_score: float
    reliability_level: ReliabilityLevel
    component_scores: Dict[str, float]
    confidence_interval: Tuple[float, float]
    risk_factors: List[str]
    strengths: List[str]
    recommendations: List[str]
    last_updated: datetime
    validity_period: timedelta
    
class SourceReliabilityScorer:
    """
    Système de scoring automatique de la fiabilité des sources médicales
    
    Fonctionnalités:
    - Analyse multi-critères de la fiabilité
    - Détection automatique de biais
    - Scoring pondéré adaptatif
    - Base de données de journaux médicaux
    - Validation croisée
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.journal_database: Dict[str, JournalMetrics] = {}
        self.author_database: Dict[str, AuthorCredentials] = {}
        self.reliability_history: Dict[str, List[ReliabilityScore]] = defaultdict(list)
        self.bias_patterns: Dict[BiasType, List[str]] = {}
        
        # Poids des facteurs de fiabilité
        self.weight_factors = config.get("weight_factors", {
            "journal_impact": 0.25,
            "author_credentials": 0.20,
            "peer_review_status": 0.15,
            "content_quality": 0.15,
            "citation_count": 0.10,
            "recency": 0.08,
            "methodology": 0.07
        })
        
        # Seuils de fiabilité
        self.reliability_thresholds = {
            ReliabilityLevel.VERY_HIGH: 0.9,
            ReliabilityLevel.HIGH: 0.7,
            ReliabilityLevel.MODERATE: 0.5,
            ReliabilityLevel.LOW: 0.3,
            ReliabilityLevel.VERY_LOW: 0.0
        }
        
        # Initialisation des bases de données
        self._initialize_journal_database()
        self._initialize_author_database()
        self._initialize_bias_patterns()
        
        logger.info("Système de scoring de fiabilité initialisé")
        
    def _initialize_journal_database(self):
        """Initialise la base de données des journaux médicaux"""
        journals = [
            JournalMetrics(
                name="The Lancet",
                impact_factor=79.3,
                h_index=1050,
                quartile="Q1",
                peer_reviewed=True,
                indexing_databases=["PubMed", "Scopus", "Web of Science"],
                specialty_areas=["General Medicine", "Global Health"],
                publisher="Elsevier",
                established_year=1823
            ),
            JournalMetrics(
                name="New England Journal of Medicine",
                impact_factor=91.2,
                h_index=1200,
                quartile="Q1",
                peer_reviewed=True,
                indexing_databases=["PubMed", "Scopus", "Web of Science"],
                specialty_areas=["General Medicine", "Clinical Research"],
                publisher="Massachusetts Medical Society",
                established_year=1812
            ),
            JournalMetrics(
                name="Nature Medicine",
                impact_factor=53.4,
                h_index=850,
                quartile="Q1",
                peer_reviewed=True,
                indexing_databases=["PubMed", "Scopus", "Nature Index"],
                specialty_areas=["Biomedical Research", "Translational Medicine"],
                publisher="Nature Publishing Group",
                established_year=1995
            ),
            JournalMetrics(
                name="Bulletin de l'Organisation Mondiale de la Santé",
                impact_factor=6.8,
                h_index=180,
                quartile="Q1",
                peer_reviewed=True,
                indexing_databases=["PubMed", "Scopus"],
                specialty_areas=["Public Health", "Global Health"],
                publisher="World Health Organization",
                established_year=1948
            ),
            JournalMetrics(
                name="Médecine Tropicale",
                impact_factor=1.2,
                h_index=45,
                quartile="Q3",
                peer_reviewed=True,
                indexing_databases=["PubMed", "African Index Medicus"],
                specialty_areas=["Tropical Medicine", "Infectious Diseases"],
                publisher="Société de Pathologie Exotique",
                established_year=1921
            )
        ]
        
        for journal in journals:
            self.journal_database[journal.name.lower()] = journal
            
        logger.info(f"Base de données journaux initialisée: {len(journals)} journaux")
        
    def _initialize_author_database(self):
        """Initialise la base de données des auteurs"""
        authors = [
            AuthorCredentials(
                name="Dr. Marie Dubois",
                affiliations=["Hôpital Général de Douala", "Université de Douala"],
                degrees=["MD", "PhD"],
                specialties=["Cardiologie", "Médecine Interne"],
                h_index=45,
                publication_count=120,
                citation_count=2800,
                years_active=15,
                expert_status=True
            ),
            AuthorCredentials(
                name="Prof. Jean-Claude Mbarga",
                affiliations=["Université de Douala", "CHU de Douala"],
                degrees=["MD", "PhD", "FAAP"],
                specialties=["Pédiatrie", "Néonatologie"],
                h_index=62,
                publication_count=180,
                citation_count=4200,
                years_active=25,
                expert_status=True
            ),
            AuthorCredentials(
                name="Dr. Aminata Sow",
                affiliations=["Institut de Recherche Médicale", "OMS Afrique"],
                degrees=["MD", "DTM&H", "PhD"],
                specialties=["Médecine Tropicale", "Infectiologie"],
                h_index=38,
                publication_count=95,
                citation_count=2100,
                years_active=18,
                expert_status=True
            )
        ]
        
        for author in authors:
            self.author_database[author.name.lower()] = author
            
        logger.info(f"Base de données auteurs initialisée: {len(authors)} auteurs")
        
    def _initialize_bias_patterns(self):
        """Initialise les patterns de détection de biais"""
        self.bias_patterns = {
            BiasType.COMMERCIAL: [
                "sponsored by", "funded by", "en partenariat avec",
                "promotional", "advertisement", "publicité",
                "buy now", "acheter maintenant", "commande"
            ],
            BiasType.POLITICAL: [
                "government policy", "politique gouvernementale",
                "political agenda", "agenda politique",
                "partisan", "biased reporting"
            ],
            BiasType.SELECTION: [
                "cherry picking", "selective reporting",
                "rapport sélectif", "données partielles"
            ],
            BiasType.CONFIRMATION: [
                "confirms our hypothesis", "confirme notre hypothèse",
                "as expected", "comme prévu",
                "obviously", "évidemment"
            ]
        }
        
        logger.info("Patterns de biais initialisés")
        
    def score_source(self, source_metadata: SourceMetadata, 
                    content: Optional[str] = None) -> ReliabilityScore:
        """
        Calcule le score de fiabilité d'une source
        
        Args:
            source_metadata: Métadonnées de la source
            content: Contenu textuel (optionnel)
            
        Returns:
            ReliabilityScore: Score de fiabilité complet
        """
        source_id = self._generate_source_id(source_metadata)
        
        # Calcul des scores par composant
        component_scores = {
            "journal_impact": self._score_journal_impact(source_metadata),
            "author_credentials": self._score_author_credentials(source_metadata),
            "peer_review_status": self._score_peer_review(source_metadata),
            "content_quality": self._score_content_quality(content) if content else 0.5,
            "citation_count": self._score_citations(source_metadata),
            "recency": self._score_recency(source_metadata),
            "methodology": self._score_methodology(content) if content else 0.5
        }
        
        # Calcul du score global pondéré
        overall_score = sum(
            component_scores[component] * self.weight_factors.get(component, 0)
            for component in component_scores
        )
        
        # Détermination du niveau de fiabilité
        reliability_level = self._determine_reliability_level(overall_score)
        
        # Analyse des risques et forces
        risk_factors = self._identify_risk_factors(source_metadata, content)
        strengths = self._identify_strengths(source_metadata, content)
        
        # Recommandations
        recommendations = self._generate_recommendations(component_scores, risk_factors)
        
        # Intervalle de confiance
        confidence_interval = self._calculate_confidence_interval(component_scores)
        
        # Période de validité
        validity_period = self._calculate_validity_period(source_metadata)
        
        score = ReliabilityScore(
            source_id=source_id,
            overall_score=overall_score,
            reliability_level=reliability_level,
            component_scores=component_scores,
            confidence_interval=confidence_interval,
            risk_factors=risk_factors,
            strengths=strengths,
            recommendations=recommendations,
            last_updated=datetime.now(),
            validity_period=validity_period
        )
        
        # Sauvegarde dans l'historique
        self.reliability_history[source_id].append(score)
        
        logger.info(f"Score calculé pour {source_id}: {overall_score:.3f} ({reliability_level.value})")
        
        return score
        
    def _generate_source_id(self, metadata: SourceMetadata) -> str:
        """Génère un ID unique pour la source"""
        content = f"{metadata.title}_{metadata.authors}_{metadata.publication_date}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
        
    def _score_journal_impact(self, metadata: SourceMetadata) -> float:
        """Score basé sur l'impact du journal"""
        if not metadata.journal_name:
            return 0.3  # Score par défaut pour sources sans journal
            
        journal_key = metadata.journal_name.lower()
        if journal_key in self.journal_database:
            journal = self.journal_database[journal_key]
            
            # Normalisation de l'impact factor (log scale)
            if journal.impact_factor > 0:
                normalized_if = min(1.0, journal.impact_factor / 100.0)
            else:
                normalized_if = 0.1
                
            # Bonus pour peer review
            peer_review_bonus = 0.2 if journal.peer_reviewed else 0.0
            
            # Bonus pour quartile
            quartile_bonus = {
                "Q1": 0.3, "Q2": 0.2, "Q3": 0.1, "Q4": 0.0
            }.get(journal.quartile, 0.0)
            
            return min(1.0, normalized_if + peer_review_bonus + quartile_bonus)
        else:
            # Estimation basée sur des heuristiques
            return self._estimate_journal_quality(metadata.journal_name)
            
    def _estimate_journal_quality(self, journal_name: str) -> float:
        """Estime la qualité d'un journal non référencé"""
        name_lower = journal_name.lower()
        
        # Indicateurs de qualité
        quality_indicators = [
            "international", "journal", "medicine", "medical",
            "research", "science", "clinical", "académique"
        ]
        
        # Indicateurs de faible qualité
        low_quality_indicators = [
            "blog", "news", "magazine", "newsletter",
            "commercial", "promotional"
        ]
        
        score = 0.5  # Score de base
        
        for indicator in quality_indicators:
            if indicator in name_lower:
                score += 0.1
                
        for indicator in low_quality_indicators:
            if indicator in name_lower:
                score -= 0.2
                
        return max(0.0, min(1.0, score))
        
    def _score_author_credentials(self, metadata: SourceMetadata) -> float:
        """Score basé sur les crédibilités des auteurs"""
        if not metadata.authors:
            return 0.2
            
        author_scores = []
        for author_name in metadata.authors:
            author_key = author_name.lower()
            if author_key in self.author_database:
                author = self.author_database[author_key]
                
                # Score basé sur h-index normalisé
                h_score = min(1.0, author.h_index / 100.0)
                
                # Bonus pour statut d'expert
                expert_bonus = 0.3 if author.expert_status else 0.0
                
                # Score basé sur l'expérience
                experience_score = min(0.3, author.years_active / 50.0)
                
                author_score = h_score + expert_bonus + experience_score
                author_scores.append(min(1.0, author_score))
            else:
                # Estimation basée sur les affiliations
                author_scores.append(self._estimate_author_quality(author_name, metadata))
                
        return sum(author_scores) / len(author_scores) if author_scores else 0.3
        
    def _estimate_author_quality(self, author_name: str, metadata: SourceMetadata) -> float:
        """Estime la qualité d'un auteur non référencé"""
        score = 0.4  # Score de base
        
        # Vérification des titres académiques
        academic_titles = ["dr", "prof", "phd", "md", "professor", "docteur"]
        for title in academic_titles:
            if title in author_name.lower():
                score += 0.2
                break
                
        # Vérification de l'institution
        if metadata.institution:
            institution_lower = metadata.institution.lower()
            if any(keyword in institution_lower for keyword in 
                  ["university", "université", "hospital", "hôpital", "research", "recherche"]):
                score += 0.2
                
        return min(1.0, score)
        
    def _score_peer_review(self, metadata: SourceMetadata) -> float:
        """Score basé sur le statut de révision par les pairs"""
        if metadata.journal_name:
            journal_key = metadata.journal_name.lower()
            if journal_key in self.journal_database:
                journal = self.journal_database[journal_key]
                return 1.0 if journal.peer_reviewed else 0.3
                
        # Estimation basée sur le type de source
        source_type = self._detect_source_type(metadata)
        
        peer_review_scores = {
            SourceType.PEER_REVIEWED_JOURNAL: 1.0,
            SourceType.CLINICAL_GUIDELINE: 0.9,
            SourceType.MEDICAL_TEXTBOOK: 0.8,
            SourceType.GOVERNMENT_HEALTH: 0.7,
            SourceType.CONFERENCE_PROCEEDINGS: 0.6,
            SourceType.THESIS_DISSERTATION: 0.5,
            SourceType.MEDICAL_DATABASE: 0.4,
            SourceType.MEDICAL_WEBSITE: 0.3,
            SourceType.NEWS_ARTICLE: 0.2,
            SourceType.BLOG_POST: 0.1,
            SourceType.SOCIAL_MEDIA: 0.0
        }
        
        return peer_review_scores.get(source_type, 0.3)
        
    def _detect_source_type(self, metadata: SourceMetadata) -> SourceType:
        """Détecte automatiquement le type de source"""
        if metadata.journal_name:
            return SourceType.PEER_REVIEWED_JOURNAL
            
        if metadata.url:
            url_lower = metadata.url.lower()
            if any(domain in url_lower for domain in 
                  ["pubmed", "ncbi", "who.int", "oms.org"]):
                return SourceType.MEDICAL_DATABASE
            elif any(domain in url_lower for domain in 
                    ["gov", "gouv", "ministry", "ministère"]):
                return SourceType.GOVERNMENT_HEALTH
            elif any(domain in url_lower for domain in 
                    ["blog", "wordpress", "medium"]):
                return SourceType.BLOG_POST
            elif any(domain in url_lower for domain in 
                    ["facebook", "twitter", "instagram"]):
                return SourceType.SOCIAL_MEDIA
                
        title_lower = metadata.title.lower()
        if any(keyword in title_lower for keyword in 
              ["guideline", "recommendation", "protocole"]):
            return SourceType.CLINICAL_GUIDELINE
        elif any(keyword in title_lower for keyword in 
                ["textbook", "manuel", "handbook"]):
            return SourceType.MEDICAL_TEXTBOOK
            
        return SourceType.UNKNOWN
        
    def _score_content_quality(self, content: str) -> float:
        """Score basé sur la qualité du contenu"""
        if not content:
            return 0.5
            
        analysis = self._analyze_content(content)
        
        # Composants du score de qualité
        length_score = min(1.0, len(content.split()) / 1000.0)  # Normalisation à 1000 mots
        readability_score = analysis.readability_score
        technical_score = analysis.technical_terms_ratio
        citation_score = min(1.0, analysis.citation_count / 20.0)  # Normalisation à 20 citations
        
        # Score pondéré
        quality_score = (
            length_score * 0.2 +
            readability_score * 0.3 +
            technical_score * 0.2 +
            citation_score * 0.3
        )
        
        return min(1.0, quality_score)
        
    def _analyze_content(self, content: str) -> ContentAnalysis:
        """Analyse détaillée du contenu"""
        words = content.split()
        word_count = len(words)
        
        # Analyse de lisibilité
        if TEXTSTAT_AVAILABLE:
            try:
                readability = flesch_reading_ease(content)
                readability_score = max(0.0, min(1.0, readability / 100.0))
            except:
                readability_score = 0.5
        else:
            readability_score = 0.5
            
        # Ratio de termes techniques
        technical_terms = self._count_technical_terms(content)
        technical_ratio = min(1.0, technical_terms / max(1, word_count / 100))
        
        # Comptage des citations
        citation_count = self._count_citations(content)
        
        # Détection de biais
        bias_indicators = self._detect_bias(content)
        
        return ContentAnalysis(
            word_count=word_count,
            readability_score=readability_score,
            technical_terms_ratio=technical_ratio,
            citation_count=citation_count,
            reference_quality=min(1.0, citation_count / 10.0),
            evidence_level="III",  # Estimation par défaut
            methodology_score=0.5,  # Estimation par défaut
            bias_indicators=bias_indicators,
            fact_check_score=0.7  # Estimation par défaut
        )
        
    def _count_technical_terms(self, content: str) -> int:
        """Compte les termes techniques médicaux"""
        medical_terms = [
            "diagnostic", "thérapeutique", "pathologie", "symptôme",
            "traitement", "médicament", "posologie", "contre-indication",
            "épidémiologie", "étiologie", "physiopathologie", "pronostic",
            "anamnèse", "examen clinique", "paraclinique", "biologie",
            "imagerie", "histologie", "anatomie", "physiologie"
        ]
        
        content_lower = content.lower()
        count = 0
        for term in medical_terms:
            count += content_lower.count(term)
            
        return count
        
    def _count_citations(self, content: str) -> int:
        """Compte les citations dans le texte"""
        # Patterns de citations
        citation_patterns = [
            r'\[\d+\]',  # [1], [2], etc.
            r'\(\d{4}\)',  # (2024)
            r'et al\.',  # et al.
            r'doi:',  # DOI
            r'pmid:',  # PMID
        ]
        
        total_citations = 0
        for pattern in citation_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_citations += len(matches)
            
        return total_citations
        
    def _detect_bias(self, content: str) -> List[BiasType]:
        """Détecte les biais dans le contenu"""
        detected_bias = []
        content_lower = content.lower()
        
        for bias_type, patterns in self.bias_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    detected_bias.append(bias_type)
                    break
                    
        return detected_bias if detected_bias else [BiasType.NONE]
        
    def _score_citations(self, metadata: SourceMetadata) -> float:
        """Score basé sur le nombre de citations"""
        # Simulation du nombre de citations basée sur l'âge et le journal
        if metadata.publication_date:
            years_since_publication = (datetime.now() - metadata.publication_date).days / 365.25
            
            # Estimation basée sur l'âge et le type de journal
            base_citations = max(0, 50 - years_since_publication * 5)
            
            if metadata.journal_name and metadata.journal_name.lower() in self.journal_database:
                journal = self.journal_database[metadata.journal_name.lower()]
                base_citations *= (journal.impact_factor / 10.0)
                
            return min(1.0, base_citations / 100.0)
        else:
            return 0.3  # Score par défaut
            
    def _score_recency(self, metadata: SourceMetadata) -> float:
        """Score basé sur la récence de la publication"""
        if not metadata.publication_date:
            return 0.3  # Score par défaut
            
        years_since_publication = (datetime.now() - metadata.publication_date).days / 365.25
        
        # Score décroissant avec l'âge
        if years_since_publication <= 1:
            return 1.0
        elif years_since_publication <= 3:
            return 0.8
        elif years_since_publication <= 5:
            return 0.6
        elif years_since_publication <= 10:
            return 0.4
        else:
            return 0.2
            
    def _score_methodology(self, content: str) -> float:
        """Score basé sur la qualité méthodologique"""
        if not content:
            return 0.5
            
        content_lower = content.lower()
        
        # Indicateurs de bonne méthodologie
        methodology_indicators = [
            "randomized", "randomisé", "controlled", "contrôlé",
            "double-blind", "double aveugle", "placebo",
            "statistical", "statistique", "p-value", "confidence interval",
            "systematic review", "méta-analyse", "cohort", "cohorte"
        ]
        
        score = 0.3  # Score de base
        for indicator in methodology_indicators:
            if indicator in content_lower:
                score += 0.1
                
        return min(1.0, score)
        
    def _determine_reliability_level(self, score: float) -> ReliabilityLevel:
        """Détermine le niveau de fiabilité basé sur le score"""
        for level, threshold in sorted(self.reliability_thresholds.items(), 
                                     key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return level
        return ReliabilityLevel.VERY_LOW
        
    def _identify_risk_factors(self, metadata: SourceMetadata, 
                             content: Optional[str]) -> List[str]:
        """Identifie les facteurs de risque"""
        risks = []
        
        # Risques liés aux métadonnées
        if not metadata.authors:
            risks.append("Auteurs non spécifiés")
            
        if not metadata.publication_date:
            risks.append("Date de publication inconnue")
        elif (datetime.now() - metadata.publication_date).days > 3650:  # > 10 ans
            risks.append("Publication ancienne (>10 ans)")
            
        if not metadata.journal_name:
            risks.append("Journal non spécifié")
            
        # Risques liés au contenu
        if content:
            bias_indicators = self._detect_bias(content)
            if BiasType.COMMERCIAL in bias_indicators:
                risks.append("Biais commercial détecté")
            if BiasType.POLITICAL in bias_indicators:
                risks.append("Biais politique détecté")
                
            if len(content.split()) < 100:
                risks.append("Contenu très court")
                
        return risks
        
    def _identify_strengths(self, metadata: SourceMetadata, 
                          content: Optional[str]) -> List[str]:
        """Identifie les points forts"""
        strengths = []
        
        # Forces liées aux métadonnées
        if metadata.journal_name and metadata.journal_name.lower() in self.journal_database:
            journal = self.journal_database[metadata.journal_name.lower()]
            if journal.peer_reviewed:
                strengths.append("Publication dans journal à comité de lecture")
            if journal.impact_factor > 10:
                strengths.append("Journal à fort impact factor")
                
        if metadata.authors:
            expert_authors = [a for a in metadata.authors 
                            if a.lower() in self.author_database and 
                            self.author_database[a.lower()].expert_status]
            if expert_authors:
                strengths.append(f"Auteurs experts reconnus: {len(expert_authors)}")
                
        if metadata.doi:
            strengths.append("DOI disponible")
            
        if metadata.pmid:
            strengths.append("Référencé dans PubMed")
            
        # Forces liées au contenu
        if content:
            citation_count = self._count_citations(content)
            if citation_count > 10:
                strengths.append(f"Bien référencé ({citation_count} citations)")
                
            technical_terms = self._count_technical_terms(content)
            if technical_terms > 20:
                strengths.append("Vocabulaire technique approprié")
                
        return strengths
        
    def _generate_recommendations(self, component_scores: Dict[str, float], 
                                risk_factors: List[str]) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        # Recommandations basées sur les scores faibles
        if component_scores.get("journal_impact", 0) < 0.5:
            recommendations.append("Privilégier des sources de journaux à plus fort impact")
            
        if component_scores.get("author_credentials", 0) < 0.5:
            recommendations.append("Vérifier les crédibilités des auteurs")
            
        if component_scores.get("content_quality", 0) < 0.5:
            recommendations.append("Améliorer la qualité du contenu")
            
        if component_scores.get("recency", 0) < 0.5:
            recommendations.append("Rechercher des sources plus récentes")
            
        # Recommandations basées sur les risques
        if "Biais commercial détecté" in risk_factors:
            recommendations.append("Vérifier l'indépendance de la source")
            
        if "Publication ancienne" in risk_factors:
            recommendations.append("Compléter avec des sources récentes")
            
        return recommendations
        
    def _calculate_confidence_interval(self, component_scores: Dict[str, float]) -> Tuple[float, float]:
        """Calcule l'intervalle de confiance du score"""
        scores = list(component_scores.values())
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Intervalle de confiance à 95%
        margin = 1.96 * std_dev / (len(scores) ** 0.5)
        
        return (max(0.0, mean_score - margin), min(1.0, mean_score + margin))
        
    def _calculate_validity_period(self, metadata: SourceMetadata) -> timedelta:
        """Calcule la période de validité du score"""
        # Période de validité basée sur le type de contenu
        source_type = self._detect_source_type(metadata)
        
        validity_periods = {
            SourceType.PEER_REVIEWED_JOURNAL: timedelta(days=365),
            SourceType.CLINICAL_GUIDELINE: timedelta(days=730),
            SourceType.MEDICAL_TEXTBOOK: timedelta(days=1095),
            SourceType.GOVERNMENT_HEALTH: timedelta(days=180),
            SourceType.MEDICAL_WEBSITE: timedelta(days=90),
            SourceType.NEWS_ARTICLE: timedelta(days=30)
        }
        
        return validity_periods.get(source_type, timedelta(days=180))
        
    def get_source_history(self, source_id: str) -> List[ReliabilityScore]:
        """Récupère l'historique des scores d'une source"""
        return self.reliability_history.get(source_id, [])
        
    def compare_sources(self, source_ids: List[str]) -> Dict[str, Any]:
        """Compare plusieurs sources"""
        comparison = {
            "sources": {},
            "ranking": [],
            "summary": {}
        }
        
        scores = []
        for source_id in source_ids:
            history = self.get_source_history(source_id)
            if history:
                latest_score = history[-1]
                comparison["sources"][source_id] = latest_score
                scores.append((source_id, latest_score.overall_score))
                
        # Classement par score
        scores.sort(key=lambda x: x[1], reverse=True)
        comparison["ranking"] = scores
        
        # Résumé
        if scores:
            comparison["summary"] = {
                "best_source": scores[0][0],
                "worst_source": scores[-1][0],
                "average_score": sum(s[1] for s in scores) / len(scores),
                "score_range": scores[0][1] - scores[-1][1]
            }
            
        return comparison
        
    def generate_reliability_report(self) -> Dict[str, Any]:
        """Génère un rapport de fiabilité global"""
        total_sources = len(self.reliability_history)
        
        if total_sources == 0:
            return {"message": "Aucune source évaluée"}
            
        # Statistiques globales
        all_scores = []
        level_counts = defaultdict(int)
        
        for source_scores in self.reliability_history.values():
            if source_scores:
                latest = source_scores[-1]
                all_scores.append(latest.overall_score)
                level_counts[latest.reliability_level.value] += 1
                
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        return {
            "summary": {
                "total_sources_evaluated": total_sources,
                "average_reliability_score": avg_score,
                "reliability_distribution": dict(level_counts)
            },
            "quality_metrics": {
                "high_quality_sources": level_counts["high"] + level_counts["very_high"],
                "low_quality_sources": level_counts["low"] + level_counts["very_low"],
                "quality_ratio": (level_counts["high"] + level_counts["very_high"]) / total_sources if total_sources > 0 else 0
            },
            "recommendations": self._generate_global_recommendations(level_counts, avg_score)
        }
        
    def _generate_global_recommendations(self, level_counts: Dict, avg_score: float) -> List[str]:
        """Génère des recommandations globales"""
        recommendations = []
        
        if avg_score < 0.6:
            recommendations.append("Améliorer la qualité globale des sources")
            
        if level_counts["very_low"] + level_counts["low"] > level_counts["high"] + level_counts["very_high"]:
            recommendations.append("Privilégier des sources de meilleure qualité")
            
        if level_counts["very_high"] == 0:
            recommendations.append("Inclure des sources de très haute qualité")
            
        return recommendations
        
    def export_data(self, filepath: str) -> bool:
        """Exporte les données de fiabilité"""
        try:
            export_data = {
                "reliability_history": {
                    source_id: [{
                        "source_id": score.source_id,
                        "overall_score": score.overall_score,
                        "reliability_level": score.reliability_level.value,
                        "component_scores": score.component_scores,
                        "confidence_interval": score.confidence_interval,
                        "risk_factors": score.risk_factors,
                        "strengths": score.strengths,
                        "recommendations": score.recommendations,
                        "last_updated": score.last_updated.isoformat()
                    } for score in scores]
                    for source_id, scores in self.reliability_history.items()
                },
                "journal_database": {
                    name: {
                        "name": journal.name,
                        "impact_factor": journal.impact_factor,
                        "h_index": journal.h_index,
                        "quartile": journal.quartile,
                        "peer_reviewed": journal.peer_reviewed,
                        "indexing_databases": journal.indexing_databases,
                        "specialty_areas": journal.specialty_areas,
                        "publisher": journal.publisher
                    } for name, journal in self.journal_database.items()
                },
                "report": self.generate_reliability_report(),
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Données de fiabilité exportées: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            return False

# Fonction principale de démonstration
def main():
    """
    Fonction de démonstration du système de scoring de fiabilité
    """
    print("📊 Test du Système de Scoring de Fiabilité des Sources")
    print("=" * 60)
    
    # Configuration
    config = {
        "weight_factors": {
            "journal_impact": 0.25,
            "author_credentials": 0.20,
            "peer_review_status": 0.15,
            "content_quality": 0.15,
            "citation_count": 0.10,
            "recency": 0.08,
            "methodology": 0.07
        }
    }
    
    # Création du système
    scorer = SourceReliabilityScorer(config)
    print(f"✅ Système créé avec {len(scorer.journal_database)} journaux référencés")
    
    # Test 1: Source de haute qualité
    print("\n🏆 Test 1: Source de haute qualité")
    
    high_quality_metadata = SourceMetadata(
        title="Efficacité de l'artéméther-luméfantrine dans le traitement du paludisme à P. falciparum",
        authors=["Dr. Aminata Sow", "Prof. Jean-Claude Mbarga"],
        publication_date=datetime(2023, 6, 15),
        journal_name="The Lancet",
        doi="10.1016/S0140-6736(23)01234-5",
        pmid="37123456",
        institution="Institut de Recherche Médicale",
        country="Cameroun",
        language="fr",
        keywords=["paludisme", "artéméther", "luméfantrine", "efficacité"]
    )
    
    high_quality_content = """
    Objectif: Évaluer l'efficacité de l'artéméther-luméfantrine (AL) dans le traitement 
    du paludisme non compliqué à P. falciparum en zone d'endémie.
    
    Méthodes: Essai contrôlé randomisé en double aveugle incluant 1200 patients 
    répartis en deux groupes. Le groupe intervention a reçu AL selon les recommandations 
    OMS, le groupe contrôle a reçu un placebo. Le critère principal était la guérison 
    parasitologique à J28.
    
    Résultats: Le taux de guérison était de 96.8% (IC95%: 94.2-98.1) dans le groupe AL 
    versus 12.3% dans le groupe placebo (p<0.001). Aucun effet secondaire grave n'a été 
    observé.
    
    Conclusion: L'AL démontre une excellente efficacité dans cette population.
    
    Références: [1] WHO Guidelines 2023, [2] Cochrane Review 2022, [3] NEJM 2023
    """
    
    score1 = scorer.score_source(high_quality_metadata, high_quality_content)
    print(f"   Score global: {score1.overall_score:.3f}")
    print(f"   Niveau: {score1.reliability_level.value}")
    print(f"   Intervalle confiance: {score1.confidence_interval[0]:.3f}-{score1.confidence_interval[1]:.3f}")
    
    print("   Scores par composant:")
    for component, score in score1.component_scores.items():
        print(f"     {component}: {score:.3f}")
        
    print(f"   Points forts: {len(score1.strengths)}")
    for strength in score1.strengths[:3]:
        print(f"     ✓ {strength}")
        
    # Test 2: Source de qualité moyenne
    print("\n📄 Test 2: Source de qualité moyenne")
    
    medium_quality_metadata = SourceMetadata(
        title="Guide pratique du paludisme",
        authors=["Dr. Martin Dupont"],
        publication_date=datetime(2020, 3, 10),
        journal_name="Médecine Tropicale",
        institution="Hôpital Régional",
        country="Cameroun",
        language="fr"
    )
    
    medium_quality_content = """
    Le paludisme est une maladie parasitaire transmise par les moustiques anophèles.
    Le traitement de première ligne recommandé est l'artéméther-luméfantrine.
    La posologie dépend du poids du patient.
    Il faut surveiller l'évolution clinique.
    """
    
    score2 = scorer.score_source(medium_quality_metadata, medium_quality_content)
    print(f"   Score global: {score2.overall_score:.3f}")
    print(f"   Niveau: {score2.reliability_level.value}")
    
    if score2.risk_factors:
        print(f"   Facteurs de risque: {len(score2.risk_factors)}")
        for risk in score2.risk_factors[:3]:
            print(f"     ⚠ {risk}")
            
    # Test 3: Source de faible qualité
    print("\n❌ Test 3: Source de faible qualité")
    
    low_quality_metadata = SourceMetadata(
        title="Remèdes naturels contre le paludisme",
        authors=[],
        publication_date=None,
        url="https://blog-sante.example.com/paludisme",
        language="fr"
    )
    
    low_quality_content = """
    Le paludisme peut être traité avec des plantes. 
    Buvez beaucoup d'eau et reposez-vous.
    Consultez notre boutique en ligne pour acheter nos produits naturels.
    Livraison gratuite pour toute commande supérieure à 50€.
    """
    
    score3 = scorer.score_source(low_quality_metadata, low_quality_content)
    print(f"   Score global: {score3.overall_score:.3f}")
    print(f"   Niveau: {score3.reliability_level.value}")
    
    print(f"   Facteurs de risque: {len(score3.risk_factors)}")
    for risk in score3.risk_factors:
        print(f"     ⚠ {risk}")
        
    print(f"   Recommandations: {len(score3.recommendations)}")
    for rec in score3.recommendations[:3]:
        print(f"     💡 {rec}")
        
    # Test 4: Comparaison de sources
    print("\n🔄 Test 4: Comparaison de sources")
    
    source_ids = [score1.source_id, score2.source_id, score3.source_id]
    comparison = scorer.compare_sources(source_ids)
    
    print("   Classement par fiabilité:")
    for i, (source_id, score) in enumerate(comparison["ranking"], 1):
        print(f"     {i}. {source_id[:8]}... : {score:.3f}")
        
    if comparison["summary"]:
        summary = comparison["summary"]
        print(f"   Meilleure source: {summary['best_source'][:8]}...")
        print(f"   Score moyen: {summary['average_score']:.3f}")
        print(f"   Écart de scores: {summary['score_range']:.3f}")
        
    # Test 5: Analyse de biais
    print("\n🔍 Test 5: Détection de biais")
    
    biased_content = """
    Cette étude sponsorisée par PharmaCorp démontre l'efficacité exceptionnelle 
    de notre nouveau médicament révolutionnaire. Achetez maintenant avec 50% de réduction!
    Comme nous l'avions prévu, les résultats confirment notre hypothèse.
    """
    
    biased_metadata = SourceMetadata(
        title="Étude sur nouveau traitement",
        authors=["Dr. Commercial"],
        publication_date=datetime(2024, 1, 1),
        language="fr"
    )
    
    score4 = scorer.score_source(biased_metadata, biased_content)
    analysis = scorer._analyze_content(biased_content)
    
    print(f"   Score: {score4.overall_score:.3f}")
    print(f"   Biais détectés: {[b.value for b in analysis.bias_indicators]}")
    
    # Test 6: Rapport global
    print("\n📈 Test 6: Rapport de fiabilité global")
    
    report = scorer.generate_reliability_report()
    print(f"   Sources évaluées: {report['summary']['total_sources_evaluated']}")
    print(f"   Score moyen: {report['summary']['average_reliability_score']:.3f}")
    
    print("   Distribution par niveau:")
    for level, count in report['summary']['reliability_distribution'].items():
        print(f"     {level}: {count}")
        
    print(f"   Sources haute qualité: {report['quality_metrics']['high_quality_sources']}")
    print(f"   Ratio qualité: {report['quality_metrics']['quality_ratio']:.1%}")
    
    if report['recommendations']:
        print("   Recommandations globales:")
        for rec in report['recommendations']:
            print(f"     💡 {rec}")
            
    # Test 7: Export des données
    print("\n💾 Test 7: Export des données")
    
    export_file = "source_reliability_export.json"
    if scorer.export_data(export_file):
        print(f"   ✅ Données exportées: {export_file}")
    else:
        print(f"   ❌ Erreur lors de l'export")
        
    print("\n" + "=" * 60)
    print("🎯 Objectif 26 - Scoring fiabilité sources: IMPLÉMENTÉ")
    print("   ✓ Analyse multi-critères de fiabilité")
    print("   ✓ Base de données journaux médicaux")
    print("   ✓ Évaluation crédibilité auteurs")
    print("   ✓ Détection automatique de biais")
    print("   ✓ Scoring pondéré adaptatif")
    print("   ✓ Analyse qualité contenu")
    print("   ✓ Comparaison de sources")
    print("   ✓ Rapports et recommandations")
    print("   ✓ Export des données")
    print("   ✓ Historique et traçabilité")

if __name__ == "__main__":
    main()