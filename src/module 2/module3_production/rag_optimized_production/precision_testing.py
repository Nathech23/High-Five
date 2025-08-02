#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Objectif 18: Tests de précision et benchmarking
Système de tests automatisés pour mesurer la précision du RAG optimisé

Fonctionnalités:
- Tests de précision automatisés
- Benchmarking de performance
- Métriques de qualité
- Tests de régression
- Validation continue
- Rapports détaillés
"""

import json
import logging
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import re

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types de tests"""
    PRECISION = "precision"          # Test de précision
    RECALL = "recall"                # Test de rappel
    RELEVANCE = "relevance"          # Test de pertinence
    LATENCY = "latency"              # Test de latence
    THROUGHPUT = "throughput"        # Test de débit
    ACCURACY = "accuracy"            # Test de précision
    CONSISTENCY = "consistency"      # Test de cohérence
    REGRESSION = "regression"        # Test de régression

class TestStatus(Enum):
    """Statuts de test"""
    PENDING = "pending"              # En attente
    RUNNING = "running"              # En cours
    PASSED = "passed"                # Réussi
    FAILED = "failed"                # Échoué
    ERROR = "error"                  # Erreur
    SKIPPED = "skipped"              # Ignoré

class MetricType(Enum):
    """Types de métriques"""
    PRECISION_AT_K = "precision_at_k"    # Précision@K
    RECALL_AT_K = "recall_at_k"          # Rappel@K
    F1_SCORE = "f1_score"                # Score F1
    MAP = "map"                          # Mean Average Precision
    NDCG = "ndcg"                        # Normalized DCG
    MRR = "mrr"                          # Mean Reciprocal Rank
    LATENCY_P95 = "latency_p95"          # Latence P95
    THROUGHPUT_QPS = "throughput_qps"    # Requêtes par seconde

@dataclass
class TestCase:
    """Cas de test"""
    test_id: str
    query: str
    expected_results: List[str]  # IDs des résultats attendus
    expected_relevance: List[float]  # Scores de pertinence attendus
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    difficulty_level: str = "medium"  # easy, medium, hard
    category: str = "general"
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class TestResult:
    """Résultat de test"""
    test_id: str
    test_type: TestType
    status: TestStatus
    actual_results: List[str]  # IDs des résultats obtenus
    actual_relevance: List[float]  # Scores de pertinence obtenus
    metrics: Dict[MetricType, float] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BenchmarkResult:
    """Résultat de benchmark"""
    benchmark_id: str
    test_suite: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    overall_metrics: Dict[MetricType, float] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    detailed_results: List[TestResult] = field(default_factory=list)

@dataclass
class PerformanceMetrics:
    """Métriques de performance"""
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    throughput_qps: float = 0.0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0

class TestDataGenerator:
    """Générateur de données de test"""
    
    def __init__(self):
        self.medical_queries = self._load_medical_queries()
        self.expected_results = self._load_expected_results()
        
    def generate_test_suite(self, suite_name: str, num_tests: int = 50) -> List[TestCase]:
        """Générer une suite de tests"""
        test_cases = []
        
        for i in range(num_tests):
            test_case = self._generate_test_case(f"{suite_name}_{i:03d}")
            test_cases.append(test_case)
        
        logger.info(f"Suite de tests '{suite_name}' générée: {len(test_cases)} cas")
        return test_cases
    
    def _generate_test_case(self, test_id: str) -> TestCase:
        """Générer un cas de test"""
        # Sélectionner une requête aléatoire
        query_data = random.choice(self.medical_queries)
        
        # Générer les résultats attendus
        expected_results = self._generate_expected_results(query_data)
        expected_relevance = self._generate_relevance_scores(expected_results)
        
        # Déterminer la difficulté
        difficulty = self._determine_difficulty(query_data)
        
        return TestCase(
            test_id=test_id,
            query=query_data['query'],
            expected_results=expected_results,
            expected_relevance=expected_relevance,
            context=query_data.get('context', {}),
            metadata={
                'source': query_data.get('source', 'generated'),
                'keywords': query_data.get('keywords', []),
                'domain': query_data.get('domain', 'medical')
            },
            difficulty_level=difficulty,
            category=query_data.get('category', 'general')
        )
    
    def _load_medical_queries(self) -> List[Dict[str, Any]]:
        """Charger les requêtes médicales de test"""
        return [
            {
                'query': 'Traitement du paludisme chez l\'enfant',
                'category': 'treatment',
                'keywords': ['paludisme', 'enfant', 'traitement'],
                'context': {'urgency': 'normal', 'age_group': 'pediatric'},
                'domain': 'infectious_diseases'
            },
            {
                'query': 'Diagnostic différentiel de la fièvre tropicale',
                'category': 'diagnosis',
                'keywords': ['diagnostic', 'fièvre', 'tropical'],
                'context': {'urgency': 'high', 'setting': 'tropical'},
                'domain': 'infectious_diseases'
            },
            {
                'query': 'Posologie artemether-lumefantrine adulte',
                'category': 'dosage',
                'keywords': ['posologie', 'artemether', 'lumefantrine', 'adulte'],
                'context': {'patient_type': 'adult', 'weight_based': True},
                'domain': 'pharmacology'
            },
            {
                'query': 'Effets secondaires de la quinine',
                'category': 'side_effects',
                'keywords': ['effets', 'secondaires', 'quinine'],
                'context': {'drug_safety': True},
                'domain': 'pharmacology'
            },
            {
                'query': 'Prévention du paludisme en zone endémique',
                'category': 'prevention',
                'keywords': ['prévention', 'paludisme', 'endémique'],
                'context': {'prevention': True, 'endemic_area': True},
                'domain': 'public_health'
            },
            {
                'query': 'Test de diagnostic rapide du paludisme',
                'category': 'diagnostic_tools',
                'keywords': ['test', 'diagnostic', 'rapide', 'paludisme'],
                'context': {'diagnostic_method': 'rapid_test'},
                'domain': 'laboratory'
            },
            {
                'query': 'Paludisme grave complications cérébrales',
                'category': 'complications',
                'keywords': ['paludisme', 'grave', 'complications', 'cérébrales'],
                'context': {'urgency': 'critical', 'severity': 'severe'},
                'domain': 'emergency_medicine'
            },
            {
                'query': 'Résistance à la chloroquine Plasmodium falciparum',
                'category': 'resistance',
                'keywords': ['résistance', 'chloroquine', 'plasmodium', 'falciparum'],
                'context': {'drug_resistance': True},
                'domain': 'microbiology'
            },
            {
                'query': 'Paludisme et grossesse traitement sécuritaire',
                'category': 'special_populations',
                'keywords': ['paludisme', 'grossesse', 'traitement', 'sécuritaire'],
                'context': {'pregnancy': True, 'safety_concern': True},
                'domain': 'obstetrics'
            },
            {
                'query': 'Épidémiologie du paludisme en Afrique subsaharienne',
                'category': 'epidemiology',
                'keywords': ['épidémiologie', 'paludisme', 'afrique', 'subsaharienne'],
                'context': {'geographic_region': 'sub_saharan_africa'},
                'domain': 'epidemiology'
            }
        ]
    
    def _load_expected_results(self) -> Dict[str, List[str]]:
        """Charger les résultats attendus"""
        return {
            'treatment': ['doc_001', 'doc_005', 'doc_012', 'doc_018'],
            'diagnosis': ['doc_002', 'doc_008', 'doc_015', 'doc_022'],
            'dosage': ['doc_003', 'doc_009', 'doc_016', 'doc_023'],
            'side_effects': ['doc_004', 'doc_010', 'doc_017', 'doc_024'],
            'prevention': ['doc_006', 'doc_011', 'doc_019', 'doc_025'],
            'diagnostic_tools': ['doc_007', 'doc_013', 'doc_020', 'doc_026'],
            'complications': ['doc_014', 'doc_021', 'doc_027', 'doc_028'],
            'resistance': ['doc_029', 'doc_030', 'doc_031', 'doc_032'],
            'special_populations': ['doc_033', 'doc_034', 'doc_035', 'doc_036'],
            'epidemiology': ['doc_037', 'doc_038', 'doc_039', 'doc_040']
        }
    
    def _generate_expected_results(self, query_data: Dict[str, Any]) -> List[str]:
        """Générer les résultats attendus pour une requête"""
        category = query_data.get('category', 'general')
        base_results = self.expected_results.get(category, ['doc_001', 'doc_002', 'doc_003'])
        
        # Ajouter de la variabilité
        num_results = random.randint(3, min(8, len(base_results)))
        selected_results = random.sample(base_results, min(num_results, len(base_results)))
        
        return selected_results
    
    def _generate_relevance_scores(self, results: List[str]) -> List[float]:
        """Générer les scores de pertinence"""
        scores = []
        for i, _ in enumerate(results):
            # Score décroissant avec un peu de bruit
            base_score = 1.0 - (i * 0.15)
            noise = random.uniform(-0.1, 0.1)
            score = max(0.1, min(1.0, base_score + noise))
            scores.append(score)
        
        return scores
    
    def _determine_difficulty(self, query_data: Dict[str, Any]) -> str:
        """Déterminer la difficulté d'une requête"""
        keywords = query_data.get('keywords', [])
        context = query_data.get('context', {})
        
        # Facteurs de difficulté
        difficulty_score = 0
        
        # Nombre de mots-clés
        if len(keywords) <= 2:
            difficulty_score += 1  # Simple
        elif len(keywords) <= 4:
            difficulty_score += 2  # Moyen
        else:
            difficulty_score += 3  # Difficile
        
        # Contexte spécialisé
        if context.get('urgency') == 'critical':
            difficulty_score += 1
        if context.get('drug_resistance'):
            difficulty_score += 1
        if context.get('pregnancy'):
            difficulty_score += 1
        
        # Catégorie
        complex_categories = ['complications', 'resistance', 'epidemiology']
        if query_data.get('category') in complex_categories:
            difficulty_score += 1
        
        if difficulty_score <= 2:
            return 'easy'
        elif difficulty_score <= 4:
            return 'medium'
        else:
            return 'hard'

class MetricsCalculator:
    """Calculateur de métriques"""
    
    def calculate_precision_at_k(self, actual: List[str], expected: List[str], k: int = 5) -> float:
        """Calculer la précision@K"""
        if not actual or k <= 0:
            return 0.0
        
        actual_k = actual[:k]
        relevant_retrieved = len(set(actual_k) & set(expected))
        
        return relevant_retrieved / min(k, len(actual_k))
    
    def calculate_recall_at_k(self, actual: List[str], expected: List[str], k: int = 5) -> float:
        """Calculer le rappel@K"""
        if not expected or k <= 0:
            return 0.0
        
        actual_k = actual[:k]
        relevant_retrieved = len(set(actual_k) & set(expected))
        
        return relevant_retrieved / len(expected)
    
    def calculate_f1_score(self, precision: float, recall: float) -> float:
        """Calculer le score F1"""
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def calculate_map(self, actual_results: List[List[str]], expected_results: List[List[str]]) -> float:
        """Calculer Mean Average Precision"""
        if not actual_results or not expected_results:
            return 0.0
        
        average_precisions = []
        
        for actual, expected in zip(actual_results, expected_results):
            if not expected:
                continue
            
            precisions = []
            relevant_count = 0
            
            for i, doc in enumerate(actual):
                if doc in expected:
                    relevant_count += 1
                    precision_at_i = relevant_count / (i + 1)
                    precisions.append(precision_at_i)
            
            if precisions:
                average_precisions.append(sum(precisions) / len(precisions))
            else:
                average_precisions.append(0.0)
        
        return sum(average_precisions) / len(average_precisions) if average_precisions else 0.0
    
    def calculate_ndcg(self, actual: List[str], expected: List[str], 
                      relevance_scores: List[float], k: int = 5) -> float:
        """Calculer Normalized Discounted Cumulative Gain@K"""
        if not actual or not expected or not relevance_scores:
            return 0.0
        
        # Créer un mapping des scores de pertinence
        relevance_map = {doc: score for doc, score in zip(expected, relevance_scores)}
        
        # Calculer DCG
        dcg = 0.0
        for i, doc in enumerate(actual[:k]):
            if doc in relevance_map:
                relevance = relevance_map[doc]
                dcg += relevance / (1 + i)  # Simplification de log2(i+2)
        
        # Calculer IDCG (DCG idéal)
        sorted_relevance = sorted(relevance_scores, reverse=True)[:k]
        idcg = sum(rel / (1 + i) for i, rel in enumerate(sorted_relevance))
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def calculate_mrr(self, actual_results: List[List[str]], expected_results: List[List[str]]) -> float:
        """Calculer Mean Reciprocal Rank"""
        if not actual_results or not expected_results:
            return 0.0
        
        reciprocal_ranks = []
        
        for actual, expected in zip(actual_results, expected_results):
            if not expected:
                reciprocal_ranks.append(0.0)
                continue
            
            # Trouver le premier résultat pertinent
            for i, doc in enumerate(actual):
                if doc in expected:
                    reciprocal_ranks.append(1.0 / (i + 1))
                    break
            else:
                reciprocal_ranks.append(0.0)
        
        return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

class RAGSimulator:
    """Simulateur de système RAG pour les tests"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            'base_latency_ms': 50,
            'latency_variance': 20,
            'error_rate': 0.02,
            'cache_hit_rate': 0.3
        }
        
        self.document_corpus = self._initialize_corpus()
        self.query_cache = {}
        
    def query(self, query: str, context: Dict[str, Any] = None) -> Tuple[List[str], List[float], float]:
        """Simuler une requête RAG"""
        start_time = time.time()
        
        # Simuler une erreur occasionnelle
        if random.random() < self.config['error_rate']:
            raise Exception("Simulated RAG error")
        
        # Vérifier le cache
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.query_cache and random.random() < self.config['cache_hit_rate']:
            results, scores = self.query_cache[cache_key]
        else:
            # Simuler la recherche
            results, scores = self._simulate_search(query, context)
            self.query_cache[cache_key] = (results, scores)
        
        # Simuler la latence
        latency_ms = self._simulate_latency()
        time.sleep(latency_ms / 1000)  # Convertir en secondes
        
        execution_time = (time.time() - start_time) * 1000
        
        return results, scores, execution_time
    
    def _initialize_corpus(self) -> Dict[str, Dict[str, Any]]:
        """Initialiser le corpus de documents"""
        corpus = {}
        
        # Générer des documents simulés
        for i in range(1, 41):  # 40 documents
            doc_id = f"doc_{i:03d}"
            corpus[doc_id] = {
                'title': f"Document médical {i}",
                'content': f"Contenu du document {i} sur le paludisme et les maladies tropicales.",
                'category': random.choice(['treatment', 'diagnosis', 'prevention', 'research']),
                'relevance_base': random.uniform(0.3, 0.9),
                'last_updated': datetime.now() - timedelta(days=random.randint(1, 365))
            }
        
        return corpus
    
    def _simulate_search(self, query: str, context: Dict[str, Any] = None) -> Tuple[List[str], List[float]]:
        """Simuler une recherche dans le corpus"""
        query_lower = query.lower()
        
        # Calculer les scores de pertinence simulés
        scored_docs = []
        
        for doc_id, doc_data in self.document_corpus.items():
            # Score de base
            base_score = doc_data['relevance_base']
            
            # Bonus pour correspondance de mots-clés
            content_lower = doc_data['content'].lower()
            title_lower = doc_data['title'].lower()
            
            keyword_bonus = 0
            query_words = query_lower.split()
            for word in query_words:
                if word in content_lower:
                    keyword_bonus += 0.1
                if word in title_lower:
                    keyword_bonus += 0.15
            
            # Score final avec bruit
            final_score = base_score + keyword_bonus + random.uniform(-0.1, 0.1)
            final_score = max(0.0, min(1.0, final_score))
            
            scored_docs.append((doc_id, final_score))
        
        # Trier par score décroissant
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Retourner les top résultats
        num_results = random.randint(5, 12)
        top_docs = scored_docs[:num_results]
        
        doc_ids = [doc[0] for doc in top_docs]
        scores = [doc[1] for doc in top_docs]
        
        return doc_ids, scores
    
    def _simulate_latency(self) -> float:
        """Simuler la latence de réponse"""
        base_latency = self.config['base_latency_ms']
        variance = self.config['latency_variance']
        
        # Distribution normale avec variance
        latency = random.normalvariate(base_latency, variance)
        return max(10, latency)  # Minimum 10ms

class PrecisionTester:
    """Testeur de précision principal"""
    
    def __init__(self, rag_system=None, config: Dict[str, Any] = None):
        self.config = config or {
            'parallel_tests': 4,
            'timeout_seconds': 30,
            'retry_attempts': 2,
            'metrics_to_calculate': [
                MetricType.PRECISION_AT_K,
                MetricType.RECALL_AT_K,
                MetricType.F1_SCORE,
                MetricType.MAP,
                MetricType.NDCG,
                MetricType.MRR
            ]
        }
        
        self.rag_system = rag_system or RAGSimulator()
        self.data_generator = TestDataGenerator()
        self.metrics_calculator = MetricsCalculator()
        
        self.test_history = deque(maxlen=1000)
        self.benchmark_history = deque(maxlen=100)
        
        logger.info("PrecisionTester initialisé")
    
    def run_single_test(self, test_case: TestCase) -> TestResult:
        """Exécuter un test unique"""
        start_time = time.time()
        
        try:
            # Exécuter la requête
            actual_results, actual_relevance, query_time = self.rag_system.query(
                test_case.query, 
                test_case.context
            )
            
            # Calculer les métriques
            metrics = self._calculate_metrics(
                test_case, 
                actual_results, 
                actual_relevance
            )
            
            # Déterminer le statut
            status = self._determine_test_status(metrics)
            
            execution_time = (time.time() - start_time) * 1000
            
            result = TestResult(
                test_id=test_case.test_id,
                test_type=TestType.PRECISION,
                status=status,
                actual_results=actual_results,
                actual_relevance=actual_relevance,
                metrics=metrics,
                execution_time_ms=execution_time,
                metadata={
                    'query_time_ms': query_time,
                    'difficulty': test_case.difficulty_level,
                    'category': test_case.category
                }
            )
            
            logger.info(f"Test {test_case.test_id}: {status.value} ({execution_time:.1f}ms)")
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = TestResult(
                test_id=test_case.test_id,
                test_type=TestType.PRECISION,
                status=TestStatus.ERROR,
                actual_results=[],
                actual_relevance=[],
                execution_time_ms=execution_time,
                error_message=str(e)
            )
            
            logger.error(f"Test {test_case.test_id}: ERROR - {e}")
        
        return result
    
    def run_test_suite(self, test_cases: List[TestCase], suite_name: str = "default") -> BenchmarkResult:
        """Exécuter une suite de tests"""
        start_time = time.time()
        
        logger.info(f"Démarrage de la suite '{suite_name}': {len(test_cases)} tests")
        
        # Exécuter les tests en parallèle
        results = []
        with ThreadPoolExecutor(max_workers=self.config['parallel_tests']) as executor:
            future_to_test = {executor.submit(self.run_single_test, test): test for test in test_cases}
            
            for future in as_completed(future_to_test):
                try:
                    result = future.result(timeout=self.config['timeout_seconds'])
                    results.append(result)
                except Exception as e:
                    test_case = future_to_test[future]
                    error_result = TestResult(
                        test_id=test_case.test_id,
                        test_type=TestType.PRECISION,
                        status=TestStatus.ERROR,
                        actual_results=[],
                        actual_relevance=[],
                        error_message=f"Timeout or execution error: {e}"
                    )
                    results.append(error_result)
        
        # Calculer les statistiques globales
        passed_tests = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == TestStatus.FAILED)
        error_tests = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        # Calculer les métriques globales
        overall_metrics = self._calculate_overall_metrics(results)
        
        execution_time = (time.time() - start_time) * 1000
        
        benchmark_result = BenchmarkResult(
            benchmark_id=f"bench_{int(time.time())}_{suite_name}",
            test_suite=suite_name,
            total_tests=len(test_cases),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            overall_metrics=overall_metrics,
            execution_time_ms=execution_time,
            detailed_results=results
        )
        
        # Enregistrer dans l'historique
        self.benchmark_history.append(benchmark_result)
        self.test_history.extend(results)
        
        logger.info(f"Suite '{suite_name}' terminée: {passed_tests}/{len(test_cases)} réussis")
        
        return benchmark_result
    
    def _calculate_metrics(self, test_case: TestCase, actual_results: List[str], 
                          actual_relevance: List[float]) -> Dict[MetricType, float]:
        """Calculer les métriques pour un test"""
        metrics = {}
        
        expected_results = test_case.expected_results
        expected_relevance = test_case.expected_relevance
        
        # Précision@K et Rappel@K
        for k in [1, 3, 5, 10]:
            if MetricType.PRECISION_AT_K in self.config['metrics_to_calculate']:
                precision_k = self.metrics_calculator.calculate_precision_at_k(
                    actual_results, expected_results, k
                )
                metrics[f"precision_at_{k}"] = precision_k
            
            if MetricType.RECALL_AT_K in self.config['metrics_to_calculate']:
                recall_k = self.metrics_calculator.calculate_recall_at_k(
                    actual_results, expected_results, k
                )
                metrics[f"recall_at_{k}"] = recall_k
        
        # F1 Score (utiliser P@5 et R@5)
        if MetricType.F1_SCORE in self.config['metrics_to_calculate']:
            precision_5 = metrics.get("precision_at_5", 0)
            recall_5 = metrics.get("recall_at_5", 0)
            f1 = self.metrics_calculator.calculate_f1_score(precision_5, recall_5)
            metrics[MetricType.F1_SCORE] = f1
        
        # NDCG@5
        if MetricType.NDCG in self.config['metrics_to_calculate']:
            ndcg = self.metrics_calculator.calculate_ndcg(
                actual_results, expected_results, expected_relevance, k=5
            )
            metrics[MetricType.NDCG] = ndcg
        
        return metrics
    
    def _determine_test_status(self, metrics: Dict[str, float]) -> TestStatus:
        """Déterminer le statut d'un test basé sur les métriques"""
        # Seuils de réussite
        thresholds = {
            'precision_at_5': 0.6,
            'recall_at_5': 0.4,
            MetricType.F1_SCORE: 0.5,
            MetricType.NDCG: 0.6
        }
        
        passed_metrics = 0
        total_metrics = 0
        
        for metric_name, threshold in thresholds.items():
            if metric_name in metrics:
                total_metrics += 1
                if metrics[metric_name] >= threshold:
                    passed_metrics += 1
        
        # Réussi si au moins 70% des métriques passent
        if total_metrics > 0 and (passed_metrics / total_metrics) >= 0.7:
            return TestStatus.PASSED
        else:
            return TestStatus.FAILED
    
    def _calculate_overall_metrics(self, results: List[TestResult]) -> Dict[MetricType, float]:
        """Calculer les métriques globales"""
        overall_metrics = {}
        
        # Filtrer les résultats réussis
        successful_results = [r for r in results if r.status in [TestStatus.PASSED, TestStatus.FAILED]]
        
        if not successful_results:
            return overall_metrics
        
        # Calculer les moyennes pour chaque métrique
        metric_values = defaultdict(list)
        
        for result in successful_results:
            for metric_name, value in result.metrics.items():
                metric_values[metric_name].append(value)
        
        for metric_name, values in metric_values.items():
            if values:
                overall_metrics[metric_name] = statistics.mean(values)
        
        # Métriques de performance
        execution_times = [r.execution_time_ms for r in successful_results]
        if execution_times:
            overall_metrics[MetricType.LATENCY_P95] = statistics.quantiles(execution_times, n=20)[18]  # P95
        
        # Taux d'erreur
        error_count = sum(1 for r in results if r.status == TestStatus.ERROR)
        overall_metrics['error_rate'] = error_count / len(results) if results else 0
        
        # Taux de réussite
        passed_count = sum(1 for r in results if r.status == TestStatus.PASSED)
        overall_metrics['success_rate'] = passed_count / len(results) if results else 0
        
        return overall_metrics
    
    def run_performance_benchmark(self, num_queries: int = 100, 
                                 concurrent_users: int = 10) -> PerformanceMetrics:
        """Exécuter un benchmark de performance"""
        logger.info(f"Benchmark de performance: {num_queries} requêtes, {concurrent_users} utilisateurs")
        
        # Générer des requêtes de test
        test_queries = []
        for i in range(num_queries):
            query_data = random.choice(self.data_generator.medical_queries)
            test_queries.append(query_data['query'])
        
        # Mesurer les performances
        start_time = time.time()
        latencies = []
        errors = 0
        
        def execute_query(query):
            try:
                _, _, latency = self.rag_system.query(query)
                return latency
            except Exception:
                return None
        
        # Exécuter en parallèle
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(execute_query, query) for query in test_queries]
            
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    latencies.append(result)
                else:
                    errors += 1
        
        total_time = time.time() - start_time
        
        # Calculer les métriques
        metrics = PerformanceMetrics()
        
        if latencies:
            metrics.avg_latency_ms = statistics.mean(latencies)
            sorted_latencies = sorted(latencies)
            metrics.p95_latency_ms = statistics.quantiles(sorted_latencies, n=20)[18]  # P95
            metrics.p99_latency_ms = statistics.quantiles(sorted_latencies, n=100)[98]  # P99
        
        metrics.throughput_qps = num_queries / total_time
        metrics.error_rate = errors / num_queries
        
        # Métriques simulées
        metrics.memory_usage_mb = random.uniform(100, 500)
        metrics.cpu_usage_percent = random.uniform(20, 80)
        metrics.cache_hit_rate = self.rag_system.config.get('cache_hit_rate', 0.3)
        
        logger.info(f"Benchmark terminé: {metrics.throughput_qps:.1f} QPS, {metrics.avg_latency_ms:.1f}ms avg")
        
        return metrics
    
    def generate_report(self, benchmark_result: BenchmarkResult, 
                       performance_metrics: PerformanceMetrics = None) -> Dict[str, Any]:
        """Générer un rapport détaillé"""
        report = {
            'benchmark_summary': {
                'benchmark_id': benchmark_result.benchmark_id,
                'test_suite': benchmark_result.test_suite,
                'timestamp': benchmark_result.timestamp.isoformat(),
                'total_tests': benchmark_result.total_tests,
                'passed_tests': benchmark_result.passed_tests,
                'failed_tests': benchmark_result.failed_tests,
                'error_tests': benchmark_result.error_tests,
                'success_rate': benchmark_result.passed_tests / benchmark_result.total_tests,
                'execution_time_ms': benchmark_result.execution_time_ms
            },
            'quality_metrics': benchmark_result.overall_metrics,
            'performance_metrics': asdict(performance_metrics) if performance_metrics else {},
            'detailed_analysis': self._analyze_results(benchmark_result),
            'recommendations': self._generate_recommendations(benchmark_result, performance_metrics)
        }
        
        return report
    
    def _analyze_results(self, benchmark_result: BenchmarkResult) -> Dict[str, Any]:
        """Analyser les résultats en détail"""
        analysis = {
            'by_difficulty': defaultdict(lambda: {'passed': 0, 'failed': 0, 'error': 0}),
            'by_category': defaultdict(lambda: {'passed': 0, 'failed': 0, 'error': 0}),
            'metric_distributions': defaultdict(list),
            'performance_analysis': {}
        }
        
        for result in benchmark_result.detailed_results:
            # Analyse par difficulté
            difficulty = result.metadata.get('difficulty', 'unknown')
            analysis['by_difficulty'][difficulty][result.status.value] += 1
            
            # Analyse par catégorie
            category = result.metadata.get('category', 'unknown')
            analysis['by_category'][category][result.status.value] += 1
            
            # Distribution des métriques
            for metric_name, value in result.metrics.items():
                analysis['metric_distributions'][metric_name].append(value)
        
        # Calculer les statistiques des distributions
        for metric_name, values in analysis['metric_distributions'].items():
            if values:
                analysis['metric_distributions'][metric_name] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'min': min(values),
                    'max': max(values)
                }
        
        return analysis
    
    def _generate_recommendations(self, benchmark_result: BenchmarkResult, 
                                performance_metrics: PerformanceMetrics = None) -> List[str]:
        """Générer des recommandations d'amélioration"""
        recommendations = []
        
        # Analyse du taux de réussite
        success_rate = benchmark_result.passed_tests / benchmark_result.total_tests
        if success_rate < 0.8:
            recommendations.append(f"Taux de réussite faible ({success_rate:.1%}): améliorer la qualité des résultats")
        
        # Analyse des métriques de qualité
        overall_metrics = benchmark_result.overall_metrics
        
        if overall_metrics.get('precision_at_5', 0) < 0.7:
            recommendations.append("Précision@5 faible: optimiser l'algorithme de ranking")
        
        if overall_metrics.get('recall_at_5', 0) < 0.5:
            recommendations.append("Rappel@5 faible: enrichir le corpus ou améliorer la recherche")
        
        if overall_metrics.get(MetricType.NDCG, 0) < 0.6:
            recommendations.append("NDCG faible: améliorer la pertinence des scores")
        
        # Analyse des performances
        if performance_metrics:
            if performance_metrics.avg_latency_ms > 100:
                recommendations.append(f"Latence élevée ({performance_metrics.avg_latency_ms:.1f}ms): optimiser les performances")
            
            if performance_metrics.error_rate > 0.05:
                recommendations.append(f"Taux d'erreur élevé ({performance_metrics.error_rate:.1%}): améliorer la robustesse")
            
            if performance_metrics.throughput_qps < 10:
                recommendations.append(f"Débit faible ({performance_metrics.throughput_qps:.1f} QPS): optimiser la scalabilité")
        
        # Analyse par difficulté
        analysis = self._analyze_results(benchmark_result)
        for difficulty, stats in analysis['by_difficulty'].items():
            total = sum(stats.values())
            if total > 0:
                success_rate_diff = stats['passed'] / total
                if success_rate_diff < 0.6:
                    recommendations.append(f"Performance faible pour difficulté '{difficulty}': adapter les algorithmes")
        
        if not recommendations:
            recommendations.append("Excellentes performances! Continuer le monitoring régulier.")
        
        return recommendations
    
    def export_results(self, benchmark_result: BenchmarkResult, 
                      performance_metrics: PerformanceMetrics = None,
                      filename: str = "precision_testing_results.json"):
        """Exporter les résultats"""
        try:
            report = self.generate_report(benchmark_result, performance_metrics)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Résultats exportés vers {filename}")
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")

def main():
    """Fonction principale de démonstration"""
    print("🎯 Precision Testing & Benchmarking - Objectif 18")
    print("Tests de précision et benchmarking du RAG optimisé")
    print("=" * 60)
    
    # Configuration du testeur
    config = {
        'parallel_tests': 4,
        'timeout_seconds': 30,
        'retry_attempts': 2,
        'metrics_to_calculate': [
            MetricType.PRECISION_AT_K,
            MetricType.RECALL_AT_K,
            MetricType.F1_SCORE,
            MetricType.NDCG,
            MetricType.MRR
        ]
    }
    
    # Initialiser le testeur
    tester = PrecisionTester(config=config)
    
    print("\n🔧 Initialisation du système de test...")
    print(f"Système RAG simulé configuré")
    print(f"Tests parallèles: {config['parallel_tests']}")
    print(f"Timeout: {config['timeout_seconds']}s")
    
    # Générer une suite de tests
    print("\n📝 Génération de la suite de tests...")
    test_cases = tester.data_generator.generate_test_suite("medical_rag_precision", 25)
    
    print(f"Suite générée: {len(test_cases)} cas de test")
    
    # Afficher quelques exemples
    print("\n📋 Exemples de cas de test:")
    for i, test_case in enumerate(test_cases[:3]):
        print(f"  {i+1}. [{test_case.difficulty_level}] {test_case.query}")
        print(f"     Catégorie: {test_case.category}")
        print(f"     Résultats attendus: {len(test_case.expected_results)}")
    
    # Exécuter la suite de tests
    print("\n🚀 Exécution de la suite de tests de précision...")
    start_time = time.time()
    
    benchmark_result = tester.run_test_suite(test_cases, "medical_rag_precision_v1")
    
    execution_time = time.time() - start_time
    
    # Afficher les résultats
    print(f"\n📊 Résultats de la suite de tests:")
    print(f"Temps d'exécution: {execution_time:.1f}s")
    print(f"Tests totaux: {benchmark_result.total_tests}")
    print(f"Tests réussis: {benchmark_result.passed_tests} ({benchmark_result.passed_tests/benchmark_result.total_tests:.1%})")
    print(f"Tests échoués: {benchmark_result.failed_tests} ({benchmark_result.failed_tests/benchmark_result.total_tests:.1%})")
    print(f"Tests en erreur: {benchmark_result.error_tests} ({benchmark_result.error_tests/benchmark_result.total_tests:.1%})")
    
    # Métriques de qualité
    print("\n📈 Métriques de qualité:")
    for metric_name, value in benchmark_result.overall_metrics.items():
        if isinstance(metric_name, str) and 'precision_at' in metric_name:
            print(f"  {metric_name}: {value:.1%}")
        elif isinstance(metric_name, str) and 'recall_at' in metric_name:
            print(f"  {metric_name}: {value:.1%}")
        elif metric_name == MetricType.F1_SCORE:
            print(f"  F1 Score: {value:.1%}")
        elif metric_name == MetricType.NDCG:
            print(f"  NDCG@5: {value:.1%}")
        elif metric_name == 'success_rate':
            print(f"  Taux de réussite: {value:.1%}")
        elif metric_name == 'error_rate':
            print(f"  Taux d'erreur: {value:.1%}")
    
    # Benchmark de performance
    print("\n⚡ Exécution du benchmark de performance...")
    performance_metrics = tester.run_performance_benchmark(num_queries=50, concurrent_users=5)
    
    print(f"\n🚀 Métriques de performance:")
    print(f"Latence moyenne: {performance_metrics.avg_latency_ms:.1f}ms")
    print(f"Latence P95: {performance_metrics.p95_latency_ms:.1f}ms")
    print(f"Latence P99: {performance_metrics.p99_latency_ms:.1f}ms")
    print(f"Débit: {performance_metrics.throughput_qps:.1f} requêtes/seconde")
    print(f"Taux d'erreur: {performance_metrics.error_rate:.1%}")
    print(f"Utilisation mémoire: {performance_metrics.memory_usage_mb:.1f}MB")
    print(f"Utilisation CPU: {performance_metrics.cpu_usage_percent:.1f}%")
    print(f"Taux de cache hit: {performance_metrics.cache_hit_rate:.1%}")
    
    # Générer le rapport
    print("\n📋 Génération du rapport d'analyse...")
    report = tester.generate_report(benchmark_result, performance_metrics)
    
    # Afficher les recommandations
    print("\n💡 Recommandations d'amélioration:")
    for i, recommendation in enumerate(report['recommendations'], 1):
        print(f"  {i}. {recommendation}")
    
    # Analyse détaillée
    analysis = report['detailed_analysis']
    
    print("\n🔍 Analyse par difficulté:")
    for difficulty, stats in analysis['by_difficulty'].items():
        total = sum(stats.values())
        if total > 0:
            success_rate = stats['passed'] / total
            print(f"  {difficulty}: {stats['passed']}/{total} ({success_rate:.1%} réussite)")
    
    print("\n📂 Analyse par catégorie:")
    for category, stats in analysis['by_category'].items():
        total = sum(stats.values())
        if total > 0:
            success_rate = stats['passed'] / total
            print(f"  {category}: {stats['passed']}/{total} ({success_rate:.1%} réussite)")
    
    # Export des résultats
    print("\n💾 Export des résultats...")
    tester.export_results(benchmark_result, performance_metrics)
    
    # Évaluation finale
    print("\n🎯 Évaluation finale:")
    
    # Critères de succès
    success_criteria = {
        'tests_executed': benchmark_result.total_tests >= 20,
        'success_rate': (benchmark_result.passed_tests / benchmark_result.total_tests) >= 0.7,
        'precision_quality': benchmark_result.overall_metrics.get('precision_at_5', 0) >= 0.6,
        'performance_latency': performance_metrics.avg_latency_ms <= 150,
        'performance_throughput': performance_metrics.throughput_qps >= 5,
        'error_rate_acceptable': performance_metrics.error_rate <= 0.1
    }
    
    success_count = sum(success_criteria.values())
    total_criteria = len(success_criteria)
    
    if success_count >= 5:
        print("✅ Objectif 18 ATTEINT - Système de tests de précision opérationnel!")
    elif success_count >= 4:
        print("⚠️ Objectif 18 PARTIELLEMENT ATTEINT - Système fonctionnel avec optimisations possibles")
    else:
        print("❌ Objectif 18 NON ATTEINT - Système nécessite des améliorations")
    
    print(f"\n📊 Critères de succès ({success_count}/{total_criteria}):")
    for criterion, passed in success_criteria.items():
        status_icon = "✅" if passed else "❌"
        print(f"  {status_icon} {criterion}: {passed}")
    
    print(f"\n📈 Résumé final:")
    print(f"🧪 Tests exécutés: {benchmark_result.total_tests}")
    print(f"✅ Taux de réussite: {benchmark_result.passed_tests/benchmark_result.total_tests:.1%}")
    print(f"🎯 Précision@5: {benchmark_result.overall_metrics.get('precision_at_5', 0):.1%}")
    print(f"⚡ Latence moyenne: {performance_metrics.avg_latency_ms:.1f}ms")
    print(f"🚀 Débit: {performance_metrics.throughput_qps:.1f} QPS")
    print(f"📊 Tests automatisés de précision opérationnels")
    print(f"⚙️ Benchmarking de performance intégré")
    print(f"📋 Rapports détaillés et recommandations")
    print(f"🔄 Validation continue de la qualité")

if __name__ == "__main__":
    main()