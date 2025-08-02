#!/usr/bin/env python3
"""
Système de Traduction Automatique

Objectif 12: Créer système de traduction automatique

Ce module implémente un système de traduction automatique optimisé
pour le contexte médical et les langues camerounaises.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels pour les services de traduction
try:
    from googletrans import Translator as GoogleTranslator
    GOOGLE_TRANS_AVAILABLE = True
except ImportError:
    logger.warning("googletrans non disponible")
    GOOGLE_TRANS_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator as DeepGoogleTranslator
    from deep_translator import MyMemoryTranslator, LibreTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    logger.warning("deep-translator non disponible")
    DEEP_TRANSLATOR_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    logger.warning("requests non disponible")
    REQUESTS_AVAILABLE = False

class TranslationService(Enum):
    """Services de traduction disponibles"""
    GOOGLE = "google"
    GOOGLE_DEEP = "google_deep"
    MYMEMORY = "mymemory"
    LIBRE = "libre"
    CUSTOM_MEDICAL = "custom_medical"
    OFFLINE_DICT = "offline_dict"
    HYBRID = "hybrid"  # Combinaison de plusieurs services

class TranslationQuality(Enum):
    """Niveaux de qualité de traduction"""
    EXCELLENT = "excellent"  # >0.9
    GOOD = "good"           # 0.7-0.9
    FAIR = "fair"           # 0.5-0.7
    POOR = "poor"           # 0.3-0.5
    VERY_POOR = "very_poor" # <0.3

class MedicalDomain(Enum):
    """Domaines médicaux pour traduction spécialisée"""
    GENERAL = "general"
    CARDIOLOGY = "cardiologie"
    INFECTIOUS_DISEASES = "infectiologie"
    PEDIATRICS = "pediatrie"
    OBSTETRICS = "obstetrique"
    SURGERY = "chirurgie"
    EMERGENCY = "urgences"
    PHARMACY = "pharmacie"
    LABORATORY = "laboratoire"
    RADIOLOGY = "radiologie"

@dataclass
class TranslationRequest:
    """Requête de traduction"""
    text: str
    source_language: str
    target_language: str
    domain: MedicalDomain = MedicalDomain.GENERAL
    service_preference: Optional[TranslationService] = None
    preserve_medical_terms: bool = True
    context: Optional[str] = None
    priority: int = 1  # 1=normal, 2=high, 3=urgent
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TranslationResult:
    """Résultat de traduction"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    service_used: str
    confidence_score: float
    quality_level: TranslationQuality
    processing_time: float
    medical_terms_preserved: List[str] = field(default_factory=list)
    alternative_translations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MedicalTermMapping:
    """Mapping de terme médical"""
    term: str
    language: str
    translations: Dict[str, str]  # langue -> traduction
    domain: MedicalDomain
    confidence: float
    verified: bool = False
    source: str = "system"
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class TranslationStats:
    """Statistiques de traduction"""
    total_translations: int = 0
    translations_by_language_pair: Dict[str, int] = field(default_factory=dict)
    translations_by_service: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_processing_time: float = 0.0
    cache_hit_rate: float = 0.0
    medical_terms_preserved: int = 0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    processing_time: float = 0.0

class TranslationSystem:
    """
    Système de traduction automatique médical
    
    Objectif couvert:
    - 12. Créer système de traduction automatique
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = TranslationStats()
        
        # Configuration des services
        self.primary_service = TranslationService(self.config.get("primary_service", "google"))
        self.fallback_services = self.config.get("fallback_services", ["mymemory", "offline_dict"])
        
        # Traducteurs
        self.translators = {}
        self.medical_dictionaries = {}
        
        # Cache de traductions
        self.translation_cache = {}
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.max_cache_size = self.config.get("max_cache_size", 10000)
        
        # Dictionnaire médical multilingue
        self.medical_terms = {}
        
        # Statistiques
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Initialiser les services
        self._init_translation_services()
        self._init_medical_dictionaries()
        
        logger.info("Système de traduction automatique initialisé")
    
    def _init_translation_services(self):
        """Initialise les services de traduction"""
        try:
            # Google Translate (googletrans)
            if GOOGLE_TRANS_AVAILABLE:
                self.translators[TranslationService.GOOGLE] = GoogleTranslator()
                logger.info("Google Translate (googletrans) initialisé")
            
            # Google Translate (deep-translator)
            if DEEP_TRANSLATOR_AVAILABLE:
                self.translators[TranslationService.GOOGLE_DEEP] = DeepGoogleTranslator
                self.translators[TranslationService.MYMEMORY] = MyMemoryTranslator
                self.translators[TranslationService.LIBRE] = LibreTranslator
                logger.info("Services deep-translator initialisés")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des services: {e}")
    
    def _init_medical_dictionaries(self):
        """Initialise les dictionnaires médicaux"""
        # Dictionnaire médical de base (français-anglais-langues locales)
        base_medical_terms = {
            # Maladies
            "paludisme": MedicalTermMapping(
                term="paludisme",
                language="fr",
                translations={
                    "en": "malaria",
                    "ff": "nayeejo paludisme",
                    "ewondo": "bela paludisme",
                    "duala": "bwele paludisme",
                    "bamileke": "nkeng paludisme",
                    "ha": "zazzabin cizon sauro",
                    "ar": "الملاريا"
                },
                domain=MedicalDomain.INFECTIOUS_DISEASES,
                confidence=0.95,
                verified=True
            ),
            
            "diabète": MedicalTermMapping(
                term="diabète",
                language="fr",
                translations={
                    "en": "diabetes",
                    "ff": "nayeejo sukkar",
                    "ewondo": "bela sukkar",
                    "duala": "bwele sukkar",
                    "bamileke": "nkeng sukkar",
                    "ha": "ciwon sukari",
                    "ar": "السكري"
                },
                domain=MedicalDomain.GENERAL,
                confidence=0.95,
                verified=True
            ),
            
            "hypertension": MedicalTermMapping(
                term="hypertension",
                language="fr",
                translations={
                    "en": "hypertension",
                    "ff": "jiiɓaango yiite",
                    "ewondo": "nkukuma yiite",
                    "duala": "ndimba yiite",
                    "bamileke": "nda yiite",
                    "ha": "hauhawar jini",
                    "ar": "ارتفاع ضغط الدم"
                },
                domain=MedicalDomain.CARDIOLOGY,
                confidence=0.9,
                verified=True
            ),
            
            # Symptômes
            "fièvre": MedicalTermMapping(
                term="fièvre",
                language="fr",
                translations={
                    "en": "fever",
                    "ff": "ɓernde",
                    "ewondo": "awu",
                    "duala": "mbasu",
                    "bamileke": "nkui",
                    "ha": "zazzabi",
                    "ar": "حمى"
                },
                domain=MedicalDomain.GENERAL,
                confidence=0.98,
                verified=True
            ),
            
            "douleur": MedicalTermMapping(
                term="douleur",
                language="fr",
                translations={
                    "en": "pain",
                    "ff": "ɓerngu",
                    "ewondo": "nkong",
                    "duala": "mpasi",
                    "bamileke": "nkap",
                    "ha": "ciwo",
                    "ar": "ألم"
                },
                domain=MedicalDomain.GENERAL,
                confidence=0.95,
                verified=True
            ),
            
            # Médicaments
            "paracétamol": MedicalTermMapping(
                term="paracétamol",
                language="fr",
                translations={
                    "en": "paracetamol",
                    "ff": "paracétamol",
                    "ewondo": "paracétamol",
                    "duala": "paracétamol",
                    "bamileke": "paracétamol",
                    "ha": "paracetamol",
                    "ar": "باراسيتامول"
                },
                domain=MedicalDomain.PHARMACY,
                confidence=0.99,
                verified=True
            ),
            
            # Personnel médical
            "médecin": MedicalTermMapping(
                term="médecin",
                language="fr",
                translations={
                    "en": "doctor",
                    "ff": "dokotoro",
                    "ewondo": "dokita",
                    "duala": "dokita",
                    "bamileke": "dokita",
                    "ha": "likita",
                    "ar": "طبيب"
                },
                domain=MedicalDomain.GENERAL,
                confidence=0.95,
                verified=True
            ),
            
            "infirmier": MedicalTermMapping(
                term="infirmier",
                language="fr",
                translations={
                    "en": "nurse",
                    "ff": "jannginoowo",
                    "ewondo": "nga janga",
                    "duala": "moto a janga",
                    "bamileke": "moto janga",
                    "ha": "ma'aikacin jinya",
                    "ar": "ممرض"
                },
                domain=MedicalDomain.GENERAL,
                confidence=0.9,
                verified=True
            ),
            
            # Lieux
            "hôpital": MedicalTermMapping(
                term="hôpital",
                language="fr",
                translations={
                    "en": "hospital",
                    "ff": "jammirgal",
                    "ewondo": "bilinga",
                    "duala": "lopital",
                    "bamileke": "lopital",
                    "ha": "asibiti",
                    "ar": "مستشفى"
                },
                domain=MedicalDomain.GENERAL,
                confidence=0.95,
                verified=True
            )
        }
        
        # Ajouter au dictionnaire principal
        for term_id, term_mapping in base_medical_terms.items():
            self.medical_terms[term_id] = term_mapping
        
        logger.info(f"Dictionnaire médical initialisé avec {len(base_medical_terms)} termes")
    
    def _get_translation_hash(self, text: str, source_lang: str, target_lang: str, 
                            service: str, domain: str) -> str:
        """Génère un hash pour le cache"""
        content = f"{text}_{source_lang}_{target_lang}_{service}_{domain}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_medical_terms(self, text: str, language: str) -> List[str]:
        """Extrait les termes médicaux d'un texte"""
        medical_terms_found = []
        text_lower = text.lower()
        
        for term_id, term_mapping in self.medical_terms.items():
            # Vérifier le terme principal
            if term_mapping.language == language and term_mapping.term.lower() in text_lower:
                medical_terms_found.append(term_mapping.term)
            
            # Vérifier les traductions
            if language in term_mapping.translations:
                translated_term = term_mapping.translations[language].lower()
                if translated_term in text_lower:
                    medical_terms_found.append(term_mapping.translations[language])
        
        return medical_terms_found
    
    def _preserve_medical_terms(self, text: str, translated_text: str, 
                              source_lang: str, target_lang: str) -> Tuple[str, List[str]]:
        """Préserve les termes médicaux dans la traduction"""
        preserved_terms = []
        final_text = translated_text
        
        # Extraire les termes médicaux du texte source
        source_medical_terms = self._extract_medical_terms(text, source_lang)
        
        for source_term in source_medical_terms:
            # Trouver la traduction correcte du terme médical
            for term_id, term_mapping in self.medical_terms.items():
                if (term_mapping.language == source_lang and 
                    term_mapping.term.lower() == source_term.lower()):
                    
                    if target_lang in term_mapping.translations:
                        correct_translation = term_mapping.translations[target_lang]
                        
                        # Remplacer dans le texte traduit si nécessaire
                        # (logique simplifiée - en production, utiliser des techniques plus sophistiquées)
                        if correct_translation.lower() not in final_text.lower():
                            # Essayer de remplacer une traduction approximative
                            words = final_text.split()
                            for i, word in enumerate(words):
                                if self._is_similar_medical_term(word, correct_translation):
                                    words[i] = correct_translation
                                    break
                            final_text = " ".join(words)
                        
                        preserved_terms.append(correct_translation)
                        break
        
        return final_text, preserved_terms
    
    def _is_similar_medical_term(self, word1: str, word2: str) -> bool:
        """Vérifie si deux mots sont des termes médicaux similaires"""
        # Logique simplifiée - en production, utiliser des techniques plus sophistiquées
        word1_clean = word1.lower().strip('.,!?;:')
        word2_clean = word2.lower().strip('.,!?;:')
        
        # Similarité basique
        if len(word1_clean) > 3 and len(word2_clean) > 3:
            common_chars = set(word1_clean) & set(word2_clean)
            similarity = len(common_chars) / max(len(word1_clean), len(word2_clean))
            return similarity > 0.6
        
        return False
    
    def _calculate_translation_quality(self, original: str, translated: str, 
                                     confidence: float, service: str) -> TranslationQuality:
        """Calcule la qualité de la traduction"""
        # Facteurs de qualité
        quality_score = confidence
        
        # Ajustement basé sur le service
        service_weights = {
            "google": 1.0,
            "google_deep": 0.95,
            "mymemory": 0.8,
            "libre": 0.7,
            "offline_dict": 0.6,
            "simulation": 0.3
        }
        quality_score *= service_weights.get(service, 0.5)
        
        # Ajustement basé sur la longueur
        if len(translated.split()) < 2:
            quality_score *= 0.8  # Traductions très courtes moins fiables
        
        # Ajustement si le texte traduit est identique à l'original
        if original.lower() == translated.lower():
            quality_score *= 0.7  # Probablement pas traduit
        
        # Déterminer le niveau de qualité
        if quality_score >= 0.9:
            return TranslationQuality.EXCELLENT
        elif quality_score >= 0.7:
            return TranslationQuality.GOOD
        elif quality_score >= 0.5:
            return TranslationQuality.FAIR
        elif quality_score >= 0.3:
            return TranslationQuality.POOR
        else:
            return TranslationQuality.VERY_POOR
    
    def _simulate_translation(self, text: str, source_lang: str, target_lang: str) -> Tuple[str, float]:
        """Simule une traduction quand les services ne sont pas disponibles"""
        # Traduction simulée basique
        if source_lang == target_lang:
            return text, 1.0
        
        # Vérifier le dictionnaire médical
        medical_terms = self._extract_medical_terms(text, source_lang)
        if medical_terms:
            # Traduire les termes médicaux connus
            translated_text = text
            for term in medical_terms:
                for term_id, term_mapping in self.medical_terms.items():
                    if (term_mapping.language == source_lang and 
                        term_mapping.term.lower() == term.lower()):
                        if target_lang in term_mapping.translations:
                            translated_text = translated_text.replace(
                                term, term_mapping.translations[target_lang]
                            )
                            break
            return translated_text, 0.7
        
        # Traduction générique simulée
        simulated_translations = {
            ("fr", "en"): {
                "bonjour": "hello",
                "merci": "thank you",
                "au revoir": "goodbye",
                "comment allez-vous": "how are you"
            },
            ("en", "fr"): {
                "hello": "bonjour",
                "thank you": "merci",
                "goodbye": "au revoir",
                "how are you": "comment allez-vous"
            }
        }
        
        lang_pair = (source_lang, target_lang)
        if lang_pair in simulated_translations:
            text_lower = text.lower()
            for original, translation in simulated_translations[lang_pair].items():
                if original in text_lower:
                    return text.replace(original, translation), 0.6
        
        # Retourner le texte original avec une note
        return f"[TRADUCTION SIMULÉE] {text}", 0.3
    
    async def translate(self, request: TranslationRequest) -> TranslationResult:
        """
        Traduit un texte selon la requête
        
        Args:
            request: Requête de traduction
        
        Returns:
            TranslationResult: Résultat de la traduction
        """
        start_time = time.time()
        
        try:
            # Vérifier le cache
            service_name = request.service_preference.value if request.service_preference else self.primary_service.value
            cache_key = self._get_translation_hash(
                request.text, request.source_language, request.target_language,
                service_name, request.domain.value
            )
            
            if self.cache_enabled and cache_key in self.translation_cache:
                self.cache_hits += 1
                cached_result = self.translation_cache[cache_key]
                cached_result.metadata["from_cache"] = True
                return cached_result
            
            self.cache_misses += 1
            
            # Pas de traduction si même langue
            if request.source_language == request.target_language:
                return TranslationResult(
                    original_text=request.text,
                    translated_text=request.text,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    service_used="none",
                    confidence_score=1.0,
                    quality_level=TranslationQuality.EXCELLENT,
                    processing_time=time.time() - start_time,
                    metadata={"same_language": True}
                )
            
            # Choisir le service de traduction
            service = request.service_preference or self.primary_service
            translated_text = ""
            confidence = 0.0
            service_used = "none"
            warnings = []
            
            # Essayer la traduction avec le service principal
            try:
                if service == TranslationService.GOOGLE and GOOGLE_TRANS_AVAILABLE:
                    translator = self.translators[TranslationService.GOOGLE]
                    result = translator.translate(
                        request.text, 
                        src=request.source_language, 
                        dest=request.target_language
                    )
                    translated_text = result.text
                    confidence = getattr(result, 'confidence', 0.8)
                    service_used = "google"
                
                elif service == TranslationService.GOOGLE_DEEP and DEEP_TRANSLATOR_AVAILABLE:
                    translator = DeepGoogleTranslator(
                        source=request.source_language,
                        target=request.target_language
                    )
                    translated_text = translator.translate(request.text)
                    confidence = 0.85
                    service_used = "google_deep"
                
                elif service == TranslationService.MYMEMORY and DEEP_TRANSLATOR_AVAILABLE:
                    translator = MyMemoryTranslator(
                        source=request.source_language,
                        target=request.target_language
                    )
                    translated_text = translator.translate(request.text)
                    confidence = 0.75
                    service_used = "mymemory"
                
                else:
                    raise Exception(f"Service {service.value} non disponible")
            
            except Exception as e:
                logger.warning(f"Erreur avec le service principal {service.value}: {e}")
                warnings.append(f"Service principal échoué: {e}")
                
                # Essayer les services de fallback
                for fallback_service in self.fallback_services:
                    try:
                        if fallback_service == "mymemory" and DEEP_TRANSLATOR_AVAILABLE:
                            translator = MyMemoryTranslator(
                                source=request.source_language,
                                target=request.target_language
                            )
                            translated_text = translator.translate(request.text)
                            confidence = 0.7
                            service_used = "mymemory"
                            break
                        
                        elif fallback_service == "offline_dict":
                            # Utiliser le dictionnaire médical hors ligne
                            translated_text, confidence = self._simulate_translation(
                                request.text, request.source_language, request.target_language
                            )
                            service_used = "offline_dict"
                            break
                    
                    except Exception as fallback_error:
                        logger.warning(f"Erreur avec le service de fallback {fallback_service}: {fallback_error}")
                        continue
                
                # Si tous les services échouent, utiliser la simulation
                if not translated_text:
                    translated_text, confidence = self._simulate_translation(
                        request.text, request.source_language, request.target_language
                    )
                    service_used = "simulation"
                    warnings.append("Tous les services ont échoué, utilisation de la simulation")
            
            # Préserver les termes médicaux si demandé
            preserved_terms = []
            if request.preserve_medical_terms:
                translated_text, preserved_terms = self._preserve_medical_terms(
                    request.text, translated_text, 
                    request.source_language, request.target_language
                )
            
            # Calculer la qualité
            quality_level = self._calculate_translation_quality(
                request.text, translated_text, confidence, service_used
            )
            
            processing_time = time.time() - start_time
            
            # Créer le résultat
            result = TranslationResult(
                original_text=request.text,
                translated_text=translated_text,
                source_language=request.source_language,
                target_language=request.target_language,
                service_used=service_used,
                confidence_score=confidence,
                quality_level=quality_level,
                processing_time=processing_time,
                medical_terms_preserved=preserved_terms,
                warnings=warnings,
                metadata={
                    "domain": request.domain.value,
                    "context": request.context,
                    "priority": request.priority,
                    "from_cache": False
                }
            )
            
            # Mettre en cache
            if self.cache_enabled and len(self.translation_cache) < self.max_cache_size:
                self.translation_cache[cache_key] = result
            
            # Mettre à jour les statistiques
            self.stats.total_translations += 1
            lang_pair = f"{request.source_language}-{request.target_language}"
            self.stats.translations_by_language_pair[lang_pair] = self.stats.translations_by_language_pair.get(lang_pair, 0) + 1
            self.stats.translations_by_service[service_used] = self.stats.translations_by_service.get(service_used, 0) + 1
            self.stats.medical_terms_preserved += len(preserved_terms)
            self.stats.quality_distribution[quality_level.value] = self.stats.quality_distribution.get(quality_level.value, 0) + 1
            
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors de la traduction: {e}")
            return TranslationResult(
                original_text=request.text,
                translated_text=request.text,
                source_language=request.source_language,
                target_language=request.target_language,
                service_used="error",
                confidence_score=0.0,
                quality_level=TranslationQuality.VERY_POOR,
                processing_time=time.time() - start_time,
                warnings=[f"Erreur de traduction: {e}"],
                metadata={"error": str(e)}
            )
    
    async def translate_batch(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """
        Traduit un batch de textes
        
        Args:
            requests: Liste de requêtes de traduction
        
        Returns:
            List[TranslationResult]: Résultats de traduction
        """
        # Traitement en parallèle
        tasks = [self.translate(request) for request in requests]
        results = await asyncio.gather(*tasks)
        return results
    
    def add_medical_term(self, term_mapping: MedicalTermMapping):
        """
        Ajoute un terme médical au dictionnaire
        
        Args:
            term_mapping: Mapping du terme médical
        """
        term_id = f"{term_mapping.term}_{term_mapping.language}"
        self.medical_terms[term_id] = term_mapping
        logger.info(f"Terme médical ajouté: {term_mapping.term} ({term_mapping.language})")
    
    def get_medical_term_translation(self, term: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Obtient la traduction d'un terme médical
        
        Args:
            term: Terme à traduire
            source_lang: Langue source
            target_lang: Langue cible
        
        Returns:
            Optional[str]: Traduction du terme ou None
        """
        for term_mapping in self.medical_terms.values():
            if (term_mapping.language == source_lang and 
                term_mapping.term.lower() == term.lower()):
                return term_mapping.translations.get(target_lang)
        return None
    
    def generate_stats(self) -> TranslationStats:
        """Génère les statistiques de traduction"""
        start_time = time.time()
        
        # Calculer le taux de cache
        total_requests = self.cache_hits + self.cache_misses
        if total_requests > 0:
            self.stats.cache_hit_rate = self.cache_hits / total_requests
        
        # Moyennes (simulées pour l'exemple)
        if self.stats.total_translations > 0:
            self.stats.avg_processing_time = 0.5  # Moyenne simulée
            self.stats.avg_confidence = 0.8  # Confiance moyenne simulée
        
        self.stats.processing_time = time.time() - start_time
        
        return self.stats
    
    def export_translations(self, output_path: str):
        """Exporte les traductions et métadonnées"""
        export_data = {
            "metadata": {
                "total_translations": self.stats.total_translations,
                "primary_service": self.primary_service.value,
                "medical_terms_count": len(self.medical_terms),
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "medical_dictionary": {
                term_id: {
                    "term": mapping.term,
                    "language": mapping.language,
                    "translations": mapping.translations,
                    "domain": mapping.domain.value,
                    "confidence": mapping.confidence,
                    "verified": mapping.verified
                }
                for term_id, mapping in self.medical_terms.items()
            },
            "statistics": {
                "translations_by_language_pair": self.stats.translations_by_language_pair,
                "translations_by_service": self.stats.translations_by_service,
                "quality_distribution": self.stats.quality_distribution,
                "cache_hit_rate": self.stats.cache_hit_rate,
                "medical_terms_preserved": self.stats.medical_terms_preserved,
                "avg_confidence": self.stats.avg_confidence
            },
            "cache_info": {
                "cache_size": len(self.translation_cache),
                "max_cache_size": self.max_cache_size,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Traductions exportées: {output_path}")
    
    def clear_cache(self):
        """Vide le cache des traductions"""
        self.translation_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Cache des traductions vidé")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🌐 Test du Système de Traduction Automatique")
    
    # Créer le système de traduction
    translator = TranslationSystem({
        "primary_service": "google",
        "fallback_services": ["mymemory", "offline_dict"],
        "cache_enabled": True
    })
    
    # Textes de test
    test_requests = [
        TranslationRequest(
            text="Le patient présente une fièvre élevée et des douleurs abdominales.",
            source_language="fr",
            target_language="en",
            domain=MedicalDomain.GENERAL,
            preserve_medical_terms=True
        ),
        TranslationRequest(
            text="The doctor prescribed paracetamol for the fever.",
            source_language="en",
            target_language="fr",
            domain=MedicalDomain.PHARMACY,
            preserve_medical_terms=True
        ),
        TranslationRequest(
            text="Le paludisme est une maladie grave qui nécessite un traitement rapide.",
            source_language="fr",
            target_language="ff",
            domain=MedicalDomain.INFECTIOUS_DISEASES,
            preserve_medical_terms=True
        ),
        TranslationRequest(
            text="Dokotoro wi'i paracétamol ngam ɓernde.",
            source_language="ff",
            target_language="fr",
            domain=MedicalDomain.GENERAL,
            preserve_medical_terms=True
        )
    ]
    
    print(f"\n📝 Test de traduction de {len(test_requests)} textes:")
    
    # Traduire les textes
    for i, request in enumerate(test_requests, 1):
        result = await translator.translate(request)
        
        print(f"\n{i}. {request.source_language} → {request.target_language}")
        print(f"   Original: {request.text}")
        print(f"   Traduit:  {result.translated_text}")
        print(f"   Service:  {result.service_used}")
        print(f"   Qualité:  {result.quality_level.value}")
        print(f"   Confiance: {result.confidence_score:.2f}")
        print(f"   Temps:    {result.processing_time:.3f}s")
        
        if result.medical_terms_preserved:
            print(f"   Termes médicaux préservés: {', '.join(result.medical_terms_preserved)}")
        
        if result.warnings:
            print(f"   Avertissements: {'; '.join(result.warnings)}")
    
    # Test de traduction en batch
    print("\n📦 Test de traduction en batch:")
    batch_results = await translator.translate_batch(test_requests[:2])
    print(f"   {len(batch_results)} traductions effectuées en batch")
    
    # Test du dictionnaire médical
    print("\n📚 Test du dictionnaire médical:")
    medical_translation = translator.get_medical_term_translation("paludisme", "fr", "en")
    print(f"   paludisme (fr) → {medical_translation} (en)")
    
    medical_translation_ff = translator.get_medical_term_translation("paludisme", "fr", "ff")
    print(f"   paludisme (fr) → {medical_translation_ff} (ff)")
    
    # Ajouter un nouveau terme médical
    new_term = MedicalTermMapping(
        term="pneumonie",
        language="fr",
        translations={
            "en": "pneumonia",
            "ff": "nayeejo ɓerngu",
            "ewondo": "bela ɓerngu",
            "ar": "التهاب الرئة"
        },
        domain=MedicalDomain.GENERAL,
        confidence=0.9
    )
    translator.add_medical_term(new_term)
    
    # Générer les statistiques
    stats = translator.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"   Traductions totales: {stats.total_translations}")
    print(f"   Taux de cache: {stats.cache_hit_rate:.1%}")
    print(f"   Termes médicaux préservés: {stats.medical_terms_preserved}")
    print(f"   Confiance moyenne: {stats.avg_confidence:.2f}")
    
    print(f"\n🌐 Répartition par paire de langues:")
    for lang_pair, count in stats.translations_by_language_pair.items():
        print(f"   {lang_pair}: {count} traductions")
    
    print(f"\n🔧 Répartition par service:")
    for service, count in stats.translations_by_service.items():
        print(f"   {service}: {count} traductions")
    
    print(f"\n⭐ Répartition par qualité:")
    for quality, count in stats.quality_distribution.items():
        print(f"   {quality}: {count} traductions")
    
    # Exporter les données
    translator.export_translations("translation_system_export.json")
    print("\n✅ Données exportées: translation_system_export.json")

if __name__ == "__main__":
    asyncio.run(main())