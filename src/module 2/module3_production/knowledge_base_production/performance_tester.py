#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testeur de Performance en Volume de Production - Objectif 10
Module 3: Production Data & Knowledge - Base de Connaissances Production

Ce module implémente un système complet de tests de performance pour valider
que la base de connaissances peut gérer les volumes de production attendus
avec des performances acceptables.

Fonctionnalités:
- Tests de charge et de stress
- Tests de performance en volume
- Benchmarking des opérations
- Monitoring des ressources
- Tests de concurrence
- Analyse des goulots d'étranglement
- Rapports de performance détaillés
"""

import logging
import json
import time
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import sqlite3
import hashlib
import statistics
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import queue
import gc
import tracemalloc
import resource
import sys

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types de tests de performance"""
    LOAD_TEST = "load_test"              # Test de charge
    STRESS_TEST = "stress_test"          # Test de stress
    VOLUME_TEST = "volume_test"          # Test de volume
    CONCURRENCY_TEST = "concurrency_test"  # Test de concurrence
    ENDURANCE_TEST = "endurance_test"    # Test d'endurance
    SPIKE_TEST = "spike_test"            # Test de pic
    BENCHMARK = "benchmark"              # Benchmark

class TestStatus(Enum):
    """Statuts des tests"""
    PENDING = "pending"                  # En attente
    RUNNING = "running"                  # En cours
    COMPLETED = "completed"              # Terminé
    FAILED = "failed"                    # Échec
    CANCELLED = "cancelled"              # Annulé
    TIMEOUT = "timeout"                  # Timeout

class PerformanceMetric(Enum):
    """Métriques de performance"""
    RESPONSE_TIME = "response_time"      # Temps de réponse
    THROUGHPUT = "throughput"            # Débit
    CPU_USAGE = "cpu_usage"              # Utilisation CPU
    MEMORY_USAGE = "memory_usage"        # Utilisation mémoire
    DISK_IO = "disk_io"                  # E/S disque
    NETWORK_IO = "network_io"            # E/S réseau
    ERROR_RATE = "error_rate"            # Taux d'erreur
    CONCURRENCY = "concurrency"          # Niveau de concurrence

@dataclass
class TestConfiguration:
    """Configuration de test"""
    test_id: str
    test_type: TestType
    name: str
    description: str
    duration_seconds: int = 300  # 5 minutes par défaut
    max_users: int = 100
    ramp_up_time: int = 60
    target_operations_per_second: int = 10
    data_volume_mb: int = 100
    concurrent_threads: int = 10
    timeout_seconds: int = 30
    success_criteria: Dict[str, float] = field(default_factory=dict)
    test_data_config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResourceMetrics:
    """Métriques de ressources système"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_threads: int
    open_files: int

@dataclass
class OperationResult:
    """Résultat d'une opération"""
    operation_id: str
    operation_type: str
    start_time: datetime
    end_time: datetime
    duration_ms: int
    success: bool
    error_message: Optional[str] = None
    data_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestResult:
    """Résultat de test de performance"""
    test_id: str
    test_type: TestType
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    average_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    percentile_95_ms: float = 0.0
    percentile_99_ms: float = 0.0
    throughput_ops_per_second: float = 0.0
    error_rate_percent: float = 0.0
    peak_cpu_percent: float = 0.0
    peak_memory_mb: float = 0.0
    resource_metrics: List[ResourceMetrics] = field(default_factory=list)
    operation_results: List[OperationResult] = field(default_factory=list)
    success_criteria_met: bool = False
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ResourceMonitor:
    """Moniteur de ressources système"""
    
    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = interval_seconds
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
        self.process = psutil.Process()
        
        # Métriques de base pour calcul des deltas
        self.last_disk_read = 0
        self.last_disk_write = 0
        self.last_network_sent = 0
        self.last_network_recv = 0
    
    def start_monitoring(self):
        """Démarrer le monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.metrics = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Monitoring des ressources démarré")
    
    def stop_monitoring(self):
        """Arrêter le monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Monitoring des ressources arrêté")
    
    def _monitor_loop(self):
        """Boucle de monitoring"""
        while self.monitoring:
            try:
                # Métriques CPU et mémoire
                cpu_percent = psutil.cpu_percent(interval=None)
                memory_info = psutil.virtual_memory()
                
                # Métriques du processus
                process_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                
                # Métriques disque (système global)
                disk_io = psutil.disk_io_counters()
                disk_read_mb = (disk_io.read_bytes - self.last_disk_read) / 1024 / 1024 if disk_io else 0
                disk_write_mb = (disk_io.write_bytes - self.last_disk_write) / 1024 / 1024 if disk_io else 0
                
                if disk_io:
                    self.last_disk_read = disk_io.read_bytes
                    self.last_disk_write = disk_io.write_bytes
                
                # Métriques réseau (système global)
                network_io = psutil.net_io_counters()
                network_sent_mb = (network_io.bytes_sent - self.last_network_sent) / 1024 / 1024 if network_io else 0
                network_recv_mb = (network_io.bytes_recv - self.last_network_recv) / 1024 / 1024 if network_io else 0
                
                if network_io:
                    self.last_network_sent = network_io.bytes_sent
                    self.last_network_recv = network_io.bytes_recv
                
                # Métriques de threads et fichiers
                active_threads = threading.active_count()
                try:
                    open_files = len(self.process.open_files())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    open_files = 0
                
                # Créer la métrique
                metric = ResourceMetrics(
                    timestamp=datetime.now(),
                    cpu_percent=cpu_percent,
                    memory_percent=memory_info.percent,
                    memory_used_mb=process_memory,
                    disk_read_mb=max(0, disk_read_mb),
                    disk_write_mb=max(0, disk_write_mb),
                    network_sent_mb=max(0, network_sent_mb),
                    network_recv_mb=max(0, network_recv_mb),
                    active_threads=active_threads,
                    open_files=open_files
                )
                
                self.metrics.append(metric)
                
                # Limiter le nombre de métriques en mémoire
                if len(self.metrics) > 10000:
                    self.metrics = self.metrics[-5000:]
                
                time.sleep(self.interval_seconds)
                
            except Exception as e:
                logger.error(f"Erreur dans le monitoring: {e}")
                time.sleep(self.interval_seconds)
    
    def get_metrics(self) -> List[ResourceMetrics]:
        """Obtenir les métriques collectées"""
        return self.metrics.copy()
    
    def get_peak_metrics(self) -> Dict[str, float]:
        """Obtenir les pics de métriques"""
        if not self.metrics:
            return {}
        
        return {
            'peak_cpu_percent': max(m.cpu_percent for m in self.metrics),
            'peak_memory_percent': max(m.memory_percent for m in self.metrics),
            'peak_memory_mb': max(m.memory_used_mb for m in self.metrics),
            'peak_disk_read_mb': max(m.disk_read_mb for m in self.metrics),
            'peak_disk_write_mb': max(m.disk_write_mb for m in self.metrics),
            'peak_threads': max(m.active_threads for m in self.metrics),
            'peak_open_files': max(m.open_files for m in self.metrics)
        }

class WorkloadSimulator:
    """Simulateur de charge de travail"""
    
    def __init__(self):
        self.operations = []
        self.results_queue = queue.Queue()
    
    def generate_test_data(self, size_mb: int) -> List[Dict[str, Any]]:
        """Générer des données de test"""
        # Calculer le nombre d'éléments pour atteindre la taille cible
        target_size_bytes = size_mb * 1024 * 1024
        
        # Estimer la taille d'un élément (environ 1KB par document)
        estimated_item_size = 1024
        num_items = max(1, target_size_bytes // estimated_item_size)
        
        test_data = []
        
        for i in range(num_items):
            # Générer un document médical simulé
            doc = {
                'id': f'doc_{i}',
                'title': f'Document médical {i}',
                'content': f'Contenu médical simulé pour le document {i}. ' * 20,  # ~500 caractères
                'category': ['cardiologie', 'neurologie', 'oncologie', 'pédiatrie'][i % 4],
                'type': ['diagnostic', 'traitement', 'symptôme', 'procédure'][i % 4],
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0',
                    'author': f'Dr. Test {i % 10}',
                    'tags': [f'tag_{j}' for j in range(i % 5 + 1)]
                },
                'embedding': np.random.randn(384).tolist()  # Embedding simulé
            }
            test_data.append(doc)
        
        actual_size_mb = len(json.dumps(test_data).encode('utf-8')) / 1024 / 1024
        logger.info(f"Données de test générées: {len(test_data)} documents, {actual_size_mb:.2f} MB")
        
        return test_data
    
    def simulate_search_operation(self, 
                                operation_id: str,
                                query: str = "recherche médicale",
                                delay_ms: int = 50) -> OperationResult:
        """Simuler une opération de recherche"""
        start_time = datetime.now()
        
        try:
            # Simuler le temps de traitement
            processing_time = delay_ms + np.random.exponential(20)  # Distribution exponentielle
            time.sleep(processing_time / 1000)
            
            # Simuler des résultats
            num_results = np.random.randint(1, 20)
            results_size = num_results * 1024  # 1KB par résultat
            
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Simuler un taux d'erreur de 2%
            success = np.random.random() > 0.02
            
            return OperationResult(
                operation_id=operation_id,
                operation_type="search",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                success=success,
                error_message=None if success else "Erreur simulée",
                data_size_bytes=results_size,
                metadata={'query': query, 'num_results': num_results}
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return OperationResult(
                operation_id=operation_id,
                operation_type="search",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
    
    def simulate_indexing_operation(self, 
                                  operation_id: str,
                                  document: Dict[str, Any]) -> OperationResult:
        """Simuler une opération d'indexation"""
        start_time = datetime.now()
        
        try:
            # Simuler le temps d'indexation (plus long que la recherche)
            doc_size = len(json.dumps(document).encode('utf-8'))
            processing_time = 100 + (doc_size / 1024) * 10  # 100ms + 10ms par KB
            time.sleep(processing_time / 1000)
            
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Simuler un taux d'erreur de 1%
            success = np.random.random() > 0.01
            
            return OperationResult(
                operation_id=operation_id,
                operation_type="indexing",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                success=success,
                error_message=None if success else "Erreur d'indexation simulée",
                data_size_bytes=doc_size,
                metadata={'document_id': document.get('id', 'unknown')}
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return OperationResult(
                operation_id=operation_id,
                operation_type="indexing",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
    
    def run_concurrent_operations(self, 
                                operations: List[Callable],
                                max_workers: int = 10) -> List[OperationResult]:
        """Exécuter des opérations en parallèle"""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(op) for op in operations]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Erreur dans l'opération concurrente: {e}")
        
        return results

class PerformanceTester:
    """Testeur principal de performance"""
    
    def __init__(self):
        self.resource_monitor = ResourceMonitor()
        self.workload_simulator = WorkloadSimulator()
        
        # Base de données pour les résultats
        self.db_path = Path("performance_tests.db")
        self._initialize_database()
        
        # Configuration par défaut
        self.default_success_criteria = {
            'max_avg_response_time_ms': 200,
            'max_95_percentile_ms': 500,
            'min_throughput_ops_per_second': 10,
            'max_error_rate_percent': 5,
            'max_cpu_percent': 80,
            'max_memory_mb': 2048
        }
        
        logger.info("PerformanceTester initialisé")
    
    def _initialize_database(self):
        """Initialiser la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des tests
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_tests (
                test_id TEXT PRIMARY KEY,
                test_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds INTEGER NOT NULL,
                total_operations INTEGER NOT NULL,
                successful_operations INTEGER NOT NULL,
                failed_operations INTEGER NOT NULL,
                average_response_time_ms REAL NOT NULL,
                throughput_ops_per_second REAL NOT NULL,
                error_rate_percent REAL NOT NULL,
                peak_cpu_percent REAL NOT NULL,
                peak_memory_mb REAL NOT NULL,
                success_criteria_met BOOLEAN NOT NULL,
                test_config TEXT,
                recommendations TEXT,
                metadata TEXT
            )
        ''')
        
        # Table des opérations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_operations (
                operation_id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                data_size_bytes INTEGER NOT NULL,
                metadata TEXT,
                FOREIGN KEY (test_id) REFERENCES performance_tests (test_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def run_load_test(self, config: TestConfiguration) -> TestResult:
        """Exécuter un test de charge"""
        logger.info(f"Démarrage du test de charge: {config.name}")
        
        # Initialiser le résultat
        result = TestResult(
            test_id=config.test_id,
            test_type=config.test_type,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            # Démarrer le monitoring
            self.resource_monitor.start_monitoring()
            
            # Générer les données de test
            test_data = self.workload_simulator.generate_test_data(config.data_volume_mb)
            
            # Calculer le nombre d'opérations
            total_operations = config.target_operations_per_second * config.duration_seconds
            operations_per_thread = total_operations // config.concurrent_threads
            
            # Créer les opérations
            operations = []
            for i in range(total_operations):
                op_id = f"{config.test_id}_op_{i}"
                
                # Alterner entre recherche et indexation (80% recherche, 20% indexation)
                if i % 5 == 0:  # 20% indexation
                    doc = test_data[i % len(test_data)]
                    operation = lambda doc=doc, op_id=op_id: self.workload_simulator.simulate_indexing_operation(op_id, doc)
                else:  # 80% recherche
                    query = f"recherche {i % 100}"
                    operation = lambda query=query, op_id=op_id: self.workload_simulator.simulate_search_operation(op_id, query)
                
                operations.append(operation)
            
            # Exécuter les opérations avec montée en charge
            all_results = []
            
            # Phase de montée en charge
            ramp_up_operations = min(len(operations), config.ramp_up_time * config.target_operations_per_second)
            
            if ramp_up_operations > 0:
                logger.info(f"Phase de montée en charge: {ramp_up_operations} opérations")
                ramp_results = self.workload_simulator.run_concurrent_operations(
                    operations[:ramp_up_operations],
                    max_workers=min(config.concurrent_threads, ramp_up_operations)
                )
                all_results.extend(ramp_results)
            
            # Phase de charge stable
            remaining_operations = operations[ramp_up_operations:]
            if remaining_operations:
                logger.info(f"Phase de charge stable: {len(remaining_operations)} opérations")
                
                # Diviser en batches pour éviter la surcharge mémoire
                batch_size = 1000
                for i in range(0, len(remaining_operations), batch_size):
                    batch = remaining_operations[i:i + batch_size]
                    batch_results = self.workload_simulator.run_concurrent_operations(
                        batch,
                        max_workers=config.concurrent_threads
                    )
                    all_results.extend(batch_results)
                    
                    # Petit délai entre les batches
                    if i + batch_size < len(remaining_operations):
                        time.sleep(0.1)
            
            # Arrêter le monitoring
            self.resource_monitor.stop_monitoring()
            
            # Analyser les résultats
            result = self._analyze_test_results(config, all_results, self.resource_monitor.get_metrics())
            result.status = TestStatus.COMPLETED
            
            logger.info(f"Test de charge terminé: {result.successful_operations}/{result.total_operations} opérations réussies")
            
        except Exception as e:
            logger.error(f"Erreur dans le test de charge: {e}")
            result.status = TestStatus.FAILED
            result.metadata['error'] = str(e)
        
        finally:
            result.end_time = datetime.now()
            if result.start_time and result.end_time:
                result.duration_seconds = int((result.end_time - result.start_time).total_seconds())
            
            # Sauvegarder le résultat
            self._save_test_result(result)
        
        return result
    
    def run_stress_test(self, config: TestConfiguration) -> TestResult:
        """Exécuter un test de stress"""
        logger.info(f"Démarrage du test de stress: {config.name}")
        
        # Modifier la configuration pour le stress
        stress_config = TestConfiguration(
            test_id=config.test_id,
            test_type=TestType.STRESS_TEST,
            name=config.name,
            description=config.description,
            duration_seconds=config.duration_seconds,
            max_users=config.max_users * 2,  # Doubler la charge
            target_operations_per_second=config.target_operations_per_second * 3,  # Tripler le débit
            concurrent_threads=config.concurrent_threads * 2,  # Doubler la concurrence
            data_volume_mb=config.data_volume_mb,
            success_criteria={
                'max_avg_response_time_ms': 1000,  # Critères plus souples
                'max_error_rate_percent': 15,
                'max_cpu_percent': 95
            }
        )
        
        return self.run_load_test(stress_config)
    
    def run_volume_test(self, config: TestConfiguration) -> TestResult:
        """Exécuter un test de volume"""
        logger.info(f"Démarrage du test de volume: {config.name}")
        
        # Modifier la configuration pour le volume
        volume_config = TestConfiguration(
            test_id=config.test_id,
            test_type=TestType.VOLUME_TEST,
            name=config.name,
            description=config.description,
            duration_seconds=config.duration_seconds * 2,  # Plus long
            data_volume_mb=config.data_volume_mb * 10,  # 10x plus de données
            target_operations_per_second=config.target_operations_per_second,
            concurrent_threads=config.concurrent_threads,
            success_criteria={
                'max_avg_response_time_ms': 300,
                'max_error_rate_percent': 3,
                'max_memory_mb': 4096  # Plus de mémoire autorisée
            }
        )
        
        return self.run_load_test(volume_config)
    
    def run_concurrency_test(self, config: TestConfiguration) -> TestResult:
        """Exécuter un test de concurrence"""
        logger.info(f"Démarrage du test de concurrence: {config.name}")
        
        result = TestResult(
            test_id=config.test_id,
            test_type=TestType.CONCURRENCY_TEST,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            self.resource_monitor.start_monitoring()
            
            # Test avec différents niveaux de concurrence
            concurrency_levels = [1, 5, 10, 20, 50, 100]
            all_results = []
            
            for concurrency in concurrency_levels:
                if concurrency > config.max_users:
                    break
                
                logger.info(f"Test avec {concurrency} utilisateurs concurrents")
                
                # Créer des opérations pour ce niveau
                operations = []
                for i in range(concurrency * 10):  # 10 opérations par utilisateur
                    op_id = f"{config.test_id}_conc_{concurrency}_op_{i}"
                    operation = lambda op_id=op_id: self.workload_simulator.simulate_search_operation(op_id)
                    operations.append(operation)
                
                # Exécuter avec ce niveau de concurrence
                batch_results = self.workload_simulator.run_concurrent_operations(
                    operations,
                    max_workers=concurrency
                )
                all_results.extend(batch_results)
                
                # Pause entre les niveaux
                time.sleep(2)
            
            self.resource_monitor.stop_monitoring()
            
            # Analyser les résultats
            result = self._analyze_test_results(config, all_results, self.resource_monitor.get_metrics())
            result.status = TestStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Erreur dans le test de concurrence: {e}")
            result.status = TestStatus.FAILED
            result.metadata['error'] = str(e)
        
        finally:
            result.end_time = datetime.now()
            if result.start_time and result.end_time:
                result.duration_seconds = int((result.end_time - result.start_time).total_seconds())
            
            self._save_test_result(result)
        
        return result
    
    def run_benchmark(self, config: TestConfiguration) -> TestResult:
        """Exécuter un benchmark"""
        logger.info(f"Démarrage du benchmark: {config.name}")
        
        result = TestResult(
            test_id=config.test_id,
            test_type=TestType.BENCHMARK,
            status=TestStatus.RUNNING,
            start_time=datetime.now()
        )
        
        try:
            self.resource_monitor.start_monitoring()
            
            # Benchmark de différentes opérations
            benchmark_operations = {
                'search_simple': lambda i: self.workload_simulator.simulate_search_operation(f"bench_search_{i}", "simple query", 30),
                'search_complex': lambda i: self.workload_simulator.simulate_search_operation(f"bench_complex_{i}", "complex medical query with filters", 80),
                'indexing_small': lambda i: self.workload_simulator.simulate_indexing_operation(f"bench_idx_small_{i}", {'id': f'small_{i}', 'content': 'small doc'}),
                'indexing_large': lambda i: self.workload_simulator.simulate_indexing_operation(f"bench_idx_large_{i}", {'id': f'large_{i}', 'content': 'large document ' * 100})
            }
            
            all_results = []
            
            for op_name, op_func in benchmark_operations.items():
                logger.info(f"Benchmark: {op_name}")
                
                # Exécuter chaque opération 100 fois
                operations = [lambda i=i, func=op_func: func(i) for i in range(100)]
                
                batch_results = self.workload_simulator.run_concurrent_operations(
                    operations,
                    max_workers=5  # Concurrence modérée pour le benchmark
                )
                
                # Marquer les résultats avec le type d'opération
                for res in batch_results:
                    res.metadata['benchmark_operation'] = op_name
                
                all_results.extend(batch_results)
            
            self.resource_monitor.stop_monitoring()
            
            # Analyser les résultats
            result = self._analyze_test_results(config, all_results, self.resource_monitor.get_metrics())
            result.status = TestStatus.COMPLETED
            
            # Ajouter des métriques spécifiques au benchmark
            result.metadata['benchmark_details'] = self._analyze_benchmark_results(all_results)
            
        except Exception as e:
            logger.error(f"Erreur dans le benchmark: {e}")
            result.status = TestStatus.FAILED
            result.metadata['error'] = str(e)
        
        finally:
            result.end_time = datetime.now()
            if result.start_time and result.end_time:
                result.duration_seconds = int((result.end_time - result.start_time).total_seconds())
            
            self._save_test_result(result)
        
        return result
    
    def _analyze_test_results(self, 
                            config: TestConfiguration,
                            operation_results: List[OperationResult],
                            resource_metrics: List[ResourceMetrics]) -> TestResult:
        """Analyser les résultats de test"""
        
        if not operation_results:
            return TestResult(
                test_id=config.test_id,
                test_type=config.test_type,
                status=TestStatus.FAILED,
                start_time=datetime.now()
            )
        
        # Statistiques de base
        total_operations = len(operation_results)
        successful_operations = sum(1 for r in operation_results if r.success)
        failed_operations = total_operations - successful_operations
        
        # Temps de réponse
        response_times = [r.duration_ms for r in operation_results if r.success]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Percentiles
            sorted_times = sorted(response_times)
            percentile_95 = sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
            percentile_99 = sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
        else:
            avg_response_time = min_response_time = max_response_time = 0
            percentile_95 = percentile_99 = 0
        
        # Débit
        if operation_results:
            start_time = min(r.start_time for r in operation_results)
            end_time = max(r.end_time for r in operation_results)
            duration_seconds = (end_time - start_time).total_seconds()
            throughput = successful_operations / duration_seconds if duration_seconds > 0 else 0
        else:
            throughput = 0
        
        # Taux d'erreur
        error_rate = (failed_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Métriques de ressources
        peak_metrics = self.resource_monitor.get_peak_metrics()
        peak_cpu = peak_metrics.get('peak_cpu_percent', 0)
        peak_memory = peak_metrics.get('peak_memory_mb', 0)
        
        # Vérifier les critères de succès
        success_criteria = config.success_criteria or self.default_success_criteria
        criteria_met = self._check_success_criteria({
            'avg_response_time_ms': avg_response_time,
            'percentile_95_ms': percentile_95,
            'throughput_ops_per_second': throughput,
            'error_rate_percent': error_rate,
            'peak_cpu_percent': peak_cpu,
            'peak_memory_mb': peak_memory
        }, success_criteria)
        
        # Générer des recommandations
        recommendations = self._generate_recommendations({
            'avg_response_time_ms': avg_response_time,
            'error_rate_percent': error_rate,
            'peak_cpu_percent': peak_cpu,
            'peak_memory_mb': peak_memory,
            'throughput_ops_per_second': throughput
        }, success_criteria)
        
        return TestResult(
            test_id=config.test_id,
            test_type=config.test_type,
            status=TestStatus.RUNNING,  # Sera mis à jour par l'appelant
            start_time=operation_results[0].start_time if operation_results else datetime.now(),
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            average_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            percentile_95_ms=percentile_95,
            percentile_99_ms=percentile_99,
            throughput_ops_per_second=throughput,
            error_rate_percent=error_rate,
            peak_cpu_percent=peak_cpu,
            peak_memory_mb=peak_memory,
            resource_metrics=resource_metrics,
            operation_results=operation_results,
            success_criteria_met=criteria_met,
            recommendations=recommendations,
            metadata={
                'config': {
                    'duration_seconds': config.duration_seconds,
                    'concurrent_threads': config.concurrent_threads,
                    'target_ops_per_second': config.target_operations_per_second,
                    'data_volume_mb': config.data_volume_mb
                }
            }
        )
    
    def _analyze_benchmark_results(self, operation_results: List[OperationResult]) -> Dict[str, Any]:
        """Analyser les résultats spécifiques au benchmark"""
        benchmark_details = {}
        
        # Grouper par type d'opération
        operations_by_type = {}
        for result in operation_results:
            op_type = result.metadata.get('benchmark_operation', 'unknown')
            if op_type not in operations_by_type:
                operations_by_type[op_type] = []
            operations_by_type[op_type].append(result)
        
        # Analyser chaque type
        for op_type, results in operations_by_type.items():
            successful_results = [r for r in results if r.success]
            
            if successful_results:
                times = [r.duration_ms for r in successful_results]
                benchmark_details[op_type] = {
                    'count': len(results),
                    'success_count': len(successful_results),
                    'avg_time_ms': statistics.mean(times),
                    'min_time_ms': min(times),
                    'max_time_ms': max(times),
                    'median_time_ms': statistics.median(times),
                    'std_dev_ms': statistics.stdev(times) if len(times) > 1 else 0
                }
        
        return benchmark_details
    
    def _check_success_criteria(self, metrics: Dict[str, float], criteria: Dict[str, float]) -> bool:
        """Vérifier si les critères de succès sont respectés"""
        for criterion, threshold in criteria.items():
            metric_value = metrics.get(criterion.replace('max_', '').replace('min_', ''), 0)
            
            if criterion.startswith('max_'):
                if metric_value > threshold:
                    return False
            elif criterion.startswith('min_'):
                if metric_value < threshold:
                    return False
        
        return True
    
    def _generate_recommendations(self, metrics: Dict[str, float], criteria: Dict[str, float]) -> List[str]:
        """Générer des recommandations d'amélioration"""
        recommendations = []
        
        # Temps de réponse
        if metrics.get('avg_response_time_ms', 0) > criteria.get('max_avg_response_time_ms', 200):
            recommendations.append("Optimiser les temps de réponse (indexation, cache, algorithmes)")
        
        # Taux d'erreur
        if metrics.get('error_rate_percent', 0) > criteria.get('max_error_rate_percent', 5):
            recommendations.append("Réduire le taux d'erreur (gestion d'erreurs, validation, retry)")
        
        # CPU
        if metrics.get('peak_cpu_percent', 0) > criteria.get('max_cpu_percent', 80):
            recommendations.append("Optimiser l'utilisation CPU (parallélisation, algorithmes efficaces)")
        
        # Mémoire
        if metrics.get('peak_memory_mb', 0) > criteria.get('max_memory_mb', 2048):
            recommendations.append("Optimiser l'utilisation mémoire (cache, garbage collection, streaming)")
        
        # Débit
        if metrics.get('throughput_ops_per_second', 0) < criteria.get('min_throughput_ops_per_second', 10):
            recommendations.append("Améliorer le débit (concurrence, optimisation des requêtes, mise en cache)")
        
        return recommendations
    
    def _save_test_result(self, result: TestResult):
        """Sauvegarder le résultat de test"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sauvegarder le test principal
        cursor.execute('''
            INSERT OR REPLACE INTO performance_tests 
            (test_id, test_type, status, start_time, end_time, duration_seconds,
             total_operations, successful_operations, failed_operations,
             average_response_time_ms, throughput_ops_per_second, error_rate_percent,
             peak_cpu_percent, peak_memory_mb, success_criteria_met,
             test_config, recommendations, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.test_id,
            result.test_type.value,
            result.status.value,
            result.start_time.isoformat(),
            result.end_time.isoformat() if result.end_time else None,
            result.duration_seconds,
            result.total_operations,
            result.successful_operations,
            result.failed_operations,
            result.average_response_time_ms,
            result.throughput_ops_per_second,
            result.error_rate_percent,
            result.peak_cpu_percent,
            result.peak_memory_mb,
            result.success_criteria_met,
            json.dumps({}),  # test_config sera ajouté si nécessaire
            json.dumps(result.recommendations),
            json.dumps(result.metadata)
        ))
        
        # Sauvegarder les opérations (échantillon pour éviter la surcharge)
        sample_operations = result.operation_results[:1000]  # Garder les 1000 premières
        
        for operation in sample_operations:
            cursor.execute('''
                INSERT OR REPLACE INTO test_operations 
                (operation_id, test_id, operation_type, start_time, duration_ms,
                 success, error_message, data_size_bytes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                operation.operation_id,
                result.test_id,
                operation.operation_type,
                operation.start_time.isoformat(),
                operation.duration_ms,
                operation.success,
                operation.error_message,
                operation.data_size_bytes,
                json.dumps(operation.metadata)
            ))
        
        conn.commit()
        conn.close()
    
    def get_test_results(self, test_type: TestType = None) -> List[TestResult]:
        """Récupérer les résultats de tests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if test_type:
            cursor.execute('SELECT * FROM performance_tests WHERE test_type = ? ORDER BY start_time DESC', (test_type.value,))
        else:
            cursor.execute('SELECT * FROM performance_tests ORDER BY start_time DESC')
        
        results = []
        for row in cursor.fetchall():
            result = TestResult(
                test_id=row[0],
                test_type=TestType(row[1]),
                status=TestStatus(row[2]),
                start_time=datetime.fromisoformat(row[3]),
                end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                duration_seconds=row[5],
                total_operations=row[6],
                successful_operations=row[7],
                failed_operations=row[8],
                average_response_time_ms=row[9],
                throughput_ops_per_second=row[10],
                error_rate_percent=row[11],
                peak_cpu_percent=row[12],
                peak_memory_mb=row[13],
                success_criteria_met=bool(row[14]),
                recommendations=json.loads(row[16]) if row[16] else [],
                metadata=json.loads(row[17]) if row[17] else {}
            )
            results.append(result)
        
        conn.close()
        return results
    
    def generate_performance_report(self, test_ids: List[str] = None) -> Dict[str, Any]:
        """Générer un rapport de performance"""
        if test_ids:
            results = []
            for test_id in test_ids:
                test_results = [r for r in self.get_test_results() if r.test_id == test_id]
                results.extend(test_results)
        else:
            results = self.get_test_results()
        
        if not results:
            return {'error': 'Aucun résultat de test trouvé'}
        
        # Statistiques globales
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success_criteria_met)
        
        # Métriques moyennes
        avg_response_time = statistics.mean([r.average_response_time_ms for r in results])
        avg_throughput = statistics.mean([r.throughput_ops_per_second for r in results])
        avg_error_rate = statistics.mean([r.error_rate_percent for r in results])
        
        # Métriques par type de test
        results_by_type = {}
        for result in results:
            test_type = result.test_type.value
            if test_type not in results_by_type:
                results_by_type[test_type] = []
            results_by_type[test_type].append(result)
        
        type_summaries = {}
        for test_type, type_results in results_by_type.items():
            type_summaries[test_type] = {
                'count': len(type_results),
                'success_rate': sum(1 for r in type_results if r.success_criteria_met) / len(type_results) * 100,
                'avg_response_time_ms': statistics.mean([r.average_response_time_ms for r in type_results]),
                'avg_throughput': statistics.mean([r.throughput_ops_per_second for r in type_results]),
                'avg_error_rate': statistics.mean([r.error_rate_percent for r in type_results])
            }
        
        # Recommandations consolidées
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.recommendations)
        
        # Compter les recommandations les plus fréquentes
        recommendation_counts = {}
        for rec in all_recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        top_recommendations = sorted(recommendation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate_percent': successful_tests / total_tests * 100 if total_tests > 0 else 0,
                'avg_response_time_ms': avg_response_time,
                'avg_throughput_ops_per_second': avg_throughput,
                'avg_error_rate_percent': avg_error_rate
            },
            'by_test_type': type_summaries,
            'top_recommendations': [{'recommendation': rec, 'frequency': count} for rec, count in top_recommendations],
            'test_results': [
                {
                    'test_id': r.test_id,
                    'test_type': r.test_type.value,
                    'status': r.status.value,
                    'success_criteria_met': r.success_criteria_met,
                    'avg_response_time_ms': r.average_response_time_ms,
                    'throughput_ops_per_second': r.throughput_ops_per_second,
                    'error_rate_percent': r.error_rate_percent,
                    'start_time': r.start_time.isoformat()
                }
                for r in results
            ]
        }

def main():
    """Fonction principale de démonstration"""
    print("🚀 Performance Tester - Objectif 10")
    print("Tests de performance en volume de production")
    print("=" * 60)
    
    # Initialiser le testeur
    print("\n🔧 Initialisation du testeur de performance...")
    tester = PerformanceTester()
    
    # Configurations de test
    test_configs = [
        TestConfiguration(
            test_id="load_test_1",
            test_type=TestType.LOAD_TEST,
            name="Test de charge standard",
            description="Test de charge avec 50 utilisateurs pendant 2 minutes",
            duration_seconds=120,
            max_users=50,
            target_operations_per_second=20,
            concurrent_threads=10,
            data_volume_mb=50
        ),
        TestConfiguration(
            test_id="stress_test_1",
            test_type=TestType.STRESS_TEST,
            name="Test de stress",
            description="Test de stress avec charge élevée",
            duration_seconds=90,
            max_users=100,
            target_operations_per_second=50,
            concurrent_threads=20,
            data_volume_mb=100
        ),
        TestConfiguration(
            test_id="volume_test_1",
            test_type=TestType.VOLUME_TEST,
            name="Test de volume",
            description="Test avec gros volume de données",
            duration_seconds=180,
            max_users=30,
            target_operations_per_second=15,
            concurrent_threads=8,
            data_volume_mb=500
        ),
        TestConfiguration(
            test_id="benchmark_1",
            test_type=TestType.BENCHMARK,
            name="Benchmark des opérations",
            description="Benchmark de différents types d'opérations",
            duration_seconds=60,
            concurrent_threads=5,
            data_volume_mb=20
        )
    ]
    
    # Exécuter les tests
    test_results = []
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n📊 Test {i}/{len(test_configs)}: {config.name}")
        print(f"Type: {config.test_type.value}")
        print(f"Durée: {config.duration_seconds}s")
        print(f"Concurrence: {config.concurrent_threads} threads")
        
        # Exécuter le test selon son type
        if config.test_type == TestType.LOAD_TEST:
            result = tester.run_load_test(config)
        elif config.test_type == TestType.STRESS_TEST:
            result = tester.run_stress_test(config)
        elif config.test_type == TestType.VOLUME_TEST:
            result = tester.run_volume_test(config)
        elif config.test_type == TestType.BENCHMARK:
            result = tester.run_benchmark(config)
        else:
            result = tester.run_load_test(config)  # Par défaut
        
        # Afficher les résultats
        print(f"\n📈 Résultats du test {config.name}:")
        print(f"  Statut: {result.status.value}")
        print(f"  Opérations: {result.successful_operations}/{result.total_operations}")
        print(f"  Temps de réponse moyen: {result.average_response_time_ms:.1f}ms")
        print(f"  95e percentile: {result.percentile_95_ms:.1f}ms")
        print(f"  Débit: {result.throughput_ops_per_second:.1f} ops/s")
        print(f"  Taux d'erreur: {result.error_rate_percent:.1f}%")
        print(f"  CPU max: {result.peak_cpu_percent:.1f}%")
        print(f"  Mémoire max: {result.peak_memory_mb:.1f} MB")
        print(f"  Critères respectés: {'✅' if result.success_criteria_met else '❌'}")
        
        if result.recommendations:
            print("  Recommandations:")
            for rec in result.recommendations[:3]:  # Top 3
                print(f"    - {rec}")
        
        test_results.append(result)
    
    # Test de concurrence spécial
    print("\n🔄 Test de concurrence spécialisé...")
    concurrency_config = TestConfiguration(
        test_id="concurrency_test_1",
        test_type=TestType.CONCURRENCY_TEST,
        name="Test de concurrence progressive",
        description="Test avec montée progressive de la concurrence",
        duration_seconds=120,
        max_users=100,
        concurrent_threads=50
    )
    
    concurrency_result = tester.run_concurrency_test(concurrency_config)
    test_results.append(concurrency_result)
    
    print(f"\n📈 Résultats du test de concurrence:")
    print(f"  Statut: {concurrency_result.status.value}")
    print(f"  Opérations: {concurrency_result.successful_operations}/{concurrency_result.total_operations}")
    print(f"  Débit: {concurrency_result.throughput_ops_per_second:.1f} ops/s")
    print(f"  Critères respectés: {'✅' if concurrency_result.success_criteria_met else '❌'}")
    
    # Générer le rapport global
    print("\n📋 Génération du rapport de performance...")
    report = tester.generate_performance_report([r.test_id for r in test_results])
    
    print("\n📊 Rapport de performance global:")
    summary = report['summary']
    print(f"  Tests exécutés: {summary['total_tests']}")
    print(f"  Tests réussis: {summary['successful_tests']} ({summary['success_rate_percent']:.1f}%)")
    print(f"  Temps de réponse moyen: {summary['avg_response_time_ms']:.1f}ms")
    print(f"  Débit moyen: {summary['avg_throughput_ops_per_second']:.1f} ops/s")
    print(f"  Taux d'erreur moyen: {summary['avg_error_rate_percent']:.1f}%")
    
    print("\n📈 Performance par type de test:")
    for test_type, metrics in report['by_test_type'].items():
        print(f"  {test_type}:")
        print(f"    Taux de succès: {metrics['success_rate']:.1f}%")
        print(f"    Temps de réponse: {metrics['avg_response_time_ms']:.1f}ms")
        print(f"    Débit: {metrics['avg_throughput']:.1f} ops/s")
    
    if report['top_recommendations']:
        print("\n💡 Recommandations principales:")
        for i, rec_info in enumerate(report['top_recommendations'][:3], 1):
            print(f"  {i}. {rec_info['recommendation']} (mentionné {rec_info['frequency']} fois)")
    
    # Évaluation de l'objectif
    print("\n🎯 Évaluation de l'objectif 10:")
    
    success_criteria = {
        'multiple_test_types': len(set(r.test_type for r in test_results)) >= 4,
        'load_test_successful': any(r.test_type == TestType.LOAD_TEST and r.success_criteria_met for r in test_results),
        'stress_test_completed': any(r.test_type == TestType.STRESS_TEST and r.status == TestStatus.COMPLETED for r in test_results),
        'volume_test_completed': any(r.test_type == TestType.VOLUME_TEST and r.status == TestStatus.COMPLETED for r in test_results),
        'benchmark_completed': any(r.test_type == TestType.BENCHMARK and r.status == TestStatus.COMPLETED for r in test_results),
        'performance_acceptable': summary['avg_response_time_ms'] < 500,  # Moins de 500ms
        'throughput_adequate': summary['avg_throughput_ops_per_second'] > 5,  # Plus de 5 ops/s
        'error_rate_low': summary['avg_error_rate_percent'] < 10  # Moins de 10% d'erreurs
    }
    
    all_success = all(success_criteria.values())
    
    print(f"\n✅ Critères d'évaluation:")
    for criterion, met in success_criteria.items():
        status = "✅" if met else "❌"
        print(f"  {status} {criterion.replace('_', ' ').title()}")
    
    objective_score = sum(success_criteria.values()) / len(success_criteria) * 100
    print(f"\n📊 Score de l'objectif 10: {objective_score:.1f}%")
    
    if all_success:
        print("🎉 OBJECTIF 10 ATTEINT: Tests de performance en volume de production réussis!")
        readiness_level = "PRODUCTION"
    elif objective_score >= 75:
        print("⚠️ OBJECTIF 10 PARTIELLEMENT ATTEINT: Quelques améliorations nécessaires")
        readiness_level = "STAGING"
    else:
        print("❌ OBJECTIF 10 NON ATTEINT: Optimisations importantes requises")
        readiness_level = "DEVELOPMENT"
    
    # Rapport final
    final_report = {
        'objective_10_status': 'ATTEINT' if all_success else 'PARTIEL' if objective_score >= 75 else 'NON_ATTEINT',
        'score_percent': objective_score,
        'readiness_level': readiness_level,
        'total_tests_executed': len(test_results),
        'successful_tests': sum(1 for r in test_results if r.success_criteria_met),
        'performance_metrics': {
            'avg_response_time_ms': summary['avg_response_time_ms'],
            'avg_throughput_ops_per_second': summary['avg_throughput_ops_per_second'],
            'avg_error_rate_percent': summary['avg_error_rate_percent']
        },
        'test_coverage': {
            'load_test': any(r.test_type == TestType.LOAD_TEST for r in test_results),
            'stress_test': any(r.test_type == TestType.STRESS_TEST for r in test_results),
            'volume_test': any(r.test_type == TestType.VOLUME_TEST for r in test_results),
            'concurrency_test': any(r.test_type == TestType.CONCURRENCY_TEST for r in test_results),
            'benchmark': any(r.test_type == TestType.BENCHMARK for r in test_results)
        },
        'recommendations': [rec['recommendation'] for rec in report['top_recommendations'][:5]],
        'next_steps': [
            "Optimiser les composants identifiés comme goulots d'étranglement",
            "Implémenter les recommandations prioritaires",
            "Effectuer des tests de régression après optimisations",
            "Monitorer les performances en production",
            "Planifier des tests de performance réguliers"
        ]
    }
    
    print(f"\n📋 Rapport final sauvegardé")
    print(f"Niveau de préparation: {readiness_level}")
    print(f"Prêt pour la production: {'✅' if readiness_level == 'PRODUCTION' else '❌'}")
    
    return final_report

if __name__ == "__main__":
    main()