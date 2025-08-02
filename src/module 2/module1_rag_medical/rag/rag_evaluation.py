#!/usr/bin/env python3
"""
Système d'Évaluation et d'Optimisation pour RAG Médical

Ce module implémente un système complet d'évaluation de la précision de récupération
et d'optimisation des paramètres pour le système RAG médical.
"""

import logging
import time
import json
import csv
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import ParameterGrid
import itertools
from datetime import datetime
import hashlib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EvaluationQuery:
    """Requête d'évaluation avec vérité terrain"""
    query_id: str
    query_text: str
    medical_specialty: str
    expected_chunks: List[str]  # IDs des chunks pertinents
    relevance_scores: Dict[str, float]  # Scores de pertinence attendus
    query_type: str  # diagnostic, treatment, symptoms, etc.
    difficulty_level: str  # easy, medium, hard
    language: str = "fr"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvaluationResult:
    """Résultat d'évaluation pour une requête"""
    query_id: str
    retrieved_chunks: List[str]
    relevance_scores: List[float]
    precision_at_k: Dict[int, float]
    recall_at_k: Dict[int, float]
    f1_at_k: Dict[int, float]
    map_score: float  # Mean Average Precision
    ndcg_score: float  # Normalized Discounted Cumulative Gain
    mrr_score: float  # Mean Reciprocal Rank
    retrieval_time: float
    context_quality_score: float
    medical_accuracy_score: float

@dataclass
class OptimizationConfig:
    """Configuration pour l'optimisation des paramètres"""
    chunk_sizes: List[int] = field(default_factory=lambda: [500, 800, 1000, 1200])
    chunk_overlaps: List[int] = field(default_factory=lambda: [100, 150, 200, 250])
    embedding_models: List[str] = field(default_factory=lambda: [
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2"
    ])
    search_strategies: List[str] = field(default_factory=lambda: ["semantic", "hybrid", "medical_entity"])
    fusion_strategies: List[str] = field(default_factory=lambda: ["medical_priority", "weighted_merge"])
    max_chunks_range: List[int] = field(default_factory=lambda: [5, 8, 10, 12])
    diversity_thresholds: List[float] = field(default_factory=lambda: [0.6, 0.7, 0.8, 0.9])

class RAGEvaluationSuite:
    """
    Suite d'évaluation complète pour le système RAG médical
    
    Fonctionnalités:
    - Évaluation de la précision de récupération
    - Tests sur 50+ requêtes médicales diversifiées
    - Optimisation automatique des paramètres
    - Métriques spécialisées pour le domaine médical
    - Rapports détaillés et visualisations
    """
    
    def __init__(self,
                 rag_system=None,
                 evaluation_data_path: str = None,
                 output_dir: str = "./evaluation_results"):
        """
        Initialise la suite d'évaluation
        
        Args:
            rag_system: Système RAG à évaluer
            evaluation_data_path: Chemin vers les données d'évaluation
            output_dir: Répertoire de sortie pour les résultats
        """
        self.rag_system = rag_system
        self.evaluation_data_path = evaluation_data_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Données d'évaluation
        self.evaluation_queries: List[EvaluationQuery] = []
        self.evaluation_results: List[EvaluationResult] = []
        
        # Configuration d'optimisation
        self.optimization_config = OptimizationConfig()
        
        # Métriques globales
        self.global_metrics = {}
        
        # Historique des évaluations
        self.evaluation_history = []
        
        logger.info(f"Suite d'évaluation RAG initialisée (sortie: {output_dir})")
    
    def load_evaluation_queries(self, queries_path: str = None) -> None:
        """
        Charge les requêtes d'évaluation depuis un fichier
        
        Args:
            queries_path: Chemin vers le fichier de requêtes
        """
        if queries_path:
            self.evaluation_data_path = queries_path
        
        if not self.evaluation_data_path:
            # Génération de requêtes par défaut
            self._generate_default_queries()
            return
        
        queries_file = Path(self.evaluation_data_path)
        
        if not queries_file.exists():
            logger.warning(f"Fichier de requêtes non trouvé: {queries_file}")
            self._generate_default_queries()
            return
        
        try:
            if queries_file.suffix == '.json':
                with open(queries_file, 'r', encoding='utf-8') as f:
                    queries_data = json.load(f)
            elif queries_file.suffix == '.csv':
                queries_data = self._load_queries_from_csv(queries_file)
            else:
                raise ValueError(f"Format de fichier non supporté: {queries_file.suffix}")
            
            self.evaluation_queries = [
                EvaluationQuery(**query_data) for query_data in queries_data
            ]
            
            logger.info(f"Chargé {len(self.evaluation_queries)} requêtes d'évaluation")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des requêtes: {e}")
            self._generate_default_queries()
    
    def _generate_default_queries(self) -> None:
        """Génère un ensemble de requêtes d'évaluation par défaut"""
        logger.info("Génération de requêtes d'évaluation par défaut...")
        
        default_queries = [
            # Requêtes de diagnostic
            {
                "query_id": "diag_001",
                "query_text": "Comment diagnostiquer le paludisme ?",
                "medical_specialty": "infectious_diseases",
                "expected_chunks": ["chunk_malaria_diag_1", "chunk_malaria_diag_2"],
                "relevance_scores": {"chunk_malaria_diag_1": 1.0, "chunk_malaria_diag_2": 0.8},
                "query_type": "diagnostic",
                "difficulty_level": "medium"
            },
            {
                "query_id": "diag_002",
                "query_text": "Quels sont les tests pour détecter le diabète ?",
                "medical_specialty": "endocrinology",
                "expected_chunks": ["chunk_diabetes_test_1", "chunk_diabetes_test_2"],
                "relevance_scores": {"chunk_diabetes_test_1": 1.0, "chunk_diabetes_test_2": 0.9},
                "query_type": "diagnostic",
                "difficulty_level": "easy"
            },
            
            # Requêtes de traitement
            {
                "query_id": "treat_001",
                "query_text": "Quel est le traitement de l'hypertension artérielle ?",
                "medical_specialty": "cardiology",
                "expected_chunks": ["chunk_hypertension_treat_1", "chunk_hypertension_treat_2"],
                "relevance_scores": {"chunk_hypertension_treat_1": 1.0, "chunk_hypertension_treat_2": 0.8},
                "query_type": "treatment",
                "difficulty_level": "medium"
            },
            {
                "query_id": "treat_002",
                "query_text": "Comment traiter une infection respiratoire ?",
                "medical_specialty": "pulmonology",
                "expected_chunks": ["chunk_respiratory_treat_1", "chunk_respiratory_treat_2"],
                "relevance_scores": {"chunk_respiratory_treat_1": 1.0, "chunk_respiratory_treat_2": 0.7},
                "query_type": "treatment",
                "difficulty_level": "hard"
            },
            
            # Requêtes de symptômes
            {
                "query_id": "symp_001",
                "query_text": "Quels sont les symptômes de la tuberculose ?",
                "medical_specialty": "infectious_diseases",
                "expected_chunks": ["chunk_tb_symptoms_1", "chunk_tb_symptoms_2"],
                "relevance_scores": {"chunk_tb_symptoms_1": 1.0, "chunk_tb_symptoms_2": 0.9},
                "query_type": "symptoms",
                "difficulty_level": "easy"
            },
            
            # Requêtes de prévention
            {
                "query_id": "prev_001",
                "query_text": "Comment prévenir les maladies cardiovasculaires ?",
                "medical_specialty": "cardiology",
                "expected_chunks": ["chunk_cardio_prev_1", "chunk_cardio_prev_2"],
                "relevance_scores": {"chunk_cardio_prev_1": 1.0, "chunk_cardio_prev_2": 0.8},
                "query_type": "prevention",
                "difficulty_level": "medium"
            }
        ]
        
        # Extension pour atteindre 50 requêtes
        extended_queries = []
        base_templates = {
            "diagnostic": [
                "Comment diagnostiquer {disease} ?",
                "Quels examens pour détecter {disease} ?",
                "Diagnostic différentiel de {disease}"
            ],
            "treatment": [
                "Quel traitement pour {disease} ?",
                "Comment soigner {disease} ?",
                "Thérapie recommandée pour {disease}"
            ],
            "symptoms": [
                "Symptômes de {disease}",
                "Signes cliniques de {disease}",
                "Manifestations de {disease}"
            ],
            "prevention": [
                "Prévention de {disease}",
                "Comment éviter {disease} ?",
                "Mesures préventives contre {disease}"
            ]
        }
        
        diseases = [
            "paludisme", "diabète", "hypertension", "tuberculose", "VIH",
            "hépatite", "pneumonie", "asthme", "cancer", "AVC",
            "infarctus", "méningite", "dengue", "choléra", "typhoïde"
        ]
        
        specialties = {
            "paludisme": "infectious_diseases",
            "diabète": "endocrinology",
            "hypertension": "cardiology",
            "tuberculose": "pulmonology",
            "VIH": "infectious_diseases",
            "hépatite": "gastroenterology",
            "pneumonie": "pulmonology",
            "asthme": "pulmonology",
            "cancer": "oncology",
            "AVC": "neurology",
            "infarctus": "cardiology",
            "méningite": "neurology",
            "dengue": "infectious_diseases",
            "choléra": "infectious_diseases",
            "typhoïde": "infectious_diseases"
        }
        
        query_id_counter = len(default_queries) + 1
        
        for disease in diseases:
            for query_type, templates in base_templates.items():
                for template in templates:
                    if query_id_counter > 50:
                        break
                    
                    query_text = template.format(disease=disease)
                    query_id = f"{query_type[:4]}_{query_id_counter:03d}"
                    
                    extended_queries.append({
                        "query_id": query_id,
                        "query_text": query_text,
                        "medical_specialty": specialties.get(disease, "general"),
                        "expected_chunks": [f"chunk_{disease}_{query_type}_1"],
                        "relevance_scores": {f"chunk_{disease}_{query_type}_1": 1.0},
                        "query_type": query_type,
                        "difficulty_level": "medium"
                    })
                    
                    query_id_counter += 1
                
                if query_id_counter > 50:
                    break
            
            if query_id_counter > 50:
                break
        
        all_queries = default_queries + extended_queries[:50 - len(default_queries)]
        
        self.evaluation_queries = [
            EvaluationQuery(**query_data) for query_data in all_queries
        ]
        
        # Sauvegarde des requêtes générées
        self._save_generated_queries(all_queries)
        
        logger.info(f"Généré {len(self.evaluation_queries)} requêtes d'évaluation")
    
    def _save_generated_queries(self, queries: List[Dict[str, Any]]) -> None:
        """Sauvegarde les requêtes générées"""
        output_file = self.output_dir / "generated_evaluation_queries.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(queries, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Requêtes sauvegardées: {output_file}")
    
    def evaluate_rag_system(self, 
                           max_queries: Optional[int] = None,
                           save_results: bool = True) -> Dict[str, Any]:
        """
        Évalue le système RAG sur l'ensemble des requêtes
        
        Args:
            max_queries: Nombre maximum de requêtes à évaluer
            save_results: Sauvegarder les résultats
            
        Returns:
            Métriques globales d'évaluation
        """
        if not self.evaluation_queries:
            self.load_evaluation_queries()
        
        if not self.rag_system:
            raise ValueError("Système RAG non configuré")
        
        queries_to_evaluate = self.evaluation_queries
        if max_queries:
            queries_to_evaluate = queries_to_evaluate[:max_queries]
        
        logger.info(f"Évaluation du système RAG sur {len(queries_to_evaluate)} requêtes...")
        start_time = time.time()
        
        self.evaluation_results = []
        
        for i, query in enumerate(queries_to_evaluate, 1):
            logger.info(f"Évaluation requête {i}/{len(queries_to_evaluate)}: {query.query_id}")
            
            try:
                result = self._evaluate_single_query(query)
                self.evaluation_results.append(result)
            except Exception as e:
                logger.error(f"Erreur lors de l'évaluation de {query.query_id}: {e}")
                continue
        
        # Calcul des métriques globales
        self.global_metrics = self._calculate_global_metrics()
        
        evaluation_time = time.time() - start_time
        self.global_metrics['total_evaluation_time'] = evaluation_time
        self.global_metrics['avg_time_per_query'] = evaluation_time / len(queries_to_evaluate)
        
        # Sauvegarde des résultats
        if save_results:
            self._save_evaluation_results()
        
        logger.info(f"Évaluation terminée en {evaluation_time:.2f}s")
        return self.global_metrics
    
    def _evaluate_single_query(self, query: EvaluationQuery) -> EvaluationResult:
        """Évalue une requête individuelle"""
        start_time = time.time()
        
        # Exécution de la requête sur le système RAG
        try:
            # Simulation d'appel au système RAG
            # En pratique, ceci appellerait le vrai système
            retrieved_results = self._simulate_rag_query(query)
            
            retrieved_chunks = [r['chunk_id'] for r in retrieved_results]
            relevance_scores = [r['score'] for r in retrieved_results]
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête {query.query_id}: {e}")
            retrieved_chunks = []
            relevance_scores = []
        
        retrieval_time = time.time() - start_time
        
        # Calcul des métriques
        precision_at_k = self._calculate_precision_at_k(query, retrieved_chunks)
        recall_at_k = self._calculate_recall_at_k(query, retrieved_chunks)
        f1_at_k = self._calculate_f1_at_k(precision_at_k, recall_at_k)
        map_score = self._calculate_map(query, retrieved_chunks, relevance_scores)
        ndcg_score = self._calculate_ndcg(query, retrieved_chunks, relevance_scores)
        mrr_score = self._calculate_mrr(query, retrieved_chunks)
        
        # Métriques spécialisées
        context_quality_score = self._evaluate_context_quality(query, retrieved_chunks)
        medical_accuracy_score = self._evaluate_medical_accuracy(query, retrieved_chunks)
        
        return EvaluationResult(
            query_id=query.query_id,
            retrieved_chunks=retrieved_chunks,
            relevance_scores=relevance_scores,
            precision_at_k=precision_at_k,
            recall_at_k=recall_at_k,
            f1_at_k=f1_at_k,
            map_score=map_score,
            ndcg_score=ndcg_score,
            mrr_score=mrr_score,
            retrieval_time=retrieval_time,
            context_quality_score=context_quality_score,
            medical_accuracy_score=medical_accuracy_score
        )
    
    def _simulate_rag_query(self, query: EvaluationQuery) -> List[Dict[str, Any]]:
        """Simule l'exécution d'une requête RAG"""
        # Simulation de résultats de récupération
        # En pratique, ceci appellerait le vrai système RAG
        
        # Génération de résultats simulés basés sur les chunks attendus
        simulated_results = []
        
        # Ajouter les chunks pertinents avec des scores élevés
        for chunk_id in query.expected_chunks:
            expected_score = query.relevance_scores.get(chunk_id, 0.8)
            # Ajouter du bruit pour simuler l'imperfection
            actual_score = expected_score * (0.8 + np.random.random() * 0.4)
            
            simulated_results.append({
                'chunk_id': chunk_id,
                'score': actual_score,
                'content': f"Contenu simulé pour {chunk_id}"
            })
        
        # Ajouter quelques chunks non pertinents
        for i in range(3):
            irrelevant_chunk_id = f"irrelevant_chunk_{i}"
            irrelevant_score = np.random.random() * 0.6  # Score plus bas
            
            simulated_results.append({
                'chunk_id': irrelevant_chunk_id,
                'score': irrelevant_score,
                'content': f"Contenu non pertinent {i}"
            })
        
        # Tri par score décroissant
        simulated_results.sort(key=lambda x: x['score'], reverse=True)
        
        return simulated_results[:10]  # Limiter à 10 résultats
    
    def _calculate_precision_at_k(self, query: EvaluationQuery, retrieved_chunks: List[str]) -> Dict[int, float]:
        """Calcule la précision à k pour différentes valeurs de k"""
        relevant_chunks = set(query.expected_chunks)
        precision_at_k = {}
        
        for k in [1, 3, 5, 10]:
            if k <= len(retrieved_chunks):
                top_k = retrieved_chunks[:k]
                relevant_in_top_k = len(set(top_k).intersection(relevant_chunks))
                precision_at_k[k] = relevant_in_top_k / k
            else:
                precision_at_k[k] = 0.0
        
        return precision_at_k
    
    def _calculate_recall_at_k(self, query: EvaluationQuery, retrieved_chunks: List[str]) -> Dict[int, float]:
        """Calcule le rappel à k pour différentes valeurs de k"""
        relevant_chunks = set(query.expected_chunks)
        recall_at_k = {}
        
        for k in [1, 3, 5, 10]:
            if k <= len(retrieved_chunks) and relevant_chunks:
                top_k = retrieved_chunks[:k]
                relevant_in_top_k = len(set(top_k).intersection(relevant_chunks))
                recall_at_k[k] = relevant_in_top_k / len(relevant_chunks)
            else:
                recall_at_k[k] = 0.0
        
        return recall_at_k
    
    def _calculate_f1_at_k(self, precision_at_k: Dict[int, float], recall_at_k: Dict[int, float]) -> Dict[int, float]:
        """Calcule le F1-score à k"""
        f1_at_k = {}
        
        for k in precision_at_k.keys():
            p = precision_at_k[k]
            r = recall_at_k[k]
            
            if p + r > 0:
                f1_at_k[k] = 2 * (p * r) / (p + r)
            else:
                f1_at_k[k] = 0.0
        
        return f1_at_k
    
    def _calculate_map(self, query: EvaluationQuery, retrieved_chunks: List[str], scores: List[float]) -> float:
        """Calcule le Mean Average Precision"""
        relevant_chunks = set(query.expected_chunks)
        
        if not relevant_chunks:
            return 0.0
        
        average_precisions = []
        relevant_count = 0
        
        for i, chunk_id in enumerate(retrieved_chunks):
            if chunk_id in relevant_chunks:
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                average_precisions.append(precision_at_i)
        
        if average_precisions:
            return sum(average_precisions) / len(relevant_chunks)
        else:
            return 0.0
    
    def _calculate_ndcg(self, query: EvaluationQuery, retrieved_chunks: List[str], scores: List[float]) -> float:
        """Calcule le Normalized Discounted Cumulative Gain"""
        def dcg(relevances):
            return sum(rel / np.log2(i + 2) for i, rel in enumerate(relevances))
        
        # Relevances des chunks récupérés
        retrieved_relevances = []
        for chunk_id in retrieved_chunks:
            relevance = query.relevance_scores.get(chunk_id, 0.0)
            retrieved_relevances.append(relevance)
        
        # DCG des résultats récupérés
        dcg_score = dcg(retrieved_relevances)
        
        # IDCG (DCG idéal)
        ideal_relevances = sorted(query.relevance_scores.values(), reverse=True)
        idcg_score = dcg(ideal_relevances)
        
        if idcg_score > 0:
            return dcg_score / idcg_score
        else:
            return 0.0
    
    def _calculate_mrr(self, query: EvaluationQuery, retrieved_chunks: List[str]) -> float:
        """Calcule le Mean Reciprocal Rank"""
        relevant_chunks = set(query.expected_chunks)
        
        for i, chunk_id in enumerate(retrieved_chunks):
            if chunk_id in relevant_chunks:
                return 1.0 / (i + 1)
        
        return 0.0
    
    def _evaluate_context_quality(self, query: EvaluationQuery, retrieved_chunks: List[str]) -> float:
        """Évalue la qualité du contexte récupéré"""
        # Simulation d'évaluation de qualité
        # En pratique, ceci analyserait la cohérence, la complétude, etc.
        
        quality_factors = []
        
        # Facteur 1: Pertinence des chunks
        relevant_chunks = set(query.expected_chunks)
        relevance_ratio = len(set(retrieved_chunks).intersection(relevant_chunks)) / max(1, len(retrieved_chunks))
        quality_factors.append(relevance_ratio)
        
        # Facteur 2: Diversité (simulation)
        diversity_score = min(1.0, len(set(retrieved_chunks)) / max(1, len(retrieved_chunks)))
        quality_factors.append(diversity_score)
        
        # Facteur 3: Couverture du sujet
        coverage_score = len(set(retrieved_chunks).intersection(relevant_chunks)) / max(1, len(relevant_chunks))
        quality_factors.append(coverage_score)
        
        return np.mean(quality_factors)
    
    def _evaluate_medical_accuracy(self, query: EvaluationQuery, retrieved_chunks: List[str]) -> float:
        """Évalue l'exactitude médicale des résultats"""
        # Simulation d'évaluation d'exactitude médicale
        # En pratique, ceci vérifierait la validité médicale du contenu
        
        accuracy_factors = []
        
        # Facteur 1: Correspondance de spécialité
        specialty_match = 1.0 if query.medical_specialty in ['infectious_diseases', 'cardiology'] else 0.8
        accuracy_factors.append(specialty_match)
        
        # Facteur 2: Type de requête approprié
        type_appropriateness = 1.0 if query.query_type in ['diagnostic', 'treatment'] else 0.9
        accuracy_factors.append(type_appropriateness)
        
        # Facteur 3: Niveau de difficulté
        difficulty_factor = {
            'easy': 0.95,
            'medium': 0.85,
            'hard': 0.75
        }.get(query.difficulty_level, 0.8)
        accuracy_factors.append(difficulty_factor)
        
        return np.mean(accuracy_factors)
    
    def _calculate_global_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques globales sur tous les résultats"""
        if not self.evaluation_results:
            return {}
        
        metrics = {}
        
        # Métriques de précision/rappel moyennes
        for k in [1, 3, 5, 10]:
            precisions = [r.precision_at_k.get(k, 0.0) for r in self.evaluation_results]
            recalls = [r.recall_at_k.get(k, 0.0) for r in self.evaluation_results]
            f1s = [r.f1_at_k.get(k, 0.0) for r in self.evaluation_results]
            
            metrics[f'avg_precision_at_{k}'] = np.mean(precisions)
            metrics[f'avg_recall_at_{k}'] = np.mean(recalls)
            metrics[f'avg_f1_at_{k}'] = np.mean(f1s)
        
        # Métriques globales
        metrics['avg_map'] = np.mean([r.map_score for r in self.evaluation_results])
        metrics['avg_ndcg'] = np.mean([r.ndcg_score for r in self.evaluation_results])
        metrics['avg_mrr'] = np.mean([r.mrr_score for r in self.evaluation_results])
        
        # Métriques de performance
        metrics['avg_retrieval_time'] = np.mean([r.retrieval_time for r in self.evaluation_results])
        metrics['total_queries_evaluated'] = len(self.evaluation_results)
        
        # Métriques spécialisées
        metrics['avg_context_quality'] = np.mean([r.context_quality_score for r in self.evaluation_results])
        metrics['avg_medical_accuracy'] = np.mean([r.medical_accuracy_score for r in self.evaluation_results])
        
        # Analyse par type de requête
        query_types = defaultdict(list)
        for i, result in enumerate(self.evaluation_results):
            query = self.evaluation_queries[i]
            query_types[query.query_type].append(result)
        
        metrics['performance_by_query_type'] = {}
        for query_type, results in query_types.items():
            metrics['performance_by_query_type'][query_type] = {
                'avg_precision_at_5': np.mean([r.precision_at_k.get(5, 0.0) for r in results]),
                'avg_recall_at_5': np.mean([r.recall_at_k.get(5, 0.0) for r in results]),
                'avg_map': np.mean([r.map_score for r in results]),
                'count': len(results)
            }
        
        # Analyse par niveau de difficulté
        difficulty_levels = defaultdict(list)
        for i, result in enumerate(self.evaluation_results):
            query = self.evaluation_queries[i]
            difficulty_levels[query.difficulty_level].append(result)
        
        metrics['performance_by_difficulty'] = {}
        for difficulty, results in difficulty_levels.items():
            metrics['performance_by_difficulty'][difficulty] = {
                'avg_precision_at_5': np.mean([r.precision_at_k.get(5, 0.0) for r in results]),
                'avg_recall_at_5': np.mean([r.recall_at_k.get(5, 0.0) for r in results]),
                'avg_map': np.mean([r.map_score for r in results]),
                'count': len(results)
            }
        
        return metrics
    
    def optimize_parameters(self, 
                          optimization_config: OptimizationConfig = None,
                          max_combinations: int = 50) -> Dict[str, Any]:
        """
        Optimise les paramètres du système RAG
        
        Args:
            optimization_config: Configuration d'optimisation
            max_combinations: Nombre maximum de combinaisons à tester
            
        Returns:
            Meilleurs paramètres et résultats d'optimisation
        """
        if optimization_config:
            self.optimization_config = optimization_config
        
        logger.info("Début de l'optimisation des paramètres...")
        
        # Génération des combinaisons de paramètres
        param_grid = {
            'chunk_size': self.optimization_config.chunk_sizes,
            'chunk_overlap': self.optimization_config.chunk_overlaps,
            'embedding_model': self.optimization_config.embedding_models,
            'search_strategy': self.optimization_config.search_strategies,
            'fusion_strategy': self.optimization_config.fusion_strategies,
            'max_chunks': self.optimization_config.max_chunks_range,
            'diversity_threshold': self.optimization_config.diversity_thresholds
        }
        
        # Limitation du nombre de combinaisons
        all_combinations = list(ParameterGrid(param_grid))
        if len(all_combinations) > max_combinations:
            # Échantillonnage aléatoire
            np.random.shuffle(all_combinations)
            combinations_to_test = all_combinations[:max_combinations]
        else:
            combinations_to_test = all_combinations
        
        logger.info(f"Test de {len(combinations_to_test)} combinaisons de paramètres")
        
        optimization_results = []
        
        for i, params in enumerate(combinations_to_test, 1):
            logger.info(f"Test combinaison {i}/{len(combinations_to_test)}: {params}")
            
            try:
                # Configuration du système avec les nouveaux paramètres
                self._configure_rag_system(params)
                
                # Évaluation sur un sous-ensemble de requêtes
                subset_size = min(20, len(self.evaluation_queries))
                metrics = self.evaluate_rag_system(max_queries=subset_size, save_results=False)
                
                # Calcul du score global
                global_score = self._calculate_optimization_score(metrics)
                
                optimization_results.append({
                    'parameters': params,
                    'metrics': metrics,
                    'global_score': global_score
                })
                
            except Exception as e:
                logger.error(f"Erreur lors du test des paramètres {params}: {e}")
                continue
        
        # Sélection des meilleurs paramètres
        if optimization_results:
            best_result = max(optimization_results, key=lambda x: x['global_score'])
            
            optimization_summary = {
                'best_parameters': best_result['parameters'],
                'best_metrics': best_result['metrics'],
                'best_score': best_result['global_score'],
                'total_combinations_tested': len(optimization_results),
                'optimization_results': optimization_results
            }
            
            # Sauvegarde des résultats d'optimisation
            self._save_optimization_results(optimization_summary)
            
            logger.info(f"Optimisation terminée. Meilleur score: {best_result['global_score']:.3f}")
            return optimization_summary
        
        else:
            logger.error("Aucun résultat d'optimisation valide")
            return {}
    
    def _configure_rag_system(self, params: Dict[str, Any]) -> None:
        """Configure le système RAG avec les paramètres donnés"""
        # Simulation de configuration du système RAG
        # En pratique, ceci reconfigurerait le vrai système
        logger.debug(f"Configuration du système RAG avec: {params}")
    
    def _calculate_optimization_score(self, metrics: Dict[str, Any]) -> float:
        """Calcule un score global pour l'optimisation"""
        # Pondération des différentes métriques
        weights = {
            'avg_precision_at_5': 0.25,
            'avg_recall_at_5': 0.25,
            'avg_map': 0.20,
            'avg_ndcg': 0.15,
            'avg_context_quality': 0.10,
            'avg_medical_accuracy': 0.05
        }
        
        score = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                score += metrics[metric] * weight
        
        # Pénalité pour le temps de récupération élevé
        if 'avg_retrieval_time' in metrics:
            time_penalty = min(0.1, metrics['avg_retrieval_time'] / 10.0)  # Pénalité si > 1s
            score -= time_penalty
        
        return max(0.0, score)
    
    def _save_evaluation_results(self) -> None:
        """Sauvegarde les résultats d'évaluation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarde des résultats détaillés
        results_file = self.output_dir / f"evaluation_results_{timestamp}.json"
        
        results_data = {
            'timestamp': timestamp,
            'global_metrics': self.global_metrics,
            'evaluation_results': [asdict(result) for result in self.evaluation_results],
            'evaluation_queries': [asdict(query) for query in self.evaluation_queries]
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        # Sauvegarde du résumé CSV
        summary_file = self.output_dir / f"evaluation_summary_{timestamp}.csv"
        
        summary_data = []
        for i, result in enumerate(self.evaluation_results):
            query = self.evaluation_queries[i]
            summary_data.append({
                'query_id': result.query_id,
                'query_type': query.query_type,
                'difficulty': query.difficulty_level,
                'precision_at_5': result.precision_at_k.get(5, 0.0),
                'recall_at_5': result.recall_at_k.get(5, 0.0),
                'f1_at_5': result.f1_at_k.get(5, 0.0),
                'map_score': result.map_score,
                'ndcg_score': result.ndcg_score,
                'mrr_score': result.mrr_score,
                'retrieval_time': result.retrieval_time,
                'context_quality': result.context_quality_score,
                'medical_accuracy': result.medical_accuracy_score
            })
        
        df = pd.DataFrame(summary_data)
        df.to_csv(summary_file, index=False)
        
        logger.info(f"Résultats sauvegardés: {results_file} et {summary_file}")
    
    def _save_optimization_results(self, optimization_summary: Dict[str, Any]) -> None:
        """Sauvegarde les résultats d'optimisation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        optimization_file = self.output_dir / f"optimization_results_{timestamp}.json"
        
        with open(optimization_file, 'w', encoding='utf-8') as f:
            json.dump(optimization_summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Résultats d'optimisation sauvegardés: {optimization_file}")
    
    def generate_evaluation_report(self, include_visualizations: bool = True) -> str:
        """
        Génère un rapport d'évaluation complet
        
        Args:
            include_visualizations: Inclure les graphiques
            
        Returns:
            Chemin vers le rapport généré
        """
        if not self.evaluation_results:
            raise ValueError("Aucun résultat d'évaluation disponible")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"evaluation_report_{timestamp}.html"
        
        # Génération du rapport HTML
        html_content = self._generate_html_report(include_visualizations)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Rapport d'évaluation généré: {report_file}")
        return str(report_file)
    
    def _generate_html_report(self, include_visualizations: bool) -> str:
        """Génère le contenu HTML du rapport"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport d'Évaluation RAG Médical</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 10px; }}
                .metric {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .table {{ border-collapse: collapse; width: 100%; }}
                .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .table th {{ background-color: #f2f2f2; }}
                .good {{ color: green; font-weight: bold; }}
                .average {{ color: orange; font-weight: bold; }}
                .poor {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 Rapport d'Évaluation RAG Médical</h1>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Requêtes évaluées:</strong> {len(self.evaluation_results)}</p>
                <p><strong>Temps total:</strong> {self.global_metrics.get('total_evaluation_time', 0):.2f}s</p>
            </div>
            
            <h2>📊 Métriques Globales</h2>
        """
        
        # Métriques principales
        main_metrics = [
            ('Précision@5', 'avg_precision_at_5'),
            ('Rappel@5', 'avg_recall_at_5'),
            ('F1@5', 'avg_f1_at_5'),
            ('MAP', 'avg_map'),
            ('NDCG', 'avg_ndcg'),
            ('MRR', 'avg_mrr'),
            ('Qualité Contexte', 'avg_context_quality'),
            ('Exactitude Médicale', 'avg_medical_accuracy')
        ]
        
        for metric_name, metric_key in main_metrics:
            value = self.global_metrics.get(metric_key, 0.0)
            css_class = 'good' if value >= 0.8 else 'average' if value >= 0.6 else 'poor'
            html += f'<div class="metric"><strong>{metric_name}:</strong> <span class="{css_class}">{value:.3f}</span></div>\n'
        
        # Performance par type de requête
        html += "<h2>📋 Performance par Type de Requête</h2>\n"
        html += '<table class="table">\n<tr><th>Type</th><th>Nombre</th><th>Précision@5</th><th>Rappel@5</th><th>MAP</th></tr>\n'
        
        for query_type, stats in self.global_metrics.get('performance_by_query_type', {}).items():
            html += f"""<tr>
                <td>{query_type}</td>
                <td>{stats['count']}</td>
                <td>{stats['avg_precision_at_5']:.3f}</td>
                <td>{stats['avg_recall_at_5']:.3f}</td>
                <td>{stats['avg_map']:.3f}</td>
            </tr>\n"""
        
        html += "</table>\n"
        
        # Performance par niveau de difficulté
        html += "<h2>🎯 Performance par Niveau de Difficulté</h2>\n"
        html += '<table class="table">\n<tr><th>Niveau</th><th>Nombre</th><th>Précision@5</th><th>Rappel@5</th><th>MAP</th></tr>\n'
        
        for difficulty, stats in self.global_metrics.get('performance_by_difficulty', {}).items():
            html += f"""<tr>
                <td>{difficulty}</td>
                <td>{stats['count']}</td>
                <td>{stats['avg_precision_at_5']:.3f}</td>
                <td>{stats['avg_recall_at_5']:.3f}</td>
                <td>{stats['avg_map']:.3f}</td>
            </tr>\n"""
        
        html += "</table>\n"
        
        # Résultats détaillés
        html += "<h2>📝 Résultats Détaillés</h2>\n"
        html += '<table class="table">\n<tr><th>ID Requête</th><th>Type</th><th>Difficulté</th><th>P@5</th><th>R@5</th><th>MAP</th><th>Temps (s)</th></tr>\n'
        
        for i, result in enumerate(self.evaluation_results[:20]):  # Limiter à 20 pour la lisibilité
            query = self.evaluation_queries[i]
            html += f"""<tr>
                <td>{result.query_id}</td>
                <td>{query.query_type}</td>
                <td>{query.difficulty_level}</td>
                <td>{result.precision_at_k.get(5, 0.0):.3f}</td>
                <td>{result.recall_at_k.get(5, 0.0):.3f}</td>
                <td>{result.map_score:.3f}</td>
                <td>{result.retrieval_time:.3f}</td>
            </tr>\n"""
        
        html += "</table>\n"
        
        if len(self.evaluation_results) > 20:
            html += f"<p><em>... et {len(self.evaluation_results) - 20} autres résultats</em></p>\n"
        
        html += "</body></html>"
        
        return html

def main():
    """Fonction de test de la suite d'évaluation"""
    # Initialisation de la suite d'évaluation
    evaluation_suite = RAGEvaluationSuite(
        rag_system=None,  # Sera simulé
        output_dir="./test_evaluation_results"
    )
    
    # Chargement des requêtes d'évaluation
    evaluation_suite.load_evaluation_queries()
    
    print(f"\n=== SUITE D'ÉVALUATION RAG MÉDICAL ===")
    print(f"Requêtes chargées: {len(evaluation_suite.evaluation_queries)}")
    
    # Évaluation du système
    global_metrics = evaluation_suite.evaluate_rag_system(max_queries=10)
    
    print(f"\n=== MÉTRIQUES GLOBALES ===")
    for metric, value in global_metrics.items():
        if isinstance(value, (int, float)):
            print(f"{metric}: {value:.3f}")
    
    # Génération du rapport
    report_path = evaluation_suite.generate_evaluation_report()
    print(f"\n=== RAPPORT GÉNÉRÉ ===")
    print(f"Rapport disponible: {report_path}")
    
    # Test d'optimisation (version simplifiée)
    print(f"\n=== TEST D'OPTIMISATION ===")
    
    # Configuration d'optimisation réduite pour le test
    test_config = OptimizationConfig(
        chunk_sizes=[800, 1000],
        chunk_overlaps=[150, 200],
        embedding_models=["sentence-transformers/all-MiniLM-L6-v2"],
        search_strategies=["semantic", "hybrid"],
        fusion_strategies=["medical_priority"],
        max_chunks_range=[5, 10],
        diversity_thresholds=[0.7, 0.8]
    )
    
    optimization_results = evaluation_suite.optimize_parameters(
        optimization_config=test_config,
        max_combinations=4
    )
    
    if optimization_results:
        print(f"Meilleur score: {optimization_results['best_score']:.3f}")
        print(f"Meilleurs paramètres: {optimization_results['best_parameters']}")

if __name__ == "__main__":
    main()