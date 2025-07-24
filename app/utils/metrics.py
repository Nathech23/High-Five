from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from contextlib import contextmanager
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

class MetricsCollector:
    def __init__(self):
        # Compteurs
        self.diagnostic_explanations_total = Counter(
            'diagnostic_explanations_total', 
            'Total number of diagnostic explanations generated'
        )
        self.therapeutic_explanations_total = Counter(
            'therapeutic_explanations_total',
            'Total number of therapeutic explanations generated'
        )
        self.llm_requests_total = Counter(
            'llm_requests_total',
            'Total number of LLM requests',
            ['endpoint', 'status']
        )
        
        # Histogrammes pour les temps de réponse
        self.response_time = Histogram(
            'llm_response_time_seconds',
            'Time spent generating LLM responses',
            ['operation']
        )
        
        # Gauges pour les métriques en temps réel
        self.active_requests = Gauge(
            'llm_active_requests',
            'Number of active LLM requests'
        )
        
        # Histogramme pour les scores de confiance
        self.confidence_scores = Histogram(
            'llm_confidence_scores',
            'Distribution of confidence scores',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
    
    def increment_counter(self, counter_name: str, labels: Dict[str, str] = None):
        """Incrémente un compteur"""
        try:
            counter = getattr(self, counter_name)
            if labels:
                counter.labels(**labels).inc()
            else:
                counter.inc()
        except AttributeError:
            logger.warning(f"Counter {counter_name} not found")
    
    def record_histogram(self, histogram_name: str, value: float, labels: Dict[str, str] = None):
        """Enregistre une valeur dans un histogramme"""
        try:
            histogram = getattr(self, histogram_name)
            if labels:
                histogram.labels(**labels).observe(value)
            else:
                histogram.observe(value)
        except AttributeError:
            logger.warning(f"Histogram {histogram_name} not found")
    
    @contextmanager
    def time_operation(self, operation: str):
        """Context manager pour mesurer le temps d'une opération"""
        start_time = time.time()
        self.active_requests.inc()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.response_time.labels(operation=operation).observe(duration)
            self.active_requests.dec()
    
    def start_metrics_server(self, port: int = 8001):
        """Démarre le serveur de métriques Prometheus"""
        try:
            start_http_server(port)
            logger.info(f"Metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

# Instance globale
metrics_collector = MetricsCollector()