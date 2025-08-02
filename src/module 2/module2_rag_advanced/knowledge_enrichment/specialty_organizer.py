#!/usr/bin/env python3
"""
Organisateur par Spécialités Médicales

Objectif 2: Créer sections par spécialités médicales

Ce module organise automatiquement le contenu médical par spécialités
et crée une structure hiérarchique pour faciliter la navigation.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalSpecialty(Enum):
    """Spécialités médicales principales"""
    CARDIOLOGIE = "cardiologie"
    ENDOCRINOLOGIE = "endocrinologie"
    INFECTIOLOGIE = "infectiologie"
    PNEUMOLOGIE = "pneumologie"
    NEUROLOGIE = "neurologie"
    PEDIATRIE = "pediatrie"
    GYNECOLOGIE = "gynecologie"
    DERMATOLOGIE = "dermatologie"
    PSYCHIATRIE = "psychiatrie"
    ORTHOPÉDIE = "orthopedie"
    OPHTALMOLOGIE = "ophtalmologie"
    ORL = "orl"
    UROLOGIE = "urologie"
    GASTROENTEROLOGIE = "gastroenterologie"
    HEMATOLOGIE = "hematologie"
    ONCOLOGIE = "oncologie"
    ANESTHESIE = "anesthesie"
    CHIRURGIE = "chirurgie"
    MEDECINE_GENERALE = "medecine_generale"
    URGENCES = "urgences"

@dataclass
class SpecialtyKeywords:
    """Mots-clés associés à une spécialité"""
    specialty: MedicalSpecialty
    primary_keywords: List[str] = field(default_factory=list)
    secondary_keywords: List[str] = field(default_factory=list)
    anatomical_terms: List[str] = field(default_factory=list)
    pathologies: List[str] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)

@dataclass
class SpecialtySection:
    """Section d'une spécialité médicale"""
    specialty: MedicalSpecialty
    name: str
    description: str
    article_ids: List[str] = field(default_factory=list)
    subsections: Dict[str, 'SpecialtySection'] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ClassificationResult:
    """Résultat de classification d'un article"""
    article_id: str
    primary_specialty: MedicalSpecialty
    secondary_specialties: List[MedicalSpecialty] = field(default_factory=list)
    confidence_score: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    classification_method: str = "automatic"

@dataclass
class OrganizationStats:
    """Statistiques d'organisation"""
    total_articles: int = 0
    classified_articles: int = 0
    unclassified_articles: int = 0
    articles_by_specialty: Dict[str, int] = field(default_factory=dict)
    avg_confidence_score: float = 0.0
    processing_time: float = 0.0

class SpecialtyOrganizer:
    """
    Organisateur automatique par spécialités médicales
    
    Objectif couvert:
    - 2. Créer sections par spécialités médicales
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.specialty_keywords = self._init_specialty_keywords()
        self.sections: Dict[MedicalSpecialty, SpecialtySection] = {}
        self.classification_results: Dict[str, ClassificationResult] = {}
        self.stats = OrganizationStats()
        
        # Configuration
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.3)
        self.enable_multi_specialty = self.config.get("enable_multi_specialty", True)
        
        # Initialiser les sections
        self._init_specialty_sections()
        
        logger.info("Organisateur par spécialités initialisé")
    
    def _init_specialty_keywords(self) -> Dict[MedicalSpecialty, SpecialtyKeywords]:
        """Initialise les mots-clés pour chaque spécialité"""
        keywords_map = {
            MedicalSpecialty.CARDIOLOGIE: SpecialtyKeywords(
                specialty=MedicalSpecialty.CARDIOLOGIE,
                primary_keywords=["cardiologie", "cardiologue", "cœur", "cardiaque"],
                secondary_keywords=["cardiovasculaire", "coronaire", "artériel"],
                anatomical_terms=["ventricule", "oreillette", "aorte", "artère", "veine"],
                pathologies=["infarctus", "angine", "arythmie", "hypertension", "insuffisance cardiaque"],
                procedures=["angioplastie", "pontage", "cathétérisme", "échocardiographie"],
                medications=["bêta-bloquant", "IEC", "diurétique", "antiarythmique"]
            ),
            
            MedicalSpecialty.ENDOCRINOLOGIE: SpecialtyKeywords(
                specialty=MedicalSpecialty.ENDOCRINOLOGIE,
                primary_keywords=["endocrinologie", "endocrinologue", "hormone", "diabète"],
                secondary_keywords=["métabolique", "glycémie", "insuline"],
                anatomical_terms=["pancréas", "thyroïde", "surrénales", "hypophyse"],
                pathologies=["diabète", "hypothyroïdie", "hyperthyroïdie", "obésité"],
                procedures=["glycémie", "HbA1c", "TSH", "échographie thyroïdienne"],
                medications=["metformine", "insuline", "lévothyroxine", "glibenclamide"]
            ),
            
            MedicalSpecialty.INFECTIOLOGIE: SpecialtyKeywords(
                specialty=MedicalSpecialty.INFECTIOLOGIE,
                primary_keywords=["infectiologie", "infection", "bactérie", "virus"],
                secondary_keywords=["antimicrobien", "résistance", "sepsis"],
                anatomical_terms=["système immunitaire", "ganglions", "rate"],
                pathologies=["paludisme", "tuberculose", "VIH", "hépatite", "méningite"],
                procedures=["hémoculture", "antibiogramme", "PCR", "sérologie"],
                medications=["antibiotique", "antiviral", "antifongique", "artéméther"]
            ),
            
            MedicalSpecialty.PNEUMOLOGIE: SpecialtyKeywords(
                specialty=MedicalSpecialty.PNEUMOLOGIE,
                primary_keywords=["pneumologie", "pneumologue", "poumon", "respiratoire"],
                secondary_keywords=["bronchique", "alvéolaire", "pleural"],
                anatomical_terms=["bronches", "alvéoles", "plèvre", "diaphragme"],
                pathologies=["asthme", "BPCO", "pneumonie", "tuberculose pulmonaire"],
                procedures=["spirométrie", "radiographie thoracique", "bronchoscopie"],
                medications=["bronchodilatateur", "corticoïde", "salbutamol"]
            ),
            
            MedicalSpecialty.NEUROLOGIE: SpecialtyKeywords(
                specialty=MedicalSpecialty.NEUROLOGIE,
                primary_keywords=["neurologie", "neurologue", "cerveau", "neurologique"],
                secondary_keywords=["cérébral", "spinal", "périphérique"],
                anatomical_terms=["cortex", "moelle épinière", "nerf", "synapse"],
                pathologies=["AVC", "épilepsie", "migraine", "Parkinson", "Alzheimer"],
                procedures=["IRM cérébrale", "EEG", "ponction lombaire"],
                medications=["antiépileptique", "L-DOPA", "sumatriptan"]
            ),
            
            MedicalSpecialty.PEDIATRIE: SpecialtyKeywords(
                specialty=MedicalSpecialty.PEDIATRIE,
                primary_keywords=["pédiatrie", "pédiatre", "enfant", "nourrisson"],
                secondary_keywords=["néonatal", "adolescent", "croissance"],
                anatomical_terms=["fontanelle", "croissance", "développement"],
                pathologies=["rougeole", "varicelle", "bronchiolite", "gastroentérite"],
                procedures=["vaccination", "courbe de croissance", "examen pédiatrique"],
                medications=["paracétamol pédiatrique", "vaccin", "SRO"]
            )
        }
        
        # Ajouter les autres spécialités avec des mots-clés de base
        for specialty in MedicalSpecialty:
            if specialty not in keywords_map:
                keywords_map[specialty] = SpecialtyKeywords(
                    specialty=specialty,
                    primary_keywords=[specialty.value],
                    secondary_keywords=[],
                    anatomical_terms=[],
                    pathologies=[],
                    procedures=[],
                    medications=[]
                )
        
        return keywords_map
    
    def _init_specialty_sections(self):
        """Initialise les sections pour chaque spécialité"""
        specialty_descriptions = {
            MedicalSpecialty.CARDIOLOGIE: "Spécialité médicale qui traite les maladies du cœur et des vaisseaux",
            MedicalSpecialty.ENDOCRINOLOGIE: "Spécialité qui traite les troubles hormonaux et métaboliques",
            MedicalSpecialty.INFECTIOLOGIE: "Spécialité qui traite les maladies infectieuses",
            MedicalSpecialty.PNEUMOLOGIE: "Spécialité qui traite les maladies respiratoires",
            MedicalSpecialty.NEUROLOGIE: "Spécialité qui traite les maladies du système nerveux",
            MedicalSpecialty.PEDIATRIE: "Spécialité qui traite les maladies de l'enfant"
        }
        
        for specialty in MedicalSpecialty:
            description = specialty_descriptions.get(
                specialty, 
                f"Spécialité médicale: {specialty.value}"
            )
            
            self.sections[specialty] = SpecialtySection(
                specialty=specialty,
                name=specialty.value.replace('_', ' ').title(),
                description=description,
                keywords=self.specialty_keywords[specialty].primary_keywords
            )
    
    async def organize_articles(self, articles: List[Any]) -> OrganizationStats:
        """
        Organise les articles par spécialités médicales
        
        Args:
            articles: Liste d'articles à organiser
        
        Returns:
            OrganizationStats: Statistiques d'organisation
        """
        import time
        start_time = time.time()
        
        logger.info(f"Organisation de {len(articles)} articles par spécialités")
        
        # Réinitialiser les statistiques
        self.stats = OrganizationStats()
        self.stats.total_articles = len(articles)
        
        # Classifier chaque article
        classification_tasks = []
        for article in articles:
            task = asyncio.create_task(self._classify_article(article))
            classification_tasks.append(task)
        
        results = await asyncio.gather(*classification_tasks)
        
        # Traiter les résultats
        total_confidence = 0.0
        for result in results:
            if result:
                self.classification_results[result.article_id] = result
                
                # Ajouter l'article à la section appropriée
                self._add_article_to_section(result)
                
                self.stats.classified_articles += 1
                total_confidence += result.confidence_score
                
                # Mettre à jour les statistiques par spécialité
                specialty_name = result.primary_specialty.value
                if specialty_name in self.stats.articles_by_specialty:
                    self.stats.articles_by_specialty[specialty_name] += 1
                else:
                    self.stats.articles_by_specialty[specialty_name] = 1
            else:
                self.stats.unclassified_articles += 1
        
        # Calculer les statistiques finales
        if self.stats.classified_articles > 0:
            self.stats.avg_confidence_score = total_confidence / self.stats.classified_articles
        
        self.stats.processing_time = time.time() - start_time
        
        logger.info(f"Organisation terminée en {self.stats.processing_time:.2f}s")
        logger.info(f"Articles classifiés: {self.stats.classified_articles}/{self.stats.total_articles}")
        
        return self.stats
    
    async def _classify_article(self, article: Any) -> Optional[ClassificationResult]:
        """
        Classifie un article dans une spécialité médicale
        
        Args:
            article: Article à classifier
        
        Returns:
            ClassificationResult: Résultat de la classification
        """
        try:
            # Extraire le texte de l'article
            text_content = self._extract_text_content(article)
            if not text_content:
                return None
            
            # Calculer les scores pour chaque spécialité
            specialty_scores = {}
            matched_keywords_by_specialty = {}
            
            for specialty, keywords in self.specialty_keywords.items():
                score, matched_keywords = self._calculate_specialty_score(text_content, keywords)
                specialty_scores[specialty] = score
                matched_keywords_by_specialty[specialty] = matched_keywords
            
            # Trouver la spécialité principale
            primary_specialty = max(specialty_scores, key=specialty_scores.get)
            primary_score = specialty_scores[primary_specialty]
            
            # Vérifier si le score dépasse le seuil
            if primary_score < self.min_confidence_threshold:
                return None
            
            # Trouver les spécialités secondaires
            secondary_specialties = []
            if self.enable_multi_specialty:
                for specialty, score in specialty_scores.items():
                    if (specialty != primary_specialty and 
                        score >= self.min_confidence_threshold * 0.7):
                        secondary_specialties.append(specialty)
            
            return ClassificationResult(
                article_id=getattr(article, 'id', str(hash(text_content))[:8]),
                primary_specialty=primary_specialty,
                secondary_specialties=secondary_specialties,
                confidence_score=primary_score,
                matched_keywords=matched_keywords_by_specialty[primary_specialty],
                classification_method="keyword_matching"
            )
        
        except Exception as e:
            logger.error(f"Erreur lors de la classification: {e}")
            return None
    
    def _extract_text_content(self, article: Any) -> str:
        """Extrait le contenu textuel d'un article"""
        text_parts = []
        
        # Titre
        if hasattr(article, 'title') and article.title:
            text_parts.append(article.title)
        
        # Contenu
        if hasattr(article, 'content') and article.content:
            text_parts.append(article.content)
        
        # Mots-clés
        if hasattr(article, 'keywords') and article.keywords:
            text_parts.extend(article.keywords)
        
        # Spécialité existante (si disponible)
        if hasattr(article, 'specialty') and article.specialty:
            text_parts.append(article.specialty)
        
        return ' '.join(text_parts).lower()
    
    def _calculate_specialty_score(self, text: str, keywords: SpecialtyKeywords) -> Tuple[float, List[str]]:
        """
        Calcule le score d'une spécialité pour un texte donné
        
        Args:
            text: Texte à analyser
            keywords: Mots-clés de la spécialité
        
        Returns:
            Tuple[float, List[str]]: Score et mots-clés trouvés
        """
        score = 0.0
        matched_keywords = []
        
        # Pondérations pour différents types de mots-clés
        weights = {
            'primary': 3.0,
            'secondary': 2.0,
            'anatomical': 1.5,
            'pathologies': 2.5,
            'procedures': 2.0,
            'medications': 1.5
        }
        
        # Vérifier les mots-clés primaires
        for keyword in keywords.primary_keywords:
            if keyword.lower() in text:
                score += weights['primary']
                matched_keywords.append(keyword)
        
        # Vérifier les mots-clés secondaires
        for keyword in keywords.secondary_keywords:
            if keyword.lower() in text:
                score += weights['secondary']
                matched_keywords.append(keyword)
        
        # Vérifier les termes anatomiques
        for keyword in keywords.anatomical_terms:
            if keyword.lower() in text:
                score += weights['anatomical']
                matched_keywords.append(keyword)
        
        # Vérifier les pathologies
        for keyword in keywords.pathologies:
            if keyword.lower() in text:
                score += weights['pathologies']
                matched_keywords.append(keyword)
        
        # Vérifier les procédures
        for keyword in keywords.procedures:
            if keyword.lower() in text:
                score += weights['procedures']
                matched_keywords.append(keyword)
        
        # Vérifier les médicaments
        for keyword in keywords.medications:
            if keyword.lower() in text:
                score += weights['medications']
                matched_keywords.append(keyword)
        
        # Normaliser le score
        max_possible_score = (
            len(keywords.primary_keywords) * weights['primary'] +
            len(keywords.secondary_keywords) * weights['secondary'] +
            len(keywords.anatomical_terms) * weights['anatomical'] +
            len(keywords.pathologies) * weights['pathologies'] +
            len(keywords.procedures) * weights['procedures'] +
            len(keywords.medications) * weights['medications']
        )
        
        if max_possible_score > 0:
            score = score / max_possible_score
        
        return min(score, 1.0), matched_keywords
    
    def _add_article_to_section(self, result: ClassificationResult):
        """Ajoute un article à la section appropriée"""
        # Ajouter à la spécialité principale
        primary_section = self.sections[result.primary_specialty]
        if result.article_id not in primary_section.article_ids:
            primary_section.article_ids.append(result.article_id)
        
        # Ajouter aux spécialités secondaires
        for secondary_specialty in result.secondary_specialties:
            secondary_section = self.sections[secondary_specialty]
            if result.article_id not in secondary_section.article_ids:
                secondary_section.article_ids.append(result.article_id)
    
    def get_section_by_specialty(self, specialty: MedicalSpecialty) -> Optional[SpecialtySection]:
        """Retourne la section d'une spécialité donnée"""
        return self.sections.get(specialty)
    
    def get_articles_by_specialty(self, specialty: MedicalSpecialty) -> List[str]:
        """Retourne les IDs des articles d'une spécialité"""
        section = self.sections.get(specialty)
        return section.article_ids if section else []
    
    def get_specialty_hierarchy(self) -> Dict[str, Any]:
        """Retourne la hiérarchie complète des spécialités"""
        hierarchy = {}
        
        for specialty, section in self.sections.items():
            hierarchy[specialty.value] = {
                "name": section.name,
                "description": section.description,
                "article_count": len(section.article_ids),
                "keywords": section.keywords,
                "subsections": {
                    name: {
                        "description": subsection.description,
                        "article_count": len(subsection.article_ids)
                    }
                    for name, subsection in section.subsections.items()
                }
            }
        
        return hierarchy
    
    def create_specialty_subsections(self, specialty: MedicalSpecialty, subsection_config: Dict[str, str]):
        """Crée des sous-sections pour une spécialité"""
        section = self.sections.get(specialty)
        if not section:
            return
        
        for subsection_name, description in subsection_config.items():
            subsection = SpecialtySection(
                specialty=specialty,
                name=subsection_name,
                description=description
            )
            section.subsections[subsection_name] = subsection
    
    def export_organization_report(self, output_path: str):
        """Exporte un rapport d'organisation"""
        report = {
            "organization_summary": {
                "total_articles": self.stats.total_articles,
                "classified_articles": self.stats.classified_articles,
                "unclassified_articles": self.stats.unclassified_articles,
                "classification_rate": self.stats.classified_articles / self.stats.total_articles if self.stats.total_articles > 0 else 0,
                "avg_confidence_score": self.stats.avg_confidence_score,
                "processing_time": self.stats.processing_time
            },
            "specialty_hierarchy": self.get_specialty_hierarchy(),
            "articles_by_specialty": self.stats.articles_by_specialty,
            "classification_results": {
                article_id: {
                    "primary_specialty": result.primary_specialty.value,
                    "secondary_specialties": [s.value for s in result.secondary_specialties],
                    "confidence_score": result.confidence_score,
                    "matched_keywords": result.matched_keywords
                }
                for article_id, result in self.classification_results.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Rapport d'organisation exporté: {output_path}")

# Fonction utilitaire pour créer des articles de test
def create_sample_articles_for_classification():
    """Crée des articles d'exemple pour tester la classification"""
    from dataclasses import dataclass
    
    @dataclass
    class TestArticle:
        id: str
        title: str
        content: str
        keywords: List[str]
    
    articles = [
        TestArticle(
            id="cardio_001",
            title="Traitement de l'infarctus du myocarde",
            content="L'infarctus du myocarde est une urgence cardiologique. Le traitement inclut l'angioplastie coronaire et les bêta-bloquants.",
            keywords=["infarctus", "cardiologie", "angioplastie"]
        ),
        TestArticle(
            id="endo_001",
            title="Gestion du diabète de type 2",
            content="Le diabète de type 2 nécessite un contrôle glycémique strict. La metformine est le traitement de première ligne.",
            keywords=["diabète", "glycémie", "metformine"]
        ),
        TestArticle(
            id="infecto_001",
            title="Traitement du paludisme",
            content="Le paludisme est traité par artéméther-luméfantrine. Un antibiogramme peut être nécessaire en cas de résistance.",
            keywords=["paludisme", "artéméther", "infection"]
        )
    ]
    
    return articles

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🏥 Test de l'Organisateur par Spécialités Médicales")
    
    # Créer l'organisateur
    organizer = SpecialtyOrganizer({
        "min_confidence_threshold": 0.2,
        "enable_multi_specialty": True
    })
    
    # Créer des sous-sections pour la cardiologie
    organizer.create_specialty_subsections(
        MedicalSpecialty.CARDIOLOGIE,
        {
            "Cardiologie interventionnelle": "Procédures invasives cardiaques",
            "Insuffisance cardiaque": "Prise en charge de l'insuffisance cardiaque",
            "Arythmies": "Troubles du rythme cardiaque"
        }
    )
    
    # Créer des articles d'exemple
    sample_articles = create_sample_articles_for_classification()
    
    # Organiser les articles
    stats = await organizer.organize_articles(sample_articles)
    
    print(f"\n📊 Résultats:")
    print(f"Articles traités: {stats.total_articles}")
    print(f"Articles classifiés: {stats.classified_articles}")
    print(f"Articles non classifiés: {stats.unclassified_articles}")
    print(f"Score de confiance moyen: {stats.avg_confidence_score:.3f}")
    print(f"Temps de traitement: {stats.processing_time:.2f}s")
    
    print(f"\n📋 Répartition par spécialité:")
    for specialty, count in stats.articles_by_specialty.items():
        print(f"  {specialty}: {count} articles")
    
    # Exporter le rapport
    organizer.export_organization_report("specialty_organization_report.json")
    print("\n✅ Rapport exporté: specialty_organization_report.json")

if __name__ == "__main__":
    asyncio.run(main())