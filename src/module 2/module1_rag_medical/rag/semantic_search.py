#!/usr/bin/env python3
"""
Système de Recherche Sémantique Avancé pour Documents Médicaux

Ce module implémente un système de recherche sémantique sophistiqué avec:
- Recherche multi-vectorielle
- Scoring de pertinence avancé
- Fusion des résultats de différentes sources
- Optimisation pour le domaine médical
"""

import logging
import time
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from sentence_transformers import util
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss
import re
from collections import defaultdict, Counter
import math
from enum import Enum
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchType(Enum):
    """Types de recherche disponibles"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    MEDICAL_ENTITY = "medical_entity"

class RelevanceMethod(Enum):
    """Méthodes de calcul de pertinence"""
    COSINE = "cosine"
    DOT_PRODUCT = "dot_product"
    EUCLIDEAN = "euclidean"
    BM25 = "bm25"
    COMBINED = "combined"

@dataclass
class SearchResult:
    """Résultat de recherche avec métadonnées"""
    document_id: str
    chunk_id: str
    content: str
    relevance_score: float
    search_type: SearchType
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlighted_content: Optional[str] = None
    explanation: Optional[str] = None
    sub_scores: Dict[str, float] = field(default_factory=dict)

@dataclass
class SearchQuery:
    """Requête de recherche structurée"""
    text: str
    search_types: List[SearchType] = field(default_factory=lambda: [SearchType.HYBRID])
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10
    min_relevance: float = 0.0
    boost_factors: Dict[str, float] = field(default_factory=dict)
    medical_context: Optional[str] = None

@dataclass
class IndexedDocument:
    """Document indexé pour la recherche"""
    document_id: str
    chunk_id: str
    content: str
    embedding: np.ndarray
    keywords: List[str]
    medical_entities: List[str]
    metadata: Dict[str, Any]
    tfidf_vector: Optional[np.ndarray] = None

class MedicalSemanticSearch:
    """
    Système de recherche sémantique avancé pour documents médicaux
    
    Fonctionnalités:
    - Recherche sémantique basée sur les embeddings
    - Recherche par mots-clés avec TF-IDF
    - Recherche hybride combinant plusieurs approches
    - Scoring de pertinence multi-critères
    - Fusion intelligente des résultats
    - Optimisations spécifiques au domaine médical
    """
    
    def __init__(self,
                 embedding_model=None,
                 language: str = "fr",
                 medical_vocabulary: Optional[List[str]] = None):
        """
        Initialise le système de recherche sémantique
        
        Args:
            embedding_model: Modèle d'embeddings (sentence-transformers)
            language: Langue des documents
            medical_vocabulary: Vocabulaire médical spécialisé
        """
        self.embedding_model = embedding_model
        self.language = language
        self.medical_vocabulary = medical_vocabulary or []
        
        # Index des documents
        self.indexed_documents: Dict[str, IndexedDocument] = {}
        
        # Index FAISS pour recherche vectorielle rapide
        self.faiss_index = None
        self.faiss_id_mapping = {}
        
        # Vectoriseur TF-IDF pour recherche par mots-clés
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        
        # Patterns médicaux pour améliorer la recherche
        self._init_medical_patterns()
        
        # Statistiques de recherche
        self.search_stats = {
            'total_searches': 0,
            'avg_search_time': 0.0,
            'search_types_used': defaultdict(int),
            'avg_results_returned': 0.0
        }
        
        logger.info(f"Système de recherche sémantique initialisé (langue: {language})")
    
    def _init_medical_patterns(self):
        """Initialise les patterns médicaux pour améliorer la recherche"""
        # Patterns pour entités médicales
        self.medical_patterns = {
            'medication': re.compile(r'\b\w+(?:ine|ol|ide|ate|um)\b', re.IGNORECASE),
            'symptom': re.compile(r'\b(?:douleur|fièvre|toux|nausée|fatigue|mal de)\b', re.IGNORECASE),
            'body_part': re.compile(r'\b(?:cœur|poumon|foie|rein|cerveau|estomac)\b', re.IGNORECASE),
            'disease': re.compile(r'\b\w+(?:ite|ose|ie|isme|pathie)\b', re.IGNORECASE)
        }
        
        # Synonymes médicaux
        self.medical_synonyms = {
            'fr': {
                'fièvre': ['hyperthermie', 'température', 'pyrexie'],
                'douleur': ['mal', 'souffrance', 'algie'],
                'médicament': ['traitement', 'thérapie', 'remède'],
                'maladie': ['pathologie', 'affection', 'trouble']
            }
        }
        
        # Termes médicaux importants avec poids
        self.medical_term_weights = {
            'diagnostic': 1.5,
            'traitement': 1.4,
            'symptôme': 1.3,
            'prévention': 1.2,
            'médicament': 1.4,
            'maladie': 1.3
        }
    
    def index_documents(self, documents: List[IndexedDocument]) -> None:
        """
        Indexe une liste de documents pour la recherche
        
        Args:
            documents: Liste des documents à indexer
        """
        if not documents:
            logger.warning("Aucun document à indexer")
            return
        
        logger.info(f"Indexation de {len(documents)} documents...")
        start_time = time.time()
        
        # Stockage des documents
        for doc in documents:
            self.indexed_documents[doc.chunk_id] = doc
        
        # Construction de l'index FAISS
        self._build_faiss_index(documents)
        
        # Construction de l'index TF-IDF
        self._build_tfidf_index(documents)
        
        indexing_time = time.time() - start_time
        logger.info(f"Indexation terminée en {indexing_time:.2f}s")
    
    def _build_faiss_index(self, documents: List[IndexedDocument]) -> None:
        """Construit l'index FAISS pour la recherche vectorielle"""
        if not documents:
            return
        
        # Extraction des embeddings
        embeddings = np.array([doc.embedding for doc in documents]).astype('float32')
        dimension = embeddings.shape[1]
        
        # Création de l'index FAISS
        self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner Product pour cosine similarity
        self.faiss_index.add(embeddings)
        
        # Mapping des IDs
        self.faiss_id_mapping = {i: doc.chunk_id for i, doc in enumerate(documents)}
        
        logger.info(f"Index FAISS construit avec {len(documents)} vecteurs")
    
    def _build_tfidf_index(self, documents: List[IndexedDocument]) -> None:
        """Construit l'index TF-IDF pour la recherche par mots-clés"""
        if not documents:
            return
        
        # Extraction des textes
        texts = [doc.content for doc in documents]
        
        # Configuration du vectoriseur TF-IDF
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english' if self.language == 'en' else None,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        
        # Création de la matrice TF-IDF
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
        
        # Stockage des vecteurs TF-IDF dans les documents
        for i, doc in enumerate(documents):
            doc.tfidf_vector = self.tfidf_matrix[i].toarray()[0]
        
        logger.info(f"Index TF-IDF construit avec {len(documents)} documents")
    
    def search(self, query: Union[str, SearchQuery]) -> List[SearchResult]:
        """
        Effectue une recherche dans les documents indexés
        
        Args:
            query: Requête de recherche (string ou SearchQuery)
            
        Returns:
            Liste des résultats de recherche triés par pertinence
        """
        # Conversion en SearchQuery si nécessaire
        if isinstance(query, str):
            query = SearchQuery(text=query)
        
        logger.info(f"Recherche: '{query.text}' (types: {[t.value for t in query.search_types]})")
        start_time = time.time()
        
        all_results = []
        
        # Exécution des différents types de recherche
        for search_type in query.search_types:
            if search_type == SearchType.SEMANTIC:
                results = self._semantic_search(query)
            elif search_type == SearchType.KEYWORD:
                results = self._keyword_search(query)
            elif search_type == SearchType.HYBRID:
                results = self._hybrid_search(query)
            elif search_type == SearchType.MEDICAL_ENTITY:
                results = self._medical_entity_search(query)
            else:
                logger.warning(f"Type de recherche non supporté: {search_type}")
                continue
            
            # Ajout du type de recherche aux résultats
            for result in results:
                result.search_type = search_type
            
            all_results.extend(results)
            self.search_stats['search_types_used'][search_type.value] += 1
        
        # Fusion et déduplication des résultats
        merged_results = self._merge_and_deduplicate_results(all_results)
        
        # Application des filtres
        filtered_results = self._apply_filters(merged_results, query.filters)
        
        # Tri final par pertinence
        final_results = sorted(
            filtered_results, 
            key=lambda x: x.relevance_score, 
            reverse=True
        )[:query.max_results]
        
        # Filtrage par seuil de pertinence
        final_results = [
            result for result in final_results 
            if result.relevance_score >= query.min_relevance
        ]
        
        # Mise à jour des statistiques
        search_time = time.time() - start_time
        self.search_stats['total_searches'] += 1
        self.search_stats['avg_search_time'] = (
            (self.search_stats['avg_search_time'] * (self.search_stats['total_searches'] - 1) + search_time) /
            self.search_stats['total_searches']
        )
        self.search_stats['avg_results_returned'] = (
            (self.search_stats['avg_results_returned'] * (self.search_stats['total_searches'] - 1) + len(final_results)) /
            self.search_stats['total_searches']
        )
        
        logger.info(f"Recherche terminée: {len(final_results)} résultats en {search_time:.3f}s")
        return final_results
    
    def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Recherche sémantique basée sur les embeddings"""
        if self.faiss_index is None or self.embedding_model is None:
            logger.warning("Index FAISS ou modèle d'embeddings non disponible")
            return []
        
        # Génération de l'embedding de la requête
        query_embedding = self.embedding_model.encode([query.text])[0]
        query_embedding = query_embedding.astype('float32').reshape(1, -1)
        
        # Recherche dans l'index FAISS
        k = min(query.max_results * 3, len(self.indexed_documents))  # Récupérer plus pour le reranking
        scores, indices = self.faiss_index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # Pas de résultat
                continue
            
            chunk_id = self.faiss_id_mapping[idx]
            doc = self.indexed_documents[chunk_id]
            
            # Calcul du score de pertinence sémantique
            relevance_score = self._calculate_semantic_relevance(
                query, doc, float(score)
            )
            
            result = SearchResult(
                document_id=doc.document_id,
                chunk_id=chunk_id,
                content=doc.content,
                relevance_score=relevance_score,
                search_type=SearchType.SEMANTIC,
                metadata=doc.metadata.copy(),
                sub_scores={'semantic_similarity': float(score)}
            )
            
            results.append(result)
        
        return results
    
    def _keyword_search(self, query: SearchQuery) -> List[SearchResult]:
        """Recherche par mots-clés avec TF-IDF"""
        if self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            logger.warning("Index TF-IDF non disponible")
            return []
        
        # Vectorisation de la requête
        query_vector = self.tfidf_vectorizer.transform([query.text])
        
        # Calcul des similarités
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
        
        # Récupération des meilleurs résultats
        top_indices = np.argsort(similarities)[::-1][:query.max_results * 2]
        
        results = []
        for idx in top_indices:
            if similarities[idx] <= 0:
                continue
            
            doc = list(self.indexed_documents.values())[idx]
            
            # Calcul du score de pertinence par mots-clés
            relevance_score = self._calculate_keyword_relevance(
                query, doc, similarities[idx]
            )
            
            # Mise en évidence des termes de recherche
            highlighted_content = self._highlight_keywords(doc.content, query.text)
            
            result = SearchResult(
                document_id=doc.document_id,
                chunk_id=doc.chunk_id,
                content=doc.content,
                relevance_score=relevance_score,
                search_type=SearchType.KEYWORD,
                metadata=doc.metadata.copy(),
                highlighted_content=highlighted_content,
                sub_scores={'tfidf_similarity': similarities[idx]}
            )
            
            results.append(result)
        
        return results
    
    def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Recherche hybride combinant sémantique et mots-clés"""
        # Exécution des recherches sémantique et par mots-clés
        semantic_query = SearchQuery(
            text=query.text,
            search_types=[SearchType.SEMANTIC],
            max_results=query.max_results * 2
        )
        keyword_query = SearchQuery(
            text=query.text,
            search_types=[SearchType.KEYWORD],
            max_results=query.max_results * 2
        )
        
        semantic_results = self._semantic_search(semantic_query)
        keyword_results = self._keyword_search(keyword_query)
        
        # Fusion des résultats avec pondération
        hybrid_results = []
        all_chunk_ids = set()
        
        # Collecte de tous les chunk_ids
        for result in semantic_results + keyword_results:
            all_chunk_ids.add(result.chunk_id)
        
        # Calcul des scores hybrides
        for chunk_id in all_chunk_ids:
            doc = self.indexed_documents[chunk_id]
            
            # Récupération des scores individuels
            semantic_score = 0.0
            keyword_score = 0.0
            
            for result in semantic_results:
                if result.chunk_id == chunk_id:
                    semantic_score = result.relevance_score
                    break
            
            for result in keyword_results:
                if result.chunk_id == chunk_id:
                    keyword_score = result.relevance_score
                    break
            
            # Calcul du score hybride pondéré
            hybrid_score = self._calculate_hybrid_relevance(
                query, doc, semantic_score, keyword_score
            )
            
            result = SearchResult(
                document_id=doc.document_id,
                chunk_id=chunk_id,
                content=doc.content,
                relevance_score=hybrid_score,
                search_type=SearchType.HYBRID,
                metadata=doc.metadata.copy(),
                sub_scores={
                    'semantic_score': semantic_score,
                    'keyword_score': keyword_score,
                    'hybrid_score': hybrid_score
                }
            )
            
            hybrid_results.append(result)
        
        return hybrid_results
    
    def _medical_entity_search(self, query: SearchQuery) -> List[SearchResult]:
        """Recherche basée sur les entités médicales"""
        # Extraction des entités médicales de la requête
        query_entities = self._extract_medical_entities(query.text)
        
        if not query_entities:
            return []
        
        results = []
        
        for chunk_id, doc in self.indexed_documents.items():
            # Calcul de la correspondance des entités médicales
            entity_match_score = self._calculate_entity_match(
                query_entities, doc.medical_entities
            )
            
            if entity_match_score > 0:
                relevance_score = self._calculate_medical_entity_relevance(
                    query, doc, entity_match_score
                )
                
                result = SearchResult(
                    document_id=doc.document_id,
                    chunk_id=chunk_id,
                    content=doc.content,
                    relevance_score=relevance_score,
                    search_type=SearchType.MEDICAL_ENTITY,
                    metadata=doc.metadata.copy(),
                    sub_scores={'entity_match': entity_match_score}
                )
                
                results.append(result)
        
        return results
    
    def _calculate_semantic_relevance(self, 
                                    query: SearchQuery, 
                                    doc: IndexedDocument, 
                                    similarity_score: float) -> float:
        """Calcule le score de pertinence sémantique"""
        base_score = similarity_score
        
        # Bonus pour les termes médicaux dans le contexte
        medical_bonus = self._calculate_medical_context_bonus(query.text, doc.content)
        
        # Bonus pour la longueur appropriée du document
        length_bonus = self._calculate_length_bonus(doc.content)
        
        # Bonus basé sur les métadonnées
        metadata_bonus = self._calculate_metadata_bonus(query, doc.metadata)
        
        final_score = base_score * (1 + medical_bonus + length_bonus + metadata_bonus)
        return min(1.0, final_score)
    
    def _calculate_keyword_relevance(self, 
                                   query: SearchQuery, 
                                   doc: IndexedDocument, 
                                   tfidf_score: float) -> float:
        """Calcule le score de pertinence par mots-clés"""
        base_score = tfidf_score
        
        # Bonus pour les correspondances exactes
        exact_match_bonus = self._calculate_exact_match_bonus(query.text, doc.content)
        
        # Bonus pour les termes médicaux
        medical_term_bonus = self._calculate_medical_term_bonus(query.text, doc.content)
        
        # Pénalité pour les documents trop courts ou trop longs
        length_penalty = self._calculate_length_penalty(doc.content)
        
        final_score = base_score * (1 + exact_match_bonus + medical_term_bonus - length_penalty)
        return min(1.0, max(0.0, final_score))
    
    def _calculate_hybrid_relevance(self, 
                                  query: SearchQuery, 
                                  doc: IndexedDocument,
                                  semantic_score: float, 
                                  keyword_score: float) -> float:
        """Calcule le score de pertinence hybride"""
        # Pondération adaptative basée sur la requête
        semantic_weight, keyword_weight = self._calculate_adaptive_weights(query.text)
        
        # Score hybride de base
        base_score = (semantic_score * semantic_weight + keyword_score * keyword_weight)
        
        # Bonus de synergie si les deux scores sont élevés
        synergy_bonus = 0.0
        if semantic_score > 0.7 and keyword_score > 0.7:
            synergy_bonus = 0.1 * min(semantic_score, keyword_score)
        
        # Bonus pour la cohérence des résultats
        consistency_bonus = self._calculate_consistency_bonus(semantic_score, keyword_score)
        
        final_score = base_score + synergy_bonus + consistency_bonus
        return min(1.0, final_score)
    
    def _calculate_medical_entity_relevance(self, 
                                          query: SearchQuery, 
                                          doc: IndexedDocument,
                                          entity_match_score: float) -> float:
        """Calcule le score de pertinence basé sur les entités médicales"""
        base_score = entity_match_score
        
        # Bonus pour la densité d'entités médicales
        entity_density = len(doc.medical_entities) / max(1, len(doc.content.split()))
        density_bonus = min(0.2, entity_density * 10)
        
        # Bonus pour les entités rares ou importantes
        rarity_bonus = self._calculate_entity_rarity_bonus(doc.medical_entities)
        
        final_score = base_score + density_bonus + rarity_bonus
        return min(1.0, final_score)
    
    def _calculate_medical_context_bonus(self, query_text: str, doc_content: str) -> float:
        """Calcule le bonus pour le contexte médical"""
        bonus = 0.0
        
        # Recherche de termes médicaux dans la requête et le document
        query_lower = query_text.lower()
        doc_lower = doc_content.lower()
        
        for term, weight in self.medical_term_weights.items():
            if term in query_lower and term in doc_lower:
                bonus += 0.05 * weight
        
        return min(0.3, bonus)
    
    def _calculate_length_bonus(self, content: str) -> float:
        """Calcule le bonus basé sur la longueur du contenu"""
        word_count = len(content.split())
        
        # Longueur optimale entre 100 et 500 mots
        if 100 <= word_count <= 500:
            return 0.1
        elif 50 <= word_count < 100 or 500 < word_count <= 1000:
            return 0.05
        else:
            return 0.0
    
    def _calculate_metadata_bonus(self, query: SearchQuery, metadata: Dict[str, Any]) -> float:
        """Calcule le bonus basé sur les métadonnées"""
        bonus = 0.0
        
        # Bonus pour la correspondance du domaine médical
        if query.medical_context and 'medical_domain' in metadata:
            if query.medical_context.lower() in metadata['medical_domain'].lower():
                bonus += 0.15
        
        # Bonus pour la source fiable
        if metadata.get('source_credibility', 0) > 0.8:
            bonus += 0.1
        
        # Bonus pour la fraîcheur du contenu
        if metadata.get('is_recent', False):
            bonus += 0.05
        
        return bonus
    
    def _calculate_exact_match_bonus(self, query_text: str, doc_content: str) -> float:
        """Calcule le bonus pour les correspondances exactes"""
        query_words = set(query_text.lower().split())
        doc_words = set(doc_content.lower().split())
        
        exact_matches = len(query_words.intersection(doc_words))
        total_query_words = len(query_words)
        
        if total_query_words == 0:
            return 0.0
        
        match_ratio = exact_matches / total_query_words
        return min(0.2, match_ratio * 0.3)
    
    def _calculate_medical_term_bonus(self, query_text: str, doc_content: str) -> float:
        """Calcule le bonus pour les termes médicaux"""
        bonus = 0.0
        
        # Recherche de patterns médicaux
        for pattern_type, pattern in self.medical_patterns.items():
            query_matches = len(pattern.findall(query_text))
            doc_matches = len(pattern.findall(doc_content))
            
            if query_matches > 0 and doc_matches > 0:
                bonus += 0.05
        
        return min(0.15, bonus)
    
    def _calculate_length_penalty(self, content: str) -> float:
        """Calcule la pénalité basée sur la longueur"""
        word_count = len(content.split())
        
        if word_count < 20:  # Trop court
            return 0.2
        elif word_count > 2000:  # Trop long
            return 0.1
        else:
            return 0.0
    
    def _calculate_adaptive_weights(self, query_text: str) -> Tuple[float, float]:
        """Calcule les poids adaptatifs pour la recherche hybride"""
        # Analyse de la requête pour déterminer les poids optimaux
        query_lower = query_text.lower()
        
        # Si la requête contient beaucoup de termes médicaux spécifiques
        medical_term_count = sum(1 for term in self.medical_term_weights.keys() if term in query_lower)
        
        if medical_term_count >= 2:
            # Favoriser la recherche sémantique pour les requêtes médicales complexes
            return 0.7, 0.3
        elif len(query_text.split()) <= 3:
            # Favoriser la recherche par mots-clés pour les requêtes courtes
            return 0.4, 0.6
        else:
            # Équilibré par défaut
            return 0.6, 0.4
    
    def _calculate_consistency_bonus(self, semantic_score: float, keyword_score: float) -> float:
        """Calcule le bonus de cohérence entre les scores"""
        # Bonus si les deux scores sont cohérents
        score_diff = abs(semantic_score - keyword_score)
        
        if score_diff < 0.2:
            return 0.05  # Scores cohérents
        elif score_diff > 0.6:
            return -0.05  # Scores très différents
        else:
            return 0.0
    
    def _extract_medical_entities(self, text: str) -> List[str]:
        """Extrait les entités médicales du texte"""
        entities = []
        text_lower = text.lower()
        
        # Recherche dans le vocabulaire médical
        for term in self.medical_vocabulary:
            if term.lower() in text_lower:
                entities.append(term)
        
        # Recherche avec les patterns médicaux
        for pattern_type, pattern in self.medical_patterns.items():
            matches = pattern.findall(text)
            entities.extend(matches)
        
        return list(set(entities))
    
    def _calculate_entity_match(self, query_entities: List[str], doc_entities: List[str]) -> float:
        """Calcule le score de correspondance des entités"""
        if not query_entities:
            return 0.0
        
        query_set = set(entity.lower() for entity in query_entities)
        doc_set = set(entity.lower() for entity in doc_entities)
        
        intersection = query_set.intersection(doc_set)
        union = query_set.union(doc_set)
        
        if not union:
            return 0.0
        
        # Score de Jaccard
        jaccard_score = len(intersection) / len(union)
        
        # Bonus pour les correspondances exactes
        exact_matches = len(intersection)
        exact_bonus = exact_matches / len(query_set) if query_set else 0
        
        return min(1.0, jaccard_score + exact_bonus * 0.2)
    
    def _calculate_entity_rarity_bonus(self, entities: List[str]) -> float:
        """Calcule le bonus pour les entités rares"""
        # Simulation de rareté basée sur la longueur des termes
        # En pratique, ceci pourrait être basé sur des statistiques réelles
        bonus = 0.0
        
        for entity in entities:
            if len(entity) > 10:  # Termes longs souvent plus spécifiques
                bonus += 0.02
            elif entity.lower() in self.medical_term_weights:
                bonus += 0.01
        
        return min(0.1, bonus)
    
    def _highlight_keywords(self, content: str, query: str) -> str:
        """Met en évidence les mots-clés de la requête dans le contenu"""
        query_words = query.lower().split()
        highlighted_content = content
        
        for word in query_words:
            if len(word) > 2:  # Ignorer les mots très courts
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                highlighted_content = pattern.sub(
                    f"**{word}**", 
                    highlighted_content
                )
        
        return highlighted_content
    
    def _merge_and_deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Fusionne et déduplique les résultats de recherche"""
        # Groupement par chunk_id
        grouped_results = defaultdict(list)
        for result in results:
            grouped_results[result.chunk_id].append(result)
        
        # Fusion des résultats pour chaque chunk
        merged_results = []
        for chunk_id, chunk_results in grouped_results.items():
            if len(chunk_results) == 1:
                merged_results.append(chunk_results[0])
            else:
                # Fusion de plusieurs résultats pour le même chunk
                merged_result = self._merge_chunk_results(chunk_results)
                merged_results.append(merged_result)
        
        return merged_results
    
    def _merge_chunk_results(self, results: List[SearchResult]) -> SearchResult:
        """Fusionne plusieurs résultats pour le même chunk"""
        # Utilisation du résultat avec le meilleur score comme base
        best_result = max(results, key=lambda x: x.relevance_score)
        
        # Calcul du score fusionné
        scores = [r.relevance_score for r in results]
        merged_score = max(scores)  # Ou moyenne pondérée selon les besoins
        
        # Fusion des sub_scores
        merged_sub_scores = {}
        for result in results:
            merged_sub_scores.update(result.sub_scores)
        
        # Fusion des types de recherche
        search_types = [r.search_type for r in results]
        merged_search_type = SearchType.HYBRID if len(set(search_types)) > 1 else search_types[0]
        
        return SearchResult(
            document_id=best_result.document_id,
            chunk_id=best_result.chunk_id,
            content=best_result.content,
            relevance_score=merged_score,
            search_type=merged_search_type,
            metadata=best_result.metadata,
            highlighted_content=best_result.highlighted_content,
            sub_scores=merged_sub_scores,
            explanation=f"Résultat fusionné de {len(results)} recherches"
        )
    
    def _apply_filters(self, results: List[SearchResult], filters: Dict[str, Any]) -> List[SearchResult]:
        """Applique les filtres aux résultats de recherche"""
        if not filters:
            return results
        
        filtered_results = []
        
        for result in results:
            include_result = True
            
            # Filtre par domaine médical
            if 'medical_domain' in filters:
                required_domain = filters['medical_domain'].lower()
                result_domain = result.metadata.get('medical_domain', '').lower()
                if required_domain not in result_domain:
                    include_result = False
            
            # Filtre par source
            if 'source' in filters:
                required_source = filters['source'].lower()
                result_source = result.metadata.get('source', '').lower()
                if required_source not in result_source:
                    include_result = False
            
            # Filtre par date
            if 'min_date' in filters:
                min_date = filters['min_date']
                result_date = result.metadata.get('date')
                if result_date and result_date < min_date:
                    include_result = False
            
            # Filtre par longueur de contenu
            if 'min_length' in filters:
                min_length = filters['min_length']
                if len(result.content) < min_length:
                    include_result = False
            
            if include_result:
                filtered_results.append(result)
        
        return filtered_results
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de recherche"""
        return {
            'total_indexed_documents': len(self.indexed_documents),
            'search_stats': self.search_stats.copy(),
            'index_info': {
                'has_faiss_index': self.faiss_index is not None,
                'has_tfidf_index': self.tfidf_vectorizer is not None,
                'faiss_vectors': len(self.faiss_id_mapping),
                'tfidf_features': self.tfidf_vectorizer.get_feature_names_out().shape[0] if self.tfidf_vectorizer else 0
            },
            'medical_vocabulary_size': len(self.medical_vocabulary)
        }
    
    def explain_search_result(self, result: SearchResult) -> str:
        """Génère une explication pour un résultat de recherche"""
        explanation_parts = []
        
        explanation_parts.append(f"Score de pertinence: {result.relevance_score:.3f}")
        explanation_parts.append(f"Type de recherche: {result.search_type.value}")
        
        if result.sub_scores:
            explanation_parts.append("Scores détaillés:")
            for score_type, score_value in result.sub_scores.items():
                explanation_parts.append(f"  - {score_type}: {score_value:.3f}")
        
        if result.metadata:
            relevant_metadata = {
                k: v for k, v in result.metadata.items() 
                if k in ['medical_domain', 'source', 'date', 'source_credibility']
            }
            if relevant_metadata:
                explanation_parts.append("Métadonnées:")
                for key, value in relevant_metadata.items():
                    explanation_parts.append(f"  - {key}: {value}")
        
        return "\n".join(explanation_parts)

def main():
    """Fonction de test du système de recherche sémantique"""
    # Simulation de documents indexés
    from sentence_transformers import SentenceTransformer
    
    # Initialisation du modèle d'embeddings
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    # Initialisation du système de recherche
    search_system = MedicalSemanticSearch(
        embedding_model=model,
        language="fr",
        medical_vocabulary=["paludisme", "fièvre", "diagnostic", "traitement", "médicament"]
    )
    
    # Documents de test
    test_documents = [
        "Le paludisme est une maladie transmise par les moustiques anophèles. Les symptômes incluent fièvre, frissons et maux de tête.",
        "Le diagnostic du paludisme se fait par examen microscopique du sang ou tests rapides. Un diagnostic précoce est essentiel.",
        "Le traitement du paludisme utilise des médicaments antipaludiques comme l'artémisinine. La posologie dépend de la gravité.",
        "La prévention du paludisme comprend l'utilisation de moustiquaires imprégnées et la chimioprophylaxie pour les voyageurs.",
        "Le diabète de type 2 est une maladie métabolique chronique caractérisée par une résistance à l'insuline.",
        "L'hypertension artérielle est un facteur de risque majeur pour les maladies cardiovasculaires."
    ]
    
    # Création des documents indexés
    indexed_docs = []
    for i, content in enumerate(test_documents):
        embedding = model.encode([content])[0]
        doc = IndexedDocument(
            document_id=f"doc_{i}",
            chunk_id=f"chunk_{i}",
            content=content,
            embedding=embedding,
            keywords=content.lower().split(),
            medical_entities=search_system._extract_medical_entities(content),
            metadata={
                'medical_domain': 'infectious_diseases' if 'paludisme' in content else 'general',
                'source': 'medical_textbook',
                'source_credibility': 0.9
            }
        )
        indexed_docs.append(doc)
    
    # Indexation des documents
    search_system.index_documents(indexed_docs)
    
    # Tests de recherche
    test_queries = [
        "symptômes du paludisme",
        "diagnostic et traitement",
        "prévention maladie",
        "diabète insuline"
    ]
    
    print("\n=== TESTS DE RECHERCHE SÉMANTIQUE ===")
    
    for query_text in test_queries:
        print(f"\n--- Requête: '{query_text}' ---")
        
        # Recherche hybride
        query = SearchQuery(
            text=query_text,
            search_types=[SearchType.HYBRID],
            max_results=3
        )
        
        results = search_system.search(query)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result.relevance_score:.3f}")
            print(f"   Type: {result.search_type.value}")
            print(f"   Contenu: {result.content[:100]}...")
            if result.sub_scores:
                print(f"   Scores détaillés: {result.sub_scores}")
    
    # Statistiques
    stats = search_system.get_search_statistics()
    print(f"\n=== STATISTIQUES ===")
    print(f"Documents indexés: {stats['total_indexed_documents']}")
    print(f"Recherches effectuées: {stats['search_stats']['total_searches']}")
    print(f"Temps moyen de recherche: {stats['search_stats']['avg_search_time']:.3f}s")

if __name__ == "__main__":
    main()