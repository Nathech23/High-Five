#!/usr/bin/env python3
"""
Glossaire Médical Multilingue

Objectif 3: Ajouter contenu en français et langues camerounaises
Objectif 5: Créer glossaire médical multilingue

Ce module gère un glossaire médical multilingue incluant le français
et les principales langues camerounaises (Fulfulde, Ewondo, Duala).

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

class SupportedLanguage(Enum):
    """Langues supportées dans le glossaire"""
    FRENCH = "fr"  # Français
    ENGLISH = "en"  # Anglais
    FULFULDE = "ff"  # Fulfulde (Peul)
    EWONDO = "ewo"  # Ewondo (Beti)
    DUALA = "dua"  # Duala
    BAMILEKE = "bax"  # Bamiléké
    HAUSA = "ha"  # Hausa

class TermCategory(Enum):
    """Catégories de termes médicaux"""
    ANATOMY = "anatomie"
    PATHOLOGY = "pathologie"
    SYMPTOM = "symptome"
    TREATMENT = "traitement"
    MEDICATION = "medicament"
    PROCEDURE = "procedure"
    SPECIALTY = "specialite"
    EQUIPMENT = "equipement"
    PREVENTION = "prevention"
    EMERGENCY = "urgence"

@dataclass
class Translation:
    """Traduction d'un terme"""
    language: SupportedLanguage
    term: str
    pronunciation: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 1.0
    source: str = "manual"

@dataclass
class MedicalTerm:
    """Terme médical multilingue"""
    id: str
    primary_term: str  # Terme principal (généralement en français)
    category: TermCategory
    translations: Dict[SupportedLanguage, Translation] = field(default_factory=dict)
    synonyms: List[str] = field(default_factory=list)
    related_terms: List[str] = field(default_factory=list)
    definition: str = ""
    usage_examples: List[str] = field(default_factory=list)
    difficulty_level: int = 1  # 1=basique, 2=intermédiaire, 3=avancé
    frequency_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour le terme"""
        import hashlib
        term_hash = hashlib.md5(self.primary_term.encode()).hexdigest()[:8]
        return f"{self.category.value}_{term_hash}"

@dataclass
class GlossaryStats:
    """Statistiques du glossaire"""
    total_terms: int = 0
    terms_by_category: Dict[str, int] = field(default_factory=dict)
    terms_by_language: Dict[str, int] = field(default_factory=dict)
    avg_translations_per_term: float = 0.0
    coverage_by_language: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0

class MultilingualGlossary:
    """
    Gestionnaire de glossaire médical multilingue
    
    Objectifs couverts:
    - 3. Ajouter contenu en français et langues camerounaises
    - 5. Créer glossaire médical multilingue
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.terms: Dict[str, MedicalTerm] = {}
        self.language_index: Dict[SupportedLanguage, Set[str]] = defaultdict(set)
        self.category_index: Dict[TermCategory, Set[str]] = defaultdict(set)
        self.stats = GlossaryStats()
        
        # Configuration
        self.auto_translate = self.config.get("auto_translate", False)
        self.min_confidence = self.config.get("min_confidence", 0.7)
        
        # Initialiser le glossaire de base
        self._init_base_glossary()
        
        logger.info("Glossaire médical multilingue initialisé")
    
    def _init_base_glossary(self):
        """Initialise le glossaire avec des termes de base"""
        base_terms = self._get_base_medical_terms()
        
        for term_data in base_terms:
            term = MedicalTerm(**term_data)
            self.add_term(term)
        
        logger.info(f"Glossaire initialisé avec {len(base_terms)} termes de base")
    
    def _get_base_medical_terms(self) -> List[Dict[str, Any]]:
        """Retourne les termes médicaux de base"""
        return [
            {
                "primary_term": "cœur",
                "category": TermCategory.ANATOMY,
                "definition": "Organe musculaire qui pompe le sang dans le corps",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "heart"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "berde", "ber-de"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "nlôm", "n-lom"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "moto", "mo-to")
                },
                "difficulty_level": 1,
                "frequency_score": 0.9
            },
            {
                "primary_term": "fièvre",
                "category": TermCategory.SYMPTOM,
                "definition": "Élévation anormale de la température corporelle",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "fever"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "ladde", "lad-de"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "awu", "a-wu"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "nyolo", "nyo-lo")
                },
                "difficulty_level": 1,
                "frequency_score": 0.95
            },
            {
                "primary_term": "paludisme",
                "category": TermCategory.PATHOLOGY,
                "definition": "Maladie parasitaire transmise par les moustiques",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "malaria"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "sette", "set-te"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "akoma", "a-ko-ma"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "maladi", "ma-la-di")
                },
                "difficulty_level": 2,
                "frequency_score": 0.8
            },
            {
                "primary_term": "médicament",
                "category": TermCategory.MEDICATION,
                "definition": "Substance utilisée pour traiter ou prévenir une maladie",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "medicine"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "lekki", "lek-ki"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "bilôm", "bi-lom"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "medi", "me-di")
                },
                "difficulty_level": 1,
                "frequency_score": 0.9
            },
            {
                "primary_term": "diabète",
                "category": TermCategory.PATHOLOGY,
                "definition": "Maladie caractérisée par un taux de sucre élevé dans le sang",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "diabetes"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "sukkar", "suk-kar"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "sukre", "su-kre"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "sukre", "su-kre")
                },
                "difficulty_level": 2,
                "frequency_score": 0.7
            },
            {
                "primary_term": "tension artérielle",
                "category": TermCategory.ANATOMY,
                "definition": "Pression exercée par le sang sur les parois des artères",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "blood pressure"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "hakkilo yiiyam", "hak-ki-lo yi-yam"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "makasi ma yii", "ma-ka-si ma yi-i"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "makasi ma moto", "ma-ka-si ma mo-to")
                },
                "difficulty_level": 2,
                "frequency_score": 0.8
            },
            {
                "primary_term": "vaccination",
                "category": TermCategory.PREVENTION,
                "definition": "Administration d'un vaccin pour prévenir une maladie",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "vaccination"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "allura", "al-lu-ra"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "piqûre", "pi-qû-re"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "pikire", "pi-ki-re")
                },
                "difficulty_level": 2,
                "frequency_score": 0.6
            },
            {
                "primary_term": "douleur",
                "category": TermCategory.SYMPTOM,
                "definition": "Sensation désagréable causée par une blessure ou une maladie",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "pain"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "ciwo", "ci-wo"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "mvé", "m-vé"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "mpasi", "m-pa-si")
                },
                "difficulty_level": 1,
                "frequency_score": 0.95
            },
            {
                "primary_term": "hôpital",
                "category": TermCategory.EQUIPMENT,
                "definition": "Établissement de soins médicaux",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "hospital"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "asibitaal", "a-si-bi-taal"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "nda bekôm", "n-da be-kom"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "lopitalo", "lo-pi-ta-lo")
                },
                "difficulty_level": 1,
                "frequency_score": 0.8
            },
            {
                "primary_term": "médecin",
                "category": TermCategory.SPECIALTY,
                "definition": "Professionnel de santé qui diagnostique et traite les maladies",
                "translations": {
                    SupportedLanguage.ENGLISH: Translation(SupportedLanguage.ENGLISH, "doctor"),
                    SupportedLanguage.FULFULDE: Translation(SupportedLanguage.FULFULDE, "lekki-jo", "lek-ki-jo"),
                    SupportedLanguage.EWONDO: Translation(SupportedLanguage.EWONDO, "bekôm", "be-kom"),
                    SupportedLanguage.DUALA: Translation(SupportedLanguage.DUALA, "dokita", "do-ki-ta")
                },
                "difficulty_level": 1,
                "frequency_score": 0.9
            }
        ]
    
    def add_term(self, term: MedicalTerm) -> bool:
        """
        Ajoute un terme au glossaire
        
        Args:
            term: Terme médical à ajouter
        
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            # Vérifier si le terme existe déjà
            if term.id in self.terms:
                logger.warning(f"Terme déjà existant: {term.id}")
                return False
            
            # Ajouter le terme
            self.terms[term.id] = term
            
            # Mettre à jour les index
            self.category_index[term.category].add(term.id)
            
            for language in term.translations.keys():
                self.language_index[language].add(term.id)
            
            logger.debug(f"Terme ajouté: {term.primary_term} ({term.id})")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du terme {term.primary_term}: {e}")
            return False
    
    def get_term(self, term_id: str) -> Optional[MedicalTerm]:
        """Retourne un terme par son ID"""
        return self.terms.get(term_id)
    
    def search_terms(self, query: str, language: Optional[SupportedLanguage] = None, 
                    category: Optional[TermCategory] = None) -> List[MedicalTerm]:
        """
        Recherche des termes dans le glossaire
        
        Args:
            query: Terme à rechercher
            language: Langue de recherche (optionnel)
            category: Catégorie de recherche (optionnel)
        
        Returns:
            List[MedicalTerm]: Termes trouvés
        """
        results = []
        query_lower = query.lower()
        
        for term in self.terms.values():
            # Filtrer par catégorie si spécifiée
            if category and term.category != category:
                continue
            
            # Rechercher dans le terme principal
            if query_lower in term.primary_term.lower():
                results.append(term)
                continue
            
            # Rechercher dans les synonymes
            if any(query_lower in synonym.lower() for synonym in term.synonyms):
                results.append(term)
                continue
            
            # Rechercher dans les traductions
            if language:
                translation = term.translations.get(language)
                if translation and query_lower in translation.term.lower():
                    results.append(term)
                    continue
            else:
                # Rechercher dans toutes les traductions
                for translation in term.translations.values():
                    if query_lower in translation.term.lower():
                        results.append(term)
                        break
        
        # Trier par score de fréquence
        results.sort(key=lambda t: t.frequency_score, reverse=True)
        
        return results
    
    def get_translation(self, term_id: str, target_language: SupportedLanguage) -> Optional[Translation]:
        """
        Retourne la traduction d'un terme dans une langue donnée
        
        Args:
            term_id: ID du terme
            target_language: Langue cible
        
        Returns:
            Optional[Translation]: Traduction si disponible
        """
        term = self.terms.get(term_id)
        if not term:
            return None
        
        return term.translations.get(target_language)
    
    def add_translation(self, term_id: str, translation: Translation) -> bool:
        """
        Ajoute une traduction à un terme existant
        
        Args:
            term_id: ID du terme
            translation: Traduction à ajouter
        
        Returns:
            bool: True si ajoutée avec succès
        """
        term = self.terms.get(term_id)
        if not term:
            logger.error(f"Terme non trouvé: {term_id}")
            return False
        
        # Vérifier la confiance minimale
        if translation.confidence < self.min_confidence:
            logger.warning(f"Confiance trop faible pour la traduction: {translation.confidence}")
            return False
        
        # Ajouter la traduction
        term.translations[translation.language] = translation
        
        # Mettre à jour l'index des langues
        self.language_index[translation.language].add(term_id)
        
        logger.debug(f"Traduction ajoutée: {term.primary_term} -> {translation.term} ({translation.language.value})")
        return True
    
    def get_terms_by_category(self, category: TermCategory) -> List[MedicalTerm]:
        """Retourne tous les termes d'une catégorie"""
        term_ids = self.category_index.get(category, set())
        return [self.terms[term_id] for term_id in term_ids if term_id in self.terms]
    
    def get_terms_by_language(self, language: SupportedLanguage) -> List[MedicalTerm]:
        """Retourne tous les termes ayant une traduction dans une langue"""
        term_ids = self.language_index.get(language, set())
        return [self.terms[term_id] for term_id in term_ids if term_id in self.terms]
    
    def get_terms_by_difficulty(self, level: int) -> List[MedicalTerm]:
        """Retourne tous les termes d'un niveau de difficulté"""
        return [term for term in self.terms.values() if term.difficulty_level == level]
    
    def calculate_coverage(self) -> Dict[SupportedLanguage, float]:
        """
        Calcule la couverture de traduction pour chaque langue
        
        Returns:
            Dict[SupportedLanguage, float]: Pourcentage de couverture par langue
        """
        total_terms = len(self.terms)
        if total_terms == 0:
            return {}
        
        coverage = {}
        for language in SupportedLanguage:
            translated_count = len(self.language_index.get(language, set()))
            coverage[language] = (translated_count / total_terms) * 100
        
        return coverage
    
    def generate_stats(self) -> GlossaryStats:
        """
        Génère les statistiques du glossaire
        
        Returns:
            GlossaryStats: Statistiques complètes
        """
        import time
        start_time = time.time()
        
        stats = GlossaryStats()
        stats.total_terms = len(self.terms)
        
        # Statistiques par catégorie
        for category, term_ids in self.category_index.items():
            stats.terms_by_category[category.value] = len(term_ids)
        
        # Statistiques par langue
        for language, term_ids in self.language_index.items():
            stats.terms_by_language[language.value] = len(term_ids)
        
        # Moyenne de traductions par terme
        if stats.total_terms > 0:
            total_translations = sum(len(term.translations) for term in self.terms.values())
            stats.avg_translations_per_term = total_translations / stats.total_terms
        
        # Couverture par langue
        coverage = self.calculate_coverage()
        stats.coverage_by_language = {lang.value: cov for lang, cov in coverage.items()}
        
        stats.processing_time = time.time() - start_time
        
        self.stats = stats
        return stats
    
    def export_glossary(self, output_path: str, language: Optional[SupportedLanguage] = None):
        """
        Exporte le glossaire dans un fichier JSON
        
        Args:
            output_path: Chemin de sortie
            language: Langue spécifique à exporter (optionnel)
        """
        export_data = {
            "metadata": {
                "total_terms": len(self.terms),
                "export_language": language.value if language else "all",
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "terms": []
        }
        
        for term in self.terms.values():
            term_data = {
                "id": term.id,
                "primary_term": term.primary_term,
                "category": term.category.value,
                "definition": term.definition,
                "difficulty_level": term.difficulty_level,
                "frequency_score": term.frequency_score,
                "synonyms": term.synonyms,
                "related_terms": term.related_terms,
                "usage_examples": term.usage_examples
            }
            
            # Ajouter les traductions
            if language:
                translation = term.translations.get(language)
                if translation:
                    term_data["translation"] = {
                        "term": translation.term,
                        "pronunciation": translation.pronunciation,
                        "notes": translation.notes,
                        "confidence": translation.confidence
                    }
            else:
                term_data["translations"] = {
                    lang.value: {
                        "term": trans.term,
                        "pronunciation": trans.pronunciation,
                        "notes": trans.notes,
                        "confidence": trans.confidence
                    }
                    for lang, trans in term.translations.items()
                }
            
            export_data["terms"].append(term_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Glossaire exporté: {output_path}")
    
    def import_glossary(self, input_path: str) -> int:
        """
        Importe un glossaire depuis un fichier JSON
        
        Args:
            input_path: Chemin du fichier à importer
        
        Returns:
            int: Nombre de termes importés
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            
            for term_data in data.get("terms", []):
                # Créer le terme
                term = MedicalTerm(
                    id=term_data.get("id", ""),
                    primary_term=term_data["primary_term"],
                    category=TermCategory(term_data["category"]),
                    definition=term_data.get("definition", ""),
                    difficulty_level=term_data.get("difficulty_level", 1),
                    frequency_score=term_data.get("frequency_score", 0.0),
                    synonyms=term_data.get("synonyms", []),
                    related_terms=term_data.get("related_terms", []),
                    usage_examples=term_data.get("usage_examples", [])
                )
                
                # Ajouter les traductions
                translations_data = term_data.get("translations", {})
                for lang_code, trans_data in translations_data.items():
                    try:
                        language = SupportedLanguage(lang_code)
                        translation = Translation(
                            language=language,
                            term=trans_data["term"],
                            pronunciation=trans_data.get("pronunciation"),
                            notes=trans_data.get("notes"),
                            confidence=trans_data.get("confidence", 1.0)
                        )
                        term.translations[language] = translation
                    except ValueError:
                        logger.warning(f"Langue non supportée: {lang_code}")
                
                # Ajouter le terme
                if self.add_term(term):
                    imported_count += 1
            
            logger.info(f"Glossaire importé: {imported_count} termes")
            return imported_count
        
        except Exception as e:
            logger.error(f"Erreur lors de l'importation: {e}")
            return 0
    
    def generate_pronunciation_guide(self, language: SupportedLanguage) -> Dict[str, str]:
        """
        Génère un guide de prononciation pour une langue
        
        Args:
            language: Langue cible
        
        Returns:
            Dict[str, str]: Guide terme -> prononciation
        """
        guide = {}
        
        for term in self.terms.values():
            translation = term.translations.get(language)
            if translation and translation.pronunciation:
                guide[translation.term] = translation.pronunciation
        
        return guide

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🌍 Test du Glossaire Médical Multilingue")
    
    # Créer le glossaire
    glossary = MultilingualGlossary({
        "auto_translate": False,
        "min_confidence": 0.7
    })
    
    # Rechercher des termes
    print("\n🔍 Recherche de 'cœur':")
    results = glossary.search_terms("cœur")
    for term in results:
        print(f"  {term.primary_term} ({term.category.value})")
        for lang, trans in term.translations.items():
            print(f"    {lang.value}: {trans.term}")
    
    # Rechercher par catégorie
    print("\n🏥 Termes de pathologie:")
    pathology_terms = glossary.get_terms_by_category(TermCategory.PATHOLOGY)
    for term in pathology_terms[:3]:  # Limiter à 3 pour l'affichage
        print(f"  {term.primary_term}")
    
    # Calculer la couverture
    print("\n📊 Couverture par langue:")
    coverage = glossary.calculate_coverage()
    for language, percentage in coverage.items():
        print(f"  {language.value}: {percentage:.1f}%")
    
    # Générer les statistiques
    stats = glossary.generate_stats()
    print(f"\n📈 Statistiques:")
    print(f"  Termes totaux: {stats.total_terms}")
    print(f"  Traductions moyennes par terme: {stats.avg_translations_per_term:.1f}")
    print(f"  Temps de traitement: {stats.processing_time:.3f}s")
    
    # Exporter le glossaire
    glossary.export_glossary("medical_glossary_multilingual.json")
    print("\n✅ Glossaire exporté: medical_glossary_multilingual.json")
    
    # Générer un guide de prononciation
    fulfulde_guide = glossary.generate_pronunciation_guide(SupportedLanguage.FULFULDE)
    print(f"\n🗣️ Guide de prononciation Fulfulde: {len(fulfulde_guide)} termes")

if __name__ == "__main__":
    asyncio.run(main())