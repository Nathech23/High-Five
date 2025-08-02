#!/usr/bin/env python3
"""
Système de Documentation des Sources et Niveaux de Preuve

Objectif 28: Documenter sources et niveaux de preuve

Ce module implémente un système complet de documentation des sources
avec classification des niveaux de preuve selon les standards EBM.

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
from typing import Dict, List, Optional, Any, Set, Tuple, Union
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
    from urllib.parse import urlparse, parse_qs
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False
    logger.warning("urllib non disponible, parsing URL limité")

class EvidenceLevel(Enum):
    """Niveaux de preuve Evidence-Based Medicine"""
    LEVEL_I = "I"      # Méta-analyses d'essais contrôlés randomisés
    LEVEL_II = "II"    # Essais contrôlés randomisés individuels
    LEVEL_III = "III"  # Études de cohorte et cas-témoins
    LEVEL_IV = "IV"    # Séries de cas et études descriptives
    LEVEL_V = "V"      # Opinion d'experts et consensus
    UNKNOWN = "Unknown"

class StudyDesign(Enum):
    """Types d'études médicales"""
    META_ANALYSIS = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    RANDOMIZED_CONTROLLED_TRIAL = "randomized_controlled_trial"
    COHORT_STUDY = "cohort_study"
    CASE_CONTROL_STUDY = "case_control_study"
    CROSS_SECTIONAL_STUDY = "cross_sectional_study"
    CASE_SERIES = "case_series"
    CASE_REPORT = "case_report"
    EXPERT_OPINION = "expert_opinion"
    NARRATIVE_REVIEW = "narrative_review"
    GUIDELINE = "guideline"
    UNKNOWN = "unknown"

class SourceType(Enum):
    """Types de sources"""
    PEER_REVIEWED_JOURNAL = "peer_reviewed_journal"
    MEDICAL_TEXTBOOK = "medical_textbook"
    CLINICAL_GUIDELINE = "clinical_guideline"
    GOVERNMENT_PUBLICATION = "government_publication"
    INTERNATIONAL_ORGANIZATION = "international_organization"
    CONFERENCE_ABSTRACT = "conference_abstract"
    THESIS = "thesis"
    PREPRINT = "preprint"
    WEBSITE = "website"
    OTHER = "other"

class CitationFormat(Enum):
    """Formats de citation"""
    VANCOUVER = "vancouver"
    APA = "apa"
    HARVARD = "harvard"
    MLA = "mla"
    CHICAGO = "chicago"

@dataclass
class Citation:
    """Citation bibliographique"""
    id: str
    authors: List[str]
    title: str
    journal: Optional[str]
    year: int
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    access_date: Optional[datetime] = None
    
@dataclass
class EvidenceSource:
    """Source de preuve médicale"""
    id: str
    citation: Citation
    source_type: SourceType
    study_design: StudyDesign
    evidence_level: EvidenceLevel
    quality_score: float  # 0-1
    sample_size: Optional[int] = None
    population: Optional[str] = None
    intervention: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_duration: Optional[str] = None
    statistical_significance: Optional[bool] = None
    confidence_interval: Optional[str] = None
    bias_risk: str = "unknown"  # low, moderate, high, unknown
    funding_source: Optional[str] = None
    conflicts_of_interest: Optional[str] = None
    
@dataclass
class EvidenceSummary:
    """Résumé des preuves"""
    topic: str
    sources: List[EvidenceSource]
    overall_evidence_level: EvidenceLevel
    strength_of_recommendation: str  # strong, moderate, weak
    quality_of_evidence: str  # high, moderate, low, very_low
    consistency: str  # consistent, inconsistent, unknown
    directness: str  # direct, indirect, unknown
    precision: str  # precise, imprecise, unknown
    publication_bias_risk: str  # low, moderate, high, unknown
    summary_statement: str
    recommendations: List[str]
    limitations: List[str]
    
@dataclass
class ProvenanceRecord:
    """Enregistrement de provenance"""
    source_id: str
    original_url: Optional[str]
    retrieval_date: datetime
    retrieval_method: str
    processor: str
    processing_date: datetime
    version: str
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class DocumentationReport:
    """Rapport de documentation"""
    content_id: str
    evidence_sources: List[EvidenceSource]
    evidence_summary: EvidenceSummary
    provenance_records: List[ProvenanceRecord]
    citation_network: Dict[str, List[str]]
    quality_assessment: Dict[str, Any]
    documentation_date: datetime
    documenter: str
    
class EvidenceDocumenter:
    """
    Système de documentation des sources et niveaux de preuve
    
    Fonctionnalités:
    - Classification automatique des niveaux de preuve
    - Génération de citations bibliographiques
    - Traçabilité complète des sources
    - Évaluation de la qualité des preuves
    - Résumés de preuves structurés
    - Export dans différents formats
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.evidence_sources: Dict[str, EvidenceSource] = {}
        self.evidence_summaries: Dict[str, EvidenceSummary] = {}
        self.provenance_records: Dict[str, List[ProvenanceRecord]] = defaultdict(list)
        self.documentation_reports: Dict[str, DocumentationReport] = {}
        
        # Configuration
        self.default_citation_format = config.get("citation_format", CitationFormat.VANCOUVER)
        self.require_citations = config.get("require_citations", True)
        self.track_provenance = config.get("track_provenance", True)
        self.version_control = config.get("version_control", True)
        
        # Patterns de détection
        self.study_design_patterns = self._initialize_study_patterns()
        self.evidence_level_mapping = self._initialize_evidence_mapping()
        
        # Base de données de journaux
        self.journal_database = self._initialize_journal_database()
        
        logger.info("Système de documentation des preuves initialisé")
        
    def _initialize_study_patterns(self) -> Dict[StudyDesign, List[str]]:
        """Initialise les patterns de détection des types d'études"""
        return {
            StudyDesign.META_ANALYSIS: [
                "meta-analysis", "méta-analyse", "meta analysis",
                "pooled analysis", "analyse groupée"
            ],
            StudyDesign.SYSTEMATIC_REVIEW: [
                "systematic review", "revue systématique",
                "systematic literature review", "cochrane review"
            ],
            StudyDesign.RANDOMIZED_CONTROLLED_TRIAL: [
                "randomized controlled trial", "essai contrôlé randomisé",
                "RCT", "randomized trial", "controlled trial",
                "double-blind", "double aveugle", "placebo-controlled"
            ],
            StudyDesign.COHORT_STUDY: [
                "cohort study", "étude de cohorte", "prospective study",
                "longitudinal study", "follow-up study"
            ],
            StudyDesign.CASE_CONTROL_STUDY: [
                "case-control study", "étude cas-témoins",
                "case control", "retrospective study"
            ],
            StudyDesign.CROSS_SECTIONAL_STUDY: [
                "cross-sectional study", "étude transversale",
                "prevalence study", "survey study"
            ],
            StudyDesign.CASE_SERIES: [
                "case series", "série de cas", "case study",
                "clinical series", "série clinique"
            ],
            StudyDesign.CASE_REPORT: [
                "case report", "rapport de cas", "case presentation",
                "clinical case", "cas clinique"
            ],
            StudyDesign.EXPERT_OPINION: [
                "expert opinion", "opinion d'expert", "consensus",
                "expert panel", "committee statement"
            ],
            StudyDesign.GUIDELINE: [
                "guideline", "guidelines", "recommandations",
                "clinical practice guideline", "consensus statement"
            ]
        }
        
    def _initialize_evidence_mapping(self) -> Dict[StudyDesign, EvidenceLevel]:
        """Initialise le mapping type d'étude -> niveau de preuve"""
        return {
            StudyDesign.META_ANALYSIS: EvidenceLevel.LEVEL_I,
            StudyDesign.SYSTEMATIC_REVIEW: EvidenceLevel.LEVEL_I,
            StudyDesign.RANDOMIZED_CONTROLLED_TRIAL: EvidenceLevel.LEVEL_II,
            StudyDesign.COHORT_STUDY: EvidenceLevel.LEVEL_III,
            StudyDesign.CASE_CONTROL_STUDY: EvidenceLevel.LEVEL_III,
            StudyDesign.CROSS_SECTIONAL_STUDY: EvidenceLevel.LEVEL_IV,
            StudyDesign.CASE_SERIES: EvidenceLevel.LEVEL_IV,
            StudyDesign.CASE_REPORT: EvidenceLevel.LEVEL_IV,
            StudyDesign.EXPERT_OPINION: EvidenceLevel.LEVEL_V,
            StudyDesign.NARRATIVE_REVIEW: EvidenceLevel.LEVEL_V,
            StudyDesign.GUIDELINE: EvidenceLevel.LEVEL_I,  # Si basé sur preuves solides
            StudyDesign.UNKNOWN: EvidenceLevel.UNKNOWN
        }
        
    def _initialize_journal_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialise la base de données des journaux"""
        return {
            "the lancet": {
                "impact_factor": 79.3,
                "quartile": "Q1",
                "peer_reviewed": True,
                "specialty": "General Medicine"
            },
            "new england journal of medicine": {
                "impact_factor": 91.2,
                "quartile": "Q1",
                "peer_reviewed": True,
                "specialty": "General Medicine"
            },
            "nature medicine": {
                "impact_factor": 53.4,
                "quartile": "Q1",
                "peer_reviewed": True,
                "specialty": "Biomedical Research"
            },
            "cochrane database of systematic reviews": {
                "impact_factor": 7.9,
                "quartile": "Q1",
                "peer_reviewed": True,
                "specialty": "Systematic Reviews"
            },
            "médecine tropicale": {
                "impact_factor": 1.2,
                "quartile": "Q3",
                "peer_reviewed": True,
                "specialty": "Tropical Medicine"
            }
        }
        
    def document_source(self, content: str, source_metadata: Dict[str, Any],
                       content_id: Optional[str] = None) -> DocumentationReport:
        """
        Documente une source avec classification automatique
        
        Args:
            content: Contenu textuel
            source_metadata: Métadonnées de la source
            content_id: ID du contenu (généré si None)
            
        Returns:
            DocumentationReport: Rapport de documentation
        """
        if not content_id:
            content_id = hashlib.md5(content.encode()).hexdigest()[:12]
            
        # Extraction des informations de citation
        citation = self._extract_citation(source_metadata)
        
        # Détection du type d'étude
        study_design = self._detect_study_design(content, source_metadata)
        
        # Classification du niveau de preuve
        evidence_level = self._classify_evidence_level(study_design, source_metadata)
        
        # Évaluation de la qualité
        quality_score = self._assess_quality(content, source_metadata, study_design)
        
        # Détection du type de source
        source_type = self._detect_source_type(source_metadata)
        
        # Extraction des détails de l'étude
        study_details = self._extract_study_details(content)
        
        # Création de la source de preuve
        evidence_source = EvidenceSource(
            id=f"src_{content_id}",
            citation=citation,
            source_type=source_type,
            study_design=study_design,
            evidence_level=evidence_level,
            quality_score=quality_score,
            **study_details
        )
        
        self.evidence_sources[evidence_source.id] = evidence_source
        
        # Création de l'enregistrement de provenance
        if self.track_provenance:
            provenance = self._create_provenance_record(source_metadata, content)
            self.provenance_records[content_id].append(provenance)
            
        # Génération du résumé de preuves
        evidence_summary = self._generate_evidence_summary(content_id, [evidence_source])
        
        # Évaluation de la qualité globale
        quality_assessment = self._assess_overall_quality([evidence_source])
        
        # Création du rapport
        report = DocumentationReport(
            content_id=content_id,
            evidence_sources=[evidence_source],
            evidence_summary=evidence_summary,
            provenance_records=self.provenance_records[content_id],
            citation_network=self._build_citation_network([evidence_source]),
            quality_assessment=quality_assessment,
            documentation_date=datetime.now(),
            documenter="EvidenceDocumenter"
        )
        
        self.documentation_reports[content_id] = report
        
        logger.info(f"Source documentée: {content_id} (niveau {evidence_level.value})")
        return report
        
    def _extract_citation(self, metadata: Dict[str, Any]) -> Citation:
        """Extrait les informations de citation"""
        citation_id = hashlib.md5(str(metadata).encode()).hexdigest()[:8]
        
        # Extraction des auteurs
        authors = metadata.get("authors", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",")]
            
        # Extraction de l'année
        year = metadata.get("year")
        if not year and "publication_date" in metadata:
            try:
                pub_date = metadata["publication_date"]
                if isinstance(pub_date, str):
                    year = int(pub_date[:4])
                elif hasattr(pub_date, "year"):
                    year = pub_date.year
            except:
                year = datetime.now().year
                
        return Citation(
            id=citation_id,
            authors=authors,
            title=metadata.get("title", "Titre non spécifié"),
            journal=metadata.get("journal", metadata.get("source")),
            year=year or datetime.now().year,
            volume=metadata.get("volume"),
            issue=metadata.get("issue"),
            pages=metadata.get("pages"),
            doi=metadata.get("doi"),
            pmid=metadata.get("pmid"),
            url=metadata.get("url"),
            access_date=datetime.now() if metadata.get("url") else None
        )
        
    def _detect_study_design(self, content: str, metadata: Dict[str, Any]) -> StudyDesign:
        """Détecte le type d'étude"""
        content_lower = content.lower()
        title_lower = metadata.get("title", "").lower()
        
        # Recherche dans le titre et le contenu
        search_text = f"{title_lower} {content_lower}"
        
        for design, patterns in self.study_design_patterns.items():
            for pattern in patterns:
                if pattern in search_text:
                    return design
                    
        # Détection basée sur la structure du contenu
        if "methods" in content_lower and "results" in content_lower:
            if "randomized" in content_lower or "randomisé" in content_lower:
                return StudyDesign.RANDOMIZED_CONTROLLED_TRIAL
            elif "cohort" in content_lower or "cohorte" in content_lower:
                return StudyDesign.COHORT_STUDY
            elif "case-control" in content_lower or "cas-témoins" in content_lower:
                return StudyDesign.CASE_CONTROL_STUDY
                
        return StudyDesign.UNKNOWN
        
    def _classify_evidence_level(self, study_design: StudyDesign, 
                               metadata: Dict[str, Any]) -> EvidenceLevel:
        """Classifie le niveau de preuve"""
        # Mapping de base
        base_level = self.evidence_level_mapping.get(study_design, EvidenceLevel.UNKNOWN)
        
        # Ajustements basés sur la qualité
        if metadata.get("journal"):
            journal_name = metadata["journal"].lower()
            if journal_name in self.journal_database:
                journal_info = self.journal_database[journal_name]
                if journal_info["quartile"] == "Q1" and journal_info["peer_reviewed"]:
                    # Maintenir le niveau pour les journaux de haute qualité
                    pass
                elif journal_info["quartile"] in ["Q3", "Q4"]:
                    # Dégrader légèrement pour les journaux de moindre qualité
                    if base_level == EvidenceLevel.LEVEL_II:
                        base_level = EvidenceLevel.LEVEL_III
                    elif base_level == EvidenceLevel.LEVEL_III:
                        base_level = EvidenceLevel.LEVEL_IV
                        
        return base_level
        
    def _assess_quality(self, content: str, metadata: Dict[str, Any], 
                       study_design: StudyDesign) -> float:
        """Évalue la qualité de la source"""
        quality_score = 0.5  # Score de base
        
        # Facteurs de qualité
        factors = {
            "peer_review": 0.2,
            "journal_impact": 0.15,
            "study_design": 0.15,
            "sample_size": 0.1,
            "methodology": 0.1,
            "statistical_analysis": 0.1,
            "conflict_of_interest": 0.1,
            "funding_transparency": 0.1
        }
        
        # Évaluation du peer review
        if metadata.get("journal"):
            journal_name = metadata["journal"].lower()
            if journal_name in self.journal_database:
                journal_info = self.journal_database[journal_name]
                if journal_info["peer_reviewed"]:
                    quality_score += factors["peer_review"]
                    
                # Impact du journal
                impact_factor = journal_info.get("impact_factor", 0)
                if impact_factor > 10:
                    quality_score += factors["journal_impact"]
                elif impact_factor > 5:
                    quality_score += factors["journal_impact"] * 0.7
                elif impact_factor > 1:
                    quality_score += factors["journal_impact"] * 0.4
                    
        # Évaluation du type d'étude
        design_scores = {
            StudyDesign.META_ANALYSIS: 1.0,
            StudyDesign.SYSTEMATIC_REVIEW: 0.9,
            StudyDesign.RANDOMIZED_CONTROLLED_TRIAL: 0.8,
            StudyDesign.COHORT_STUDY: 0.6,
            StudyDesign.CASE_CONTROL_STUDY: 0.5,
            StudyDesign.CROSS_SECTIONAL_STUDY: 0.4,
            StudyDesign.CASE_SERIES: 0.3,
            StudyDesign.CASE_REPORT: 0.2,
            StudyDesign.EXPERT_OPINION: 0.3
        }
        
        design_score = design_scores.get(study_design, 0.2)
        quality_score += factors["study_design"] * design_score
        
        # Évaluation de la méthodologie (basée sur le contenu)
        content_lower = content.lower()
        
        methodology_indicators = [
            "statistical analysis", "analyse statistique",
            "confidence interval", "intervalle de confiance",
            "p-value", "valeur p", "significance",
            "bias", "biais", "limitation", "strength"
        ]
        
        methodology_score = 0
        for indicator in methodology_indicators:
            if indicator in content_lower:
                methodology_score += 0.1
                
        quality_score += factors["methodology"] * min(1.0, methodology_score)
        
        # Détection des conflits d'intérêts
        conflict_indicators = [
            "conflict of interest", "conflit d'intérêt",
            "funding", "financement", "sponsor",
            "no conflict", "aucun conflit"
        ]
        
        if any(indicator in content_lower for indicator in conflict_indicators):
            quality_score += factors["conflict_of_interest"]
            
        return min(1.0, quality_score)
        
    def _detect_source_type(self, metadata: Dict[str, Any]) -> SourceType:
        """Détecte le type de source"""
        if metadata.get("journal"):
            return SourceType.PEER_REVIEWED_JOURNAL
        elif metadata.get("source_type") == "guideline":
            return SourceType.CLINICAL_GUIDELINE
        elif metadata.get("url"):
            url = metadata["url"].lower()
            if any(domain in url for domain in ["who.int", "cdc.gov", "nih.gov"]):
                return SourceType.INTERNATIONAL_ORGANIZATION
            elif any(domain in url for domain in ["gov", "gouv"]):
                return SourceType.GOVERNMENT_PUBLICATION
            else:
                return SourceType.WEBSITE
        else:
            return SourceType.OTHER
            
    def _extract_study_details(self, content: str) -> Dict[str, Any]:
        """Extrait les détails de l'étude du contenu"""
        details = {}
        content_lower = content.lower()
        
        # Extraction de la taille d'échantillon
        sample_patterns = [
            r'n\s*=\s*(\d+)',
            r'(\d+)\s+patients?',
            r'(\d+)\s+participants?',
            r'échantillon\s+de\s+(\d+)'
        ]
        
        for pattern in sample_patterns:
            match = re.search(pattern, content_lower)
            if match:
                details["sample_size"] = int(match.group(1))
                break
                
        # Extraction de la durée de suivi
        follow_up_patterns = [
            r'follow-up\s+of\s+([\d\w\s]+)',
            r'suivi\s+de\s+([\d\w\s]+)',
            r'(\d+)\s+months?\s+follow-up',
            r'(\d+)\s+years?\s+follow-up'
        ]
        
        for pattern in follow_up_patterns:
            match = re.search(pattern, content_lower)
            if match:
                details["follow_up_duration"] = match.group(1)
                break
                
        # Détection de la significativité statistique
        if re.search(r'p\s*<\s*0\.05', content_lower):
            details["statistical_significance"] = True
        elif re.search(r'p\s*>\s*0\.05', content_lower):
            details["statistical_significance"] = False
            
        # Extraction de l'intervalle de confiance
        ci_match = re.search(r'(95%\s*ci[^\d]*[\d\.\-\s,]+)', content_lower)
        if ci_match:
            details["confidence_interval"] = ci_match.group(1)
            
        return details
        
    def _create_provenance_record(self, metadata: Dict[str, Any], 
                                content: str) -> ProvenanceRecord:
        """Crée un enregistrement de provenance"""
        source_id = hashlib.md5(str(metadata).encode()).hexdigest()[:12]
        checksum = hashlib.sha256(content.encode()).hexdigest()
        
        return ProvenanceRecord(
            source_id=source_id,
            original_url=metadata.get("url"),
            retrieval_date=datetime.now(),
            retrieval_method="manual_input",
            processor="EvidenceDocumenter",
            processing_date=datetime.now(),
            version="1.0",
            checksum=checksum,
            metadata=metadata.copy()
        )
        
    def _generate_evidence_summary(self, topic: str, 
                                 sources: List[EvidenceSource]) -> EvidenceSummary:
        """Génère un résumé des preuves"""
        if not sources:
            return EvidenceSummary(
                topic=topic,
                sources=[],
                overall_evidence_level=EvidenceLevel.UNKNOWN,
                strength_of_recommendation="insufficient",
                quality_of_evidence="very_low",
                consistency="unknown",
                directness="unknown",
                precision="unknown",
                publication_bias_risk="unknown",
                summary_statement="Preuves insuffisantes",
                recommendations=[],
                limitations=["Nombre insuffisant de sources"]
            )
            
        # Détermination du niveau de preuve global
        evidence_levels = [s.evidence_level for s in sources]
        level_counts = {level: evidence_levels.count(level) for level in EvidenceLevel}
        
        # Le niveau le plus élevé avec au moins une source
        overall_level = EvidenceLevel.LEVEL_V
        for level in [EvidenceLevel.LEVEL_I, EvidenceLevel.LEVEL_II, 
                     EvidenceLevel.LEVEL_III, EvidenceLevel.LEVEL_IV]:
            if level_counts[level] > 0:
                overall_level = level
                break
                
        # Évaluation de la qualité globale
        avg_quality = sum(s.quality_score for s in sources) / len(sources)
        
        if avg_quality >= 0.8:
            quality_of_evidence = "high"
        elif avg_quality >= 0.6:
            quality_of_evidence = "moderate"
        elif avg_quality >= 0.4:
            quality_of_evidence = "low"
        else:
            quality_of_evidence = "very_low"
            
        # Force de la recommandation
        if overall_level in [EvidenceLevel.LEVEL_I, EvidenceLevel.LEVEL_II] and avg_quality >= 0.7:
            strength = "strong"
        elif overall_level == EvidenceLevel.LEVEL_III and avg_quality >= 0.6:
            strength = "moderate"
        else:
            strength = "weak"
            
        # Évaluation de la cohérence
        study_designs = [s.study_design for s in sources]
        if len(set(study_designs)) == 1:
            consistency = "consistent"
        elif len(sources) < 3:
            consistency = "unknown"
        else:
            consistency = "inconsistent"
            
        return EvidenceSummary(
            topic=topic,
            sources=sources,
            overall_evidence_level=overall_level,
            strength_of_recommendation=strength,
            quality_of_evidence=quality_of_evidence,
            consistency=consistency,
            directness="direct",  # Simplification
            precision="precise" if avg_quality >= 0.7 else "imprecise",
            publication_bias_risk="low" if len(sources) >= 5 else "moderate",
            summary_statement=f"Preuves de niveau {overall_level.value} avec qualité {quality_of_evidence}",
            recommendations=self._generate_recommendations(sources, strength),
            limitations=self._identify_limitations(sources)
        )
        
    def _generate_recommendations(self, sources: List[EvidenceSource], 
                                strength: str) -> List[str]:
        """Génère des recommandations basées sur les preuves"""
        recommendations = []
        
        if strength == "strong":
            recommendations.append("Recommandation forte basée sur des preuves de haute qualité")
        elif strength == "moderate":
            recommendations.append("Recommandation modérée basée sur des preuves de qualité acceptable")
        else:
            recommendations.append("Recommandation faible - preuves limitées")
            
        # Recommandations spécifiques basées sur les types d'études
        study_types = [s.study_design for s in sources]
        
        if StudyDesign.META_ANALYSIS in study_types:
            recommendations.append("Méta-analyse disponible - preuves synthétisées")
        if StudyDesign.RANDOMIZED_CONTROLLED_TRIAL in study_types:
            recommendations.append("Essais contrôlés randomisés disponibles")
            
        return recommendations
        
    def _identify_limitations(self, sources: List[EvidenceSource]) -> List[str]:
        """Identifie les limitations des preuves"""
        limitations = []
        
        if len(sources) < 3:
            limitations.append("Nombre limité de sources")
            
        avg_quality = sum(s.quality_score for s in sources) / len(sources)
        if avg_quality < 0.6:
            limitations.append("Qualité moyenne des sources limitée")
            
        study_designs = [s.study_design for s in sources]
        if StudyDesign.CASE_REPORT in study_designs or StudyDesign.CASE_SERIES in study_designs:
            limitations.append("Inclusion d'études de faible niveau de preuve")
            
        if all(s.sample_size and s.sample_size < 100 for s in sources if s.sample_size):
            limitations.append("Tailles d'échantillon limitées")
            
        return limitations
        
    def _build_citation_network(self, sources: List[EvidenceSource]) -> Dict[str, List[str]]:
        """Construit le réseau de citations"""
        network = {}
        
        for source in sources:
            network[source.id] = []
            # Ici on pourrait analyser les références croisées
            # Pour la démonstration, on crée un réseau simple
            
        return network
        
    def _assess_overall_quality(self, sources: List[EvidenceSource]) -> Dict[str, Any]:
        """Évalue la qualité globale des preuves"""
        if not sources:
            return {"overall_score": 0.0, "grade": "insufficient"}
            
        scores = [s.quality_score for s in sources]
        overall_score = sum(scores) / len(scores)
        
        # Système de notation GRADE simplifié
        if overall_score >= 0.8:
            grade = "high"
        elif overall_score >= 0.6:
            grade = "moderate"
        elif overall_score >= 0.4:
            grade = "low"
        else:
            grade = "very_low"
            
        return {
            "overall_score": overall_score,
            "grade": grade,
            "individual_scores": scores,
            "source_count": len(sources),
            "evidence_levels": [s.evidence_level.value for s in sources]
        }
        
    def format_citation(self, citation: Citation, 
                       format_type: CitationFormat = None) -> str:
        """
        Formate une citation selon le style demandé
        
        Args:
            citation: Citation à formater
            format_type: Format de citation
            
        Returns:
            str: Citation formatée
        """
        if not format_type:
            format_type = self.default_citation_format
            
        if format_type == CitationFormat.VANCOUVER:
            return self._format_vancouver(citation)
        elif format_type == CitationFormat.APA:
            return self._format_apa(citation)
        elif format_type == CitationFormat.HARVARD:
            return self._format_harvard(citation)
        else:
            return self._format_vancouver(citation)  # Par défaut
            
    def _format_vancouver(self, citation: Citation) -> str:
        """Formate selon le style Vancouver"""
        authors = ", ".join(citation.authors[:3])
        if len(citation.authors) > 3:
            authors += ", et al."
            
        formatted = f"{authors}. {citation.title}."
        
        if citation.journal:
            formatted += f" {citation.journal}."
            
        formatted += f" {citation.year}"
        
        if citation.volume:
            formatted += f";{citation.volume}"
            if citation.issue:
                formatted += f"({citation.issue})"
                
        if citation.pages:
            formatted += f":{citation.pages}"
            
        if citation.doi:
            formatted += f". doi:{citation.doi}"
            
        return formatted + "."
        
    def _format_apa(self, citation: Citation) -> str:
        """Formate selon le style APA"""
        if citation.authors:
            if len(citation.authors) == 1:
                authors = citation.authors[0]
            elif len(citation.authors) <= 7:
                authors = ", ".join(citation.authors[:-1]) + f", & {citation.authors[-1]}"
            else:
                authors = ", ".join(citation.authors[:6]) + ", ... " + citation.authors[-1]
        else:
            authors = "Auteur inconnu"
            
        formatted = f"{authors} ({citation.year}). {citation.title}."
        
        if citation.journal:
            formatted += f" {citation.journal}"
            if citation.volume:
                formatted += f", {citation.volume}"
                if citation.issue:
                    formatted += f"({citation.issue})"
                    
        if citation.pages:
            formatted += f", {citation.pages}"
            
        if citation.doi:
            formatted += f". https://doi.org/{citation.doi}"
            
        return formatted + "."
        
    def _format_harvard(self, citation: Citation) -> str:
        """Formate selon le style Harvard"""
        if citation.authors:
            if len(citation.authors) == 1:
                authors = citation.authors[0]
            else:
                authors = citation.authors[0] + " et al."
        else:
            authors = "Auteur inconnu"
            
        formatted = f"{authors} {citation.year}, '{citation.title}'"
        
        if citation.journal:
            formatted += f", {citation.journal}"
            if citation.volume:
                formatted += f", vol. {citation.volume}"
                if citation.issue:
                    formatted += f", no. {citation.issue}"
                    
        if citation.pages:
            formatted += f", pp. {citation.pages}"
            
        return formatted + "."
        
    def get_documentation_report(self, content_id: str) -> Optional[DocumentationReport]:
        """Récupère le rapport de documentation"""
        return self.documentation_reports.get(content_id)
        
    def search_by_evidence_level(self, level: EvidenceLevel) -> List[EvidenceSource]:
        """Recherche par niveau de preuve"""
        return [source for source in self.evidence_sources.values() 
                if source.evidence_level == level]
                
    def search_by_study_design(self, design: StudyDesign) -> List[EvidenceSource]:
        """Recherche par type d'étude"""
        return [source for source in self.evidence_sources.values() 
                if source.study_design == design]
                
    def generate_bibliography(self, content_ids: List[str], 
                            format_type: CitationFormat = None) -> str:
        """Génère une bibliographie"""
        bibliography = []
        
        for content_id in content_ids:
            report = self.documentation_reports.get(content_id)
            if report:
                for source in report.evidence_sources:
                    citation_text = self.format_citation(source.citation, format_type)
                    bibliography.append(citation_text)
                    
        # Tri alphabétique
        bibliography.sort()
        
        return "\n".join(f"{i+1}. {citation}" for i, citation in enumerate(bibliography))
        
    def generate_evidence_table(self, content_ids: List[str]) -> List[Dict[str, Any]]:
        """Génère un tableau des preuves"""
        table = []
        
        for content_id in content_ids:
            report = self.documentation_reports.get(content_id)
            if report:
                for source in report.evidence_sources:
                    table.append({
                        "authors": ", ".join(source.citation.authors[:3]),
                        "year": source.citation.year,
                        "title": source.citation.title,
                        "journal": source.citation.journal,
                        "study_design": source.study_design.value,
                        "evidence_level": source.evidence_level.value,
                        "quality_score": f"{source.quality_score:.2f}",
                        "sample_size": source.sample_size or "NR",
                        "doi": source.citation.doi or "NR"
                    })
                    
        return table
        
    def export_data(self, filepath: str) -> bool:
        """Exporte les données de documentation"""
        try:
            export_data = {
                "evidence_sources": {
                    source_id: {
                        "id": source.id,
                        "citation": {
                            "authors": source.citation.authors,
                            "title": source.citation.title,
                            "journal": source.citation.journal,
                            "year": source.citation.year,
                            "doi": source.citation.doi,
                            "pmid": source.citation.pmid,
                            "url": source.citation.url
                        },
                        "source_type": source.source_type.value,
                        "study_design": source.study_design.value,
                        "evidence_level": source.evidence_level.value,
                        "quality_score": source.quality_score,
                        "sample_size": source.sample_size,
                        "statistical_significance": source.statistical_significance,
                        "bias_risk": source.bias_risk
                    } for source_id, source in self.evidence_sources.items()
                },
                "documentation_reports": {
                    report_id: {
                        "content_id": report.content_id,
                        "evidence_summary": {
                            "topic": report.evidence_summary.topic,
                            "overall_evidence_level": report.evidence_summary.overall_evidence_level.value,
                            "strength_of_recommendation": report.evidence_summary.strength_of_recommendation,
                            "quality_of_evidence": report.evidence_summary.quality_of_evidence,
                            "summary_statement": report.evidence_summary.summary_statement,
                            "recommendations": report.evidence_summary.recommendations,
                            "limitations": report.evidence_summary.limitations
                        },
                        "quality_assessment": report.quality_assessment,
                        "documentation_date": report.documentation_date.isoformat(),
                        "documenter": report.documenter
                    } for report_id, report in self.documentation_reports.items()
                },
                "statistics": {
                    "total_sources": len(self.evidence_sources),
                    "total_reports": len(self.documentation_reports),
                    "evidence_level_distribution": {
                        level.value: len(self.search_by_evidence_level(level))
                        for level in EvidenceLevel
                    },
                    "study_design_distribution": {
                        design.value: len(self.search_by_study_design(design))
                        for design in StudyDesign
                    }
                },
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Données de documentation exportées: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export: {e}")
            return False

# Fonction principale de démonstration
def main():
    """
    Fonction de démonstration du système de documentation des preuves
    """
    print("📚 Test du Système de Documentation des Sources et Niveaux de Preuve")
    print("=" * 70)
    
    # Configuration
    config = {
        "citation_format": CitationFormat.VANCOUVER,
        "require_citations": True,
        "track_provenance": True,
        "version_control": True
    }
    
    # Création du système
    documenter = EvidenceDocumenter(config)
    print(f"✅ Système créé avec {len(documenter.journal_database)} journaux référencés")
    
    # Test 1: Documentation d'une méta-analyse
    print("\n🏆 Test 1: Documentation méta-analyse (Niveau I)")
    
    meta_analysis_content = """
    Efficacité de l'artéméther-luméfantrine dans le traitement du paludisme: 
    méta-analyse de 15 essais contrôlés randomisés.
    
    Méthodes: Recherche systématique dans PubMed, Cochrane Library et Embase. 
    Inclusion de 15 ECR (n=8,247 patients). Analyse statistique avec modèle 
    à effets aléatoires.
    
    Résultats: Taux de guérison poolé de 96.2% (IC95%: 94.1-97.8, p<0.001). 
    Hétérogénéité faible (I²=12%). Aucun biais de publication détecté.
    
    Conclusion: L'artéméther-luméfantrine démontre une excellente efficacité 
    avec des preuves de haute qualité.
    """
    
    meta_metadata = {
        "title": "Efficacité de l'artéméther-luméfantrine: méta-analyse",
        "authors": ["Dr. Aminata Sow", "Prof. Jean-Claude Mbarga", "Dr. Marie Dubois"],
        "journal": "Cochrane Database of Systematic Reviews",
        "year": 2024,
        "volume": "3",
        "doi": "10.1002/14651858.CD012345",
        "pmid": "38123456"
    }
    
    report1 = documenter.document_source(meta_analysis_content, meta_metadata, "meta_001")
    
    print(f"   Niveau de preuve: {report1.evidence_sources[0].evidence_level.value}")
    print(f"   Type d'étude: {report1.evidence_sources[0].study_design.value}")
    print(f"   Score qualité: {report1.evidence_sources[0].quality_score:.3f}")
    print(f"   Force recommandation: {report1.evidence_summary.strength_of_recommendation}")
    
    # Test 2: Documentation d'un essai contrôlé randomisé
    print("\n🎯 Test 2: Documentation ECR (Niveau II)")
    
    rct_content = """
    Essai contrôlé randomisé en double aveugle comparant l'artéméther-luméfantrine 
    au placebo dans le traitement du paludisme non compliqué.
    
    Méthodes: 1,200 patients randomisés (1:1). Critère principal: guérison 
    parasitologique à J28. Analyse en intention de traiter.
    
    Résultats: Guérison: 97.1% vs 8.2% (p<0.001, RR=11.8, IC95%: 8.9-15.6). 
    Effets secondaires mineurs: 12% vs 5% (p=0.02).
    
    Conclusion: Efficacité supérieure significative de l'AL.
    """
    
    rct_metadata = {
        "title": "Efficacité de l'artéméther-luméfantrine: essai randomisé",
        "authors": ["Dr. Paul Nguema", "Dr. Fatima Al-Hassan"],
        "journal": "The Lancet",
        "year": 2025,
        "volume": "401",
        "issue": "10375",
        "pages": "567-575",
        "doi": "10.1016/S0140-6736(23)00123-4"
    }
    
    report2 = documenter.document_source(rct_content, rct_metadata, "rct_001")
    
    print(f"   Niveau de preuve: {report2.evidence_sources[0].evidence_level.value}")
    print(f"   Taille échantillon: {report2.evidence_sources[0].sample_size}")
    print(f"   Significativité: {report2.evidence_sources[0].statistical_significance}")
    print(f"   IC: {report2.evidence_sources[0].confidence_interval}")
    
    # Test 3: Documentation d'une série de cas (Niveau IV)
    print("\n📋 Test 3: Documentation série de cas (Niveau IV)")
    
    case_series_content = """
    Série de 25 cas de paludisme grave traités par artésunate intraveineux 
    au service de réanimation de l'Hôpital Général de Douala.
    
    Patients: 25 adultes avec paludisme grave (score de Glasgow <11). 
    Traitement: artésunate IV 2.4mg/kg à H0, H12, H24 puis quotidien.
    
    Résultats: Guérison complète: 22/25 (88%). Décès: 3/25 (12%). 
    Durée moyenne d'hospitalisation: 6.2 jours.
    
    Conclusion: Bonne efficacité de l'artésunate dans cette série.
    """
    
    case_metadata = {
        "title": "Série de cas: paludisme grave traité par artésunate",
        "authors": ["Dr. Martin Dupont"],
        "journal": "Médecine Tropicale",
        "year": 2023,
        "volume": "83",
        "pages": "45-52"
    }
    
    report3 = documenter.document_source(case_series_content, case_metadata, "case_001")
    
    print(f"   Niveau de preuve: {report3.evidence_sources[0].evidence_level.value}")
    print(f"   Score qualité: {report3.evidence_sources[0].quality_score:.3f}")
    print(f"   Limitations: {len(report3.evidence_summary.limitations)}")
    
    # Test 4: Formatage des citations
    print("\n📝 Test 4: Formatage des citations")
    
    citation = report1.evidence_sources[0].citation
    
    vancouver = documenter.format_citation(citation, CitationFormat.VANCOUVER)
    apa = documenter.format_citation(citation, CitationFormat.APA)
    harvard = documenter.format_citation(citation, CitationFormat.HARVARD)
    
    print("   Vancouver:")
    print(f"     {vancouver}")
    print("   APA:")
    print(f"     {apa}")
    print("   Harvard:")
    print(f"     {harvard}")
    
    # Test 5: Recherche par niveau de preuve
    print("\n🔍 Test 5: Recherche par niveau de preuve")
    
    level_i_sources = documenter.search_by_evidence_level(EvidenceLevel.LEVEL_I)
    level_ii_sources = documenter.search_by_evidence_level(EvidenceLevel.LEVEL_II)
    level_iv_sources = documenter.search_by_evidence_level(EvidenceLevel.LEVEL_IV)
    
    print(f"   Niveau I: {len(level_i_sources)} sources")
    print(f"   Niveau II: {len(level_ii_sources)} sources")
    print(f"   Niveau IV: {len(level_iv_sources)} sources")
    
    # Test 6: Recherche par type d'étude
    print("\n🧪 Test 6: Recherche par type d'étude")
    
    meta_sources = documenter.search_by_study_design(StudyDesign.META_ANALYSIS)
    rct_sources = documenter.search_by_study_design(StudyDesign.RANDOMIZED_CONTROLLED_TRIAL)
    case_sources = documenter.search_by_study_design(StudyDesign.CASE_SERIES)
    
    print(f"   Méta-analyses: {len(meta_sources)}")
    print(f"   ECR: {len(rct_sources)}")
    print(f"   Séries de cas: {len(case_sources)}")
    
    # Test 7: Génération de bibliographie
    print("\n📖 Test 7: Génération de bibliographie")
    
    bibliography = documenter.generate_bibliography(
        ["meta_001", "rct_001", "case_001"], 
        CitationFormat.VANCOUVER
    )
    
    print("   Bibliographie (Vancouver):")
    for line in bibliography.split("\n")[:3]:  # Première 3 références
        print(f"     {line}")
        
    # Test 8: Tableau des preuves
    print("\n📊 Test 8: Tableau des preuves")
    
    evidence_table = documenter.generate_evidence_table(["meta_001", "rct_001", "case_001"])
    
    print("   Tableau des preuves:")
    print(f"     {'Auteurs':<20} {'Année':<6} {'Type':<15} {'Niveau':<8} {'Qualité':<8}")
    print("     " + "-" * 65)
    
    for row in evidence_table:
        authors = row['authors'][:17] + "..." if len(row['authors']) > 20 else row['authors']
        print(f"     {authors:<20} {row['year']:<6} {row['study_design'][:12]:<15} {row['evidence_level']:<8} {row['quality_score']:<8}")
        
    # Test 9: Résumé des preuves globales
    print("\n📈 Test 9: Résumé des preuves globales")
    
    all_sources = list(documenter.evidence_sources.values())
    global_summary = documenter._generate_evidence_summary("Traitement paludisme", all_sources)
    
    print(f"   Niveau global: {global_summary.overall_evidence_level.value}")
    print(f"   Qualité: {global_summary.quality_of_evidence}")
    print(f"   Force recommandation: {global_summary.strength_of_recommendation}")
    print(f"   Cohérence: {global_summary.consistency}")
    
    print("   Recommandations:")
    for rec in global_summary.recommendations[:3]:
        print(f"     • {rec}")
        
    if global_summary.limitations:
        print("   Limitations:")
        for lim in global_summary.limitations[:3]:
            print(f"     ⚠ {lim}")
            
    # Test 10: Export des données
    print("\n💾 Test 10: Export des données")
    
    export_file = "evidence_documentation_export.json"
    if documenter.export_data(export_file):
        print(f"   ✅ Données exportées: {export_file}")
        
        # Statistiques d'export
        with open(export_file, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
            
        stats = export_data['statistics']
        print(f"   Sources documentées: {stats['total_sources']}")
        print(f"   Rapports générés: {stats['total_reports']}")
        
        print("   Distribution niveaux de preuve:")
        for level, count in stats['evidence_level_distribution'].items():
            if count > 0:
                print(f"     {level}: {count}")
    else:
        print(f"   ❌ Erreur lors de l'export")
        
    print("\n" + "=" * 70)
    print("🎯 Objectif 28 - Documentation sources et niveaux de preuve: IMPLÉMENTÉ")
    print("   ✓ Classification automatique niveaux de preuve EBM")
    print("   ✓ Génération citations bibliographiques multiples formats")
    print("   ✓ Traçabilité complète des sources")
    print("   ✓ Évaluation qualité des preuves")
    print("   ✓ Résumés de preuves structurés")
    print("   ✓ Recherche par niveau et type d'étude")
    print("   ✓ Tableaux et bibliographies automatiques")
    print("   ✓ Système de provenance")
    print("   ✓ Export données complètes")
    print("   ✓ Support standards internationaux")

if __name__ == "__main__":
    main()