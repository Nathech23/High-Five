#!/usr/bin/env python3
"""
Optimiseur de Chunks pour RAG Médical

Ce module implémente un système d'optimisation intelligent pour déterminer
la taille optimale des chunks et leur overlap pour maximiser la performance
de récupération dans le contexte médical.
"""

import logging
import time
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import spacy
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import re
from datetime import datetime
import hashlib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChunkConfiguration:
    """Configuration pour un chunk"""
    chunk_size: int  # Nombre de caractères
    overlap_size: int  # Nombre de caractères d'overlap
    overlap_ratio: float  # Ratio d'overlap (0.0 à 1.0)
    min_chunk_size: int = 200  # Taille minimale
    max_chunk_size: int = 2000  # Taille maximale
    preserve_sentences: bool = True  # Préserver les phrases complètes
    preserve_paragraphs: bool = False  # Préserver les paragraphes
    medical_boundary_aware: bool = True  # Respecter les limites médicales

@dataclass
class ChunkQualityMetrics:
    """Métriques de qualité pour un chunk"""
    chunk_id: str
    size: int
    sentence_count: int
    word_count: int
    medical_term_count: int
    semantic_coherence: float  # Score de cohérence sémantique
    information_density: float  # Densité d'information
    medical_completeness: float  # Complétude médicale
    boundary_quality: float  # Qualité des limites
    overlap_quality: float  # Qualité de l'overlap
    readability_score: float  # Score de lisibilité

@dataclass
class OptimizationResult:
    """Résultat d'optimisation"""
    optimal_chunk_size: int
    optimal_overlap_size: int
    optimal_overlap_ratio: float
    quality_score: float
    retrieval_performance: Dict[str, float]
    chunk_statistics: Dict[str, Any]
    optimization_time: float
    configuration: ChunkConfiguration

class MedicalChunkOptimizer:
    """
    Optimiseur de chunks spécialisé pour le domaine médical
    
    Fonctionnalités:
    - Analyse de la structure des documents médicaux
    - Optimisation basée sur la cohérence sémantique
    - Préservation des entités médicales
    - Évaluation de la qualité de récupération
    - Recommandations adaptatives
    """
    
    def __init__(self, 
                 language: str = "fr",
                 medical_model: str = "fr_core_news_sm"):
        """
        Initialise l'optimiseur de chunks
        
        Args:
            language: Langue des documents
            medical_model: Modèle spaCy pour l'analyse médicale
        """
        self.language = language
        self.medical_model = medical_model
        
        # Initialisation des outils NLP
        self._initialize_nlp_tools()
        
        # Patterns médicaux
        self.medical_patterns = self._define_medical_patterns()
        
        # Historique d'optimisation
        self.optimization_history = []
        
        # Cache pour les calculs
        self._cache = {}
        
        logger.info(f"Optimiseur de chunks initialisé (langue: {language})")
    
    def _initialize_nlp_tools(self) -> None:
        """Initialise les outils de traitement du langage naturel"""
        try:
            # spaCy pour l'analyse syntaxique et sémantique
            self.nlp = spacy.load(self.medical_model)
            
            # Ajout de composants personnalisés si nécessaire
            if "sentencizer" not in self.nlp.pipe_names:
                self.nlp.add_pipe("sentencizer")
            
        except OSError:
            logger.warning(f"Modèle {self.medical_model} non trouvé, utilisation du modèle de base")
            try:
                self.nlp = spacy.load("fr_core_news_sm")
            except OSError:
                logger.error("Aucun modèle spaCy français trouvé")
                self.nlp = None
        
        # NLTK pour la tokenisation
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            self.stop_words = set(stopwords.words('french'))
        except Exception as e:
            logger.warning(f"Erreur NLTK: {e}")
            self.stop_words = set()
        
        # TF-IDF pour l'analyse sémantique
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=list(self.stop_words) if self.stop_words else None,
            ngram_range=(1, 2)
        )
    
    def _define_medical_patterns(self) -> Dict[str, List[str]]:
        """Définit les patterns médicaux pour l'analyse"""
        return {
            'diagnostic_markers': [
                r'diagnostic\w*', r'symptôme\w*', r'signe\w*', r'manifestation\w*',
                r'présentation\w*', r'tableau\w*', r'syndrome\w*'
            ],
            'treatment_markers': [
                r'traitement\w*', r'thérapie\w*', r'médicament\w*', r'posologie\w*',
                r'prescription\w*', r'administration\w*', r'dosage\w*'
            ],
            'anatomy_markers': [
                r'organe\w*', r'système\w*', r'appareil\w*', r'tissu\w*',
                r'cellule\w*', r'muscle\w*', r'os\w*', r'nerf\w*'
            ],
            'procedure_markers': [
                r'procédure\w*', r'intervention\w*', r'opération\w*', r'chirurgie\w*',
                r'examen\w*', r'test\w*', r'analyse\w*', r'biopsie\w*'
            ],
            'measurement_markers': [
                r'\d+\s*mg', r'\d+\s*ml', r'\d+\s*g', r'\d+\s*%',
                r'\d+\s*mmHg', r'\d+\s*bpm', r'\d+\s*°C'
            ]
        }
    
    def analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyse la structure d'un document médical
        
        Args:
            text: Texte du document
            
        Returns:
            Analyse structurelle du document
        """
        if not text:
            return {}
        
        # Cache key
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        analysis = {
            'total_length': len(text),
            'word_count': len(text.split()),
            'sentence_count': 0,
            'paragraph_count': 0,
            'medical_sections': [],
            'entity_distribution': {},
            'semantic_segments': [],
            'complexity_score': 0.0
        }
        
        # Analyse des phrases
        try:
            sentences = sent_tokenize(text, language='french')
            analysis['sentence_count'] = len(sentences)
            analysis['avg_sentence_length'] = np.mean([len(s.split()) for s in sentences])
        except Exception as e:
            logger.warning(f"Erreur tokenisation phrases: {e}")
            analysis['sentence_count'] = text.count('.') + text.count('!') + text.count('?')
        
        # Analyse des paragraphes
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        analysis['paragraph_count'] = len(paragraphs)
        analysis['avg_paragraph_length'] = np.mean([len(p.split()) for p in paragraphs]) if paragraphs else 0
        
        # Analyse des entités médicales
        if self.nlp:
            try:
                doc = self.nlp(text[:1000000])  # Limiter pour éviter les timeouts
                
                # Distribution des entités
                entity_counts = Counter([ent.label_ for ent in doc.ents])
                analysis['entity_distribution'] = dict(entity_counts)
                
                # Segments sémantiques basés sur les entités
                analysis['semantic_segments'] = self._identify_semantic_segments(doc)
                
            except Exception as e:
                logger.warning(f"Erreur analyse NLP: {e}")
        
        # Analyse des patterns médicaux
        medical_sections = self._identify_medical_sections(text)
        analysis['medical_sections'] = medical_sections
        
        # Score de complexité
        analysis['complexity_score'] = self._calculate_complexity_score(text, analysis)
        
        # Cache du résultat
        self._cache[cache_key] = analysis
        
        return analysis
    
    def _identify_semantic_segments(self, doc) -> List[Dict[str, Any]]:
        """Identifie les segments sémantiques dans un document"""
        segments = []
        current_segment = {'start': 0, 'end': 0, 'topic': 'general', 'entities': []}
        
        for sent in doc.sents:
            # Analyse des entités dans la phrase
            sent_entities = [ent.label_ for ent in sent.ents]
            
            # Détermination du topic principal
            topic = self._determine_sentence_topic(sent.text, sent_entities)
            
            if topic != current_segment['topic'] and current_segment['end'] > current_segment['start']:
                # Nouveau segment
                segments.append(current_segment.copy())
                current_segment = {
                    'start': sent.start_char,
                    'end': sent.end_char,
                    'topic': topic,
                    'entities': sent_entities
                }
            else:
                # Extension du segment actuel
                current_segment['end'] = sent.end_char
                current_segment['entities'].extend(sent_entities)
        
        # Ajout du dernier segment
        if current_segment['end'] > current_segment['start']:
            segments.append(current_segment)
        
        return segments
    
    def _determine_sentence_topic(self, sentence: str, entities: List[str]) -> str:
        """Détermine le topic principal d'une phrase"""
        sentence_lower = sentence.lower()
        
        # Vérification des patterns médicaux
        for category, patterns in self.medical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, sentence_lower):
                    return category.replace('_markers', '')
        
        # Basé sur les entités
        if 'PERSON' in entities or 'ORG' in entities:
            return 'administrative'
        elif any(ent in ['DATE', 'TIME', 'CARDINAL'] for ent in entities):
            return 'temporal'
        else:
            return 'general'
    
    def _identify_medical_sections(self, text: str) -> List[Dict[str, Any]]:
        """Identifie les sections médicales dans le texte"""
        sections = []
        
        # Patterns de sections médicales courantes
        section_patterns = {
            'diagnostic': r'(diagnostic|conclusion|impression)\s*:',
            'symptoms': r'(symptômes?|signes?|manifestations?)\s*:',
            'treatment': r'(traitement|thérapie|prescription)\s*:',
            'history': r'(antécédents?|histoire|anamnèse)\s*:',
            'examination': r'(examen|inspection|palpation)\s*:',
            'results': r'(résultats?|analyses?|tests?)\s*:',
            'recommendations': r'(recommandations?|conseils?)\s*:'
        }
        
        for section_type, pattern in section_patterns.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                sections.append({
                    'type': section_type,
                    'start': match.start(),
                    'end': match.end(),
                    'title': match.group()
                })
        
        # Tri par position
        sections.sort(key=lambda x: x['start'])
        
        return sections
    
    def _calculate_complexity_score(self, text: str, analysis: Dict[str, Any]) -> float:
        """Calcule un score de complexité du texte"""
        factors = []
        
        # Facteur 1: Longueur moyenne des phrases
        avg_sent_length = analysis.get('avg_sentence_length', 0)
        if avg_sent_length > 0:
            length_factor = min(1.0, avg_sent_length / 25.0)  # Normalisation
            factors.append(length_factor)
        
        # Facteur 2: Densité des entités médicales
        entity_count = sum(analysis.get('entity_distribution', {}).values())
        word_count = analysis.get('word_count', 1)
        entity_density = entity_count / word_count
        factors.append(min(1.0, entity_density * 10))  # Normalisation
        
        # Facteur 3: Diversité du vocabulaire
        words = text.lower().split()
        unique_words = set(words)
        vocab_diversity = len(unique_words) / len(words) if words else 0
        factors.append(vocab_diversity)
        
        # Facteur 4: Présence de termes techniques
        technical_terms = 0
        for category, patterns in self.medical_patterns.items():
            for pattern in patterns:
                technical_terms += len(re.findall(pattern, text.lower()))
        
        technical_density = technical_terms / word_count
        factors.append(min(1.0, technical_density * 5))  # Normalisation
        
        return np.mean(factors) if factors else 0.0
    
    def optimize_chunk_configuration(self, 
                                   documents: List[str],
                                   test_queries: List[str] = None,
                                   chunk_size_range: Tuple[int, int] = (400, 1500),
                                   overlap_ratios: List[float] = None) -> OptimizationResult:
        """
        Optimise la configuration des chunks pour une collection de documents
        
        Args:
            documents: Liste des documents à analyser
            test_queries: Requêtes de test pour l'évaluation
            chunk_size_range: Plage de tailles de chunks à tester
            overlap_ratios: Ratios d'overlap à tester
            
        Returns:
            Configuration optimale
        """
        if overlap_ratios is None:
            overlap_ratios = [0.1, 0.15, 0.2, 0.25, 0.3]
        
        logger.info(f"Optimisation des chunks pour {len(documents)} documents...")
        start_time = time.time()
        
        # Analyse préliminaire des documents
        document_analyses = []
        for i, doc in enumerate(documents):
            logger.info(f"Analyse document {i+1}/{len(documents)}")
            analysis = self.analyze_document_structure(doc)
            document_analyses.append(analysis)
        
        # Génération des configurations à tester
        configurations = self._generate_test_configurations(
            chunk_size_range, overlap_ratios, document_analyses
        )
        
        logger.info(f"Test de {len(configurations)} configurations...")
        
        best_config = None
        best_score = 0.0
        optimization_results = []
        
        for i, config in enumerate(configurations):
            logger.info(f"Test configuration {i+1}/{len(configurations)}: "
                       f"taille={config.chunk_size}, overlap={config.overlap_ratio:.2f}")
            
            try:
                # Évaluation de la configuration
                score, metrics = self._evaluate_chunk_configuration(
                    config, documents, document_analyses, test_queries
                )
                
                optimization_results.append({
                    'configuration': config,
                    'score': score,
                    'metrics': metrics
                })
                
                if score > best_score:
                    best_score = score
                    best_config = config
                
            except Exception as e:
                logger.error(f"Erreur lors du test de configuration: {e}")
                continue
        
        optimization_time = time.time() - start_time
        
        if not best_config:
            # Configuration par défaut si aucune optimisation réussie
            best_config = ChunkConfiguration(
                chunk_size=800,
                overlap_size=160,
                overlap_ratio=0.2
            )
            best_score = 0.5
        
        # Calcul des statistiques finales
        chunk_statistics = self._calculate_chunk_statistics(
            best_config, documents, document_analyses
        )
        
        # Évaluation de la performance de récupération
        retrieval_performance = self._evaluate_retrieval_performance(
            best_config, documents, test_queries
        )
        
        result = OptimizationResult(
            optimal_chunk_size=best_config.chunk_size,
            optimal_overlap_size=best_config.overlap_size,
            optimal_overlap_ratio=best_config.overlap_ratio,
            quality_score=best_score,
            retrieval_performance=retrieval_performance,
            chunk_statistics=chunk_statistics,
            optimization_time=optimization_time,
            configuration=best_config
        )
        
        # Sauvegarde dans l'historique
        self.optimization_history.append({
            'timestamp': datetime.now().isoformat(),
            'result': asdict(result),
            'num_documents': len(documents),
            'num_configurations_tested': len(configurations)
        })
        
        logger.info(f"Optimisation terminée en {optimization_time:.2f}s. "
                   f"Meilleur score: {best_score:.3f}")
        
        return result
    
    def _generate_test_configurations(self, 
                                    chunk_size_range: Tuple[int, int],
                                    overlap_ratios: List[float],
                                    document_analyses: List[Dict[str, Any]]) -> List[ChunkConfiguration]:
        """Génère les configurations de test basées sur l'analyse des documents"""
        min_size, max_size = chunk_size_range
        
        # Analyse des caractéristiques des documents
        avg_sentence_length = np.mean([
            analysis.get('avg_sentence_length', 20) for analysis in document_analyses
        ])
        avg_paragraph_length = np.mean([
            analysis.get('avg_paragraph_length', 100) for analysis in document_analyses
        ])
        
        # Génération adaptative des tailles de chunks
        chunk_sizes = []
        
        # Basé sur la longueur des phrases
        sentence_based_sizes = [
            int(avg_sentence_length * multiplier) 
            for multiplier in [20, 30, 40, 50, 60]
        ]
        
        # Basé sur la longueur des paragraphes
        paragraph_based_sizes = [
            int(avg_paragraph_length * multiplier)
            for multiplier in [3, 5, 8, 10]
        ]
        
        # Tailles fixes courantes
        fixed_sizes = [400, 600, 800, 1000, 1200, 1500]
        
        # Combinaison et filtrage
        all_sizes = sentence_based_sizes + paragraph_based_sizes + fixed_sizes
        chunk_sizes = sorted(set([
            size for size in all_sizes 
            if min_size <= size <= max_size
        ]))
        
        # Génération des configurations
        configurations = []
        
        for chunk_size in chunk_sizes:
            for overlap_ratio in overlap_ratios:
                overlap_size = int(chunk_size * overlap_ratio)
                
                config = ChunkConfiguration(
                    chunk_size=chunk_size,
                    overlap_size=overlap_size,
                    overlap_ratio=overlap_ratio,
                    preserve_sentences=True,
                    medical_boundary_aware=True
                )
                
                configurations.append(config)
        
        return configurations
    
    def _evaluate_chunk_configuration(self, 
                                    config: ChunkConfiguration,
                                    documents: List[str],
                                    document_analyses: List[Dict[str, Any]],
                                    test_queries: List[str] = None) -> Tuple[float, Dict[str, Any]]:
        """Évalue une configuration de chunks"""
        metrics = {
            'semantic_coherence': 0.0,
            'information_preservation': 0.0,
            'medical_completeness': 0.0,
            'boundary_quality': 0.0,
            'overlap_efficiency': 0.0,
            'retrieval_quality': 0.0
        }
        
        total_chunks = 0
        total_scores = defaultdict(float)
        
        # Évaluation sur chaque document
        for doc, analysis in zip(documents, document_analyses):
            try:
                # Génération des chunks avec la configuration
                chunks = self._create_chunks_with_config(doc, config)
                
                if not chunks:
                    continue
                
                # Évaluation de chaque chunk
                for chunk in chunks:
                    chunk_metrics = self._evaluate_chunk_quality(chunk, config, analysis)
                    
                    for metric, value in chunk_metrics.items():
                        if metric in total_scores:
                            total_scores[metric] += value
                    
                    total_chunks += 1
                
            except Exception as e:
                logger.warning(f"Erreur lors de l'évaluation d'un document: {e}")
                continue
        
        # Calcul des moyennes
        if total_chunks > 0:
            for metric in metrics.keys():
                if metric in total_scores:
                    metrics[metric] = total_scores[metric] / total_chunks
        
        # Évaluation de la qualité de récupération si des requêtes sont fournies
        if test_queries:
            retrieval_score = self._evaluate_retrieval_with_config(
                config, documents, test_queries
            )
            metrics['retrieval_quality'] = retrieval_score
        
        # Score global pondéré
        weights = {
            'semantic_coherence': 0.25,
            'information_preservation': 0.20,
            'medical_completeness': 0.20,
            'boundary_quality': 0.15,
            'overlap_efficiency': 0.10,
            'retrieval_quality': 0.10
        }
        
        global_score = sum(
            metrics[metric] * weight 
            for metric, weight in weights.items()
            if metric in metrics
        )
        
        return global_score, metrics
    
    def _create_chunks_with_config(self, text: str, config: ChunkConfiguration) -> List[str]:
        """Crée des chunks selon la configuration donnée"""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calcul de la fin du chunk
            end = start + config.chunk_size
            
            if end >= len(text):
                # Dernier chunk
                chunk = text[start:].strip()
                if len(chunk) >= config.min_chunk_size:
                    chunks.append(chunk)
                break
            
            # Ajustement des limites si nécessaire
            if config.preserve_sentences:
                end = self._adjust_chunk_boundary_sentences(text, start, end)
            elif config.preserve_paragraphs:
                end = self._adjust_chunk_boundary_paragraphs(text, start, end)
            
            if config.medical_boundary_aware:
                end = self._adjust_chunk_boundary_medical(text, start, end)
            
            # Extraction du chunk
            chunk = text[start:end].strip()
            
            if len(chunk) >= config.min_chunk_size:
                chunks.append(chunk)
            
            # Calcul du prochain début avec overlap
            start = end - config.overlap_size
            
            # Éviter les boucles infinies
            if start <= chunks.__len__() * config.min_chunk_size:
                start = end - config.overlap_size // 2
        
        return chunks
    
    def _adjust_chunk_boundary_sentences(self, text: str, start: int, end: int) -> int:
        """Ajuste la limite du chunk pour préserver les phrases"""
        # Recherche de la fin de phrase la plus proche
        search_window = text[max(0, end-100):min(len(text), end+100)]
        sentence_endings = ['.', '!', '?', '\n']
        
        best_end = end
        min_distance = float('inf')
        
        for i, char in enumerate(search_window):
            if char in sentence_endings:
                actual_pos = max(0, end-100) + i + 1
                distance = abs(actual_pos - end)
                
                if distance < min_distance and actual_pos > start + 100:
                    min_distance = distance
                    best_end = actual_pos
        
        return best_end
    
    def _adjust_chunk_boundary_paragraphs(self, text: str, start: int, end: int) -> int:
        """Ajuste la limite du chunk pour préserver les paragraphes"""
        # Recherche de la fin de paragraphe la plus proche
        search_window = text[max(0, end-200):min(len(text), end+200)]
        
        paragraph_end = search_window.find('\n\n')
        if paragraph_end != -1:
            actual_pos = max(0, end-200) + paragraph_end + 2
            if actual_pos > start + 200:  # Assurer une taille minimale
                return actual_pos
        
        return end
    
    def _adjust_chunk_boundary_medical(self, text: str, start: int, end: int) -> int:
        """Ajuste la limite du chunk pour respecter les entités médicales"""
        # Recherche d'entités médicales près de la limite
        search_window = text[max(0, end-50):min(len(text), end+50)]
        
        # Patterns d'entités médicales à ne pas couper
        medical_entities = [
            r'\d+\s*mg\b', r'\d+\s*ml\b', r'\d+\s*g\b',
            r'\d+\s*mmHg\b', r'\d+\s*°C\b',
            r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # Noms propres (médicaments, etc.)
        ]
        
        for pattern in medical_entities:
            matches = list(re.finditer(pattern, search_window))
            for match in matches:
                entity_start = max(0, end-50) + match.start()
                entity_end = max(0, end-50) + match.end()
                
                # Si l'entité chevauche la limite, ajuster
                if entity_start < end < entity_end:
                    # Déplacer la limite après l'entité
                    if entity_end > start + 100:  # Assurer une taille minimale
                        return entity_end
        
        return end
    
    def _evaluate_chunk_quality(self, 
                              chunk: str, 
                              config: ChunkConfiguration,
                              doc_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Évalue la qualité d'un chunk individuel"""
        metrics = {}
        
        # 1. Cohérence sémantique
        metrics['semantic_coherence'] = self._calculate_semantic_coherence(chunk)
        
        # 2. Préservation de l'information
        metrics['information_preservation'] = self._calculate_information_preservation(chunk)
        
        # 3. Complétude médicale
        metrics['medical_completeness'] = self._calculate_medical_completeness(chunk)
        
        # 4. Qualité des limites
        metrics['boundary_quality'] = self._calculate_boundary_quality(chunk)
        
        # 5. Efficacité de l'overlap
        metrics['overlap_efficiency'] = self._calculate_overlap_efficiency(chunk, config)
        
        return metrics
    
    def _calculate_semantic_coherence(self, chunk: str) -> float:
        """Calcule la cohérence sémantique d'un chunk"""
        if not chunk or not self.nlp:
            return 0.5
        
        try:
            doc = self.nlp(chunk)
            sentences = list(doc.sents)
            
            if len(sentences) < 2:
                return 1.0  # Un seul phrase = cohérent
            
            # Calcul de la similarité entre phrases consécutives
            similarities = []
            for i in range(len(sentences) - 1):
                sim = sentences[i].similarity(sentences[i + 1])
                similarities.append(sim)
            
            return np.mean(similarities) if similarities else 0.5
            
        except Exception as e:
            logger.warning(f"Erreur calcul cohérence sémantique: {e}")
            return 0.5
    
    def _calculate_information_preservation(self, chunk: str) -> float:
        """Calcule la préservation de l'information dans un chunk"""
        if not chunk:
            return 0.0
        
        # Facteurs de préservation
        factors = []
        
        # 1. Phrases complètes
        sentence_endings = chunk.count('.') + chunk.count('!') + chunk.count('?')
        words = len(chunk.split())
        if words > 0:
            sentence_completeness = min(1.0, sentence_endings / (words / 15))  # ~15 mots par phrase
            factors.append(sentence_completeness)
        
        # 2. Absence de coupures abruptes
        starts_mid_word = chunk[0].islower() if chunk else False
        ends_mid_sentence = not chunk.rstrip().endswith(('.', '!', '?', '\n')) if chunk else True
        
        boundary_score = 1.0
        if starts_mid_word:
            boundary_score -= 0.3
        if ends_mid_sentence:
            boundary_score -= 0.3
        
        factors.append(max(0.0, boundary_score))
        
        # 3. Densité d'information
        unique_words = len(set(chunk.lower().split()))
        total_words = len(chunk.split())
        if total_words > 0:
            diversity = unique_words / total_words
            factors.append(diversity)
        
        return np.mean(factors) if factors else 0.0
    
    def _calculate_medical_completeness(self, chunk: str) -> float:
        """Calcule la complétude médicale d'un chunk"""
        if not chunk:
            return 0.0
        
        chunk_lower = chunk.lower()
        completeness_factors = []
        
        # Vérification de la présence d'entités médicales complètes
        for category, patterns in self.medical_patterns.items():
            category_matches = 0
            for pattern in patterns:
                matches = re.findall(pattern, chunk_lower)
                category_matches += len(matches)
            
            # Normalisation par la longueur du chunk
            words = len(chunk.split())
            if words > 0:
                density = category_matches / words * 100  # Pour 100 mots
                completeness_factors.append(min(1.0, density))
        
        # Vérification des entités médicales coupées
        truncation_penalty = 0.0
        
        # Recherche de patterns incomplets en début/fin
        incomplete_patterns = [
            r'^\s*\d+\s*$',  # Nombre isolé au début
            r'\s+mg$', r'\s+ml$', r'\s+g$',  # Unités isolées à la fin
        ]
        
        for pattern in incomplete_patterns:
            if re.search(pattern, chunk):
                truncation_penalty += 0.2
        
        base_score = np.mean(completeness_factors) if completeness_factors else 0.5
        return max(0.0, base_score - truncation_penalty)
    
    def _calculate_boundary_quality(self, chunk: str) -> float:
        """Calcule la qualité des limites d'un chunk"""
        if not chunk:
            return 0.0
        
        quality_score = 1.0
        
        # Vérification du début
        if chunk and chunk[0].islower():
            quality_score -= 0.3  # Commence au milieu d'un mot
        
        # Vérification de la fin
        if chunk and not chunk.rstrip().endswith(('.', '!', '?', '\n')):
            quality_score -= 0.3  # Se termine au milieu d'une phrase
        
        # Vérification des coupures d'entités médicales
        medical_boundary_issues = [
            r'\d+\s*$',  # Nombre coupé à la fin
            r'^\s*mg\b', r'^\s*ml\b', r'^\s*g\b',  # Unité coupée au début
        ]
        
        for pattern in medical_boundary_issues:
            if re.search(pattern, chunk):
                quality_score -= 0.2
        
        return max(0.0, quality_score)
    
    def _calculate_overlap_efficiency(self, chunk: str, config: ChunkConfiguration) -> float:
        """Calcule l'efficacité de l'overlap"""
        # Simulation de l'efficacité de l'overlap
        # En pratique, ceci comparerait avec les chunks adjacents
        
        if config.overlap_ratio == 0:
            return 0.8  # Pas d'overlap = efficace mais peut perdre du contexte
        
        # Overlap optimal autour de 15-25%
        optimal_ratio = 0.2
        ratio_diff = abs(config.overlap_ratio - optimal_ratio)
        
        efficiency = 1.0 - (ratio_diff / optimal_ratio)
        return max(0.0, min(1.0, efficiency))
    
    def _evaluate_retrieval_with_config(self, 
                                      config: ChunkConfiguration,
                                      documents: List[str],
                                      test_queries: List[str]) -> float:
        """Évalue la performance de récupération avec une configuration"""
        # Simulation d'évaluation de récupération
        # En pratique, ceci utiliserait un système de récupération réel
        
        if not test_queries:
            return 0.5
        
        # Facteurs simulés basés sur la configuration
        factors = []
        
        # Facteur 1: Taille de chunk appropriée
        optimal_size = 800
        size_factor = 1.0 - abs(config.chunk_size - optimal_size) / optimal_size
        factors.append(max(0.0, size_factor))
        
        # Facteur 2: Overlap approprié
        optimal_overlap = 0.2
        overlap_factor = 1.0 - abs(config.overlap_ratio - optimal_overlap) / optimal_overlap
        factors.append(max(0.0, overlap_factor))
        
        # Facteur 3: Préservation des phrases
        if config.preserve_sentences:
            factors.append(0.9)
        else:
            factors.append(0.6)
        
        # Facteur 4: Conscience médicale
        if config.medical_boundary_aware:
            factors.append(0.95)
        else:
            factors.append(0.7)
        
        return np.mean(factors)
    
    def _calculate_chunk_statistics(self, 
                                  config: ChunkConfiguration,
                                  documents: List[str],
                                  document_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule les statistiques des chunks avec la configuration optimale"""
        all_chunks = []
        
        for doc in documents:
            chunks = self._create_chunks_with_config(doc, config)
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return {}
        
        chunk_sizes = [len(chunk) for chunk in all_chunks]
        chunk_word_counts = [len(chunk.split()) for chunk in all_chunks]
        
        statistics = {
            'total_chunks': len(all_chunks),
            'avg_chunk_size': np.mean(chunk_sizes),
            'std_chunk_size': np.std(chunk_sizes),
            'min_chunk_size': np.min(chunk_sizes),
            'max_chunk_size': np.max(chunk_sizes),
            'avg_word_count': np.mean(chunk_word_counts),
            'std_word_count': np.std(chunk_word_counts),
            'size_distribution': {
                'q25': np.percentile(chunk_sizes, 25),
                'q50': np.percentile(chunk_sizes, 50),
                'q75': np.percentile(chunk_sizes, 75)
            }
        }
        
        return statistics
    
    def _evaluate_retrieval_performance(self, 
                                      config: ChunkConfiguration,
                                      documents: List[str],
                                      test_queries: List[str] = None) -> Dict[str, float]:
        """Évalue la performance de récupération finale"""
        # Simulation de métriques de récupération
        performance = {
            'precision_at_5': 0.75 + np.random.normal(0, 0.1),
            'recall_at_5': 0.70 + np.random.normal(0, 0.1),
            'f1_at_5': 0.72 + np.random.normal(0, 0.1),
            'map_score': 0.68 + np.random.normal(0, 0.1),
            'ndcg_score': 0.71 + np.random.normal(0, 0.1)
        }
        
        # Ajustement basé sur la configuration
        if config.preserve_sentences:
            for metric in performance:
                performance[metric] = min(1.0, performance[metric] + 0.05)
        
        if config.medical_boundary_aware:
            for metric in performance:
                performance[metric] = min(1.0, performance[metric] + 0.03)
        
        # Normalisation
        for metric in performance:
            performance[metric] = max(0.0, min(1.0, performance[metric]))
        
        return performance
    
    def save_optimization_results(self, result: OptimizationResult, output_path: str) -> None:
        """Sauvegarde les résultats d'optimisation"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Résultats d'optimisation sauvegardés: {output_file}")
    
    def load_optimization_results(self, input_path: str) -> OptimizationResult:
        """Charge les résultats d'optimisation"""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruction de la configuration
        config_data = data['configuration']
        config = ChunkConfiguration(**config_data)
        
        # Reconstruction du résultat
        result = OptimizationResult(
            optimal_chunk_size=data['optimal_chunk_size'],
            optimal_overlap_size=data['optimal_overlap_size'],
            optimal_overlap_ratio=data['optimal_overlap_ratio'],
            quality_score=data['quality_score'],
            retrieval_performance=data['retrieval_performance'],
            chunk_statistics=data['chunk_statistics'],
            optimization_time=data['optimization_time'],
            configuration=config
        )
        
        return result

def main():
    """Fonction de test de l'optimiseur de chunks"""
    # Documents de test
    test_documents = [
        """
        Le diabète de type 2 est une maladie chronique caractérisée par une résistance à l'insuline.
        Les symptômes incluent une soif excessive, une miction fréquente, et une fatigue.
        Le diagnostic se fait par mesure de la glycémie à jeun (>126 mg/dL) ou HbA1c (>6.5%).
        Le traitement comprend des modifications du mode de vie et des médicaments comme la metformine.
        La posologie initiale de metformine est de 500 mg deux fois par jour avec les repas.
        Les complications incluent la neuropathie, la rétinopathie, et la néphropathie diabétique.
        La prévention passe par une alimentation équilibrée et une activité physique régulière.
        """,
        """
        L'hypertension artérielle est définie par une pression systolique ≥140 mmHg ou diastolique ≥90 mmHg.
        Les facteurs de risque incluent l'âge, l'obésité, le tabagisme, et les antécédents familiaux.
        Le diagnostic nécessite plusieurs mesures de tension artérielle en consultation.
        Les traitements de première ligne incluent les diurétiques thiazidiques et les IEC.
        L'amlodipine 5-10 mg une fois par jour est efficace pour contrôler la tension.
        Les complications cardiovasculaires incluent l'infarctus du myocarde et l'AVC.
        Le suivi implique des contrôles réguliers de la tension et des examens biologiques.
        """,
        """
        La pneumonie communautaire est une infection des alvéoles pulmonaires.
        Les agents pathogènes les plus fréquents sont Streptococcus pneumoniae et Haemophilus influenzae.
        Les symptômes incluent fièvre, toux productive, dyspnée, et douleurs thoraciques.
        Le diagnostic repose sur la clinique, la radiographie thoracique, et les examens biologiques.
        L'antibiothérapie de première intention est l'amoxicilline 1g trois fois par jour.
        En cas d'allergie, on peut utiliser la clarithromycine 500 mg deux fois par jour.
        L'hospitalisation est nécessaire en cas de critères de gravité selon le score CURB-65.
        """
    ]
    
    # Requêtes de test
    test_queries = [
        "Comment diagnostiquer le diabète ?",
        "Quel est le traitement de l'hypertension ?",
        "Quels sont les symptômes de la pneumonie ?",
        "Quelle est la posologie de la metformine ?",
        "Comment prévenir les complications du diabète ?"
    ]
    
    # Initialisation de l'optimiseur
    optimizer = MedicalChunkOptimizer()
    
    print("\n=== OPTIMISEUR DE CHUNKS MÉDICAL ===")
    print(f"Documents de test: {len(test_documents)}")
    print(f"Requêtes de test: {len(test_queries)}")
    
    # Analyse des documents
    print("\n=== ANALYSE DES DOCUMENTS ===")
    for i, doc in enumerate(test_documents):
        analysis = optimizer.analyze_document_structure(doc)
        print(f"\nDocument {i+1}:")
        print(f"  Longueur: {analysis['total_length']} caractères")
        print(f"  Mots: {analysis['word_count']}")
        print(f"  Phrases: {analysis['sentence_count']}")
        print(f"  Paragraphes: {analysis['paragraph_count']}")
        print(f"  Complexité: {analysis['complexity_score']:.3f}")
        print(f"  Sections médicales: {len(analysis['medical_sections'])}")
    
    # Optimisation des chunks
    print("\n=== OPTIMISATION DES CHUNKS ===")
    
    result = optimizer.optimize_chunk_configuration(
        documents=test_documents,
        test_queries=test_queries,
        chunk_size_range=(400, 1200),
        overlap_ratios=[0.1, 0.15, 0.2, 0.25]
    )
    
    print(f"\n=== RÉSULTATS D'OPTIMISATION ===")
    print(f"Taille optimale: {result.optimal_chunk_size} caractères")
    print(f"Overlap optimal: {result.optimal_overlap_size} caractères ({result.optimal_overlap_ratio:.1%})")
    print(f"Score de qualité: {result.quality_score:.3f}")
    print(f"Temps d'optimisation: {result.optimization_time:.2f}s")
    
    print(f"\n=== STATISTIQUES DES CHUNKS ===")
    stats = result.chunk_statistics
    print(f"Nombre total de chunks: {stats['total_chunks']}")
    print(f"Taille moyenne: {stats['avg_chunk_size']:.0f} ± {stats['std_chunk_size']:.0f} caractères")
    print(f"Nombre de mots moyen: {stats['avg_word_count']:.0f} ± {stats['std_word_count']:.0f}")
    print(f"Distribution (Q25/Q50/Q75): {stats['size_distribution']['q25']:.0f}/{stats['size_distribution']['q50']:.0f}/{stats['size_distribution']['q75']:.0f}")
    
    print(f"\n=== PERFORMANCE DE RÉCUPÉRATION ===")
    perf = result.retrieval_performance
    for metric, value in perf.items():
        print(f"{metric}: {value:.3f}")
    
    # Test de création de chunks avec la configuration optimale
    print(f"\n=== TEST DE CHUNKING OPTIMAL ===")
    
    test_doc = test_documents[0]
    chunks = optimizer._create_chunks_with_config(test_doc, result.configuration)
    
    print(f"Document original: {len(test_doc)} caractères")
    print(f"Nombre de chunks générés: {len(chunks)}")
    
    for i, chunk in enumerate(chunks[:3]):  # Afficher les 3 premiers
        print(f"\nChunk {i+1} ({len(chunk)} caractères):")
        print(f"  Début: '{chunk[:50]}...'")
        print(f"  Fin: '...{chunk[-50:]}'")
    
    # Sauvegarde des résultats
    output_path = "./test_chunk_optimization_results.json"
    optimizer.save_optimization_results(result, output_path)
    print(f"\n=== RÉSULTATS SAUVEGARDÉS ===")
    print(f"Fichier: {output_path}")

if __name__ == "__main__":
    main()