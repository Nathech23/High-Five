#!/usr/bin/env python3
"""
Validation Pipeline - Objectif 3

Crée un pipeline de validation automatique pour le contenu médical.
Gère la validation multi-niveaux, les règles métier et l'assurance qualité.

Auteur: Équipe Hackathon Hôpital Général de Douala
Version: 3.0.0
"""

import re
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vérification des dépendances optionnelles
try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False
    logger.warning("textstat non disponible - analyse de lisibilité limitée")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn non disponible - analyse avancée limitée")

class ValidationLevel(Enum):
    """Niveaux de validation"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ValidationStatus(Enum):
    """Statuts de validation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"

class ValidationCategory(Enum):
    """Catégories de validation"""
    CONTENT_QUALITY = "content_quality"
    MEDICAL_ACCURACY = "medical_accuracy"
    LANGUAGE_QUALITY = "language_quality"
    STRUCTURE = "structure"
    METADATA = "metadata"
    COMPLIANCE = "compliance"
    SAFETY = "safety"

@dataclass
class ValidationRule:
    """Règle de validation"""
    id: str
    name: str
    category: ValidationCategory
    level: ValidationLevel
    description: str
    weight: float  # Poids dans le score final (0.0 à 1.0)
    is_mandatory: bool
    error_message: str
    warning_message: Optional[str] = None
    enabled: bool = True

@dataclass
class ValidationResult:
    """Résultat de validation"""
    rule_id: str
    rule_name: str
    status: ValidationStatus
    score: float  # 0.0 à 1.0
    message: str
    details: Dict[str, Any]
    execution_time_ms: float
    suggestions: List[str]

@dataclass
class ValidationReport:
    """Rapport de validation complet"""
    document_id: str
    validation_id: str
    timestamp: datetime
    overall_status: ValidationStatus
    overall_score: float
    level_used: ValidationLevel
    results: List[ValidationResult]
    summary: Dict[str, Any]
    recommendations: List[str]
    processing_time_ms: float

class ValidationRuleBase(ABC):
    """Classe de base pour les règles de validation"""
    
    def __init__(self, rule: ValidationRule):
        self.rule = rule
        
    @abstractmethod
    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        """Exécute la validation"""
        pass
        
    def _create_result(self, status: ValidationStatus, score: float, 
                      message: str, details: Dict[str, Any] = None,
                      suggestions: List[str] = None) -> ValidationResult:
        """Crée un résultat de validation"""
        return ValidationResult(
            rule_id=self.rule.id,
            rule_name=self.rule.name,
            status=status,
            score=score,
            message=message,
            details=details or {},
            execution_time_ms=0.0,
            suggestions=suggestions or []
        )

class ContentLengthRule(ValidationRuleBase):
    """Règle de validation de la longueur du contenu"""
    
    def __init__(self, rule: ValidationRule, min_length: int = 100, max_length: int = 50000):
        super().__init__(rule)
        self.min_length = min_length
        self.max_length = max_length
        
    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        content_length = len(content.strip())
        
        if content_length < self.min_length:
            return self._create_result(
                ValidationStatus.FAILED,
                0.0,
                f"Contenu trop court: {content_length} caractères (minimum: {self.min_length})",
                {"length": content_length, "min_required": self.min_length},
                ["Ajouter plus de détails et d'explications"]
            )
        elif content_length > self.max_length:
            return self._create_result(
                ValidationStatus.FAILED,
                0.0,
                f"Contenu trop long: {content_length} caractères (maximum: {self.max_length})",
                {"length": content_length, "max_allowed": self.max_length},
                ["Diviser le contenu en sections plus petites"]
            )
        else:
            score = min(1.0, content_length / (self.min_length * 3))  # Score optimal à 3x le minimum
            return self._create_result(
                ValidationStatus.PASSED,
                score,
                f"Longueur appropriée: {content_length} caractères",
                {"length": content_length}
            )

class MedicalTerminologyRule(ValidationRuleBase):
    """Règle de validation de la terminologie médicale"""
    
    def __init__(self, rule: ValidationRule):
        super().__init__(rule)
        # Termes médicaux de base pour validation
        self.medical_terms = {
            "anatomie": ["cœur", "poumon", "foie", "rein", "cerveau", "estomac", "intestin"],
            "pathologies": ["hypertension", "diabète", "pneumonie", "paludisme", "tuberculose"],
            "traitements": ["antibiotique", "antihypertenseur", "insuline", "vaccination"],
            "examens": ["radiographie", "échographie", "scanner", "IRM", "biopsie"],
            "symptômes": ["fièvre", "douleur", "toux", "dyspnée", "nausée"]
        }
        
    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        content_lower = content.lower()
        found_terms = {}
        total_terms = 0
        
        for category, terms in self.medical_terms.items():
            found_in_category = []
            for term in terms:
                if term in content_lower:
                    found_in_category.append(term)
                    total_terms += 1
            if found_in_category:
                found_terms[category] = found_in_category
                
        # Score basé sur la diversité terminologique
        categories_covered = len(found_terms)
        max_categories = len(self.medical_terms)
        
        if total_terms == 0:
            return self._create_result(
                ValidationStatus.FAILED,
                0.0,
                "Aucune terminologie médicale détectée",
                {"terms_found": 0, "categories_covered": 0},
                ["Ajouter des termes médicaux appropriés"]
            )
        elif categories_covered < 2:
            return self._create_result(
                ValidationStatus.REQUIRES_REVIEW,
                0.4,
                f"Terminologie limitée: {total_terms} termes, {categories_covered} catégories",
                {"terms_found": total_terms, "categories_covered": categories_covered, "found_terms": found_terms},
                ["Diversifier la terminologie médicale"]
            )
        else:
            score = min(1.0, (categories_covered / max_categories) * 1.2)
            return self._create_result(
                ValidationStatus.PASSED,
                score,
                f"Terminologie appropriée: {total_terms} termes, {categories_covered} catégories",
                {"terms_found": total_terms, "categories_covered": categories_covered, "found_terms": found_terms}
            )

class LanguageQualityRule(ValidationRuleBase):
    """Règle de validation de la qualité linguistique"""
    
    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        issues = []
        score = 1.0
        
        # Vérification des phrases trop courtes/longues
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        short_sentences = [s for s in sentences if len(s) < 10]
        long_sentences = [s for s in sentences if len(s) > 200]
        
        if len(short_sentences) > len(sentences) * 0.3:
            issues.append("Trop de phrases courtes")
            score -= 0.2
            
        if len(long_sentences) > len(sentences) * 0.2:
            issues.append("Phrases trop longues détectées")
            score -= 0.2
            
        # Vérification de la répétition de mots
        words = re.findall(r'\b\w+\b', content.lower())
        if len(words) > 0:
            unique_words = set(words)
            repetition_ratio = len(words) / len(unique_words)
            
            if repetition_ratio > 3.0:
                issues.append("Répétitions excessives détectées")
                score -= 0.3
                
        # Analyse de lisibilité si disponible
        readability_score = None
        if TEXTSTAT_AVAILABLE:
            try:
                readability_score = textstat.flesch_reading_ease(content)
                if readability_score < 30:  # Très difficile
                    issues.append("Texte très difficile à lire")
                    score -= 0.2
                elif readability_score > 90:  # Très facile
                    issues.append("Texte peut-être trop simple")
                    score -= 0.1
            except:
                pass
                
        score = max(0.0, score)
        
        details = {
            "sentence_count": len(sentences),
            "short_sentences": len(short_sentences),
            "long_sentences": len(long_sentences),
            "word_count": len(words),
            "unique_words": len(unique_words) if words else 0,
            "readability_score": readability_score
        }
        
        if score >= 0.8:
            status = ValidationStatus.PASSED
            message = "Qualité linguistique satisfaisante"
        elif score >= 0.6:
            status = ValidationStatus.REQUIRES_REVIEW
            message = f"Qualité linguistique acceptable avec réserves: {', '.join(issues)}"
        else:
            status = ValidationStatus.FAILED
            message = f"Qualité linguistique insuffisante: {', '.join(issues)}"
            
        suggestions = []
        if "phrases courtes" in message:
            suggestions.append("Développer les phrases pour plus de clarté")
        if "phrases longues" in message:
            suggestions.append("Diviser les phrases complexes")
        if "répétitions" in message:
            suggestions.append("Utiliser des synonymes pour éviter les répétitions")
            
        return self._create_result(status, score, message, details, suggestions)

class StructureRule(ValidationRuleBase):
    """Règle de validation de la structure du document"""
    
    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        score = 0.0
        structure_elements = []
        
        # Vérification des titres/sections
        title_patterns = [r'^#+ .+', r'^[A-Z][^.]*:$', r'^\d+\. .+']
        titles_found = 0
        
        for pattern in title_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            titles_found += len(matches)
            
        if titles_found > 0:
            structure_elements.append("Titres/sections")
            score += 0.3
            
        # Vérification des listes
        list_patterns = [r'^[-*+] .+', r'^\d+\. .+', r'^[a-z]\) .+']
        lists_found = 0
        
        for pattern in list_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            lists_found += len(matches)
            
        if lists_found > 0:
            structure_elements.append("Listes")
            score += 0.2
            
        # Vérification des paragraphes
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if len(paragraphs) >= 2:
            structure_elements.append("Paragraphes multiples")
            score += 0.2
            
        # Vérification des références/citations
        citation_patterns = [r'\[\d+\]', r'\(\d{4}\)', r'et al\.', r'doi:']
        citations_found = 0
        
        for pattern in citation_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            citations_found += len(matches)
            
        if citations_found > 0:
            structure_elements.append("Références/citations")
            score += 0.3
            
        details = {
            "titles_found": titles_found,
            "lists_found": lists_found,
            "paragraphs_count": len(paragraphs),
            "citations_found": citations_found,
            "structure_elements": structure_elements
        }
        
        if score >= 0.8:
            status = ValidationStatus.PASSED
            message = f"Structure bien organisée: {', '.join(structure_elements)}"
        elif score >= 0.5:
            status = ValidationStatus.REQUIRES_REVIEW
            message = f"Structure acceptable: {', '.join(structure_elements)}"
        else:
            status = ValidationStatus.FAILED
            message = "Structure insuffisante"
            
        suggestions = []
        if titles_found == 0:
            suggestions.append("Ajouter des titres et sections")
        if len(paragraphs) < 2:
            suggestions.append("Organiser le contenu en paragraphes")
        if citations_found == 0:
            suggestions.append("Ajouter des références bibliographiques")
            
        return self._create_result(status, score, message, details, suggestions)

class MetadataRule(ValidationRuleBase):
    """Règle de validation des métadonnées"""
    
    def __init__(self, rule: ValidationRule):
        super().__init__(rule)
        self.required_fields = ["title", "domain", "source", "language"]
        self.optional_fields = ["author", "date", "keywords", "abstract"]
        
    def validate(self, content: str, metadata: Dict[str, Any]) -> ValidationResult:
        score = 0.0
        missing_required = []
        present_optional = []
        
        # Vérification des champs requis
        for field in self.required_fields:
            if field in metadata and metadata[field]:
                score += 1.0 / len(self.required_fields)
            else:
                missing_required.append(field)
                
        # Bonus pour les champs optionnels
        for field in self.optional_fields:
            if field in metadata and metadata[field]:
                present_optional.append(field)
                score += 0.1  # Bonus
                
        score = min(1.0, score)  # Plafonner à 1.0
        
        details = {
            "required_fields_present": len(self.required_fields) - len(missing_required),
            "required_fields_total": len(self.required_fields),
            "optional_fields_present": len(present_optional),
            "missing_required": missing_required,
            "present_optional": present_optional
        }
        
        if missing_required:
            status = ValidationStatus.FAILED
            message = f"Métadonnées incomplètes: champs manquants {missing_required}"
            suggestions = [f"Ajouter le champ '{field}'" for field in missing_required]
        else:
            status = ValidationStatus.PASSED
            message = f"Métadonnées complètes ({len(present_optional)} champs optionnels)"
            suggestions = []
            
        return self._create_result(status, score, message, details, suggestions)

class ValidationPipeline:
    """Pipeline de validation automatique"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "default_level": ValidationLevel.INTERMEDIATE,
            "parallel_execution": False,
            "stop_on_critical_failure": True,
            "min_passing_score": 0.7,
            "enable_suggestions": True
        }
        
        self.rules: Dict[ValidationLevel, List[ValidationRuleBase]] = {
            ValidationLevel.BASIC: [],
            ValidationLevel.INTERMEDIATE: [],
            ValidationLevel.ADVANCED: [],
            ValidationLevel.EXPERT: []
        }
        
        self.validation_history: List[ValidationReport] = []
        
        # Initialisation des règles par défaut
        self._initialize_default_rules()
        
        logger.info("ValidationPipeline initialisé")
        
    def _initialize_default_rules(self):
        """Initialise les règles de validation par défaut"""
        
        # Règles de base
        basic_rules = [
            ContentLengthRule(
                ValidationRule(
                    id="content_length",
                    name="Longueur du contenu",
                    category=ValidationCategory.CONTENT_QUALITY,
                    level=ValidationLevel.BASIC,
                    description="Vérifie que le contenu a une longueur appropriée",
                    weight=0.2,
                    is_mandatory=True,
                    error_message="Longueur de contenu inappropriée"
                )
            ),
            MetadataRule(
                ValidationRule(
                    id="metadata_completeness",
                    name="Complétude des métadonnées",
                    category=ValidationCategory.METADATA,
                    level=ValidationLevel.BASIC,
                    description="Vérifie la présence des métadonnées requises",
                    weight=0.3,
                    is_mandatory=True,
                    error_message="Métadonnées incomplètes"
                )
            )
        ]
        
        # Règles intermédiaires
        intermediate_rules = basic_rules + [
            MedicalTerminologyRule(
                ValidationRule(
                    id="medical_terminology",
                    name="Terminologie médicale",
                    category=ValidationCategory.MEDICAL_ACCURACY,
                    level=ValidationLevel.INTERMEDIATE,
                    description="Vérifie l'usage approprié de la terminologie médicale",
                    weight=0.4,
                    is_mandatory=True,
                    error_message="Terminologie médicale insuffisante"
                )
            ),
            LanguageQualityRule(
                ValidationRule(
                    id="language_quality",
                    name="Qualité linguistique",
                    category=ValidationCategory.LANGUAGE_QUALITY,
                    level=ValidationLevel.INTERMEDIATE,
                    description="Évalue la qualité de la langue et de la rédaction",
                    weight=0.3,
                    is_mandatory=False,
                    error_message="Qualité linguistique insuffisante"
                )
            )
        ]
        
        # Règles avancées
        advanced_rules = intermediate_rules + [
            StructureRule(
                ValidationRule(
                    id="document_structure",
                    name="Structure du document",
                    category=ValidationCategory.STRUCTURE,
                    level=ValidationLevel.ADVANCED,
                    description="Évalue l'organisation et la structure du document",
                    weight=0.2,
                    is_mandatory=False,
                    error_message="Structure de document insuffisante"
                )
            )
        ]
        
        # Attribution des règles aux niveaux
        self.rules[ValidationLevel.BASIC] = basic_rules
        self.rules[ValidationLevel.INTERMEDIATE] = intermediate_rules
        self.rules[ValidationLevel.ADVANCED] = advanced_rules
        self.rules[ValidationLevel.EXPERT] = advanced_rules  # Même que avancé pour la démo
        
    def add_custom_rule(self, rule: ValidationRuleBase, level: ValidationLevel):
        """Ajoute une règle personnalisée"""
        self.rules[level].append(rule)
        logger.info(f"Règle personnalisée ajoutée: {rule.rule.name} (niveau {level.value})")
        
    def validate_document(self, 
                         document_id: str,
                         content: str, 
                         metadata: Dict[str, Any],
                         level: ValidationLevel = None) -> ValidationReport:
        """Valide un document complet"""
        
        start_time = datetime.now()
        validation_id = f"val_{int(start_time.timestamp())}_{document_id}"
        
        if level is None:
            level = self.config["default_level"]
            
        logger.info(f"Validation document {document_id} (niveau {level.value})")
        
        # Récupération des règles pour ce niveau
        rules_to_apply = self.rules.get(level, [])
        
        results = []
        overall_score = 0.0
        total_weight = 0.0
        critical_failure = False
        
        # Exécution des règles
        for rule in rules_to_apply:
            try:
                rule_start = datetime.now()
                result = rule.validate(content, metadata)
                rule_end = datetime.now()
                
                result.execution_time_ms = (rule_end - rule_start).total_seconds() * 1000
                results.append(result)
                
                # Calcul du score pondéré
                weight = rule.rule.weight
                overall_score += result.score * weight
                total_weight += weight
                
                # Vérification d'échec critique
                if (rule.rule.is_mandatory and 
                    result.status == ValidationStatus.FAILED and
                    self.config["stop_on_critical_failure"]):
                    critical_failure = True
                    logger.warning(f"Échec critique détecté: {rule.rule.name}")
                    break
                    
            except Exception as e:
                logger.error(f"Erreur exécution règle {rule.rule.name}: {e}")
                error_result = ValidationResult(
                    rule_id=rule.rule.id,
                    rule_name=rule.rule.name,
                    status=ValidationStatus.FAILED,
                    score=0.0,
                    message=f"Erreur d'exécution: {e}",
                    details={"error": str(e)},
                    execution_time_ms=0.0,
                    suggestions=["Vérifier la configuration de la règle"]
                )
                results.append(error_result)
                
        # Calcul du score final
        if total_weight > 0:
            overall_score = overall_score / total_weight
        else:
            overall_score = 0.0
            
        # Détermination du statut global
        if critical_failure:
            overall_status = ValidationStatus.FAILED
        elif overall_score >= self.config["min_passing_score"]:
            overall_status = ValidationStatus.PASSED
        elif overall_score >= 0.5:
            overall_status = ValidationStatus.REQUIRES_REVIEW
        else:
            overall_status = ValidationStatus.FAILED
            
        # Génération du résumé
        summary = self._generate_summary(results, overall_score)
        
        # Génération des recommandations
        recommendations = self._generate_recommendations(results)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        # Création du rapport
        report = ValidationReport(
            document_id=document_id,
            validation_id=validation_id,
            timestamp=start_time,
            overall_status=overall_status,
            overall_score=overall_score,
            level_used=level,
            results=results,
            summary=summary,
            recommendations=recommendations,
            processing_time_ms=processing_time
        )
        
        # Ajout à l'historique
        self.validation_history.append(report)
        
        logger.info(f"Validation terminée: {overall_status.value} (score: {overall_score:.3f})")
        return report
        
    def _generate_summary(self, results: List[ValidationResult], overall_score: float) -> Dict[str, Any]:
        """Génère un résumé des résultats"""
        summary = {
            "total_rules": len(results),
            "passed": len([r for r in results if r.status == ValidationStatus.PASSED]),
            "failed": len([r for r in results if r.status == ValidationStatus.FAILED]),
            "requires_review": len([r for r in results if r.status == ValidationStatus.REQUIRES_REVIEW]),
            "overall_score": overall_score,
            "categories": {},
            "execution_time_total": sum(r.execution_time_ms for r in results)
        }
        
        # Résumé par catégorie
        categories = {}
        for result in results:
            # Trouver la catégorie de la règle
            category = "unknown"
            for level_rules in self.rules.values():
                for rule in level_rules:
                    if rule.rule.id == result.rule_id:
                        category = rule.rule.category.value
                        break
                        
            if category not in categories:
                categories[category] = {"passed": 0, "failed": 0, "total": 0, "avg_score": 0.0}
                
            categories[category]["total"] += 1
            if result.status == ValidationStatus.PASSED:
                categories[category]["passed"] += 1
            elif result.status == ValidationStatus.FAILED:
                categories[category]["failed"] += 1
                
        # Calcul des scores moyens par catégorie
        for category in categories:
            category_results = [r for r in results if any(
                rule.rule.category.value == category and rule.rule.id == r.rule_id
                for level_rules in self.rules.values()
                for rule in level_rules
            )]
            if category_results:
                categories[category]["avg_score"] = sum(r.score for r in category_results) / len(category_results)
                
        summary["categories"] = categories
        return summary
        
    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Génère des recommandations basées sur les résultats"""
        recommendations = []
        
        # Collecte des suggestions de toutes les règles
        all_suggestions = []
        for result in results:
            all_suggestions.extend(result.suggestions)
            
        # Dédoublonnage et priorisation
        unique_suggestions = list(set(all_suggestions))
        
        # Recommandations générales basées sur les échecs
        failed_results = [r for r in results if r.status == ValidationStatus.FAILED]
        if failed_results:
            recommendations.append(f"Corriger {len(failed_results)} problème(s) critique(s)")
            
        review_results = [r for r in results if r.status == ValidationStatus.REQUIRES_REVIEW]
        if review_results:
            recommendations.append(f"Réviser {len(review_results)} point(s) d'amélioration")
            
        # Ajout des suggestions spécifiques
        recommendations.extend(unique_suggestions[:5])  # Limiter à 5 suggestions
        
        return recommendations
        
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de validation"""
        if not self.validation_history:
            return {"total_validations": 0}
            
        total = len(self.validation_history)
        passed = len([r for r in self.validation_history if r.overall_status == ValidationStatus.PASSED])
        failed = len([r for r in self.validation_history if r.overall_status == ValidationStatus.FAILED])
        review = len([r for r in self.validation_history if r.overall_status == ValidationStatus.REQUIRES_REVIEW])
        
        avg_score = sum(r.overall_score for r in self.validation_history) / total
        avg_time = sum(r.processing_time_ms for r in self.validation_history) / total
        
        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "requires_review": review,
            "success_rate": passed / total if total > 0 else 0.0,
            "average_score": avg_score,
            "average_processing_time_ms": avg_time,
            "last_validation": self.validation_history[-1].timestamp.isoformat()
        }
        
    def export_data(self, output_path: str) -> Dict[str, Any]:
        """Exporte les données de validation"""
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "pipeline_version": "3.0.0",
                "objective": "Objectif 3 - Pipeline de validation automatique"
            },
            "configuration": self.config,
            "statistics": self.get_validation_statistics(),
            "validation_history": [],
            "rules_summary": {}
        }
        
        # Export de l'historique (derniers 50)
        recent_history = self.validation_history[-50:]
        for report in recent_history:
            report_data = asdict(report)
            report_data["timestamp"] = report.timestamp.isoformat()
            export_data["validation_history"].append(report_data)
            
        # Résumé des règles par niveau
        for level, rules in self.rules.items():
            export_data["rules_summary"][level.value] = {
                "total_rules": len(rules),
                "mandatory_rules": len([r for r in rules if r.rule.is_mandatory]),
                "categories": list(set(r.rule.category.value for r in rules))
            }
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
            return {
                "success": True,
                "file_path": output_path,
                "validations_exported": len(export_data["validation_history"])
            }
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def main():
    """Fonction principale de démonstration"""
    print("✅ Validation Pipeline - Objectif 3")
    print("Pipeline de validation automatique du contenu")
    print("=" * 50)
    
    # Initialisation
    pipeline = ValidationPipeline({
        "default_level": ValidationLevel.INTERMEDIATE,
        "min_passing_score": 0.7,
        "stop_on_critical_failure": False,
        "enable_suggestions": True
    })
    
    # Documents de test
    test_documents = [
        {
            "id": "doc_001",
            "content": """# Hypertension Artérielle
            
L'hypertension artérielle est une pathologie cardiovasculaire majeure caractérisée par une élévation persistante de la pression artérielle. Elle constitue un facteur de risque important pour les maladies coronariennes, l'insuffisance cardiaque et les accidents vasculaires cérébraux.
            
## Diagnostic
            
Le diagnostic repose sur la mesure répétée de la pression artérielle. Les valeurs seuils sont :
            - Pression systolique ≥ 140 mmHg
            - Pression diastolique ≥ 90 mmHg
            
## Traitement
            
Le traitement comprend :
            1. Mesures hygiéno-diététiques
            2. Antihypertenseurs si nécessaire
            3. Suivi régulier
            
Les principales classes d'antihypertenseurs incluent les inhibiteurs de l'enzyme de conversion, les antagonistes des récepteurs de l'angiotensine II, les diurétiques thiazidiques et les inhibiteurs calciques.
            """,
            "metadata": {
                "title": "Hypertension Artérielle - Guide Clinique",
                "domain": "cardiologie",
                "source": "Hôpital Général de Douala",
                "language": "fr",
                "author": "Dr. Médecin",
                "date": "2024-01-15",
                "keywords": ["hypertension", "cardiovasculaire", "traitement"]
            }
        },
        {
            "id": "doc_002",
            "content": "Paludisme maladie grave Afrique. Fièvre. Traitement urgent.",
            "metadata": {
                "title": "Paludisme",
                "domain": "médecine_tropicale",
                "source": "source_inconnue",
                "language": "fr"
            }
        },
        {
            "id": "doc_003",
            "content": """La pneumonie est une infection des poumons qui peut être causée par des bactéries, des virus ou des champignons. Les symptômes incluent la toux, la fièvre, les frissons et la difficulté à respirer. Le diagnostic se fait par radiographie pulmonaire et examens biologiques. Le traitement dépend de l'agent pathogène identifié. Les antibiotiques sont utilisés pour les pneumonies bactériennes. La prévention inclut la vaccination contre le pneumocoque et la grippe. Les patients âgés et immunodéprimés sont plus à risque de complications graves.""",
            "metadata": {
                "title": "Pneumonie - Diagnostic et Traitement",
                "domain": "pneumologie",
                "source": "Revue Médicale",
                "language": "fr",
                "author": "Dr. Pneumologue"
            }
        }
    ]
    
    print(f"\n📋 Test de validation sur {len(test_documents)} documents...")
    
    # Validation des documents
    reports = []
    for doc in test_documents:
        print(f"\n🔍 Validation du document {doc['id']}...")
        
        report = pipeline.validate_document(
            doc["id"],
            doc["content"],
            doc["metadata"],
            ValidationLevel.INTERMEDIATE
        )
        
        reports.append(report)
        
        print(f"Statut: {report.overall_status.value}")
        print(f"Score: {report.overall_score:.3f}")
        print(f"Temps: {report.processing_time_ms:.1f}ms")
        
        # Affichage des résultats détaillés
        print("\nRésultats par règle:")
        for result in report.results:
            status_icon = "✅" if result.status == ValidationStatus.PASSED else "❌" if result.status == ValidationStatus.FAILED else "⚠️"
            print(f"  {status_icon} {result.rule_name}: {result.score:.2f} - {result.message}")
            
        if report.recommendations:
            print("\nRecommandations:")
            for rec in report.recommendations[:3]:  # Limiter à 3
                print(f"  • {rec}")
                
    # Statistiques globales
    print("\n📊 Statistiques de validation...")
    stats = pipeline.get_validation_statistics()
    print(f"Total validations: {stats['total_validations']}")
    print(f"Taux de succès: {stats['success_rate']:.2%}")
    print(f"Score moyen: {stats['average_score']:.3f}")
    print(f"Temps moyen: {stats['average_processing_time_ms']:.1f}ms")
    
    # Test avec différents niveaux
    print("\n🎯 Test des niveaux de validation...")
    test_doc = test_documents[0]
    
    for level in [ValidationLevel.BASIC, ValidationLevel.INTERMEDIATE, ValidationLevel.ADVANCED]:
        report = pipeline.validate_document(
            f"{test_doc['id']}_{level.value}",
            test_doc["content"],
            test_doc["metadata"],
            level
        )
        print(f"Niveau {level.value}: {len(report.results)} règles, score {report.overall_score:.3f}")
        
    # Export des données
    print("\n💾 Export des données de validation...")
    export_result = pipeline.export_data("validation_pipeline_export.json")
    if export_result["success"]:
        print(f"Données exportées: {export_result['validations_exported']} validations")
        
    print("\n✅ Objectif 3 - Pipeline de validation automatique implémenté!")
    print(f"📈 {stats['total_validations']} validations effectuées avec {stats['success_rate']:.1%} de succès")

if __name__ == "__main__":
    main()