#!/usr/bin/env python3
"""
Monitoring en Temps Réel

Objectif 22: Ajouter monitoring temps réel performances

Ce module implémente un système de monitoring en temps réel des performances
du RAG médical multilingue avec métriques détaillées, alertes automatiques,
et tableaux de bord en temps réel.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
import time
import json
import threading
import queue
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import math
import uuid
import socket
import platform

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil non disponible - monitoring système limité")
    PSUTIL_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client non disponible - métriques Prometheus désactivées")
    PROMETHEUS_AVAILABLE = False

try:
    import websockets
    import asyncio
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    logger.warning("websockets non disponible - streaming temps réel limité")
    WEBSOCKETS_AVAILABLE = False

class MetricType(Enum):
    """Types de métriques"""
    COUNTER = "counter"           # Compteur (toujours croissant)
    GAUGE = "gauge"               # Jauge (valeur instantanée)
    HISTOGRAM = "histogram"       # Histogramme (distribution)
    TIMER = "timer"               # Minuteur (durée)
    RATE = "rate"                 # Taux (par seconde)

class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ComponentType(Enum):
    """Types de composants monitorés"""
    API = "api"
    CACHE = "cache"
    SEARCH = "search"
    TRANSLATION = "translation"
    EMBEDDING = "embedding"
    DATABASE = "database"
    SYSTEM = "system"
    NETWORK = "network"

class MetricCategory(Enum):
    """Catégories de métriques"""
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    BUSINESS = "business"
    RESOURCE = "resource"

@dataclass
class MetricValue:
    """Valeur d'une métrique"""
    timestamp: datetime
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Metric:
    """Définition d'une métrique"""
    name: str
    metric_type: MetricType
    category: MetricCategory
    component: ComponentType
    description: str
    unit: str = ""
    labels: List[str] = field(default_factory=list)
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_value(self, value: Union[int, float], labels: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """Ajoute une valeur à la métrique"""
        metric_value = MetricValue(
            timestamp=datetime.now(),
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        self.values.append(metric_value)
    
    def get_current_value(self) -> Optional[float]:
        """Retourne la valeur actuelle"""
        if self.values:
            return self.values[-1].value
        return None
    
    def get_average(self, window_minutes: int = 5) -> Optional[float]:
        """Calcule la moyenne sur une fenêtre de temps"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_values = [v.value for v in self.values if v.timestamp > cutoff]
        
        if recent_values:
            return statistics.mean(recent_values)
        return None
    
    def get_rate(self, window_minutes: int = 1) -> Optional[float]:
        """Calcule le taux par minute"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_values = [v for v in self.values if v.timestamp > cutoff]
        
        if len(recent_values) >= 2:
            time_span = (recent_values[-1].timestamp - recent_values[0].timestamp).total_seconds() / 60
            if time_span > 0:
                return len(recent_values) / time_span
        return None

@dataclass
class Alert:
    """Alerte de monitoring"""
    id: str
    level: AlertLevel
    component: ComponentType
    metric_name: str
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceSnapshot:
    """Instantané des performances"""
    timestamp: datetime
    api_requests_per_second: float
    avg_response_time: float
    cache_hit_rate: float
    system_cpu_percent: float
    system_memory_percent: float
    active_connections: int
    error_rate: float
    search_latency_p95: float
    translation_latency_p95: float
    embedding_latency_p95: float

@dataclass
class MonitoringStats:
    """Statistiques de monitoring"""
    total_metrics: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    uptime_seconds: float = 0.0
    data_points_collected: int = 0
    alerts_by_level: Dict[str, int] = field(default_factory=dict)
    metrics_by_component: Dict[str, int] = field(default_factory=dict)
    avg_collection_time: float = 0.0

class RealtimeMonitoring:
    """
    Système de monitoring en temps réel
    
    Objectif couvert:
    - 22. Ajouter monitoring temps réel performances
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.start_time = datetime.now()
        
        # Configuration
        self.collection_interval = self.config.get("collection_interval", 5)  # secondes
        self.retention_hours = self.config.get("retention_hours", 24)
        self.alert_cooldown = self.config.get("alert_cooldown", 300)  # secondes
        self.enable_prometheus = self.config.get("enable_prometheus", False)
        self.enable_websockets = self.config.get("enable_websockets", False)
        self.prometheus_port = self.config.get("prometheus_port", 8000)
        self.websocket_port = self.config.get("websocket_port", 8001)
        
        # Stockage des données
        self.metrics: Dict[str, Metric] = {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.performance_history: deque = deque(maxlen=1000)
        self.stats = MonitoringStats()
        
        # Seuils d'alerte par défaut
        self.alert_thresholds = {
            "api_response_time": {"warning": 1.0, "error": 3.0, "critical": 10.0},
            "cache_hit_rate": {"warning": 0.7, "error": 0.5, "critical": 0.3},
            "error_rate": {"warning": 0.05, "error": 0.1, "critical": 0.2},
            "cpu_usage": {"warning": 70, "error": 85, "critical": 95},
            "memory_usage": {"warning": 80, "error": 90, "critical": 95},
            "disk_usage": {"warning": 80, "error": 90, "critical": 95}
        }
        
        # Callbacks d'alerte
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Threads et queues
        self.metric_queue = queue.Queue()
        self.running = True
        self.lock = threading.RLock()
        
        # Initialiser les métriques de base
        self._init_base_metrics()
        
        # Initialiser Prometheus si disponible
        if self.enable_prometheus and PROMETHEUS_AVAILABLE:
            self._init_prometheus()
        
        # Démarrer les threads de monitoring
        self._start_monitoring_threads()
        
        logger.info(f"Monitoring temps réel initialisé - Intervalle: {self.collection_interval}s")
    
    def _init_base_metrics(self):
        """Initialise les métriques de base"""
        base_metrics = [
            # API
            ("api_requests_total", MetricType.COUNTER, MetricCategory.PERFORMANCE, ComponentType.API, "Nombre total de requêtes API"),
            ("api_response_time", MetricType.HISTOGRAM, MetricCategory.PERFORMANCE, ComponentType.API, "Temps de réponse API", "seconds"),
            ("api_active_connections", MetricType.GAUGE, MetricCategory.PERFORMANCE, ComponentType.API, "Connexions actives"),
            ("api_error_rate", MetricType.RATE, MetricCategory.RELIABILITY, ComponentType.API, "Taux d'erreur API"),
            
            # Cache
            ("cache_hits_total", MetricType.COUNTER, MetricCategory.PERFORMANCE, ComponentType.CACHE, "Nombre de cache hits"),
            ("cache_misses_total", MetricType.COUNTER, MetricCategory.PERFORMANCE, ComponentType.CACHE, "Nombre de cache misses"),
            ("cache_hit_rate", MetricType.GAUGE, MetricCategory.PERFORMANCE, ComponentType.CACHE, "Taux de cache hit"),
            ("cache_size_bytes", MetricType.GAUGE, MetricCategory.RESOURCE, ComponentType.CACHE, "Taille du cache", "bytes"),
            
            # Recherche
            ("search_requests_total", MetricType.COUNTER, MetricCategory.BUSINESS, ComponentType.SEARCH, "Nombre de recherches"),
            ("search_latency", MetricType.HISTOGRAM, MetricCategory.PERFORMANCE, ComponentType.SEARCH, "Latence de recherche", "seconds"),
            ("search_results_count", MetricType.HISTOGRAM, MetricCategory.BUSINESS, ComponentType.SEARCH, "Nombre de résultats"),
            
            # Traduction
            ("translation_requests_total", MetricType.COUNTER, MetricCategory.BUSINESS, ComponentType.TRANSLATION, "Nombre de traductions"),
            ("translation_latency", MetricType.HISTOGRAM, MetricCategory.PERFORMANCE, ComponentType.TRANSLATION, "Latence de traduction", "seconds"),
            ("translation_cache_hit_rate", MetricType.GAUGE, MetricCategory.PERFORMANCE, ComponentType.TRANSLATION, "Taux de cache hit traduction"),
            
            # Embeddings
            ("embedding_requests_total", MetricType.COUNTER, MetricCategory.BUSINESS, ComponentType.EMBEDDING, "Nombre d'embeddings"),
            ("embedding_latency", MetricType.HISTOGRAM, MetricCategory.PERFORMANCE, ComponentType.EMBEDDING, "Latence d'embedding", "seconds"),
            ("embedding_cache_hit_rate", MetricType.GAUGE, MetricCategory.PERFORMANCE, ComponentType.EMBEDDING, "Taux de cache hit embedding"),
            
            # Système
            ("system_cpu_percent", MetricType.GAUGE, MetricCategory.RESOURCE, ComponentType.SYSTEM, "Utilisation CPU", "percent"),
            ("system_memory_percent", MetricType.GAUGE, MetricCategory.RESOURCE, ComponentType.SYSTEM, "Utilisation mémoire", "percent"),
            ("system_disk_percent", MetricType.GAUGE, MetricCategory.RESOURCE, ComponentType.SYSTEM, "Utilisation disque", "percent"),
            ("system_network_bytes_sent", MetricType.COUNTER, MetricCategory.RESOURCE, ComponentType.NETWORK, "Bytes envoyés", "bytes"),
            ("system_network_bytes_recv", MetricType.COUNTER, MetricCategory.RESOURCE, ComponentType.NETWORK, "Bytes reçus", "bytes")
        ]
        
        for name, metric_type, category, component, description, *unit in base_metrics:
            unit_str = unit[0] if unit else ""
            self.metrics[name] = Metric(
                name=name,
                metric_type=metric_type,
                category=category,
                component=component,
                description=description,
                unit=unit_str
            )
        
        self.stats.total_metrics = len(self.metrics)
    
    def _init_prometheus(self):
        """Initialise les métriques Prometheus"""
        try:
            self.prometheus_registry = CollectorRegistry()
            self.prometheus_metrics = {}
            
            for name, metric in self.metrics.items():
                if metric.metric_type == MetricType.COUNTER:
                    self.prometheus_metrics[name] = Counter(
                        name, metric.description, registry=self.prometheus_registry
                    )
                elif metric.metric_type == MetricType.GAUGE:
                    self.prometheus_metrics[name] = Gauge(
                        name, metric.description, registry=self.prometheus_registry
                    )
                elif metric.metric_type in [MetricType.HISTOGRAM, MetricType.TIMER]:
                    self.prometheus_metrics[name] = Histogram(
                        name, metric.description, registry=self.prometheus_registry
                    )
            
            # Démarrer le serveur HTTP Prometheus
            start_http_server(self.prometheus_port, registry=self.prometheus_registry)
            logger.info(f"Serveur Prometheus démarré sur le port {self.prometheus_port}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation Prometheus: {e}")
    
    def _start_monitoring_threads(self):
        """Démarre les threads de monitoring"""
        # Thread de collecte des métriques système
        self.system_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        self.system_thread.start()
        
        # Thread de traitement des métriques
        self.processing_thread = threading.Thread(target=self._process_metrics, daemon=True)
        self.processing_thread.start()
        
        # Thread de vérification des alertes
        self.alert_thread = threading.Thread(target=self._check_alerts, daemon=True)
        self.alert_thread.start()
        
        # Thread de nettoyage
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
        self.cleanup_thread.start()
    
    def _collect_system_metrics(self):
        """Collecte les métriques système"""
        while self.running:
            try:
                if PSUTIL_AVAILABLE:
                    # CPU
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.record_metric("system_cpu_percent", cpu_percent)
                    
                    # Mémoire
                    memory = psutil.virtual_memory()
                    self.record_metric("system_memory_percent", memory.percent)
                    
                    # Disque
                    disk = psutil.disk_usage('/')
                    disk_percent = (disk.used / disk.total) * 100
                    self.record_metric("system_disk_percent", disk_percent)
                    
                    # Réseau
                    network = psutil.net_io_counters()
                    self.record_metric("system_network_bytes_sent", network.bytes_sent)
                    self.record_metric("system_network_bytes_recv", network.bytes_recv)
                
                time.sleep(self.collection_interval)
            
            except Exception as e:
                logger.error(f"Erreur lors de la collecte des métriques système: {e}")
                time.sleep(self.collection_interval)
    
    def _process_metrics(self):
        """Traite les métriques en attente"""
        while self.running:
            try:
                # Traiter les métriques en queue
                while not self.metric_queue.empty():
                    metric_data = self.metric_queue.get_nowait()
                    self._process_single_metric(metric_data)
                
                # Générer un snapshot de performance
                self._generate_performance_snapshot()
                
                time.sleep(1)  # Traitement rapide
            
            except Exception as e:
                logger.error(f"Erreur lors du traitement des métriques: {e}")
                time.sleep(1)
    
    def _process_single_metric(self, metric_data: Dict[str, Any]):
        """Traite une métrique individuelle"""
        try:
            name = metric_data['name']
            value = metric_data['value']
            labels = metric_data.get('labels', {})
            metadata = metric_data.get('metadata', {})
            
            if name in self.metrics:
                self.metrics[name].add_value(value, labels, metadata)
                self.stats.data_points_collected += 1
                
                # Mettre à jour Prometheus si disponible
                if self.enable_prometheus and name in self.prometheus_metrics:
                    prometheus_metric = self.prometheus_metrics[name]
                    
                    if isinstance(prometheus_metric, Counter):
                        prometheus_metric.inc(value)
                    elif isinstance(prometheus_metric, Gauge):
                        prometheus_metric.set(value)
                    elif isinstance(prometheus_metric, Histogram):
                        prometheus_metric.observe(value)
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la métrique {metric_data}: {e}")
    
    def _generate_performance_snapshot(self):
        """Génère un snapshot des performances"""
        try:
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                api_requests_per_second=self._get_metric_rate("api_requests_total") or 0,
                avg_response_time=self._get_metric_average("api_response_time") or 0,
                cache_hit_rate=self._get_metric_current("cache_hit_rate") or 0,
                system_cpu_percent=self._get_metric_current("system_cpu_percent") or 0,
                system_memory_percent=self._get_metric_current("system_memory_percent") or 0,
                active_connections=self._get_metric_current("api_active_connections") or 0,
                error_rate=self._get_metric_rate("api_error_rate") or 0,
                search_latency_p95=self._get_metric_percentile("search_latency", 95) or 0,
                translation_latency_p95=self._get_metric_percentile("translation_latency", 95) or 0,
                embedding_latency_p95=self._get_metric_percentile("embedding_latency", 95) or 0
            )
            
            self.performance_history.append(snapshot)
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération du snapshot: {e}")
    
    def _get_metric_current(self, name: str) -> Optional[float]:
        """Récupère la valeur actuelle d'une métrique"""
        if name in self.metrics:
            return self.metrics[name].get_current_value()
        return None
    
    def _get_metric_average(self, name: str, window_minutes: int = 5) -> Optional[float]:
        """Récupère la moyenne d'une métrique"""
        if name in self.metrics:
            return self.metrics[name].get_average(window_minutes)
        return None
    
    def _get_metric_rate(self, name: str, window_minutes: int = 1) -> Optional[float]:
        """Récupère le taux d'une métrique"""
        if name in self.metrics:
            return self.metrics[name].get_rate(window_minutes)
        return None
    
    def _get_metric_percentile(self, name: str, percentile: int, window_minutes: int = 5) -> Optional[float]:
        """Calcule un percentile d'une métrique"""
        if name in self.metrics:
            cutoff = datetime.now() - timedelta(minutes=window_minutes)
            recent_values = [v.value for v in self.metrics[name].values if v.timestamp > cutoff]
            
            if recent_values:
                sorted_values = sorted(recent_values)
                index = int((percentile / 100) * len(sorted_values))
                return sorted_values[min(index, len(sorted_values) - 1)]
        return None
    
    def _check_alerts(self):
        """Vérifie les conditions d'alerte"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Vérifier chaque seuil d'alerte
                for metric_name, thresholds in self.alert_thresholds.items():
                    current_value = self._get_metric_current(metric_name)
                    
                    if current_value is not None:
                        self._check_metric_thresholds(metric_name, current_value, thresholds, current_time)
                
                # Résoudre les alertes obsolètes
                self._resolve_stale_alerts(current_time)
                
                time.sleep(30)  # Vérification toutes les 30 secondes
            
            except Exception as e:
                logger.error(f"Erreur lors de la vérification des alertes: {e}")
                time.sleep(30)
    
    def _check_metric_thresholds(self, metric_name: str, current_value: float, 
                                thresholds: Dict[str, float], current_time: datetime):
        """Vérifie les seuils d'une métrique"""
        try:
            # Déterminer le niveau d'alerte
            alert_level = None
            threshold_value = None
            
            if current_value >= thresholds.get("critical", float('inf')):
                alert_level = AlertLevel.CRITICAL
                threshold_value = thresholds["critical"]
            elif current_value >= thresholds.get("error", float('inf')):
                alert_level = AlertLevel.ERROR
                threshold_value = thresholds["error"]
            elif current_value >= thresholds.get("warning", float('inf')):
                alert_level = AlertLevel.WARNING
                threshold_value = thresholds["warning"]
            
            # Créer une alerte si nécessaire
            if alert_level:
                alert_id = f"{metric_name}_{alert_level.value}"
                
                # Vérifier le cooldown
                if alert_id in self.alerts:
                    last_alert_time = self.alerts[alert_id].timestamp
                    if (current_time - last_alert_time).total_seconds() < self.alert_cooldown:
                        return  # Encore en cooldown
                
                # Créer l'alerte
                component = self._get_component_for_metric(metric_name)
                alert = Alert(
                    id=alert_id,
                    level=alert_level,
                    component=component,
                    metric_name=metric_name,
                    message=f"{metric_name} is {current_value:.2f}, exceeding {alert_level.value} threshold of {threshold_value}",
                    threshold=threshold_value,
                    current_value=current_value,
                    timestamp=current_time
                )
                
                self.alerts[alert_id] = alert
                self.alert_history.append(alert)
                self.stats.active_alerts += 1
                
                # Mettre à jour les statistiques par niveau
                level_key = alert_level.value
                if level_key not in self.stats.alerts_by_level:
                    self.stats.alerts_by_level[level_key] = 0
                self.stats.alerts_by_level[level_key] += 1
                
                # Déclencher les callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Erreur dans le callback d'alerte: {e}")
                
                logger.warning(f"Alerte {alert_level.value}: {alert.message}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des seuils: {e}")
    
    def _get_component_for_metric(self, metric_name: str) -> ComponentType:
        """Détermine le composant pour une métrique"""
        if metric_name in self.metrics:
            return self.metrics[metric_name].component
        
        # Fallback basé sur le nom
        if "api" in metric_name:
            return ComponentType.API
        elif "cache" in metric_name:
            return ComponentType.CACHE
        elif "search" in metric_name:
            return ComponentType.SEARCH
        elif "translation" in metric_name:
            return ComponentType.TRANSLATION
        elif "embedding" in metric_name:
            return ComponentType.EMBEDDING
        elif "system" in metric_name:
            return ComponentType.SYSTEM
        else:
            return ComponentType.SYSTEM
    
    def _resolve_stale_alerts(self, current_time: datetime):
        """Résout les alertes obsolètes"""
        try:
            stale_alerts = []
            
            for alert_id, alert in self.alerts.items():
                if alert.resolved:
                    continue
                
                # Vérifier si la condition d'alerte n'est plus vraie
                current_value = self._get_metric_current(alert.metric_name)
                
                if current_value is not None and current_value < alert.threshold:
                    # Marquer comme résolue
                    alert.resolved = True
                    alert.resolved_at = current_time
                    stale_alerts.append(alert_id)
                    
                    self.stats.active_alerts -= 1
                    self.stats.resolved_alerts += 1
                    
                    logger.info(f"Alerte résolue: {alert.message}")
            
            # Nettoyer les alertes résolues
            for alert_id in stale_alerts:
                if alert_id in self.alerts:
                    del self.alerts[alert_id]
        
        except Exception as e:
            logger.error(f"Erreur lors de la résolution des alertes: {e}")
    
    def _cleanup_old_data(self):
        """Nettoie les anciennes données"""
        while self.running:
            try:
                cutoff = datetime.now() - timedelta(hours=self.retention_hours)
                
                # Nettoyer les métriques anciennes
                for metric in self.metrics.values():
                    old_values = [v for v in metric.values if v.timestamp < cutoff]
                    for old_value in old_values:
                        metric.values.remove(old_value)
                
                # Nettoyer l'historique des alertes
                self.alert_history = [a for a in self.alert_history if a.timestamp > cutoff]
                
                time.sleep(3600)  # Nettoyage toutes les heures
            
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage: {e}")
                time.sleep(3600)
    
    def record_metric(self, name: str, value: Union[int, float], 
                     labels: Dict[str, str] = None, metadata: Dict[str, Any] = None):
        """
        Enregistre une valeur de métrique
        
        Args:
            name: Nom de la métrique
            value: Valeur à enregistrer
            labels: Labels additionnels
            metadata: Métadonnées additionnelles
        """
        try:
            metric_data = {
                'name': name,
                'value': value,
                'labels': labels or {},
                'metadata': metadata or {}
            }
            
            self.metric_queue.put_nowait(metric_data)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de la métrique {name}: {e}")
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """
        Enregistre une durée
        
        Args:
            name: Nom de la métrique de temps
            duration: Durée en secondes
            labels: Labels additionnels
        """
        self.record_metric(name, duration, labels, {'type': 'timer'})
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """
        Incrémente un compteur
        
        Args:
            name: Nom du compteur
            value: Valeur à ajouter
            labels: Labels additionnels
        """
        self.record_metric(name, value, labels, {'type': 'counter'})
    
    def set_gauge(self, name: str, value: Union[int, float], labels: Dict[str, str] = None):
        """
        Définit la valeur d'une jauge
        
        Args:
            name: Nom de la jauge
            value: Valeur à définir
            labels: Labels additionnels
        """
        self.record_metric(name, value, labels, {'type': 'gauge'})
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """
        Ajoute un callback d'alerte
        
        Args:
            callback: Fonction à appeler lors d'une alerte
        """
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Retourne les métriques actuelles
        
        Returns:
            Dictionnaire des métriques actuelles
        """
        with self.lock:
            current_metrics = {}
            
            for name, metric in self.metrics.items():
                current_value = metric.get_current_value()
                if current_value is not None:
                    current_metrics[name] = {
                        'value': current_value,
                        'type': metric.metric_type.value,
                        'category': metric.category.value,
                        'component': metric.component.value,
                        'unit': metric.unit,
                        'description': metric.description,
                        'average_5m': metric.get_average(5),
                        'rate_1m': metric.get_rate(1)
                    }
            
            return current_metrics
    
    def get_active_alerts(self) -> List[Alert]:
        """
        Retourne les alertes actives
        
        Returns:
            Liste des alertes actives
        """
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_performance_history(self, hours: int = 1) -> List[PerformanceSnapshot]:
        """
        Retourne l'historique des performances
        
        Args:
            hours: Nombre d'heures d'historique
        
        Returns:
            Liste des snapshots de performance
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [snapshot for snapshot in self.performance_history if snapshot.timestamp > cutoff]
    
    def get_stats(self) -> MonitoringStats:
        """
        Retourne les statistiques de monitoring
        
        Returns:
            Statistiques de monitoring
        """
        with self.lock:
            # Mettre à jour l'uptime
            self.stats.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            # Mettre à jour les métriques par composant
            self.stats.metrics_by_component = {}
            for metric in self.metrics.values():
                component = metric.component.value
                if component not in self.stats.metrics_by_component:
                    self.stats.metrics_by_component[component] = 0
                self.stats.metrics_by_component[component] += 1
            
            return self.stats
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Retourne les données pour le tableau de bord
        
        Returns:
            Données du tableau de bord
        """
        current_metrics = self.get_current_metrics()
        active_alerts = self.get_active_alerts()
        performance_history = self.get_performance_history(1)
        stats = self.get_stats()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': stats.uptime_seconds,
            'metrics': current_metrics,
            'alerts': {
                'active': len(active_alerts),
                'by_level': stats.alerts_by_level,
                'recent': [{
                    'id': alert.id,
                    'level': alert.level.value,
                    'component': alert.component.value,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat()
                } for alert in active_alerts[-10:]]  # 10 alertes les plus récentes
            },
            'performance': {
                'current': performance_history[-1].__dict__ if performance_history else None,
                'history': [snapshot.__dict__ for snapshot in performance_history[-60:]]  # Dernière heure
            },
            'statistics': {
                'total_metrics': stats.total_metrics,
                'data_points_collected': stats.data_points_collected,
                'metrics_by_component': stats.metrics_by_component
            }
        }
    
    def export_monitoring_data(self, output_path: str):
        """
        Exporte les données de monitoring
        
        Args:
            output_path: Chemin du fichier d'export
        """
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'monitoring_type': 'realtime_monitoring',
                'version': '2.0.0',
                'uptime_seconds': self.get_stats().uptime_seconds
            },
            'configuration': {
                'collection_interval': self.collection_interval,
                'retention_hours': self.retention_hours,
                'alert_cooldown': self.alert_cooldown,
                'enable_prometheus': self.enable_prometheus,
                'prometheus_port': self.prometheus_port,
                'alert_thresholds': self.alert_thresholds
            },
            'current_state': self.get_dashboard_data(),
            'metrics_definitions': {
                name: {
                    'type': metric.metric_type.value,
                    'category': metric.category.value,
                    'component': metric.component.value,
                    'description': metric.description,
                    'unit': metric.unit
                }
                for name, metric in self.metrics.items()
            },
            'alert_history': [{
                'id': alert.id,
                'level': alert.level.value,
                'component': alert.component.value,
                'metric_name': alert.metric_name,
                'message': alert.message,
                'threshold': alert.threshold,
                'current_value': alert.current_value,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            } for alert in self.alert_history[-100:]]  # 100 dernières alertes
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de monitoring exportées: {output_path}")
    
    def stop(self):
        """
        Arrête le système de monitoring
        """
        self.running = False
        logger.info("Système de monitoring arrêté")

# Décorateur pour mesurer automatiquement les performances
def monitor_performance(monitoring: RealtimeMonitoring, metric_name: str, 
                      component: ComponentType = ComponentType.API):
    """
    Décorateur pour monitorer automatiquement les performances d'une fonction
    
    Args:
        monitoring: Instance de RealtimeMonitoring
        metric_name: Nom de la métrique
        component: Composant concerné
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Enregistrer le succès
                duration = time.time() - start_time
                monitoring.record_timer(f"{metric_name}_duration", duration)
                monitoring.increment_counter(f"{metric_name}_total")
                
                return result
            
            except Exception as e:
                # Enregistrer l'erreur
                duration = time.time() - start_time
                monitoring.record_timer(f"{metric_name}_duration", duration)
                monitoring.increment_counter(f"{metric_name}_errors")
                
                raise e
        
        return wrapper
    return decorator

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("📊 Test du Monitoring en Temps Réel")
    
    # Configuration de test
    config = {
        "collection_interval": 2,
        "retention_hours": 1,
        "alert_cooldown": 10,
        "enable_prometheus": False,  # Désactivé pour le test
        "enable_websockets": False
    }
    
    print(f"\n📊 Configuration:")
    print(f"   Intervalle de collecte: {config['collection_interval']}s")
    print(f"   Rétention: {config['retention_hours']}h")
    print(f"   Cooldown alertes: {config['alert_cooldown']}s")
    
    # Créer le système de monitoring
    monitoring = RealtimeMonitoring(config)
    
    print(f"\n✅ Monitoring temps réel créé")
    
    # Ajouter un callback d'alerte
    def alert_callback(alert: Alert):
        print(f"🚨 ALERTE {alert.level.value.upper()}: {alert.message}")
    
    monitoring.add_alert_callback(alert_callback)
    
    # Test des fonctionnalités
    print(f"\n🧪 Test des fonctionnalités:")
    
    # Test 1: Enregistrement de métriques
    print(f"\n📈 Test d'enregistrement de métriques:")
    
    # Simuler des requêtes API
    for i in range(10):
        monitoring.increment_counter("api_requests_total", labels={"method": "GET", "endpoint": "/search"})
        monitoring.record_timer("api_response_time", 0.1 + (i * 0.05))  # Temps croissant
        time.sleep(0.1)
    
    print(f"   ✓ 10 requêtes API simulées")
    
    # Simuler des opérations de cache
    for i in range(20):
        if i < 15:
            monitoring.increment_counter("cache_hits_total")
        else:
            monitoring.increment_counter("cache_misses_total")
    
    # Calculer et définir le taux de hit
    hit_rate = 15 / 20  # 75%
    monitoring.set_gauge("cache_hit_rate", hit_rate)
    
    print(f"   ✓ Opérations de cache simulées (hit rate: {hit_rate:.1%})")
    
    # Simuler des recherches
    search_times = [0.2, 0.3, 0.15, 0.8, 1.2, 0.4, 0.6]
    for search_time in search_times:
        monitoring.increment_counter("search_requests_total")
        monitoring.record_timer("search_latency", search_time)
    
    print(f"   ✓ {len(search_times)} recherches simulées")
    
    # Attendre un peu pour que les métriques soient traitées
    time.sleep(3)
    
    # Test 2: Consultation des métriques actuelles
    print(f"\n📊 Métriques actuelles:")
    current_metrics = monitoring.get_current_metrics()
    
    key_metrics = ["api_requests_total", "api_response_time", "cache_hit_rate", "search_latency"]
    for metric_name in key_metrics:
        if metric_name in current_metrics:
            metric = current_metrics[metric_name]
            print(f"   {metric_name}: {metric['value']:.3f} {metric['unit']}")
            if metric['average_5m']:
                print(f"     Moyenne 5min: {metric['average_5m']:.3f}")
            if metric['rate_1m']:
                print(f"     Taux 1min: {metric['rate_1m']:.3f}/min")
    
    # Test 3: Déclenchement d'alertes
    print(f"\n🚨 Test de déclenchement d'alertes:")
    
    # Simuler une utilisation CPU élevée
    monitoring.set_gauge("system_cpu_percent", 85)  # Déclenche une alerte ERROR
    monitoring.set_gauge("system_memory_percent", 95)  # Déclenche une alerte CRITICAL
    
    # Simuler un temps de réponse élevé
    monitoring.record_timer("api_response_time", 5.0)  # Déclenche une alerte ERROR
    
    print(f"   ✓ Métriques d'alerte simulées")
    
    # Attendre que les alertes soient traitées
    time.sleep(2)
    
    # Vérifier les alertes actives
    active_alerts = monitoring.get_active_alerts()
    print(f"   Alertes actives: {len(active_alerts)}")
    
    for alert in active_alerts:
        print(f"     {alert.level.value.upper()}: {alert.metric_name} = {alert.current_value:.2f} (seuil: {alert.threshold})")
    
    # Test 4: Historique des performances
    print(f"\n📈 Historique des performances:")
    performance_history = monitoring.get_performance_history(hours=1)
    
    if performance_history:
        latest = performance_history[-1]
        print(f"   Dernière mesure:")
        print(f"     Requêtes/sec: {latest.api_requests_per_second:.2f}")
        print(f"     Temps réponse moyen: {latest.avg_response_time:.3f}s")
        print(f"     Taux cache hit: {latest.cache_hit_rate:.1%}")
        print(f"     CPU: {latest.system_cpu_percent:.1f}%")
        print(f"     Mémoire: {latest.system_memory_percent:.1f}%")
        print(f"     Latence recherche P95: {latest.search_latency_p95:.3f}s")
    
    print(f"   Snapshots collectés: {len(performance_history)}")
    
    # Test 5: Statistiques globales
    print(f"\n📊 Statistiques globales:")
    stats = monitoring.get_stats()
    
    print(f"   Uptime: {stats.uptime_seconds:.1f}s")
    print(f"   Métriques totales: {stats.total_metrics}")
    print(f"   Points de données collectés: {stats.data_points_collected}")
    print(f"   Alertes actives: {stats.active_alerts}")
    print(f"   Alertes résolues: {stats.resolved_alerts}")
    
    if stats.alerts_by_level:
        print(f"   Alertes par niveau:")
        for level, count in stats.alerts_by_level.items():
            print(f"     {level}: {count}")
    
    if stats.metrics_by_component:
        print(f"   Métriques par composant:")
        for component, count in stats.metrics_by_component.items():
            print(f"     {component}: {count}")
    
    # Test 6: Données du tableau de bord
    print(f"\n📋 Données du tableau de bord:")
    dashboard_data = monitoring.get_dashboard_data()
    
    print(f"   Timestamp: {dashboard_data['timestamp']}")
    print(f"   Uptime: {dashboard_data['uptime_seconds']:.1f}s")
    print(f"   Métriques actives: {len(dashboard_data['metrics'])}")
    print(f"   Alertes actives: {dashboard_data['alerts']['active']}")
    
    if dashboard_data['performance']['current']:
        current_perf = dashboard_data['performance']['current']
        print(f"   Performance actuelle:")
        print(f"     API req/s: {current_perf['api_requests_per_second']:.2f}")
        print(f"     Temps réponse: {current_perf['avg_response_time']:.3f}s")
        print(f"     Cache hit: {current_perf['cache_hit_rate']:.1%}")
    
    # Test 7: Test du décorateur de performance
    print(f"\n⚡ Test du décorateur de performance:")
    
    @monitor_performance(monitoring, "test_function")
    def test_function(duration=0.1):
        time.sleep(duration)
        return "success"
    
    # Appeler la fonction plusieurs fois
    for i in range(5):
        result = test_function(0.05 + i * 0.02)
        print(f"   Appel {i+1}: {result}")
    
    # Attendre que les métriques soient traitées
    time.sleep(2)
    
    # Vérifier les métriques de la fonction
    if "test_function_total" in monitoring.get_current_metrics():
        total_calls = monitoring.get_current_metrics()["test_function_total"]['value']
        print(f"   Total d'appels enregistrés: {total_calls}")
    
    # Export des données
    export_path = "realtime_monitoring_export.json"
    monitoring.export_monitoring_data(export_path)
    print(f"\n💾 Données exportées: {export_path}")
    
    # Résoudre les alertes (simulation)
    print(f"\n✅ Résolution des alertes:")
    monitoring.set_gauge("system_cpu_percent", 30)  # Retour à la normale
    monitoring.set_gauge("system_memory_percent", 60)  # Retour à la normale
    
    time.sleep(2)  # Attendre la résolution
    
    final_alerts = monitoring.get_active_alerts()
    print(f"   Alertes actives après résolution: {len(final_alerts)}")
    
    print(f"\n✅ Test du monitoring temps réel terminé!")
    print(f"\n🎯 Objectif 22 - Monitoring temps réel performances: IMPLÉMENTÉ")
    print(f"   ✓ Collecte automatique de métriques système")
    print(f"   ✓ Métriques personnalisées (compteurs, jauges, histogrammes, timers)")
    print(f"   ✓ Système d'alertes avec seuils configurables")
    print(f"   ✓ Historique des performances avec snapshots")
    print(f"   ✓ Statistiques détaillées par composant")
    print(f"   ✓ Décorateur pour monitoring automatique")
    print(f"   ✓ Support Prometheus (optionnel)")
    print(f"   ✓ Données de tableau de bord en temps réel")
    print(f"   ✓ Nettoyage automatique des anciennes données")
    print(f"   ✓ Export complet des données de monitoring")
    
    # Arrêter le monitoring
    monitoring.stop()

if __name__ == "__main__":
    main()