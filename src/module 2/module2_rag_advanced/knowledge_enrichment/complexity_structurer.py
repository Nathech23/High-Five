#!/usr/bin/env python3
"""
Structureur de Complexité Médicale

Objectif 4: Structurer informations par niveau de complexité

Ce module organise automatiquement le contenu médical par niveaux
de complexité pour adapter l'information au public cible.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplexityLevel(Enum):
    """Niveaux de complexité du contenu médical"""
    BASIC = "basique"  # Grand public, patients
    INTERMEDIATE = "intermediaire"  # Personnel soignant, étudiants
    ADVANCED = "avance"  # Médecins, spécialistes
    EXPERT = "expert"  # Recherche, formation médicale avancée

class ContentType(Enum):
    """Types de contenu médical"""
    DEFINITION = "definition"
    SYMPTOM = "symptome"
    TREATMENT = "traitement"
    DIAGNOSIS = "diagnostic"
    PREVENTION = "prevention"
    PROCEDURE = "procedure"
    MEDICATION = "medicament"
    ANATOMY = "anatomie"
    PATHOPHYSIOLOGY = "physiopathologie"
    RESEARCH = "recherche"

class TargetAudience(Enum):
    """Public cible"""
    GENERAL_PUBLIC = "grand_public"
    PATIENTS = "patients"
    FAMILIES = "familles"
    NURSES = "infirmiers"
    STUDENTS = "etudiants"
    DOCTORS = "medecins"
    SPECIALISTS = "specialistes"
    RESEARCHERS = "chercheurs"

@dataclass
class ComplexityIndicators:
    """Indicateurs de complexité d'un contenu"""
    technical_terms_count: int = 0
    medical_jargon_count: int = 0
    sentence_complexity: float = 0.0
    readability_score: float = 0.0
    concept_density: float = 0.0
    prerequisite_knowledge: List[str] = field(default_factory=list)
    statistical_content: bool = False
    research_references: int = 0

@dataclass
class StructuredContent:
    """Contenu structuré par niveau de complexité"""
    id: str
    original_content: str
    complexity_level: ComplexityLevel
    content_type: ContentType
    target_audience: TargetAudience
    structured_versions: Dict[ComplexityLevel, str] = field(default_factory=dict)
    complexity_indicators: ComplexityIndicators = field(default_factory=ComplexityIndicators)
    keywords: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour le contenu"""
        import hashlib
        content_hash = hashlib.md5(self.original_content[:100].encode()).hexdigest()[:8]
        return f"{self.content_type.value}_{content_hash}"

@dataclass
class ComplexityStats:
    """Statistiques de structuration par complexité"""
    total_content: int = 0
    content_by_level: Dict[str, int] = field(default_factory=dict)
    content_by_type: Dict[str, int] = field(default_factory=dict)
    content_by_audience: Dict[str, int] = field(default_factory=dict)
    avg_readability_score: float = 0.0
    processing_time: float = 0.0

class ComplexityStructurer:
    """
    Structureur automatique de complexité médicale
    
    Objectif couvert:
    - 4. Structurer informations par niveau de complexité
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.structured_content: Dict[str, StructuredContent] = {}
        self.complexity_patterns = self._init_complexity_patterns()
        self.audience_mapping = self._init_audience_mapping()
        self.stats = ComplexityStats()
        
        # Configuration
        self.auto_generate_versions = self.config.get("auto_generate_versions", True)
        self.readability_threshold = self.config.get("readability_threshold", 0.6)
        
        logger.info("Structureur de complexité initialisé")
    
    def _init_complexity_patterns(self) -> Dict[str, Any]:
        """Initialise les patterns de détection de complexité"""
        return {
            "technical_terms": re.compile(
                r'\b(physiopathologie|étiopathogénie|pharmacocinétique|pharmacodynamie|'
                r'épidémiologie|biomarqueur|cytokine|métabolisme|génétique|moléculaire|'
                r'histopathologie|immunologie|endocrinologie|neurophysiologie)\b',
                re.IGNORECASE
            ),
            "medical_jargon": re.compile(
                r'\b(syndrome|pathologie|étiologie|nosologie|sémiologie|anamnèse|'
                r'diagnostic différentiel|pronostic|thérapeutique|iatrogène|idiopathique|'
                r'symptomatologie|clinique|paraclinique)\b',
                re.IGNORECASE
            ),
            "statistical_terms": re.compile(
                r'\b(p-value|intervalle de confiance|odds ratio|risque relatif|'
                r'sensibilité|spécificité|prévalence|incidence|méta-analyse|'
                r'randomisé|double aveugle|cohorte|cas-témoins)\b',
                re.IGNORECASE
            ),
            "research_indicators": re.compile(
                r'\b(étude|recherche|publication|journal|revue|article|référence|'
                r'bibliographie|PubMed|DOI|PMID)\b',
                re.IGNORECASE
            ),
            "dosage_patterns": re.compile(
                r'\b\d+\s*(mg|g|ml|l|UI|mcg|mmol|mEq)\/?(kg|m²|jour|h)?\b',
                re.IGNORECASE
            ),
            "complex_sentences": re.compile(
                r'[^.!?]*[,;][^.!?]*[,;][^.!?]*[.!?]',
                re.IGNORECASE
            )
        }
    
    def _init_audience_mapping(self) -> Dict[ComplexityLevel, List[TargetAudience]]:
        """Initialise le mapping complexité -> audience"""
        return {
            ComplexityLevel.BASIC: [
                TargetAudience.GENERAL_PUBLIC,
                TargetAudience.PATIENTS,
                TargetAudience.FAMILIES
            ],
            ComplexityLevel.INTERMEDIATE: [
                TargetAudience.NURSES,
                TargetAudience.STUDENTS
            ],
            ComplexityLevel.ADVANCED: [
                TargetAudience.DOCTORS,
                TargetAudience.SPECIALISTS
            ],
            ComplexityLevel.EXPERT: [
                TargetAudience.RESEARCHERS,
                TargetAudience.SPECIALISTS
            ]
        }
    
    async def structure_content(self, content_list: List[Any]) -> ComplexityStats:
        """
        Structure le contenu par niveaux de complexité
        
        Args:
            content_list: Liste de contenus à structurer
        
        Returns:
            ComplexityStats: Statistiques de structuration
        """
        import time
        start_time = time.time()
        
        logger.info(f"Structuration de {len(content_list)} contenus par complexité")
        
        # Réinitialiser les statistiques
        self.stats = ComplexityStats()
        self.stats.total_content = len(content_list)
        
        # Traiter chaque contenu
        processing_tasks = []
        for content in content_list:
            task = asyncio.create_task(self._process_single_content(content))
            processing_tasks.append(task)
        
        results = await asyncio.gather(*processing_tasks)
        
        # Compiler les résultats
        total_readability = 0.0
        valid_results = 0
        
        for result in results:
            if result:
                self.structured_content[result.id] = result
                
                # Mettre à jour les statistiques
                level_name = result.complexity_level.value
                if level_name in self.stats.content_by_level:
                    self.stats.content_by_level[level_name] += 1
                else:
                    self.stats.content_by_level[level_name] = 1
                
                type_name = result.content_type.value
                if type_name in self.stats.content_by_type:
                    self.stats.content_by_type[type_name] += 1
                else:
                    self.stats.content_by_type[type_name] = 1
                
                audience_name = result.target_audience.value
                if audience_name in self.stats.content_by_audience:
                    self.stats.content_by_audience[audience_name] += 1
                else:
                    self.stats.content_by_audience[audience_name] = 1
                
                total_readability += result.complexity_indicators.readability_score
                valid_results += 1
        
        # Calculer les statistiques finales
        if valid_results > 0:
            self.stats.avg_readability_score = total_readability / valid_results
        
        self.stats.processing_time = time.time() - start_time
        
        logger.info(f"Structuration terminée en {self.stats.processing_time:.2f}s")
        logger.info(f"Contenus structurés: {valid_results}/{self.stats.total_content}")
        
        return self.stats
    
    async def _process_single_content(self, content: Any) -> Optional[StructuredContent]:
        """
        Traite un contenu individuel
        
        Args:
            content: Contenu à traiter
        
        Returns:
            Optional[StructuredContent]: Contenu structuré
        """
        try:
            # Extraire le texte du contenu
            text_content = self._extract_text_content(content)
            if not text_content:
                return None
            
            # Analyser la complexité
            indicators = self._analyze_complexity(text_content)
            
            # Déterminer le niveau de complexité
            complexity_level = self._determine_complexity_level(indicators)
            
            # Déterminer le type de contenu
            content_type = self._determine_content_type(text_content)
            
            # Déterminer l'audience cible
            target_audience = self._determine_target_audience(complexity_level, content_type)
            
            # Créer le contenu structuré
            structured = StructuredContent(
                original_content=text_content,
                complexity_level=complexity_level,
                content_type=content_type,
                target_audience=target_audience,
                complexity_indicators=indicators,
                keywords=self._extract_keywords(text_content)
            )
            
            # Générer les versions adaptées si activé
            if self.auto_generate_versions:
                await self._generate_adapted_versions(structured)
            
            return structured
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement du contenu: {e}")
            return None
    
    def _extract_text_content(self, content: Any) -> str:
        """Extrait le contenu textuel"""
        text_parts = []
        
        # Titre
        if hasattr(content, 'title') and content.title:
            text_parts.append(content.title)
        
        # Contenu principal
        if hasattr(content, 'content') and content.content:
            text_parts.append(content.content)
        elif isinstance(content, str):
            text_parts.append(content)
        
        # Description
        if hasattr(content, 'description') and content.description:
            text_parts.append(content.description)
        
        return ' '.join(text_parts)
    
    def _analyze_complexity(self, text: str) -> ComplexityIndicators:
        """
        Analyse la complexité d'un texte
        
        Args:
            text: Texte à analyser
        
        Returns:
            ComplexityIndicators: Indicateurs de complexité
        """
        indicators = ComplexityIndicators()
        
        # Compter les termes techniques
        technical_matches = self.complexity_patterns["technical_terms"].findall(text)
        indicators.technical_terms_count = len(technical_matches)
        
        # Compter le jargon médical
        jargon_matches = self.complexity_patterns["medical_jargon"].findall(text)
        indicators.medical_jargon_count = len(jargon_matches)
        
        # Analyser la complexité des phrases
        complex_sentences = self.complexity_patterns["complex_sentences"].findall(text)
        total_sentences = len(re.split(r'[.!?]+', text))
        if total_sentences > 0:
            indicators.sentence_complexity = len(complex_sentences) / total_sentences
        
        # Calculer le score de lisibilité (approximation)
        indicators.readability_score = self._calculate_readability_score(text)
        
        # Calculer la densité conceptuelle
        indicators.concept_density = self._calculate_concept_density(text)
        
        # Détecter le contenu statistique
        statistical_matches = self.complexity_patterns["statistical_terms"].findall(text)
        indicators.statistical_content = len(statistical_matches) > 0
        
        # Compter les références de recherche
        research_matches = self.complexity_patterns["research_indicators"].findall(text)
        indicators.research_references = len(research_matches)
        
        # Identifier les prérequis
        indicators.prerequisite_knowledge = self._identify_prerequisites(text)
        
        return indicators
    
    def _calculate_readability_score(self, text: str) -> float:
        """
        Calcule un score de lisibilité approximatif
        
        Args:
            text: Texte à analyser
        
        Returns:
            float: Score de lisibilité (0-1, 1 = très lisible)
        """
        # Compter les mots et phrases
        words = len(text.split())
        sentences = len(re.split(r'[.!?]+', text))
        
        if sentences == 0 or words == 0:
            return 0.0
        
        # Mots par phrase
        words_per_sentence = words / sentences
        
        # Pénaliser les phrases longues
        sentence_penalty = min(words_per_sentence / 20, 1.0)
        
        # Pénaliser les mots techniques
        technical_words = len(self.complexity_patterns["technical_terms"].findall(text))
        technical_penalty = min(technical_words / words * 10, 1.0) if words > 0 else 0
        
        # Score final
        score = 1.0 - (sentence_penalty * 0.5 + technical_penalty * 0.5)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_concept_density(self, text: str) -> float:
        """
        Calcule la densité conceptuelle du texte
        
        Args:
            text: Texte à analyser
        
        Returns:
            float: Densité conceptuelle (0-1)
        """
        words = text.split()
        if not words:
            return 0.0
        
        # Compter les concepts médicaux
        medical_concepts = (
            len(self.complexity_patterns["technical_terms"].findall(text)) +
            len(self.complexity_patterns["medical_jargon"].findall(text))
        )
        
        # Densité = concepts / mots totaux
        density = medical_concepts / len(words)
        
        return min(density, 1.0)
    
    def _identify_prerequisites(self, text: str) -> List[str]:
        """
        Identifie les connaissances prérequises
        
        Args:
            text: Texte à analyser
        
        Returns:
            List[str]: Liste des prérequis
        """
        prerequisites = []
        
        # Prérequis basés sur les termes techniques
        if self.complexity_patterns["technical_terms"].search(text):
            prerequisites.append("Connaissances médicales de base")
        
        if self.complexity_patterns["statistical_terms"].search(text):
            prerequisites.append("Notions de statistiques médicales")
        
        if "pharmacocinétique" in text.lower() or "pharmacodynamie" in text.lower():
            prerequisites.append("Pharmacologie")
        
        if "génétique" in text.lower() or "moléculaire" in text.lower():
            prerequisites.append("Biologie moléculaire")
        
        return prerequisites
    
    def _determine_complexity_level(self, indicators: ComplexityIndicators) -> ComplexityLevel:
        """
        Détermine le niveau de complexité basé sur les indicateurs
        
        Args:
            indicators: Indicateurs de complexité
        
        Returns:
            ComplexityLevel: Niveau de complexité
        """
        # Score composite
        complexity_score = 0.0
        
        # Contribution des termes techniques
        if indicators.technical_terms_count > 5:
            complexity_score += 0.3
        elif indicators.technical_terms_count > 2:
            complexity_score += 0.2
        elif indicators.technical_terms_count > 0:
            complexity_score += 0.1
        
        # Contribution du jargon médical
        if indicators.medical_jargon_count > 3:
            complexity_score += 0.2
        elif indicators.medical_jargon_count > 1:
            complexity_score += 0.1
        
        # Contribution de la complexité des phrases
        complexity_score += indicators.sentence_complexity * 0.2
        
        # Contribution de la densité conceptuelle
        complexity_score += indicators.concept_density * 0.2
        
        # Contribution du contenu statistique
        if indicators.statistical_content:
            complexity_score += 0.1
        
        # Contribution des références de recherche
        if indicators.research_references > 2:
            complexity_score += 0.1
        
        # Pénalité pour faible lisibilité
        if indicators.readability_score < 0.3:
            complexity_score += 0.2
        
        # Déterminer le niveau
        if complexity_score >= 0.7:
            return ComplexityLevel.EXPERT
        elif complexity_score >= 0.5:
            return ComplexityLevel.ADVANCED
        elif complexity_score >= 0.3:
            return ComplexityLevel.INTERMEDIATE
        else:
            return ComplexityLevel.BASIC
    
    def _determine_content_type(self, text: str) -> ContentType:
        """
        Détermine le type de contenu
        
        Args:
            text: Texte à analyser
        
        Returns:
            ContentType: Type de contenu
        """
        text_lower = text.lower()
        
        # Patterns pour chaque type
        type_patterns = {
            ContentType.DEFINITION: ["définition", "qu'est-ce que", "signifie", "terme"],
            ContentType.SYMPTOM: ["symptôme", "signe", "manifestation", "présente"],
            ContentType.TREATMENT: ["traitement", "thérapie", "soigner", "guérir"],
            ContentType.DIAGNOSIS: ["diagnostic", "diagnostiquer", "examen", "test"],
            ContentType.PREVENTION: ["prévention", "prévenir", "éviter", "protection"],
            ContentType.PROCEDURE: ["procédure", "intervention", "opération", "technique"],
            ContentType.MEDICATION: ["médicament", "traitement", "posologie", "dose"],
            ContentType.ANATOMY: ["anatomie", "organe", "structure", "système"],
            ContentType.PATHOPHYSIOLOGY: ["physiopathologie", "mécanisme", "processus"],
            ContentType.RESEARCH: ["étude", "recherche", "résultats", "publication"]
        }
        
        # Compter les correspondances pour chaque type
        type_scores = {}
        for content_type, patterns in type_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text_lower)
            type_scores[content_type] = score
        
        # Retourner le type avec le score le plus élevé
        best_type = max(type_scores, key=type_scores.get)
        
        # Si aucun pattern ne correspond, retourner DEFINITION par défaut
        if type_scores[best_type] == 0:
            return ContentType.DEFINITION
        
        return best_type
    
    def _determine_target_audience(self, complexity_level: ComplexityLevel, 
                                 content_type: ContentType) -> TargetAudience:
        """
        Détermine l'audience cible
        
        Args:
            complexity_level: Niveau de complexité
            content_type: Type de contenu
        
        Returns:
            TargetAudience: Audience cible
        """
        # Mapping par défaut basé sur la complexité
        default_audiences = self.audience_mapping.get(complexity_level, [])
        
        if not default_audiences:
            return TargetAudience.GENERAL_PUBLIC
        
        # Ajustements basés sur le type de contenu
        if content_type in [ContentType.RESEARCH, ContentType.PATHOPHYSIOLOGY]:
            if TargetAudience.RESEARCHERS in default_audiences:
                return TargetAudience.RESEARCHERS
            elif TargetAudience.SPECIALISTS in default_audiences:
                return TargetAudience.SPECIALISTS
        
        elif content_type in [ContentType.PREVENTION, ContentType.SYMPTOM]:
            if complexity_level == ComplexityLevel.BASIC:
                return TargetAudience.PATIENTS
        
        # Retourner la première audience par défaut
        return default_audiences[0]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrait les mots-clés du texte
        
        Args:
            text: Texte à analyser
        
        Returns:
            List[str]: Liste de mots-clés
        """
        keywords = []
        
        # Extraire les termes techniques
        technical_terms = self.complexity_patterns["technical_terms"].findall(text)
        keywords.extend(technical_terms)
        
        # Extraire le jargon médical
        medical_terms = self.complexity_patterns["medical_jargon"].findall(text)
        keywords.extend(medical_terms)
        
        # Extraire les dosages
        dosages = self.complexity_patterns["dosage_patterns"].findall(text)
        keywords.extend([f"{d[0]}{d[1]}" for d in dosages if len(d) >= 2])
        
        # Supprimer les doublons et retourner
        return list(set(keywords))
    
    async def _generate_adapted_versions(self, structured: StructuredContent):
        """
        Génère des versions adaptées pour différents niveaux
        
        Args:
            structured: Contenu structuré à adapter
        """
        original_text = structured.original_content
        
        # Générer une version basique
        if structured.complexity_level != ComplexityLevel.BASIC:
            basic_version = self._simplify_text(original_text, ComplexityLevel.BASIC)
            structured.structured_versions[ComplexityLevel.BASIC] = basic_version
        
        # Générer une version intermédiaire
        if structured.complexity_level not in [ComplexityLevel.BASIC, ComplexityLevel.INTERMEDIATE]:
            intermediate_version = self._simplify_text(original_text, ComplexityLevel.INTERMEDIATE)
            structured.structured_versions[ComplexityLevel.INTERMEDIATE] = intermediate_version
        
        # La version originale est conservée pour son niveau
        structured.structured_versions[structured.complexity_level] = original_text
    
    def _simplify_text(self, text: str, target_level: ComplexityLevel) -> str:
        """
        Simplifie un texte pour un niveau cible
        
        Args:
            text: Texte à simplifier
            target_level: Niveau cible
        
        Returns:
            str: Texte simplifié
        """
        simplified = text
        
        if target_level == ComplexityLevel.BASIC:
            # Remplacements pour le grand public
            replacements = {
                "physiopathologie": "mécanisme de la maladie",
                "étiopathogénie": "cause de la maladie",
                "pharmacocinétique": "action du médicament dans le corps",
                "syndrome": "ensemble de symptômes",
                "pathologie": "maladie",
                "thérapeutique": "traitement",
                "diagnostic différentiel": "autres maladies possibles",
                "iatrogène": "causé par un traitement médical",
                "idiopathique": "de cause inconnue"
            }
            
            for technical, simple in replacements.items():
                simplified = re.sub(r'\b' + technical + r'\b', simple, simplified, flags=re.IGNORECASE)
        
        elif target_level == ComplexityLevel.INTERMEDIATE:
            # Simplifications modérées pour le personnel soignant
            replacements = {
                "physiopathologie": "mécanisme physiopathologique",
                "étiopathogénie": "origine et développement"
            }
            
            for technical, simple in replacements.items():
                simplified = re.sub(r'\b' + technical + r'\b', simple, simplified, flags=re.IGNORECASE)
        
        return simplified
    
    def get_content_by_level(self, level: ComplexityLevel) -> List[StructuredContent]:
        """Retourne tous les contenus d'un niveau de complexité"""
        return [content for content in self.structured_content.values() 
                if content.complexity_level == level]
    
    def get_content_by_audience(self, audience: TargetAudience) -> List[StructuredContent]:
        """Retourne tous les contenus pour une audience donnée"""
        return [content for content in self.structured_content.values() 
                if content.target_audience == audience]
    
    def get_adapted_version(self, content_id: str, target_level: ComplexityLevel) -> Optional[str]:
        """Retourne une version adaptée d'un contenu"""
        content = self.structured_content.get(content_id)
        if not content:
            return None
        
        return content.structured_versions.get(target_level)
    
    def export_complexity_report(self, output_path: str):
        """Exporte un rapport de structuration par complexité"""
        report = {
            "complexity_summary": {
                "total_content": self.stats.total_content,
                "content_by_level": self.stats.content_by_level,
                "content_by_type": self.stats.content_by_type,
                "content_by_audience": self.stats.content_by_audience,
                "avg_readability_score": self.stats.avg_readability_score,
                "processing_time": self.stats.processing_time
            },
            "structured_content": {
                content_id: {
                    "complexity_level": content.complexity_level.value,
                    "content_type": content.content_type.value,
                    "target_audience": content.target_audience.value,
                    "readability_score": content.complexity_indicators.readability_score,
                    "technical_terms_count": content.complexity_indicators.technical_terms_count,
                    "available_versions": list(content.structured_versions.keys()),
                    "keywords": content.keywords
                }
                for content_id, content in self.structured_content.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Rapport de complexité exporté: {output_path}")

# Fonction utilitaire pour créer du contenu de test
def create_sample_content_for_complexity():
    """Crée du contenu d'exemple pour tester la structuration"""
    return [
        "Le cœur est un organe vital qui pompe le sang dans tout le corps.",
        
        "La physiopathologie de l'infarctus du myocarde implique une occlusion coronaire "
        "entraînant une ischémie myocardique avec nécrose tissulaire. Le diagnostic "
        "différentiel doit exclure l'angine instable et l'embolie pulmonaire.",
        
        "Une méta-analyse récente (p<0.001, IC 95%) démontre l'efficacité de la "
        "pharmacocinétique optimisée des inhibiteurs de l'enzyme de conversion dans "
        "la réduction du risque relatif de mortalité cardiovasculaire chez les patients "
        "présentant une dysfonction ventriculaire gauche post-infarctus.",
        
        "La fièvre est une élévation de la température corporelle. Elle peut être "
        "causée par une infection. Il faut consulter un médecin si elle persiste."
    ]

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("📊 Test du Structureur de Complexité Médicale")
    
    # Créer le structureur
    structurer = ComplexityStructurer({
        "auto_generate_versions": True,
        "readability_threshold": 0.6
    })
    
    # Créer du contenu d'exemple
    sample_content = create_sample_content_for_complexity()
    
    # Structurer le contenu
    stats = await structurer.structure_content(sample_content)
    
    print(f"\n📈 Résultats:")
    print(f"Contenus traités: {stats.total_content}")
    print(f"Score de lisibilité moyen: {stats.avg_readability_score:.3f}")
    print(f"Temps de traitement: {stats.processing_time:.2f}s")
    
    print(f"\n📋 Répartition par niveau:")
    for level, count in stats.content_by_level.items():
        print(f"  {level}: {count} contenus")
    
    print(f"\n👥 Répartition par audience:")
    for audience, count in stats.content_by_audience.items():
        print(f"  {audience}: {count} contenus")
    
    # Afficher un exemple de structuration
    if structurer.structured_content:
        example_id = list(structurer.structured_content.keys())[0]
        example = structurer.structured_content[example_id]
        
        print(f"\n📝 Exemple de structuration:")
        print(f"Niveau: {example.complexity_level.value}")
        print(f"Type: {example.content_type.value}")
        print(f"Audience: {example.target_audience.value}")
        print(f"Mots-clés: {', '.join(example.keywords[:5])}")
    
    # Exporter le rapport
    structurer.export_complexity_report("complexity_structure_report.json")
    print("\n✅ Rapport exporté: complexity_structure_report.json")

if __name__ == "__main__":
    asyncio.run(main())