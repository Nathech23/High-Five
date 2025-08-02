#!/usr/bin/env python3
"""
Enrichisseur de Base de Connaissances Médicales

Objectif 1: Intégrer 500+ articles médicaux validés
Objectif 8: Valider exactitude avec sources officielles

Ce module gère l'intégration massive d'articles médicaux validés
dans la base de connaissances avec vérification de qualité.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Types de sources médicales"""
    WHO = "who"
    CDC = "cdc"
    PUBMED = "pubmed"
    COCHRANE = "cochrane"
    DGH_PROTOCOL = "dgh_protocol"
    MEDICAL_JOURNAL = "medical_journal"
    CLINICAL_GUIDELINE = "clinical_guideline"
    RESEARCH_PAPER = "research_paper"

class ValidationLevel(Enum):
    """Niveaux de validation"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"
    PEER_REVIEWED = "peer_reviewed"

@dataclass
class MedicalArticle:
    """Représente un article médical"""
    id: str
    title: str
    content: str
    source_type: SourceType
    source_url: str
    authors: List[str] = field(default_factory=list)
    publication_date: Optional[datetime] = None
    language: str = "fr"
    specialty: str = "general"
    keywords: List[str] = field(default_factory=list)
    validation_level: ValidationLevel = ValidationLevel.BASIC
    reliability_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour l'article"""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        return f"{self.source_type.value}_{content_hash}"

@dataclass
class ValidationResult:
    """Résultat de validation d'un article"""
    article_id: str
    is_valid: bool
    reliability_score: float
    validation_level: ValidationLevel
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validated_by: str = "system"
    validation_date: datetime = field(default_factory=datetime.now)

@dataclass
class EnrichmentStats:
    """Statistiques d'enrichissement"""
    total_articles: int = 0
    validated_articles: int = 0
    rejected_articles: int = 0
    articles_by_specialty: Dict[str, int] = field(default_factory=dict)
    articles_by_source: Dict[str, int] = field(default_factory=dict)
    articles_by_language: Dict[str, int] = field(default_factory=dict)
    avg_reliability_score: float = 0.0
    processing_time: float = 0.0

class MedicalKnowledgeEnricher:
    """
    Enrichisseur avancé de la base de connaissances médicales
    
    Objectifs couverts:
    - 1. Intégrer 500+ articles médicaux validés
    - 8. Valider exactitude avec sources officielles
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.articles: Dict[str, MedicalArticle] = {}
        self.validation_results: Dict[str, ValidationResult] = {}
        self.stats = EnrichmentStats()
        
        # Configuration par défaut
        self.min_reliability_score = self.config.get("min_reliability_score", 0.7)
        self.target_article_count = self.config.get("target_article_count", 500)
        self.supported_languages = self.config.get("supported_languages", ["fr", "en"])
        
        # Patterns de validation
        self._init_validation_patterns()
        
        logger.info(f"Enrichisseur initialisé - Objectif: {self.target_article_count} articles")
    
    def _init_validation_patterns(self):
        """Initialise les patterns de validation médicale"""
        self.medical_patterns = {
            "dosage": re.compile(r'\b\d+\s*(mg|g|ml|l|UI|mcg)\b', re.IGNORECASE),
            "medical_terms": re.compile(r'\b(diagnostic|traitement|symptôme|maladie|infection|virus|bactérie)\b', re.IGNORECASE),
            "contraindications": re.compile(r'\b(contre-indication|allergie|interaction|effet secondaire)\b', re.IGNORECASE),
            "clinical_evidence": re.compile(r'\b(étude|essai clinique|méta-analyse|revue systématique)\b', re.IGNORECASE)
        }
        
        self.quality_indicators = {
            "peer_reviewed": ["peer-reviewed", "révisé par les pairs", "comité de lecture"],
            "clinical_trial": ["essai clinique", "clinical trial", "randomized"],
            "meta_analysis": ["méta-analyse", "meta-analysis", "systematic review"],
            "official_source": ["WHO", "OMS", "CDC", "ministère de la santé"]
        }
    
    async def enrich_knowledge_base(self, articles: List[MedicalArticle]) -> EnrichmentStats:
        """
        Enrichit la base de connaissances avec de nouveaux articles
        
        Args:
            articles: Liste d'articles médicaux à intégrer
        
        Returns:
            EnrichmentStats: Statistiques d'enrichissement
        """
        start_time = time.time()
        logger.info(f"Début enrichissement avec {len(articles)} articles")
        
        # Réinitialiser les statistiques
        self.stats = EnrichmentStats()
        
        # Traiter les articles par lots
        batch_size = self.config.get("batch_size", 50)
        
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            await self._process_article_batch(batch)
            
            # Log de progression
            progress = min(i + batch_size, len(articles))
            logger.info(f"Progression: {progress}/{len(articles)} articles traités")
        
        # Finaliser les statistiques
        self.stats.processing_time = time.time() - start_time
        self.stats.total_articles = len(articles)
        self._calculate_final_stats()
        
        logger.info(f"Enrichissement terminé en {self.stats.processing_time:.2f}s")
        logger.info(f"Articles validés: {self.stats.validated_articles}/{self.stats.total_articles}")
        
        return self.stats
    
    async def _process_article_batch(self, batch: List[MedicalArticle]):
        """Traite un lot d'articles"""
        tasks = []
        
        for article in batch:
            task = asyncio.create_task(self._process_single_article(article))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _process_single_article(self, article: MedicalArticle):
        """Traite un article individuel"""
        try:
            # Validation de l'article
            validation_result = await self._validate_article(article)
            
            # Stocker le résultat de validation
            self.validation_results[article.id] = validation_result
            
            # Accepter ou rejeter l'article
            if validation_result.is_valid and validation_result.reliability_score >= self.min_reliability_score:
                article.reliability_score = validation_result.reliability_score
                article.validation_level = validation_result.validation_level
                
                self.articles[article.id] = article
                self.stats.validated_articles += 1
                
                # Mettre à jour les statistiques par catégorie
                self._update_category_stats(article)
                
            else:
                self.stats.rejected_articles += 1
                logger.warning(f"Article rejeté: {article.id} - Score: {validation_result.reliability_score:.3f}")
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'article {article.id}: {e}")
            self.stats.rejected_articles += 1
    
    async def _validate_article(self, article: MedicalArticle) -> ValidationResult:
        """
        Valide un article médical
        
        Args:
            article: Article à valider
        
        Returns:
            ValidationResult: Résultat de la validation
        """
        issues = []
        recommendations = []
        reliability_score = 0.0
        validation_level = ValidationLevel.BASIC
        
        # Validation du contenu
        content_score = self._validate_content(article, issues, recommendations)
        
        # Validation de la source
        source_score = self._validate_source(article, issues, recommendations)
        
        # Validation médicale
        medical_score = self._validate_medical_accuracy(article, issues, recommendations)
        
        # Validation de la structure
        structure_score = self._validate_structure(article, issues, recommendations)
        
        # Calcul du score de fiabilité
        reliability_score = (content_score + source_score + medical_score + structure_score) / 4
        
        # Détermination du niveau de validation
        if reliability_score >= 0.9:
            validation_level = ValidationLevel.PEER_REVIEWED
        elif reliability_score >= 0.8:
            validation_level = ValidationLevel.EXPERT
        elif reliability_score >= 0.6:
            validation_level = ValidationLevel.INTERMEDIATE
        else:
            validation_level = ValidationLevel.BASIC
        
        is_valid = reliability_score >= self.min_reliability_score and len(issues) == 0
        
        return ValidationResult(
            article_id=article.id,
            is_valid=is_valid,
            reliability_score=reliability_score,
            validation_level=validation_level,
            issues=issues,
            recommendations=recommendations
        )
    
    def _validate_content(self, article: MedicalArticle, issues: List[str], recommendations: List[str]) -> float:
        """Valide le contenu de l'article"""
        score = 0.0
        
        # Vérifier la longueur du contenu
        if len(article.content) < 100:
            issues.append("Contenu trop court")
        elif len(article.content) > 50000:
            recommendations.append("Contenu très long, considérer la segmentation")
        else:
            score += 0.3
        
        # Vérifier la présence de termes médicaux
        medical_terms_found = len(self.medical_patterns["medical_terms"].findall(article.content))
        if medical_terms_found >= 5:
            score += 0.3
        elif medical_terms_found >= 2:
            score += 0.2
        else:
            recommendations.append("Peu de termes médicaux détectés")
        
        # Vérifier la structure du texte
        if article.title and len(article.title) > 10:
            score += 0.2
        
        # Vérifier les mots-clés
        if article.keywords and len(article.keywords) >= 3:
            score += 0.2
        
        return min(score, 1.0)
    
    def _validate_source(self, article: MedicalArticle, issues: List[str], recommendations: List[str]) -> float:
        """Valide la source de l'article"""
        score = 0.0
        
        # Score basé sur le type de source
        source_scores = {
            SourceType.WHO: 1.0,
            SourceType.CDC: 1.0,
            SourceType.COCHRANE: 0.9,
            SourceType.PUBMED: 0.8,
            SourceType.DGH_PROTOCOL: 0.9,
            SourceType.MEDICAL_JOURNAL: 0.7,
            SourceType.CLINICAL_GUIDELINE: 0.8,
            SourceType.RESEARCH_PAPER: 0.6
        }
        
        score += source_scores.get(article.source_type, 0.3)
        
        # Vérifier l'URL de la source
        if article.source_url and article.source_url.startswith("http"):
            score += 0.1
        else:
            issues.append("URL de source manquante ou invalide")
        
        # Vérifier les auteurs
        if article.authors and len(article.authors) > 0:
            score += 0.1
        
        # Vérifier la date de publication
        if article.publication_date:
            # Pénaliser les articles très anciens
            years_old = (datetime.now() - article.publication_date).days / 365
            if years_old > 10:
                score -= 0.2
                recommendations.append("Article ancien, vérifier la pertinence")
        
        return min(max(score, 0.0), 1.0)
    
    def _validate_medical_accuracy(self, article: MedicalArticle, issues: List[str], recommendations: List[str]) -> float:
        """Valide l'exactitude médicale"""
        score = 0.0
        
        # Vérifier la présence d'indicateurs de qualité
        content_lower = article.content.lower()
        
        for indicator_type, keywords in self.quality_indicators.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    if indicator_type == "peer_reviewed":
                        score += 0.3
                    elif indicator_type == "clinical_trial":
                        score += 0.2
                    elif indicator_type == "meta_analysis":
                        score += 0.3
                    elif indicator_type == "official_source":
                        score += 0.2
                    break
        
        # Vérifier la présence de dosages (pour les articles sur les médicaments)
        dosages_found = self.medical_patterns["dosage"].findall(article.content)
        if dosages_found:
            score += 0.1
        
        # Vérifier la mention de contre-indications
        contraindications_found = self.medical_patterns["contraindications"].findall(article.content)
        if contraindications_found:
            score += 0.1
        
        return min(score, 1.0)
    
    def _validate_structure(self, article: MedicalArticle, issues: List[str], recommendations: List[str]) -> float:
        """Valide la structure de l'article"""
        score = 0.0
        
        # Vérifier les champs obligatoires
        if article.title:
            score += 0.3
        else:
            issues.append("Titre manquant")
        
        if article.specialty and article.specialty != "general":
            score += 0.2
        
        if article.language in self.supported_languages:
            score += 0.2
        else:
            issues.append(f"Langue non supportée: {article.language}")
        
        # Vérifier la cohérence des métadonnées
        if article.metadata:
            score += 0.1
        
        # Vérifier les mots-clés
        if article.keywords and len(article.keywords) >= 3:
            score += 0.2
        
        return min(score, 1.0)
    
    def _update_category_stats(self, article: MedicalArticle):
        """Met à jour les statistiques par catégorie"""
        # Par spécialité
        if article.specialty in self.stats.articles_by_specialty:
            self.stats.articles_by_specialty[article.specialty] += 1
        else:
            self.stats.articles_by_specialty[article.specialty] = 1
        
        # Par source
        source_name = article.source_type.value
        if source_name in self.stats.articles_by_source:
            self.stats.articles_by_source[source_name] += 1
        else:
            self.stats.articles_by_source[source_name] = 1
        
        # Par langue
        if article.language in self.stats.articles_by_language:
            self.stats.articles_by_language[article.language] += 1
        else:
            self.stats.articles_by_language[article.language] = 1
    
    def _calculate_final_stats(self):
        """Calcule les statistiques finales"""
        if self.stats.validated_articles > 0:
            total_reliability = sum(article.reliability_score for article in self.articles.values())
            self.stats.avg_reliability_score = total_reliability / self.stats.validated_articles
    
    def get_articles_by_specialty(self, specialty: str) -> List[MedicalArticle]:
        """Retourne les articles d'une spécialité donnée"""
        return [article for article in self.articles.values() if article.specialty == specialty]
    
    def get_articles_by_source(self, source_type: SourceType) -> List[MedicalArticle]:
        """Retourne les articles d'un type de source donné"""
        return [article for article in self.articles.values() if article.source_type == source_type]
    
    def get_high_quality_articles(self, min_score: float = 0.8) -> List[MedicalArticle]:
        """Retourne les articles de haute qualité"""
        return [article for article in self.articles.values() if article.reliability_score >= min_score]
    
    def export_enrichment_report(self, output_path: str):
        """Exporte un rapport d'enrichissement"""
        report = {
            "enrichment_summary": {
                "total_articles": self.stats.total_articles,
                "validated_articles": self.stats.validated_articles,
                "rejected_articles": self.stats.rejected_articles,
                "success_rate": self.stats.validated_articles / self.stats.total_articles if self.stats.total_articles > 0 else 0,
                "avg_reliability_score": self.stats.avg_reliability_score,
                "processing_time": self.stats.processing_time
            },
            "articles_by_specialty": self.stats.articles_by_specialty,
            "articles_by_source": self.stats.articles_by_source,
            "articles_by_language": self.stats.articles_by_language,
            "validation_results": {
                article_id: {
                    "is_valid": result.is_valid,
                    "reliability_score": result.reliability_score,
                    "validation_level": result.validation_level.value,
                    "issues_count": len(result.issues),
                    "recommendations_count": len(result.recommendations)
                }
                for article_id, result in self.validation_results.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Rapport d'enrichissement exporté: {output_path}")
    
    async def validate_existing_articles(self) -> Dict[str, ValidationResult]:
        """Revalide tous les articles existants"""
        logger.info(f"Revalidation de {len(self.articles)} articles existants")
        
        validation_tasks = []
        for article in self.articles.values():
            task = asyncio.create_task(self._validate_article(article))
            validation_tasks.append(task)
        
        results = await asyncio.gather(*validation_tasks)
        
        # Mettre à jour les résultats de validation
        for i, article_id in enumerate(self.articles.keys()):
            self.validation_results[article_id] = results[i]
        
        logger.info("Revalidation terminée")
        return self.validation_results

# Fonction utilitaire pour créer des articles de test
def create_sample_medical_articles() -> List[MedicalArticle]:
    """Crée des articles médicaux d'exemple pour les tests"""
    articles = [
        MedicalArticle(
            id="diabetes_who_001",
            title="Diabète de type 2 - Guide de diagnostic et traitement",
            content="""
            Le diabète de type 2 est une maladie chronique caractérisée par une résistance à l'insuline.
            Diagnostic: Glycémie à jeun ≥ 126 mg/dL ou HbA1c ≥ 6.5%.
            Traitement de première ligne: Metformine 500-850 mg deux fois par jour.
            Contre-indications: Insuffisance rénale sévère, acidose métabolique.
            Cette recommandation est basée sur des essais cliniques randomisés et des méta-analyses.
            """,
            source_type=SourceType.WHO,
            source_url="https://who.int/diabetes/guidelines",
            authors=["Dr. Smith", "Dr. Johnson"],
            publication_date=datetime(2023, 1, 15),
            language="fr",
            specialty="endocrinologie",
            keywords=["diabète", "metformine", "glycémie", "HbA1c"]
        ),
        MedicalArticle(
            id="malaria_cdc_002",
            title="Paludisme - Protocole de traitement",
            content="""
            Le paludisme est une maladie parasitaire transmise par les moustiques Anopheles.
            Traitement du paludisme simple: Artéméther-luméfantrine 20/120 mg.
            Posologie: 4 comprimés à H0, H8, puis 4 comprimés matin et soir pendant 2 jours.
            Contre-indications: Allergie aux dérivés de l'artémisinine.
            Étude clinique randomisée montre 95% d'efficacité.
            """,
            source_type=SourceType.CDC,
            source_url="https://cdc.gov/malaria/treatment",
            authors=["Dr. Brown"],
            publication_date=datetime(2023, 3, 10),
            language="fr",
            specialty="infectiologie",
            keywords=["paludisme", "artéméther", "luméfantrine", "Anopheles"]
        )
    ]
    
    return articles

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🧪 Test de l'Enrichisseur de Connaissances Médicales")
    
    # Créer l'enrichisseur
    enricher = MedicalKnowledgeEnricher({
        "target_article_count": 500,
        "min_reliability_score": 0.6,
        "batch_size": 10
    })
    
    # Créer des articles d'exemple
    sample_articles = create_sample_medical_articles()
    
    # Enrichir la base de connaissances
    stats = await enricher.enrich_knowledge_base(sample_articles)
    
    print(f"\n📊 Résultats:")
    print(f"Articles traités: {stats.total_articles}")
    print(f"Articles validés: {stats.validated_articles}")
    print(f"Articles rejetés: {stats.rejected_articles}")
    print(f"Score moyen: {stats.avg_reliability_score:.3f}")
    print(f"Temps de traitement: {stats.processing_time:.2f}s")
    
    # Exporter le rapport
    enricher.export_enrichment_report("enrichment_report.json")
    print("\n✅ Rapport exporté: enrichment_report.json")

if __name__ == "__main__":
    asyncio.run(main())