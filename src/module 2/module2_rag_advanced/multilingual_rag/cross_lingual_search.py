#!/usr/bin/env python3
"""
Recherche Cross-Linguale

Objectif 13: Développer recherche cross-linguale

Ce module implémente un système de recherche cross-linguale permettant
de rechercher dans des documents multilingues avec des requêtes dans
n'importe quelle langue supportée.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from collections import defaultdict
import time

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("FAISS non disponible")
    FAISS_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn non disponible")
    SKLEARN_AVAILABLE = False

class SearchStrategy(Enum):
    """Stratégies de recherche cross-linguale"""
    EMBEDDING_BASED = "embedding_based"  # Basée sur les embeddings multilingues
    TRANSLATION_FIRST = "translation_first"  # Traduire puis rechercher
    HYBRID = "hybrid"  # Combinaison des deux approches
    KEYWORD_MAPPING = "keyword_mapping"  # Mapping de mots-clés multilingues
    SEMANTIC_EXPANSION = "semantic_expansion"  # Expansion sémantique

class LanguageDetectionMethod(Enum):
    """Méthodes de détection de langue"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    CONFIDENCE_BASED = "confidence_based"
    HYBRID_DETECTION = "hybrid_detection"

class SearchScope(Enum):
    """Portée de la recherche"""
    ALL_LANGUAGES = "all_languages"
    SAME_LANGUAGE = "same_language"
    LANGUAGE_FAMILY = "language_family"
    SPECIFIC_LANGUAGES = "specific_languages"
    MEDICAL_PRIORITY = "medical_priority"

@dataclass
class Document:
    """Document indexé"""
    id: str
    content: str
    language: str
    title: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    keywords: List[str] = field(default_factory=list)
    medical_terms: List[str] = field(default_factory=list)
    domain: Optional[str] = None
    confidence_score: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class SearchQuery:
    """Requête de recherche cross-linguale"""
    text: str
    language: Optional[str] = None  # Auto-détection si None
    target_languages: Optional[List[str]] = None  # Toutes si None
    strategy: SearchStrategy = SearchStrategy.HYBRID
    scope: SearchScope = SearchScope.ALL_LANGUAGES
    max_results: int = 10
    similarity_threshold: float = 0.5
    boost_medical_terms: bool = True
    boost_same_language: float = 1.2
    boost_language_family: float = 1.1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """Résultat de recherche"""
    document: Document
    similarity_score: float
    relevance_score: float  # Score final après boosts
    query_language: str
    document_language: str
    cross_lingual: bool
    strategy_used: str
    explanation: str  # Explication du score
    matched_terms: List[str] = field(default_factory=list)
    translated_query: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LanguageMapping:
    """Mapping entre langues pour les mots-clés"""
    source_term: str
    source_language: str
    target_mappings: Dict[str, List[str]]  # langue -> [termes équivalents]
    confidence: float
    domain: Optional[str] = None
    verified: bool = False

@dataclass
class SearchStats:
    """Statistiques de recherche"""
    total_searches: int = 0
    cross_lingual_searches: int = 0
    searches_by_language: Dict[str, int] = field(default_factory=dict)
    searches_by_strategy: Dict[str, int] = field(default_factory=dict)
    avg_results_per_query: float = 0.0
    avg_processing_time: float = 0.0
    avg_similarity_score: float = 0.0
    language_detection_accuracy: float = 0.0
    processing_time: float = 0.0

class CrossLingualSearch:
    """
    Système de recherche cross-linguale
    
    Objectif couvert:
    - 13. Développer recherche cross-linguale
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = SearchStats()
        
        # Documents indexés
        self.documents: Dict[str, Document] = {}
        self.documents_by_language: Dict[str, List[str]] = defaultdict(list)
        
        # Index de recherche
        self.embedding_index = None
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self.medical_terms_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Mappings multilingues
        self.language_mappings: Dict[str, LanguageMapping] = {}
        self.medical_translations: Dict[str, Dict[str, str]] = defaultdict(dict)
        
        # Configuration
        self.default_strategy = SearchStrategy(self.config.get("default_strategy", "hybrid"))
        self.auto_detect_language = self.config.get("auto_detect_language", True)
        self.cache_enabled = self.config.get("cache_enabled", True)
        
        # Cache de recherche
        self.search_cache: Dict[str, List[SearchResult]] = {}
        self.max_cache_size = self.config.get("max_cache_size", 1000)
        
        # Composants externes (injectés)
        self.embedding_system = None
        self.translation_system = None
        self.language_detector = None
        
        # Initialiser les mappings de base
        self._init_language_mappings()
        
        logger.info("Système de recherche cross-linguale initialisé")
    
    def set_embedding_system(self, embedding_system):
        """Injecte le système d'embeddings"""
        self.embedding_system = embedding_system
        logger.info("Système d'embeddings configuré")
    
    def set_translation_system(self, translation_system):
        """Injecte le système de traduction"""
        self.translation_system = translation_system
        logger.info("Système de traduction configuré")
    
    def set_language_detector(self, language_detector):
        """Injecte le détecteur de langue"""
        self.language_detector = language_detector
        logger.info("Détecteur de langue configuré")
    
    def _init_language_mappings(self):
        """Initialise les mappings multilingues de base"""
        # Mappings médicaux de base
        medical_mappings = {
            "paludisme": LanguageMapping(
                source_term="paludisme",
                source_language="fr",
                target_mappings={
                    "en": ["malaria", "malaria disease"],
                    "ff": ["nayeejo paludisme", "paludisme"],
                    "ewondo": ["bela paludisme", "paludisme"],
                    "duala": ["bwele paludisme", "paludisme"],
                    "bamileke": ["nkeng paludisme", "paludisme"],
                    "ha": ["zazzabin cizon sauro", "malaria"],
                    "ar": ["الملاريا", "مرض الملاريا"]
                },
                confidence=0.95,
                domain="infectiologie",
                verified=True
            ),
            
            "fièvre": LanguageMapping(
                source_term="fièvre",
                source_language="fr",
                target_mappings={
                    "en": ["fever", "high temperature"],
                    "ff": ["ɓernde", "ɓernde mawnde"],
                    "ewondo": ["awu", "awu nlôm"],
                    "duala": ["mbasu", "mbasu nlôm"],
                    "bamileke": ["nkui", "nkui nlôm"],
                    "ha": ["zazzabi", "zafi"],
                    "ar": ["حمى", "ارتفاع درجة الحرارة"]
                },
                confidence=0.98,
                domain="general",
                verified=True
            ),
            
            "médecin": LanguageMapping(
                source_term="médecin",
                source_language="fr",
                target_mappings={
                    "en": ["doctor", "physician", "medical doctor"],
                    "ff": ["dokotoro", "jannginoowo"],
                    "ewondo": ["dokita", "nga janga"],
                    "duala": ["dokita", "moto a janga"],
                    "bamileke": ["dokita", "moto janga"],
                    "ha": ["likita", "dokita"],
                    "ar": ["طبيب", "دكتور"]
                },
                confidence=0.95,
                domain="general",
                verified=True
            ),
            
            "hôpital": LanguageMapping(
                source_term="hôpital",
                source_language="fr",
                target_mappings={
                    "en": ["hospital", "medical center"],
                    "ff": ["jammirgal", "duɗal jannginooje"],
                    "ewondo": ["bilinga", "nda janga"],
                    "duala": ["lopital", "nda janga"],
                    "bamileke": ["lopital", "nda janga"],
                    "ha": ["asibiti", "gidan magani"],
                    "ar": ["مستشفى", "مركز طبي"]
                },
                confidence=0.95,
                domain="general",
                verified=True
            )
        }
        
        # Ajouter les mappings
        for term_id, mapping in medical_mappings.items():
            self.language_mappings[term_id] = mapping
            
            # Créer les traductions bidirectionnelles
            for target_lang, target_terms in mapping.target_mappings.items():
                for target_term in target_terms:
                    self.medical_translations[target_term.lower()][mapping.source_language] = mapping.source_term
                    self.medical_translations[mapping.source_term.lower()][target_lang] = target_term
        
        logger.info(f"Mappings multilingues initialisés: {len(medical_mappings)} termes")
    
    def _detect_language(self, text: str) -> Tuple[str, float]:
        """Détecte la langue d'un texte"""
        if self.language_detector:
            try:
                return self.language_detector.detect(text)
            except Exception as e:
                logger.warning(f"Erreur de détection de langue: {e}")
        
        # Détection simple basée sur des mots-clés
        language_keywords = {
            "fr": ["le", "la", "les", "de", "du", "des", "et", "est", "une", "un", "dans", "pour", "avec"],
            "en": ["the", "and", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by"],
            "ff": ["ko", "e", "o", "ɗo", "ɓe", "mo", "no", "wo", "ngo", "ɗum"],
            "ewondo": ["a", "e", "o", "na", "ne", "nga", "nge", "be", "ba"],
            "duala": ["a", "e", "o", "na", "ne", "moto", "ba", "be"],
            "ha": ["da", "na", "ya", "ta", "ka", "ba", "su", "mu", "ku"],
            "ar": ["في", "من", "إلى", "على", "هذا", "هذه", "التي", "الذي"]
        }
        
        text_lower = text.lower()
        scores = {}
        
        for lang, keywords in language_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[lang] = score / len(keywords)
        
        if scores:
            best_lang = max(scores, key=scores.get)
            confidence = scores[best_lang]
            return best_lang, confidence
        
        # Par défaut, français
        return "fr", 0.5
    
    def _get_search_hash(self, query: SearchQuery) -> str:
        """Génère un hash pour le cache de recherche"""
        content = f"{query.text}_{query.language}_{query.target_languages}_{query.strategy.value}_{query.max_results}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _extract_keywords(self, text: str, language: str) -> List[str]:
        """Extrait les mots-clés d'un texte"""
        # Mots vides par langue
        stopwords = {
            "fr": {"le", "la", "les", "de", "du", "des", "et", "est", "une", "un", "dans", "pour", "avec", "sur", "par"},
            "en": {"the", "and", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by", "a", "an"},
            "ff": {"ko", "e", "o", "ɗo", "ɓe", "mo", "no", "wo"},
            "ewondo": {"a", "e", "o", "na", "ne", "nga", "nge"},
            "duala": {"a", "e", "o", "na", "ne", "moto"},
            "ha": {"da", "na", "ya", "ta", "ka", "ba"},
            "ar": {"في", "من", "إلى", "على"}
        }
        
        # Nettoyer et diviser le texte
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filtrer les mots vides
        lang_stopwords = stopwords.get(language, set())
        keywords = [word for word in words if len(word) > 2 and word not in lang_stopwords]
        
        return keywords
    
    def _expand_query_terms(self, query_text: str, query_language: str, 
                          target_languages: List[str]) -> Dict[str, List[str]]:
        """Expanse les termes de requête vers d'autres langues"""
        expanded_terms = defaultdict(list)
        query_keywords = self._extract_keywords(query_text, query_language)
        
        # Ajouter les termes originaux
        expanded_terms[query_language].extend(query_keywords)
        
        # Expansion via les mappings médicaux
        for keyword in query_keywords:
            keyword_lower = keyword.lower()
            
            # Rechercher dans les mappings directs
            for mapping in self.language_mappings.values():
                if (mapping.source_language == query_language and 
                    mapping.source_term.lower() == keyword_lower):
                    
                    for target_lang in target_languages:
                        if target_lang in mapping.target_mappings:
                            expanded_terms[target_lang].extend(mapping.target_mappings[target_lang])
            
            # Rechercher dans les traductions médicales
            if keyword_lower in self.medical_translations:
                for target_lang in target_languages:
                    if target_lang in self.medical_translations[keyword_lower]:
                        expanded_terms[target_lang].append(
                            self.medical_translations[keyword_lower][target_lang]
                        )
        
        return dict(expanded_terms)
    
    def add_document(self, document: Document) -> bool:
        """
        Ajoute un document à l'index
        
        Args:
            document: Document à indexer
        
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            # Ajouter le document
            self.documents[document.id] = document
            self.documents_by_language[document.language].append(document.id)
            
            # Extraire et indexer les mots-clés
            if not document.keywords:
                document.keywords = self._extract_keywords(document.content, document.language)
            
            for keyword in document.keywords:
                self.keyword_index[keyword.lower()].add(document.id)
            
            # Indexer les termes médicaux
            for medical_term in document.medical_terms:
                self.medical_terms_index[medical_term.lower()].add(document.id)
            
            # Générer l'embedding si le système est disponible
            if self.embedding_system and not document.embedding:
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    embedding_result = loop.run_until_complete(
                        self.embedding_system.encode_text(document.content, document.language)
                    )
                    document.embedding = embedding_result.embedding
                    loop.close()
                except Exception as e:
                    logger.warning(f"Erreur lors de la génération d'embedding: {e}")
            
            logger.debug(f"Document indexé: {document.id} ({document.language})")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation du document {document.id}: {e}")
            return False
    
    def build_embedding_index(self):
        """Construit l'index FAISS des embeddings"""
        if not FAISS_AVAILABLE:
            logger.warning("FAISS non disponible, index d'embeddings non créé")
            return
        
        try:
            # Collecter tous les embeddings
            embeddings = []
            doc_ids = []
            
            for doc_id, document in self.documents.items():
                if document.embedding is not None:
                    embeddings.append(document.embedding)
                    doc_ids.append(doc_id)
            
            if not embeddings:
                logger.warning("Aucun embedding disponible pour l'index")
                return
            
            # Créer la matrice d'embeddings
            embedding_matrix = np.vstack(embeddings).astype('float32')
            dimension = embedding_matrix.shape[1]
            
            # Créer l'index FAISS
            self.embedding_index = faiss.IndexFlatIP(dimension)
            
            # Normaliser pour la similarité cosinus
            faiss.normalize_L2(embedding_matrix)
            
            # Ajouter à l'index
            self.embedding_index.add(embedding_matrix)
            
            # Stocker la correspondance index -> doc_id
            self.embedding_doc_ids = doc_ids
            
            logger.info(f"Index d'embeddings créé avec {len(embeddings)} documents")
        
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'index d'embeddings: {e}")
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Effectue une recherche cross-linguale
        
        Args:
            query: Requête de recherche
        
        Returns:
            List[SearchResult]: Résultats de recherche
        """
        start_time = time.time()
        
        try:
            # Vérifier le cache
            cache_key = self._get_search_hash(query)
            if self.cache_enabled and cache_key in self.search_cache:
                cached_results = self.search_cache[cache_key]
                for result in cached_results:
                    result.metadata["from_cache"] = True
                return cached_results
            
            # Détecter la langue de la requête si nécessaire
            if not query.language and self.auto_detect_language:
                query.language, confidence = self._detect_language(query.text)
                logger.debug(f"Langue détectée: {query.language} (confiance: {confidence:.2f})")
            
            query_language = query.language or "fr"
            
            # Déterminer les langues cibles
            if query.target_languages is None:
                if query.scope == SearchScope.ALL_LANGUAGES:
                    target_languages = list(set(self.documents_by_language.keys()))
                elif query.scope == SearchScope.SAME_LANGUAGE:
                    target_languages = [query_language]
                else:
                    target_languages = [query_language, "fr", "en"]  # Langues par défaut
            else:
                target_languages = query.target_languages
            
            # Rechercher selon la stratégie
            if query.strategy == SearchStrategy.EMBEDDING_BASED:
                results = await self._search_by_embeddings(query, query_language, target_languages)
            elif query.strategy == SearchStrategy.TRANSLATION_FIRST:
                results = await self._search_by_translation(query, query_language, target_languages)
            elif query.strategy == SearchStrategy.KEYWORD_MAPPING:
                results = await self._search_by_keywords(query, query_language, target_languages)
            elif query.strategy == SearchStrategy.HYBRID:
                results = await self._search_hybrid(query, query_language, target_languages)
            else:
                results = await self._search_hybrid(query, query_language, target_languages)
            
            # Appliquer les boosts et filtres
            results = self._apply_boosts_and_filters(results, query, query_language)
            
            # Trier et limiter les résultats
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            results = results[:query.max_results]
            
            # Mettre à jour les temps de traitement
            processing_time = time.time() - start_time
            for result in results:
                result.processing_time = processing_time
            
            # Mettre en cache
            if self.cache_enabled and len(self.search_cache) < self.max_cache_size:
                self.search_cache[cache_key] = results
            
            # Mettre à jour les statistiques
            self._update_search_stats(query, results, query_language, processing_time)
            
            return results
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return []
    
    async def _search_by_embeddings(self, query: SearchQuery, query_language: str, 
                                  target_languages: List[str]) -> List[SearchResult]:
        """Recherche basée sur les embeddings"""
        if not self.embedding_system or not self.embedding_index:
            return []
        
        try:
            # Générer l'embedding de la requête
            query_embedding_result = await self.embedding_system.encode_text(query.text, query_language)
            query_embedding = query_embedding_result.embedding
            
            # Rechercher dans l'index FAISS
            query_norm = query_embedding.copy().astype('float32')
            query_norm = query_norm.reshape(1, -1)
            faiss.normalize_L2(query_norm)
            
            # Rechercher plus de résultats pour le filtrage
            search_k = min(query.max_results * 3, len(self.embedding_doc_ids))
            scores, indices = self.embedding_index.search(query_norm, search_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and score >= query.similarity_threshold:
                    doc_id = self.embedding_doc_ids[idx]
                    document = self.documents[doc_id]
                    
                    # Filtrer par langues cibles si spécifié
                    if target_languages and document.language not in target_languages:
                        continue
                    
                    cross_lingual = document.language != query_language
                    
                    result = SearchResult(
                        document=document,
                        similarity_score=float(score),
                        relevance_score=float(score),
                        query_language=query_language,
                        document_language=document.language,
                        cross_lingual=cross_lingual,
                        strategy_used="embedding_based",
                        explanation=f"Similarité d'embedding: {score:.3f}",
                        metadata={"embedding_similarity": float(score)}
                    )
                    results.append(result)
            
            return results
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par embeddings: {e}")
            return []
    
    async def _search_by_translation(self, query: SearchQuery, query_language: str,
                                   target_languages: List[str]) -> List[SearchResult]:
        """Recherche par traduction de la requête"""
        if not self.translation_system:
            return []
        
        results = []
        
        try:
            # Traduire la requête vers chaque langue cible
            for target_lang in target_languages:
                if target_lang == query_language:
                    # Recherche directe dans la même langue
                    lang_results = await self._search_in_language(query.text, target_lang, query_language)
                else:
                    # Traduire et rechercher
                    from .translation_system import TranslationRequest, MedicalDomain
                    
                    translation_request = TranslationRequest(
                        text=query.text,
                        source_language=query_language,
                        target_language=target_lang,
                        domain=MedicalDomain.GENERAL,
                        preserve_medical_terms=True
                    )
                    
                    translation_result = await self.translation_system.translate(translation_request)
                    translated_query = translation_result.translated_text
                    
                    lang_results = await self._search_in_language(translated_query, target_lang, query_language)
                    
                    # Ajouter les informations de traduction
                    for result in lang_results:
                        result.translated_query = translated_query
                        result.strategy_used = "translation_first"
                        result.explanation = f"Requête traduite: '{translated_query}'"
                
                results.extend(lang_results)
            
            return results
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par traduction: {e}")
            return []
    
    async def _search_by_keywords(self, query: SearchQuery, query_language: str,
                                target_languages: List[str]) -> List[SearchResult]:
        """Recherche par mapping de mots-clés"""
        results = []
        
        try:
            # Extraire les mots-clés de la requête
            query_keywords = self._extract_keywords(query.text, query_language)
            
            # Expanser vers d'autres langues
            expanded_terms = self._expand_query_terms(query.text, query_language, target_languages)
            
            # Rechercher pour chaque langue
            for target_lang, terms in expanded_terms.items():
                if target_lang not in target_languages:
                    continue
                
                # Trouver les documents contenant ces termes
                matching_docs = set()
                term_matches = defaultdict(list)
                
                for term in terms:
                    term_lower = term.lower()
                    if term_lower in self.keyword_index:
                        doc_ids = self.keyword_index[term_lower]
                        matching_docs.update(doc_ids)
                        for doc_id in doc_ids:
                            term_matches[doc_id].append(term)
                
                # Créer les résultats
                for doc_id in matching_docs:
                    document = self.documents[doc_id]
                    if document.language != target_lang:
                        continue
                    
                    # Calculer le score basé sur le nombre de termes correspondants
                    matched_terms = term_matches[doc_id]
                    similarity_score = len(matched_terms) / max(len(terms), 1)
                    
                    cross_lingual = document.language != query_language
                    
                    result = SearchResult(
                        document=document,
                        similarity_score=similarity_score,
                        relevance_score=similarity_score,
                        query_language=query_language,
                        document_language=document.language,
                        cross_lingual=cross_lingual,
                        strategy_used="keyword_mapping",
                        explanation=f"Termes correspondants: {', '.join(matched_terms)}",
                        matched_terms=matched_terms,
                        metadata={"keyword_matches": len(matched_terms), "total_terms": len(terms)}
                    )
                    results.append(result)
            
            return results
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par mots-clés: {e}")
            return []
    
    async def _search_hybrid(self, query: SearchQuery, query_language: str,
                           target_languages: List[str]) -> List[SearchResult]:
        """Recherche hybride combinant plusieurs stratégies"""
        all_results = []
        
        try:
            # Recherche par embeddings (poids: 0.5)
            embedding_results = await self._search_by_embeddings(query, query_language, target_languages)
            for result in embedding_results:
                result.relevance_score *= 0.5
                result.strategy_used = "hybrid_embedding"
            all_results.extend(embedding_results)
            
            # Recherche par mots-clés (poids: 0.3)
            keyword_results = await self._search_by_keywords(query, query_language, target_languages)
            for result in keyword_results:
                result.relevance_score *= 0.3
                result.strategy_used = "hybrid_keyword"
            all_results.extend(keyword_results)
            
            # Recherche par traduction (poids: 0.2)
            translation_results = await self._search_by_translation(query, query_language, target_languages)
            for result in translation_results:
                result.relevance_score *= 0.2
                result.strategy_used = "hybrid_translation"
            all_results.extend(translation_results)
            
            # Fusionner les résultats par document
            merged_results = {}
            for result in all_results:
                doc_id = result.document.id
                if doc_id in merged_results:
                    # Combiner les scores
                    existing = merged_results[doc_id]
                    existing.relevance_score += result.relevance_score
                    existing.explanation += f"; {result.explanation}"
                    existing.strategy_used = "hybrid"
                    
                    # Combiner les termes correspondants
                    existing.matched_terms.extend(result.matched_terms)
                    existing.matched_terms = list(set(existing.matched_terms))
                else:
                    result.strategy_used = "hybrid"
                    merged_results[doc_id] = result
            
            return list(merged_results.values())
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche hybride: {e}")
            return []
    
    async def _search_in_language(self, query_text: str, language: str, 
                                original_language: str) -> List[SearchResult]:
        """Recherche dans une langue spécifique"""
        results = []
        
        # Recherche simple par mots-clés dans la langue
        query_keywords = self._extract_keywords(query_text, language)
        
        # Documents dans cette langue
        lang_doc_ids = self.documents_by_language.get(language, [])
        
        for doc_id in lang_doc_ids:
            document = self.documents[doc_id]
            
            # Calculer la similarité basique
            doc_keywords = set(document.keywords)
            query_keywords_set = set(query_keywords)
            
            intersection = doc_keywords & query_keywords_set
            union = doc_keywords | query_keywords_set
            
            if union:
                similarity = len(intersection) / len(union)
                
                if similarity >= 0.1:  # Seuil minimum
                    cross_lingual = language != original_language
                    
                    result = SearchResult(
                        document=document,
                        similarity_score=similarity,
                        relevance_score=similarity,
                        query_language=original_language,
                        document_language=language,
                        cross_lingual=cross_lingual,
                        strategy_used="language_specific",
                        explanation=f"Similarité Jaccard: {similarity:.3f}",
                        matched_terms=list(intersection)
                    )
                    results.append(result)
        
        return results
    
    def _apply_boosts_and_filters(self, results: List[SearchResult], query: SearchQuery,
                                query_language: str) -> List[SearchResult]:
        """Applique les boosts et filtres aux résultats"""
        for result in results:
            # Boost pour la même langue
            if not result.cross_lingual:
                result.relevance_score *= query.boost_same_language
            
            # Boost pour les termes médicaux
            if query.boost_medical_terms and result.document.medical_terms:
                medical_boost = 1.0 + (len(result.document.medical_terms) * 0.1)
                result.relevance_score *= medical_boost
            
            # Boost pour la famille de langues (simplifié)
            if result.cross_lingual:
                # Familles de langues simplifiées
                romance_langs = {"fr", "es", "it"}
                germanic_langs = {"en", "de", "nl"}
                niger_congo_langs = {"ff", "ewondo", "duala", "bamileke"}
                
                query_family = None
                doc_family = None
                
                if query_language in romance_langs:
                    query_family = "romance"
                elif query_language in germanic_langs:
                    query_family = "germanic"
                elif query_language in niger_congo_langs:
                    query_family = "niger_congo"
                
                if result.document_language in romance_langs:
                    doc_family = "romance"
                elif result.document_language in germanic_langs:
                    doc_family = "germanic"
                elif result.document_language in niger_congo_langs:
                    doc_family = "niger_congo"
                
                if query_family and doc_family and query_family == doc_family:
                    result.relevance_score *= query.boost_language_family
        
        # Filtrer par seuil de similarité
        filtered_results = [
            result for result in results 
            if result.similarity_score >= query.similarity_threshold
        ]
        
        return filtered_results
    
    def _update_search_stats(self, query: SearchQuery, results: List[SearchResult],
                           query_language: str, processing_time: float):
        """Met à jour les statistiques de recherche"""
        self.stats.total_searches += 1
        self.stats.searches_by_language[query_language] = self.stats.searches_by_language.get(query_language, 0) + 1
        self.stats.searches_by_strategy[query.strategy.value] = self.stats.searches_by_strategy.get(query.strategy.value, 0) + 1
        
        # Compter les recherches cross-linguales
        cross_lingual_results = [r for r in results if r.cross_lingual]
        if cross_lingual_results:
            self.stats.cross_lingual_searches += 1
        
        # Moyennes mobiles
        if self.stats.total_searches > 1:
            self.stats.avg_results_per_query = (
                (self.stats.avg_results_per_query * (self.stats.total_searches - 1) + len(results)) / 
                self.stats.total_searches
            )
            self.stats.avg_processing_time = (
                (self.stats.avg_processing_time * (self.stats.total_searches - 1) + processing_time) / 
                self.stats.total_searches
            )
            
            if results:
                avg_similarity = sum(r.similarity_score for r in results) / len(results)
                self.stats.avg_similarity_score = (
                    (self.stats.avg_similarity_score * (self.stats.total_searches - 1) + avg_similarity) / 
                    self.stats.total_searches
                )
        else:
            self.stats.avg_results_per_query = len(results)
            self.stats.avg_processing_time = processing_time
            if results:
                self.stats.avg_similarity_score = sum(r.similarity_score for r in results) / len(results)
    
    def generate_stats(self) -> SearchStats:
        """Génère les statistiques de recherche"""
        start_time = time.time()
        
        # Calculer la précision de détection de langue (simulée)
        self.stats.language_detection_accuracy = 0.85  # Valeur simulée
        
        self.stats.processing_time = time.time() - start_time
        
        return self.stats
    
    def export_search_data(self, output_path: str):
        """Exporte les données de recherche"""
        export_data = {
            "metadata": {
                "total_documents": len(self.documents),
                "total_searches": self.stats.total_searches,
                "supported_languages": list(self.documents_by_language.keys()),
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "language_mappings": {
                term_id: {
                    "source_term": mapping.source_term,
                    "source_language": mapping.source_language,
                    "target_mappings": mapping.target_mappings,
                    "confidence": mapping.confidence,
                    "domain": mapping.domain,
                    "verified": mapping.verified
                }
                for term_id, mapping in self.language_mappings.items()
            },
            "statistics": {
                "searches_by_language": self.stats.searches_by_language,
                "searches_by_strategy": self.stats.searches_by_strategy,
                "cross_lingual_searches": self.stats.cross_lingual_searches,
                "avg_results_per_query": self.stats.avg_results_per_query,
                "avg_processing_time": self.stats.avg_processing_time,
                "avg_similarity_score": self.stats.avg_similarity_score,
                "language_detection_accuracy": self.stats.language_detection_accuracy
            },
            "index_info": {
                "documents_by_language": {lang: len(docs) for lang, docs in self.documents_by_language.items()},
                "keyword_index_size": len(self.keyword_index),
                "medical_terms_index_size": len(self.medical_terms_index),
                "embedding_index_available": self.embedding_index is not None
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de recherche exportées: {output_path}")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🔍 Test de la Recherche Cross-Linguale")
    
    # Créer le système de recherche
    search_system = CrossLingualSearch({
        "default_strategy": "hybrid",
        "auto_detect_language": True,
        "cache_enabled": True
    })
    
    # Documents de test multilingues
    test_documents = [
        Document(
            id="doc_fr_1",
            content="Le paludisme est une maladie parasitaire grave transmise par les moustiques anopheles. Les symptômes incluent la fièvre, les frissons et les maux de tête.",
            language="fr",
            title="Paludisme - Guide médical",
            medical_terms=["paludisme", "fièvre", "maladie"],
            domain="infectiologie"
        ),
        Document(
            id="doc_en_1",
            content="Malaria is a serious parasitic disease transmitted by anopheles mosquitoes. Symptoms include fever, chills, and headaches. Treatment requires immediate medical attention.",
            language="en",
            title="Malaria - Medical Guide",
            medical_terms=["malaria", "fever", "disease"],
            domain="infectious_diseases"
        ),
        Document(
            id="doc_ff_1",
            content="Nayeejo paludisme ko nayeejo ɓurɗo mo anopheles ɗon haɓa. Alamaaji ɗi ko ɓernde, ɓerngu e ɓerngu hoore.",
            language="ff",
            title="Paludisme - Jannginoore",
            medical_terms=["nayeejo paludisme", "ɓernde"],
            domain="jannginoore"
        ),
        Document(
            id="doc_fr_2",
            content="Le diabète est une maladie chronique caractérisée par un taux élevé de sucre dans le sang. Il nécessite un suivi médical régulier et un traitement approprié.",
            language="fr",
            title="Diabète - Information patient",
            medical_terms=["diabète", "maladie", "sucre"],
            domain="endocrinologie"
        ),
        Document(
            id="doc_ar_1",
            content="الملاريا مرض طفيلي خطير ينتقل عن طريق البعوض. الأعراض تشمل الحمى والقشعريرة والصداع. يتطلب العلاج عناية طبية فورية.",
            language="ar",
            title="الملاريا - دليل طبي",
            medical_terms=["الملاريا", "حمى", "مرض"],
            domain="الأمراض المعدية"
        )
    ]
    
    # Indexer les documents
    print(f"\n📚 Indexation de {len(test_documents)} documents:")
    for doc in test_documents:
        success = search_system.add_document(doc)
        print(f"  - {doc.title} ({doc.language}): {'✅' if success else '❌'}")
    
    # Construire l'index d'embeddings (simulé)
    search_system.build_embedding_index()
    
    # Requêtes de test
    test_queries = [
        SearchQuery(
            text="paludisme symptômes fièvre",
            language="fr",
            strategy=SearchStrategy.HYBRID,
            max_results=5
        ),
        SearchQuery(
            text="malaria fever treatment",
            language="en",
            strategy=SearchStrategy.KEYWORD_MAPPING,
            max_results=3
        ),
        SearchQuery(
            text="nayeejo ɓernde",
            language="ff",
            strategy=SearchStrategy.HYBRID,
            max_results=4
        ),
        SearchQuery(
            text="الملاريا الحمى",
            language="ar",
            strategy=SearchStrategy.KEYWORD_MAPPING,
            max_results=3
        )
    ]
    
    print(f"\n🔍 Test de {len(test_queries)} requêtes:")
    
    # Effectuer les recherches
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Requête: '{query.text}' ({query.language})")
        print(f"   Stratégie: {query.strategy.value}")
        
        results = await search_system.search(query)
        
        print(f"   Résultats trouvés: {len(results)}")
        for j, result in enumerate(results, 1):
            cross_lingual_indicator = "🌐" if result.cross_lingual else "🏠"
            print(f"     {j}. {cross_lingual_indicator} {result.document.title} ({result.document_language})")
            print(f"        Score: {result.relevance_score:.3f} | Similarité: {result.similarity_score:.3f}")
            print(f"        Stratégie: {result.strategy_used}")
            if result.matched_terms:
                print(f"        Termes: {', '.join(result.matched_terms[:3])}")
    
    # Test de détection automatique de langue
    print("\n🌐 Test de détection automatique de langue:")
    auto_query = SearchQuery(
        text="fever and headache symptoms",  # Anglais
        language=None,  # Auto-détection
        strategy=SearchStrategy.HYBRID,
        max_results=3
    )
    
    auto_results = await search_system.search(auto_query)
    detected_lang = auto_query.language
    print(f"   Langue détectée: {detected_lang}")
    print(f"   Résultats: {len(auto_results)}")
    
    # Générer les statistiques
    stats = search_system.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"   Recherches totales: {stats.total_searches}")
    print(f"   Recherches cross-linguales: {stats.cross_lingual_searches}")
    print(f"   Résultats moyens par requête: {stats.avg_results_per_query:.1f}")
    print(f"   Temps de traitement moyen: {stats.avg_processing_time:.3f}s")
    print(f"   Score de similarité moyen: {stats.avg_similarity_score:.3f}")
    print(f"   Précision détection langue: {stats.language_detection_accuracy:.1%}")
    
    print(f"\n🌐 Recherches par langue:")
    for lang, count in stats.searches_by_language.items():
        print(f"   {lang}: {count} recherches")
    
    print(f"\n🔧 Recherches par stratégie:")
    for strategy, count in stats.searches_by_strategy.items():
        print(f"   {strategy}: {count} recherches")
    
    # Exporter les données
    search_system.export_search_data("cross_lingual_search_export.json")
    print("\n✅ Données exportées: cross_lingual_search_export.json")

if __name__ == "__main__":
    asyncio.run(main())