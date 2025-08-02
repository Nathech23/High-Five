#!/usr/bin/env python3
"""
Chunking Optimisé Multilingue

Objectif 14: Optimiser chunking pour différentes langues

Ce module implémente un système de chunking intelligent adapté aux
spécificités linguistiques de chaque langue, incluant les langues
camerounaises et les textes médicaux.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import re
import logging
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from collections import defaultdict, Counter
import time
import math

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    logger.warning("NLTK non disponible")
    NLTK_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    logger.warning("spaCy non disponible")
    SPACY_AVAILABLE = False

class ChunkingStrategy(Enum):
    """Stratégies de chunking"""
    FIXED_SIZE = "fixed_size"  # Taille fixe
    SENTENCE_BASED = "sentence_based"  # Basé sur les phrases
    PARAGRAPH_BASED = "paragraph_based"  # Basé sur les paragraphes
    SEMANTIC_BASED = "semantic_based"  # Basé sur la sémantique
    MEDICAL_STRUCTURE = "medical_structure"  # Structure médicale
    LANGUAGE_ADAPTIVE = "language_adaptive"  # Adaptatif par langue
    HYBRID = "hybrid"  # Combinaison de stratégies

class LanguageFamily(Enum):
    """Familles de langues"""
    ROMANCE = "romance"  # Français, espagnol, italien
    GERMANIC = "germanic"  # Anglais, allemand
    NIGER_CONGO = "niger_congo"  # Langues camerounaises
    AFROASIATIC = "afroasiatic"  # Arabe, hausa
    SINO_TIBETAN = "sino_tibetan"  # Chinois
    OTHER = "other"

class TextType(Enum):
    """Types de texte médical"""
    CLINICAL_NOTE = "clinical_note"  # Note clinique
    RESEARCH_PAPER = "research_paper"  # Article de recherche
    PROTOCOL = "protocol"  # Protocole de soins
    PATIENT_INFO = "patient_info"  # Information patient
    DRUG_INFO = "drug_info"  # Information médicament
    DIAGNOSTIC = "diagnostic"  # Diagnostic
    TREATMENT = "treatment"  # Traitement
    GENERAL = "general"  # Général

@dataclass
class LanguageConfig:
    """Configuration spécifique à une langue"""
    language: str
    family: LanguageFamily
    sentence_separators: List[str]
    paragraph_separators: List[str]
    word_separators: List[str]
    stopwords: Set[str]
    avg_word_length: float
    avg_sentence_length: int  # En mots
    chunk_size_multiplier: float  # Multiplicateur pour la taille de chunk
    overlap_ratio: float  # Ratio de chevauchement
    medical_indicators: List[str]  # Indicateurs de contenu médical
    punctuation_patterns: List[str]  # Patterns de ponctuation
    special_rules: Dict[str, Any]  # Règles spéciales

@dataclass
class Chunk:
    """Chunk de texte"""
    id: str
    content: str
    language: str
    start_position: int
    end_position: int
    word_count: int
    sentence_count: int
    chunk_index: int
    overlap_with_previous: int  # Nombre de caractères de chevauchement
    overlap_with_next: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    medical_terms: List[str] = field(default_factory=list)
    key_phrases: List[str] = field(default_factory=list)
    semantic_coherence: float = 0.0
    readability_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ChunkingResult:
    """Résultat du chunking"""
    chunks: List[Chunk]
    total_chunks: int
    total_words: int
    total_characters: int
    avg_chunk_size: float
    avg_overlap: float
    strategy_used: str
    language: str
    processing_time: float
    quality_score: float  # Score de qualité du chunking
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChunkingStats:
    """Statistiques de chunking"""
    total_documents_processed: int = 0
    total_chunks_created: int = 0
    chunks_by_language: Dict[str, int] = field(default_factory=dict)
    chunks_by_strategy: Dict[str, int] = field(default_factory=dict)
    avg_chunk_size_by_language: Dict[str, float] = field(default_factory=dict)
    avg_processing_time: float = 0.0
    avg_quality_score: float = 0.0
    processing_time: float = 0.0

class OptimizedChunking:
    """
    Système de chunking optimisé multilingue
    
    Objectif couvert:
    - 14. Optimiser chunking pour différentes langues
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = ChunkingStats()
        
        # Configuration par langue
        self.language_configs: Dict[str, LanguageConfig] = {}
        
        # Cache de chunking
        self.chunking_cache: Dict[str, ChunkingResult] = {}
        self.max_cache_size = self.config.get("max_cache_size", 100)
        
        # Configuration par défaut
        self.default_chunk_size = self.config.get("default_chunk_size", 512)
        self.default_overlap = self.config.get("default_overlap", 50)
        self.min_chunk_size = self.config.get("min_chunk_size", 100)
        self.max_chunk_size = self.config.get("max_chunk_size", 1000)
        
        # Initialiser les configurations de langues
        self._init_language_configs()
        
        # Patterns médicaux
        self._init_medical_patterns()
        
        logger.info("Système de chunking optimisé initialisé")
    
    def _init_language_configs(self):
        """Initialise les configurations spécifiques aux langues"""
        
        # Français
        self.language_configs["fr"] = LanguageConfig(
            language="fr",
            family=LanguageFamily.ROMANCE,
            sentence_separators=[".", "!", "?", ";"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"le", "la", "les", "de", "du", "des", "et", "est", "une", "un", "dans", "pour", "avec", "sur", "par", "ce", "cette", "ces", "que", "qui", "dont", "où"},
            avg_word_length=5.2,
            avg_sentence_length=15,
            chunk_size_multiplier=1.0,
            overlap_ratio=0.1,
            medical_indicators=["patient", "diagnostic", "traitement", "symptôme", "maladie", "médecin", "hôpital", "clinique"],
            punctuation_patterns=[r"\.", r"\!", r"\?", r";", r":"],
            special_rules={"preserve_medical_terms": True, "respect_sentence_boundaries": True}
        )
        
        # Anglais
        self.language_configs["en"] = LanguageConfig(
            language="en",
            family=LanguageFamily.GERMANIC,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"the", "and", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by", "a", "an", "this", "that", "these", "those"},
            avg_word_length=4.7,
            avg_sentence_length=12,
            chunk_size_multiplier=0.9,
            overlap_ratio=0.1,
            medical_indicators=["patient", "diagnosis", "treatment", "symptom", "disease", "doctor", "hospital", "clinic"],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={"preserve_medical_terms": True, "respect_sentence_boundaries": True}
        )
        
        # Fulfulde
        self.language_configs["ff"] = LanguageConfig(
            language="ff",
            family=LanguageFamily.NIGER_CONGO,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"ko", "e", "o", "ɗo", "ɓe", "mo", "no", "wo", "ngo", "ɗum", "ɗon", "ɗi"},
            avg_word_length=6.1,
            avg_sentence_length=10,
            chunk_size_multiplier=1.2,
            overlap_ratio=0.15,
            medical_indicators=["jannginoowo", "dokotoro", "jammirgal", "nayeejo", "ɓernde"],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={"preserve_medical_terms": True, "agglutinative_aware": True}
        )
        
        # Ewondo
        self.language_configs["ewondo"] = LanguageConfig(
            language="ewondo",
            family=LanguageFamily.NIGER_CONGO,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"a", "e", "o", "na", "ne", "nga", "nge", "be", "ba", "ye", "wa"},
            avg_word_length=5.8,
            avg_sentence_length=9,
            chunk_size_multiplier=1.3,
            overlap_ratio=0.15,
            medical_indicators=["dokita", "nga janga", "nda janga", "bela", "awu"],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={"preserve_medical_terms": True, "tonal_aware": True}
        )
        
        # Duala
        self.language_configs["duala"] = LanguageConfig(
            language="duala",
            family=LanguageFamily.NIGER_CONGO,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"a", "e", "o", "na", "ne", "moto", "ba", "be", "wa", "we"},
            avg_word_length=5.5,
            avg_sentence_length=8,
            chunk_size_multiplier=1.4,
            overlap_ratio=0.2,
            medical_indicators=["dokita", "moto a janga", "nda janga", "bwele", "mbasu"],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={"preserve_medical_terms": True, "coastal_bantu_rules": True}
        )
        
        # Bamiléké
        self.language_configs["bamileke"] = LanguageConfig(
            language="bamileke",
            family=LanguageFamily.NIGER_CONGO,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"a", "e", "o", "na", "ne", "moto", "ba", "be", "wa", "nkeng"},
            avg_word_length=5.9,
            avg_sentence_length=9,
            chunk_size_multiplier=1.3,
            overlap_ratio=0.15,
            medical_indicators=["dokita", "moto janga", "nda janga", "nkeng", "nkui"],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={"preserve_medical_terms": True, "grassfields_rules": True}
        )
        
        # Hausa
        self.language_configs["ha"] = LanguageConfig(
            language="ha",
            family=LanguageFamily.AFROASIATIC,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"da", "na", "ya", "ta", "ka", "ba", "su", "mu", "ku", "za", "mai"},
            avg_word_length=4.8,
            avg_sentence_length=11,
            chunk_size_multiplier=1.1,
            overlap_ratio=0.12,
            medical_indicators=["likita", "dokita", "asibiti", "gidan magani", "zazzabi"],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={"preserve_medical_terms": True, "semitic_aware": True}
        )
        
        # Arabe
        self.language_configs["ar"] = LanguageConfig(
            language="ar",
            family=LanguageFamily.AFROASIATIC,
            sentence_separators=[".", "!", "?", "؟", "!"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords={"في", "من", "إلى", "على", "هذا", "هذه", "التي", "الذي", "أن", "كان", "كانت"},
            avg_word_length=4.2,
            avg_sentence_length=13,
            chunk_size_multiplier=0.8,
            overlap_ratio=0.1,
            medical_indicators=["طبيب", "مستشفى", "مرض", "علاج", "تشخيص", "مريض"],
            punctuation_patterns=[r"\.", r"\!", r"\?", r"؟"],
            special_rules={"preserve_medical_terms": True, "rtl_text": True, "root_based": True}
        )
        
        logger.info(f"Configurations de langues initialisées: {len(self.language_configs)} langues")
    
    def _init_medical_patterns(self):
        """Initialise les patterns médicaux pour la détection de structure"""
        self.medical_patterns = {
            "section_headers": [
                r"^(DIAGNOSTIC|TRAITEMENT|SYMPTÔMES|ANTÉCÉDENTS|EXAMEN|CONCLUSION)\s*:?",
                r"^(DIAGNOSIS|TREATMENT|SYMPTOMS|HISTORY|EXAMINATION|CONCLUSION)\s*:?",
                r"^(HISTOIRE|PRÉSENTATION|PLAN|SUIVI)\s*:?",
                r"^(HISTORY|PRESENTATION|PLAN|FOLLOW-UP)\s*:?"
            ],
            "medical_lists": [
                r"^\s*[-•*]\s+",  # Listes à puces
                r"^\s*\d+[.):]\s+",  # Listes numérotées
                r"^\s*[a-z][.):]\s+"  # Listes alphabétiques
            ],
            "dosage_patterns": [
                r"\d+\s*(mg|g|ml|l|UI|mcg)\b",
                r"\d+\s*fois\s*par\s*(jour|semaine|mois)",
                r"\d+\s*times\s*(daily|weekly|monthly)"
            ],
            "vital_signs": [
                r"\b(TA|BP|FC|HR|FR|RR|T°|Temp)\s*[:=]?\s*\d+",
                r"\b\d+/\d+\s*(mmHg|bpm)\b",
                r"\b\d+°C\b"
            ]
        }
    
    def _detect_language(self, text: str) -> str:
        """Détecte la langue d'un texte"""
        # Détection simple basée sur des mots-clés caractéristiques
        language_indicators = {
            "fr": ["le", "la", "les", "de", "du", "des", "et", "est", "une", "un"],
            "en": ["the", "and", "is", "are", "of", "in", "to", "for"],
            "ff": ["ko", "ɗo", "ɓe", "ɗum", "ɗon", "ɗi", "ngo"],
            "ewondo": ["nga", "nge", "bela", "awu", "nlôm"],
            "duala": ["moto", "bwele", "mbasu", "lopital"],
            "bamileke": ["nkeng", "nkui", "dokita"],
            "ha": ["da", "na", "ya", "ta", "ka", "ba", "likita"],
            "ar": ["في", "من", "إلى", "على", "هذا", "الذي", "طبيب"]
        }
        
        text_lower = text.lower()
        scores = {}
        
        for lang, indicators in language_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                scores[lang] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "fr"  # Par défaut
    
    def _get_language_config(self, language: str) -> LanguageConfig:
        """Récupère la configuration pour une langue"""
        if language in self.language_configs:
            return self.language_configs[language]
        
        # Configuration par défaut pour les langues non supportées
        return LanguageConfig(
            language=language,
            family=LanguageFamily.OTHER,
            sentence_separators=[".", "!", "?"],
            paragraph_separators=["\n\n", "\r\n\r\n"],
            word_separators=[" ", "\t", "\n"],
            stopwords=set(),
            avg_word_length=5.0,
            avg_sentence_length=12,
            chunk_size_multiplier=1.0,
            overlap_ratio=0.1,
            medical_indicators=[],
            punctuation_patterns=[r"\.", r"\!", r"\?"],
            special_rules={}
        )
    
    def _split_into_sentences(self, text: str, language_config: LanguageConfig) -> List[str]:
        """Divise le texte en phrases selon la langue"""
        if NLTK_AVAILABLE:
            try:
                # Utiliser NLTK si disponible
                if language_config.language == "fr":
                    return sent_tokenize(text, language="french")
                elif language_config.language == "en":
                    return sent_tokenize(text, language="english")
            except Exception as e:
                logger.warning(f"Erreur NLTK pour {language_config.language}: {e}")
        
        # Méthode de fallback basée sur les séparateurs
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            if char in language_config.sentence_separators:
                # Vérifier si c'est vraiment la fin d'une phrase
                stripped = current_sentence.strip()
                if len(stripped) > 3:  # Éviter les phrases trop courtes
                    sentences.append(stripped)
                    current_sentence = ""
        
        # Ajouter la dernière phrase si elle existe
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _split_into_paragraphs(self, text: str, language_config: LanguageConfig) -> List[str]:
        """Divise le texte en paragraphes"""
        paragraphs = []
        
        for separator in language_config.paragraph_separators:
            if separator in text:
                paragraphs = text.split(separator)
                break
        
        if not paragraphs:
            paragraphs = [text]
        
        # Nettoyer et filtrer les paragraphes vides
        cleaned_paragraphs = []
        for para in paragraphs:
            cleaned = para.strip()
            if cleaned:
                cleaned_paragraphs.append(cleaned)
        
        return cleaned_paragraphs
    
    def _extract_medical_terms(self, text: str, language_config: LanguageConfig) -> List[str]:
        """Extrait les termes médicaux du texte"""
        medical_terms = []
        text_lower = text.lower()
        
        # Rechercher les indicateurs médicaux de la langue
        for indicator in language_config.medical_indicators:
            if indicator.lower() in text_lower:
                medical_terms.append(indicator)
        
        # Rechercher les patterns médicaux
        for pattern_type, patterns in self.medical_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                medical_terms.extend(matches)
        
        return list(set(medical_terms))
    
    def _calculate_semantic_coherence(self, chunk_text: str, language_config: LanguageConfig) -> float:
        """Calcule la cohérence sémantique d'un chunk"""
        # Méthode simplifiée basée sur la répétition de mots-clés
        words = re.findall(r'\b\w+\b', chunk_text.lower())
        
        # Filtrer les mots vides
        content_words = [word for word in words if word not in language_config.stopwords and len(word) > 2]
        
        if len(content_words) < 2:
            return 0.5
        
        # Calculer la diversité lexicale
        unique_words = set(content_words)
        lexical_diversity = len(unique_words) / len(content_words)
        
        # Calculer la répétition de termes importants
        word_counts = Counter(content_words)
        repeated_words = sum(1 for count in word_counts.values() if count > 1)
        repetition_score = repeated_words / len(unique_words) if unique_words else 0
        
        # Score de cohérence combiné
        coherence = (lexical_diversity * 0.3) + (repetition_score * 0.7)
        return min(coherence, 1.0)
    
    def _calculate_readability_score(self, chunk_text: str, language_config: LanguageConfig) -> float:
        """Calcule le score de lisibilité d'un chunk"""
        sentences = self._split_into_sentences(chunk_text, language_config)
        words = re.findall(r'\b\w+\b', chunk_text)
        
        if not sentences or not words:
            return 0.5
        
        # Métriques de base
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Score basé sur les moyennes de la langue
        sentence_score = 1.0 - abs(avg_sentence_length - language_config.avg_sentence_length) / language_config.avg_sentence_length
        word_score = 1.0 - abs(avg_word_length - language_config.avg_word_length) / language_config.avg_word_length
        
        # Normaliser les scores
        sentence_score = max(0.0, min(1.0, sentence_score))
        word_score = max(0.0, min(1.0, word_score))
        
        return (sentence_score + word_score) / 2
    
    def _get_optimal_chunk_size(self, text: str, language_config: LanguageConfig, 
                              strategy: ChunkingStrategy) -> int:
        """Détermine la taille optimale de chunk pour le texte et la langue"""
        base_size = self.default_chunk_size
        
        # Ajuster selon la langue
        adjusted_size = int(base_size * language_config.chunk_size_multiplier)
        
        # Ajuster selon la stratégie
        if strategy == ChunkingStrategy.SENTENCE_BASED:
            # Estimer le nombre de phrases pour atteindre la taille cible
            sentences = self._split_into_sentences(text[:1000], language_config)  # Échantillon
            if sentences:
                avg_sentence_chars = sum(len(s) for s in sentences) / len(sentences)
                target_sentences = max(1, int(adjusted_size / avg_sentence_chars))
                adjusted_size = int(target_sentences * avg_sentence_chars)
        
        elif strategy == ChunkingStrategy.PARAGRAPH_BASED:
            # Ajuster pour les paragraphes
            adjusted_size = int(adjusted_size * 1.5)  # Les paragraphes sont généralement plus longs
        
        elif strategy == ChunkingStrategy.MEDICAL_STRUCTURE:
            # Ajuster pour la structure médicale
            adjusted_size = int(adjusted_size * 0.8)  # Chunks plus petits pour préserver la structure
        
        # Respecter les limites
        return max(self.min_chunk_size, min(self.max_chunk_size, adjusted_size))
    
    def _get_optimal_overlap(self, language_config: LanguageConfig, strategy: ChunkingStrategy) -> int:
        """Détermine le chevauchement optimal"""
        base_overlap = self.default_overlap
        
        # Ajuster selon la langue
        adjusted_overlap = int(base_overlap * (1 + language_config.overlap_ratio))
        
        # Ajuster selon la stratégie
        if strategy == ChunkingStrategy.SEMANTIC_BASED:
            adjusted_overlap = int(adjusted_overlap * 1.5)  # Plus de chevauchement pour la cohérence
        elif strategy == ChunkingStrategy.MEDICAL_STRUCTURE:
            adjusted_overlap = int(adjusted_overlap * 0.5)  # Moins de chevauchement pour préserver la structure
        
        return adjusted_overlap
    
    def chunk_text(self, text: str, language: Optional[str] = None, 
                  strategy: ChunkingStrategy = ChunkingStrategy.LANGUAGE_ADAPTIVE,
                  text_type: TextType = TextType.GENERAL,
                  custom_chunk_size: Optional[int] = None,
                  custom_overlap: Optional[int] = None) -> ChunkingResult:
        """
        Divise un texte en chunks optimisés
        
        Args:
            text: Texte à diviser
            language: Langue du texte (auto-détection si None)
            strategy: Stratégie de chunking
            text_type: Type de texte médical
            custom_chunk_size: Taille de chunk personnalisée
            custom_overlap: Chevauchement personnalisé
        
        Returns:
            ChunkingResult: Résultat du chunking
        """
        start_time = time.time()
        
        try:
            # Détecter la langue si nécessaire
            if not language:
                language = self._detect_language(text)
            
            # Récupérer la configuration de langue
            language_config = self._get_language_config(language)
            
            # Déterminer les paramètres optimaux
            chunk_size = custom_chunk_size or self._get_optimal_chunk_size(text, language_config, strategy)
            overlap = custom_overlap or self._get_optimal_overlap(language_config, strategy)
            
            # Effectuer le chunking selon la stratégie
            if strategy == ChunkingStrategy.FIXED_SIZE:
                chunks = self._chunk_fixed_size(text, chunk_size, overlap, language_config)
            elif strategy == ChunkingStrategy.SENTENCE_BASED:
                chunks = self._chunk_sentence_based(text, chunk_size, overlap, language_config)
            elif strategy == ChunkingStrategy.PARAGRAPH_BASED:
                chunks = self._chunk_paragraph_based(text, chunk_size, overlap, language_config)
            elif strategy == ChunkingStrategy.MEDICAL_STRUCTURE:
                chunks = self._chunk_medical_structure(text, chunk_size, overlap, language_config, text_type)
            elif strategy == ChunkingStrategy.LANGUAGE_ADAPTIVE:
                chunks = self._chunk_language_adaptive(text, chunk_size, overlap, language_config, text_type)
            elif strategy == ChunkingStrategy.HYBRID:
                chunks = self._chunk_hybrid(text, chunk_size, overlap, language_config, text_type)
            else:
                chunks = self._chunk_language_adaptive(text, chunk_size, overlap, language_config, text_type)
            
            # Calculer les métriques
            processing_time = time.time() - start_time
            total_words = len(re.findall(r'\b\w+\b', text))
            total_characters = len(text)
            avg_chunk_size = sum(len(chunk.content) for chunk in chunks) / len(chunks) if chunks else 0
            avg_overlap = sum(chunk.overlap_with_previous for chunk in chunks) / len(chunks) if chunks else 0
            
            # Calculer le score de qualité
            quality_score = self._calculate_chunking_quality(chunks, language_config)
            
            # Créer le résultat
            result = ChunkingResult(
                chunks=chunks,
                total_chunks=len(chunks),
                total_words=total_words,
                total_characters=total_characters,
                avg_chunk_size=avg_chunk_size,
                avg_overlap=avg_overlap,
                strategy_used=strategy.value,
                language=language,
                processing_time=processing_time,
                quality_score=quality_score,
                metadata={
                    "chunk_size_used": chunk_size,
                    "overlap_used": overlap,
                    "text_type": text_type.value,
                    "language_family": language_config.family.value
                }
            )
            
            # Mettre à jour les statistiques
            self._update_chunking_stats(result, language, strategy)
            
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors du chunking: {e}")
            return ChunkingResult(
                chunks=[],
                total_chunks=0,
                total_words=0,
                total_characters=0,
                avg_chunk_size=0,
                avg_overlap=0,
                strategy_used=strategy.value,
                language=language or "unknown",
                processing_time=time.time() - start_time,
                quality_score=0.0
            )
    
    def _chunk_fixed_size(self, text: str, chunk_size: int, overlap: int, 
                         language_config: LanguageConfig) -> List[Chunk]:
        """Chunking à taille fixe"""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_content = text[start:end]
            
            # Calculer le chevauchement
            overlap_prev = min(overlap, start) if chunk_index > 0 else 0
            overlap_next = min(overlap, len(text) - end) if end < len(text) else 0
            
            # Créer le chunk
            chunk = self._create_chunk(
                chunk_content, language_config.language, start, end, 
                chunk_index, overlap_prev, overlap_next
            )
            chunks.append(chunk)
            
            # Avancer avec chevauchement
            start = end - overlap
            chunk_index += 1
            
            if start >= len(text):
                break
        
        return chunks
    
    def _chunk_sentence_based(self, text: str, target_size: int, overlap: int,
                            language_config: LanguageConfig) -> List[Chunk]:
        """Chunking basé sur les phrases"""
        sentences = self._split_into_sentences(text, language_config)
        chunks = []
        current_chunk = ""
        current_sentences = []
        chunk_index = 0
        char_position = 0
        
        for sentence in sentences:
            # Vérifier si ajouter cette phrase dépasse la taille cible
            if current_chunk and len(current_chunk + " " + sentence) > target_size:
                # Créer un chunk avec les phrases actuelles
                chunk_start = char_position - len(current_chunk)
                chunk_end = char_position
                
                chunk = self._create_chunk(
                    current_chunk, language_config.language, 
                    chunk_start, chunk_end, chunk_index, 0, 0
                )
                chunks.append(chunk)
                
                # Gérer le chevauchement (garder quelques phrases)
                overlap_sentences = current_sentences[-2:] if len(current_sentences) > 2 else []
                current_chunk = " ".join(overlap_sentences)
                current_sentences = overlap_sentences[:]
                chunk_index += 1
            
            # Ajouter la phrase actuelle
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_sentences.append(sentence)
            char_position += len(sentence) + 1
        
        # Ajouter le dernier chunk
        if current_chunk:
            chunk_start = char_position - len(current_chunk)
            chunk = self._create_chunk(
                current_chunk, language_config.language,
                chunk_start, char_position, chunk_index, 0, 0
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_paragraph_based(self, text: str, target_size: int, overlap: int,
                             language_config: LanguageConfig) -> List[Chunk]:
        """Chunking basé sur les paragraphes"""
        paragraphs = self._split_into_paragraphs(text, language_config)
        chunks = []
        current_chunk = ""
        chunk_index = 0
        char_position = 0
        
        for paragraph in paragraphs:
            # Vérifier si ajouter ce paragraphe dépasse la taille cible
            if current_chunk and len(current_chunk + "\n\n" + paragraph) > target_size:
                # Créer un chunk
                chunk_start = char_position - len(current_chunk)
                chunk = self._create_chunk(
                    current_chunk, language_config.language,
                    chunk_start, char_position, chunk_index, 0, 0
                )
                chunks.append(chunk)
                
                current_chunk = paragraph
                chunk_index += 1
            else:
                # Ajouter le paragraphe
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            
            char_position += len(paragraph) + 2  # +2 pour \n\n
        
        # Ajouter le dernier chunk
        if current_chunk:
            chunk_start = char_position - len(current_chunk)
            chunk = self._create_chunk(
                current_chunk, language_config.language,
                chunk_start, char_position, chunk_index, 0, 0
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_medical_structure(self, text: str, target_size: int, overlap: int,
                               language_config: LanguageConfig, text_type: TextType) -> List[Chunk]:
        """Chunking basé sur la structure médicale"""
        # Détecter les sections médicales
        sections = self._detect_medical_sections(text)
        
        if not sections:
            # Fallback vers chunking par phrases
            return self._chunk_sentence_based(text, target_size, overlap, language_config)
        
        chunks = []
        chunk_index = 0
        
        for section_start, section_end, section_type in sections:
            section_text = text[section_start:section_end]
            
            # Si la section est trop grande, la diviser
            if len(section_text) > target_size:
                section_chunks = self._chunk_sentence_based(
                    section_text, target_size, overlap, language_config
                )
                
                # Ajuster les positions
                for chunk in section_chunks:
                    chunk.start_position += section_start
                    chunk.end_position += section_start
                    chunk.chunk_index = chunk_index
                    chunk.metadata["medical_section"] = section_type
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                # Créer un chunk pour toute la section
                chunk = self._create_chunk(
                    section_text, language_config.language,
                    section_start, section_end, chunk_index, 0, 0
                )
                chunk.metadata["medical_section"] = section_type
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _chunk_language_adaptive(self, text: str, target_size: int, overlap: int,
                               language_config: LanguageConfig, text_type: TextType) -> List[Chunk]:
        """Chunking adaptatif selon la langue"""
        # Choisir la stratégie selon la famille de langue
        if language_config.family == LanguageFamily.NIGER_CONGO:
            # Pour les langues camerounaises, privilégier les phrases courtes
            return self._chunk_sentence_based(text, int(target_size * 0.8), overlap, language_config)
        
        elif language_config.family == LanguageFamily.AFROASIATIC:
            # Pour l'arabe et le hausa, tenir compte de la structure des mots
            if language_config.special_rules.get("rtl_text"):
                # Texte de droite à gauche
                return self._chunk_rtl_aware(text, target_size, overlap, language_config)
            else:
                return self._chunk_sentence_based(text, target_size, overlap, language_config)
        
        elif language_config.family in [LanguageFamily.ROMANCE, LanguageFamily.GERMANIC]:
            # Pour les langues européennes, utiliser la structure standard
            if text_type == TextType.CLINICAL_NOTE:
                return self._chunk_medical_structure(text, target_size, overlap, language_config, text_type)
            else:
                return self._chunk_paragraph_based(text, target_size, overlap, language_config)
        
        else:
            # Stratégie par défaut
            return self._chunk_sentence_based(text, target_size, overlap, language_config)
    
    def _chunk_hybrid(self, text: str, target_size: int, overlap: int,
                     language_config: LanguageConfig, text_type: TextType) -> List[Chunk]:
        """Chunking hybride combinant plusieurs stratégies"""
        # Essayer d'abord la structure médicale
        medical_chunks = self._chunk_medical_structure(text, target_size, overlap, language_config, text_type)
        
        # Si peu de chunks médicaux, essayer par paragraphes
        if len(medical_chunks) < 3:
            paragraph_chunks = self._chunk_paragraph_based(text, target_size, overlap, language_config)
            
            # Si toujours peu de chunks, utiliser les phrases
            if len(paragraph_chunks) < 2:
                return self._chunk_sentence_based(text, target_size, overlap, language_config)
            else:
                return paragraph_chunks
        else:
            return medical_chunks
    
    def _chunk_rtl_aware(self, text: str, target_size: int, overlap: int,
                        language_config: LanguageConfig) -> List[Chunk]:
        """Chunking adapté aux textes de droite à gauche (arabe)"""
        # Pour l'instant, utiliser la méthode par phrases
        # TODO: Implémenter une logique spécifique RTL
        return self._chunk_sentence_based(text, target_size, overlap, language_config)
    
    def _detect_medical_sections(self, text: str) -> List[Tuple[int, int, str]]:
        """Détecte les sections médicales dans le texte"""
        sections = []
        
        for pattern in self.medical_patterns["section_headers"]:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            
            for i, match in enumerate(matches):
                start = match.start()
                
                # Trouver la fin de la section (début de la suivante ou fin du texte)
                if i + 1 < len(matches):
                    end = matches[i + 1].start()
                else:
                    end = len(text)
                
                section_type = match.group(1).upper()
                sections.append((start, end, section_type))
        
        # Trier par position
        sections.sort(key=lambda x: x[0])
        
        return sections
    
    def _create_chunk(self, content: str, language: str, start_pos: int, end_pos: int,
                     chunk_index: int, overlap_prev: int, overlap_next: int) -> Chunk:
        """Crée un objet Chunk"""
        language_config = self._get_language_config(language)
        
        # Calculer les métriques
        words = re.findall(r'\b\w+\b', content)
        sentences = self._split_into_sentences(content, language_config)
        
        # Extraire les informations
        medical_terms = self._extract_medical_terms(content, language_config)
        semantic_coherence = self._calculate_semantic_coherence(content, language_config)
        readability_score = self._calculate_readability_score(content, language_config)
        
        # Générer un ID unique
        chunk_id = hashlib.md5(f"{content[:50]}_{chunk_index}_{start_pos}".encode()).hexdigest()[:12]
        
        return Chunk(
            id=chunk_id,
            content=content,
            language=language,
            start_position=start_pos,
            end_position=end_pos,
            word_count=len(words),
            sentence_count=len(sentences),
            chunk_index=chunk_index,
            overlap_with_previous=overlap_prev,
            overlap_with_next=overlap_next,
            medical_terms=medical_terms,
            semantic_coherence=semantic_coherence,
            readability_score=readability_score
        )
    
    def _calculate_chunking_quality(self, chunks: List[Chunk], language_config: LanguageConfig) -> float:
        """Calcule la qualité globale du chunking"""
        if not chunks:
            return 0.0
        
        # Métriques de qualité
        avg_coherence = sum(chunk.semantic_coherence for chunk in chunks) / len(chunks)
        avg_readability = sum(chunk.readability_score for chunk in chunks) / len(chunks)
        
        # Variance de taille (plus c'est uniforme, mieux c'est)
        sizes = [len(chunk.content) for chunk in chunks]
        avg_size = sum(sizes) / len(sizes)
        size_variance = sum((size - avg_size) ** 2 for size in sizes) / len(sizes)
        size_uniformity = 1.0 / (1.0 + size_variance / (avg_size ** 2))
        
        # Score de qualité combiné
        quality = (avg_coherence * 0.4) + (avg_readability * 0.3) + (size_uniformity * 0.3)
        
        return min(quality, 1.0)
    
    def _update_chunking_stats(self, result: ChunkingResult, language: str, strategy: ChunkingStrategy):
        """Met à jour les statistiques de chunking"""
        self.stats.total_documents_processed += 1
        self.stats.total_chunks_created += result.total_chunks
        
        # Statistiques par langue
        self.stats.chunks_by_language[language] = self.stats.chunks_by_language.get(language, 0) + result.total_chunks
        
        # Statistiques par stratégie
        self.stats.chunks_by_strategy[strategy.value] = self.stats.chunks_by_strategy.get(strategy.value, 0) + result.total_chunks
        
        # Taille moyenne par langue
        if language in self.stats.avg_chunk_size_by_language:
            current_avg = self.stats.avg_chunk_size_by_language[language]
            current_count = self.stats.chunks_by_language[language] - result.total_chunks
            new_avg = ((current_avg * current_count) + (result.avg_chunk_size * result.total_chunks)) / self.stats.chunks_by_language[language]
            self.stats.avg_chunk_size_by_language[language] = new_avg
        else:
            self.stats.avg_chunk_size_by_language[language] = result.avg_chunk_size
        
        # Moyennes globales
        total_docs = self.stats.total_documents_processed
        self.stats.avg_processing_time = ((self.stats.avg_processing_time * (total_docs - 1)) + result.processing_time) / total_docs
        self.stats.avg_quality_score = ((self.stats.avg_quality_score * (total_docs - 1)) + result.quality_score) / total_docs
    
    def generate_stats(self) -> ChunkingStats:
        """Génère les statistiques de chunking"""
        start_time = time.time()
        self.stats.processing_time = time.time() - start_time
        return self.stats
    
    def export_chunking_data(self, output_path: str):
        """Exporte les données de chunking"""
        export_data = {
            "metadata": {
                "total_documents_processed": self.stats.total_documents_processed,
                "total_chunks_created": self.stats.total_chunks_created,
                "supported_languages": list(self.language_configs.keys()),
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "language_configurations": {
                lang: {
                    "family": config.family.value,
                    "avg_word_length": config.avg_word_length,
                    "avg_sentence_length": config.avg_sentence_length,
                    "chunk_size_multiplier": config.chunk_size_multiplier,
                    "overlap_ratio": config.overlap_ratio,
                    "medical_indicators_count": len(config.medical_indicators)
                }
                for lang, config in self.language_configs.items()
            },
            "statistics": {
                "chunks_by_language": self.stats.chunks_by_language,
                "chunks_by_strategy": self.stats.chunks_by_strategy,
                "avg_chunk_size_by_language": self.stats.avg_chunk_size_by_language,
                "avg_processing_time": self.stats.avg_processing_time,
                "avg_quality_score": self.stats.avg_quality_score
            },
            "chunking_patterns": {
                "medical_patterns": {k: len(v) for k, v in self.medical_patterns.items()},
                "default_chunk_size": self.default_chunk_size,
                "default_overlap": self.default_overlap,
                "min_chunk_size": self.min_chunk_size,
                "max_chunk_size": self.max_chunk_size
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de chunking exportées: {output_path}")

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("📝 Test du Chunking Optimisé Multilingue")
    
    # Créer le système de chunking
    chunking_system = OptimizedChunking({
        "default_chunk_size": 400,
        "default_overlap": 50,
        "min_chunk_size": 100,
        "max_chunk_size": 800
    })
    
    # Textes de test multilingues
    test_texts = {
        "fr": """
        DIAGNOSTIC: Le patient présente des symptômes de paludisme aigu.
        
        SYMPTÔMES: Fièvre élevée (39°C), frissons, maux de tête intenses, nausées et vomissements. 
        Le patient rapporte également une fatigue extrême et des douleurs musculaires.
        
        EXAMEN CLINIQUE: TA: 120/80 mmHg, FC: 95 bpm, FR: 22/min, T°: 39.2°C.
        Pâleur conjonctivale présente. Splénomégalie palpable.
        
        TRAITEMENT: Artéméther-luméfantrine 20mg/120mg, 4 comprimés à prendre selon le protocole standard.
        Paracétamol 1g toutes les 6 heures pour la fièvre. Repos au lit et hydratation abondante.
        
        SUIVI: Contrôle dans 48 heures. Si persistance des symptômes, envisager hospitalisation.
        """,
        
        "en": """
        DIAGNOSIS: Patient presents with acute malaria symptoms.
        
        SYMPTOMS: High fever (39°C), chills, severe headaches, nausea and vomiting.
        Patient also reports extreme fatigue and muscle pain.
        
        CLINICAL EXAMINATION: BP: 120/80 mmHg, HR: 95 bpm, RR: 22/min, Temp: 39.2°C.
        Conjunctival pallor present. Palpable splenomegaly.
        
        TREATMENT: Artemether-lumefantrine 20mg/120mg, 4 tablets according to standard protocol.
        Paracetamol 1g every 6 hours for fever. Bed rest and adequate hydration.
        
        FOLLOW-UP: Check-up in 48 hours. If symptoms persist, consider hospitalization.
        """,
        
        "ff": """
        Jannginoowo dokotoro wi'i: Neddo oo ena nayeejo paludisme ɓurɗo.
        
        Alamaaji: Ɓernde mawnde (39°C), ɓerngu, ɓerngu hoore, naange e ɓoggol.
        Neddo wi'i kadi ko ɓerngu ɓurɗo e ɓerngu ɓerngu.
        
        Jannginoore: Dokotoro janngi neddo oo, wi'i ko ɓernde mawnde ena.
        
        Jannginoore: Artéméther-luméfantrine, ɓur ɗuuɗi nayi. Paracétamol ngam ɓernde.
        Ɗaɓɓitaago e ñaamdu ndiyam heɓi.
        """,
        
        "ar": """
        التشخيص: يعاني المريض من أعراض الملاريا الحادة.
        
        الأعراض: حمى عالية (39 درجة مئوية)، قشعريرة، صداع شديد، غثيان وقيء.
        يشكو المريض أيضاً من إرهاق شديد وآلام في العضلات.
        
        الفحص السريري: ضغط الدم 120/80، نبضات القلب 95، التنفس 22، الحرارة 39.2 درجة.
        شحوب في الملتحمة. تضخم في الطحال.
        
        العلاج: أرتيميثر-لوميفانترين 20/120 ملغ، 4 أقراص حسب البروتوكول.
        باراسيتامول 1 غرام كل 6 ساعات للحمى. راحة في السرير وإكثار من السوائل.
        """
    }
    
    # Stratégies à tester
    strategies = [
        ChunkingStrategy.SENTENCE_BASED,
        ChunkingStrategy.MEDICAL_STRUCTURE,
        ChunkingStrategy.LANGUAGE_ADAPTIVE,
        ChunkingStrategy.HYBRID
    ]
    
    print(f"\n📊 Test de {len(test_texts)} langues avec {len(strategies)} stratégies:")
    
    # Tester chaque combinaison
    for language, text in test_texts.items():
        print(f"\n🌐 Langue: {language.upper()}")
        print(f"   Texte: {len(text)} caractères, {len(text.split())} mots")
        
        for strategy in strategies:
            print(f"\n   📝 Stratégie: {strategy.value}")
            
            # Effectuer le chunking
            result = chunking_system.chunk_text(
                text=text,
                language=language,
                strategy=strategy,
                text_type=TextType.CLINICAL_NOTE
            )
            
            print(f"      Chunks créés: {result.total_chunks}")
            print(f"      Taille moyenne: {result.avg_chunk_size:.1f} caractères")
            print(f"      Chevauchement moyen: {result.avg_overlap:.1f} caractères")
            print(f"      Score de qualité: {result.quality_score:.3f}")
            print(f"      Temps de traitement: {result.processing_time:.3f}s")
            
            # Afficher les premiers chunks
            for i, chunk in enumerate(result.chunks[:2]):
                print(f"        Chunk {i+1}:")
                print(f"          Taille: {len(chunk.content)} caractères")
                print(f"          Mots: {chunk.word_count}")
                print(f"          Phrases: {chunk.sentence_count}")
                print(f"          Cohérence: {chunk.semantic_coherence:.3f}")
                print(f"          Lisibilité: {chunk.readability_score:.3f}")
                if chunk.medical_terms:
                    print(f"          Termes médicaux: {', '.join(chunk.medical_terms[:3])}")
                print(f"          Contenu: {chunk.content[:100]}...")
    
    # Test de chunking adaptatif
    print("\n🔄 Test de chunking adaptatif:")
    mixed_text = """
    Le paludisme est une maladie grave. Malaria is a serious disease. 
    Nayeejo paludisme ko nayeejo ɓurɗo. الملاريا مرض خطير.
    
    DIAGNOSTIC: Fièvre, maux de tête.
    DIAGNOSIS: Fever, headache.
    Alamaaji: Ɓernde, ɓerngu hoore.
    الأعراض: حمى، صداع.
    """
    
    adaptive_result = chunking_system.chunk_text(
        text=mixed_text,
        language=None,  # Auto-détection
        strategy=ChunkingStrategy.LANGUAGE_ADAPTIVE
    )
    
    print(f"   Langue détectée: {adaptive_result.language}")
    print(f"   Chunks créés: {adaptive_result.total_chunks}")
    print(f"   Score de qualité: {adaptive_result.quality_score:.3f}")
    
    # Générer les statistiques
    stats = chunking_system.generate_stats()
    print(f"\n📊 Statistiques globales:")
    print(f"   Documents traités: {stats.total_documents_processed}")
    print(f"   Chunks créés: {stats.total_chunks_created}")
    print(f"   Temps moyen: {stats.avg_processing_time:.3f}s")
    print(f"   Score qualité moyen: {stats.avg_quality_score:.3f}")
    
    print(f"\n🌐 Chunks par langue:")
    for lang, count in stats.chunks_by_language.items():
        avg_size = stats.avg_chunk_size_by_language.get(lang, 0)
        print(f"   {lang}: {count} chunks (taille moy: {avg_size:.1f})")
    
    print(f"\n🔧 Chunks par stratégie:")
    for strategy, count in stats.chunks_by_strategy.items():
        print(f"   {strategy}: {count} chunks")
    
    # Exporter les données
    chunking_system.export_chunking_data("optimized_chunking_export.json")
    print("\n✅ Données exportées: optimized_chunking_export.json")

if __name__ == "__main__":
    main()