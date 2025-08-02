#!/usr/bin/env python3
"""
Optimisation des Performances API

Objectif 24: Optimiser performances API

Ce module implémente un système d'optimisation automatique des performances
de l'API RAG médical multilingue avec mise en cache intelligente, compression,
limitation de débit, optimisation des requêtes et monitoring adaptatif.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
import time
import json
import threading
import asyncio
import gzip
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import math
import hashlib
import uuid
import functools

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis non disponible - cache distribué désactivé")
    REDIS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil non disponible - monitoring système limité")
    PSUTIL_AVAILABLE = False

try:
    from fastapi import FastAPI, Request, Response, HTTPException
    from fastapi.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    logger.warning("FastAPI non disponible - middleware désactivé")
    FASTAPI_AVAILABLE = False

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    logger.warning("aioredis non disponible - cache async désactivé")
    AIOREDIS_AVAILABLE = False

class OptimizationStrategy(Enum):
    """Stratégies d'optimisation"""
    AGGRESSIVE = "aggressive"     # Optimisation agressive
    BALANCED = "balanced"         # Équilibré performance/ressources
    CONSERVATIVE = "conservative" # Conservateur, privilégie la stabilité
    ADAPTIVE = "adaptive"         # Adaptatif selon la charge

class CompressionType(Enum):
    """Types de compression"""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "brotli"
    AUTO = "auto"

class CacheStrategy(Enum):
    """Stratégies de cache"""
    NO_CACHE = "no_cache"
    MEMORY_ONLY = "memory_only"
    REDIS_ONLY = "redis_only"
    HYBRID = "hybrid"
    INTELLIGENT = "intelligent"

class RateLimitStrategy(Enum):
    """Stratégies de limitation de débit"""
    FIXED = "fixed"               # Limite fixe
    SLIDING_WINDOW = "sliding_window" # Fenêtre glissante
    TOKEN_BUCKET = "token_bucket"  # Seau à jetons
    ADAPTIVE = "adaptive"         # Adaptatif selon la charge

class OptimizationMetric(Enum):
    """Métriques d'optimisation"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"

@dataclass
class PerformanceMetrics:
    """Métriques de performance"""
    timestamp: datetime
    response_time_ms: float
    throughput_rps: float
    cpu_percent: float
    memory_percent: float
    cache_hit_rate: float
    error_rate: float
    active_connections: int
    queue_size: int
    compression_ratio: float = 1.0

@dataclass
class OptimizationRule:
    """Règle d'optimisation"""
    id: str
    name: str
    condition: str  # Expression conditionnelle
    action: str     # Action à effectuer
    priority: int   # Priorité (1 = haute, 10 = basse)
    enabled: bool = True
    cooldown_seconds: int = 300
    last_triggered: Optional[datetime] = None

@dataclass
class RateLimitConfig:
    """Configuration de limitation de débit"""
    requests_per_second: int
    burst_size: int
    window_size_seconds: int
    strategy: RateLimitStrategy
    per_user: bool = True
    per_ip: bool = True

@dataclass
class CompressionConfig:
    """Configuration de compression"""
    enabled: bool
    compression_type: CompressionType
    min_size_bytes: int
    compression_level: int
    mime_types: List[str] = field(default_factory=lambda: ['application/json', 'text/plain'])

@dataclass
class CacheConfig:
    """Configuration de cache"""
    strategy: CacheStrategy
    ttl_seconds: int
    max_size_mb: int
    compression_enabled: bool
    redis_url: Optional[str] = None

class APIOptimizer:
    """
    Système d'optimisation des performances API
    
    Objectif couvert:
    - 24. Optimiser performances API
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Configuration générale
        self.optimization_strategy = OptimizationStrategy(
            self.config.get("optimization_strategy", "balanced")
        )
        self.monitoring_interval = self.config.get("monitoring_interval", 30)
        self.optimization_interval = self.config.get("optimization_interval", 300)
        self.enable_auto_optimization = self.config.get("enable_auto_optimization", True)
        
        # Configuration de cache
        self.cache_config = CacheConfig(
            strategy=CacheStrategy(self.config.get("cache_strategy", "hybrid")),
            ttl_seconds=self.config.get("cache_ttl", 3600),
            max_size_mb=self.config.get("cache_max_size_mb", 512),
            compression_enabled=self.config.get("cache_compression", True),
            redis_url=self.config.get("redis_url")
        )
        
        # Configuration de compression
        self.compression_config = CompressionConfig(
            enabled=self.config.get("compression_enabled", True),
            compression_type=CompressionType(self.config.get("compression_type", "auto")),
            min_size_bytes=self.config.get("compression_min_size", 1024),
            compression_level=self.config.get("compression_level", 6)
        )
        
        # Configuration de limitation de débit
        self.rate_limit_config = RateLimitConfig(
            requests_per_second=self.config.get("rate_limit_rps", 100),
            burst_size=self.config.get("rate_limit_burst", 200),
            window_size_seconds=self.config.get("rate_limit_window", 60),
            strategy=RateLimitStrategy(self.config.get("rate_limit_strategy", "sliding_window"))
        )
        
        # Stockage des données
        self.performance_history: deque = deque(maxlen=1000)
        self.optimization_rules: Dict[str, OptimizationRule] = {}
        self.rate_limit_buckets: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.request_queue: deque = deque()
        
        # Cache en mémoire
        self.memory_cache: Dict[str, Any] = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'size_bytes': 0
        }
        
        # Métriques en temps réel
        self.current_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            response_time_ms=0.0,
            throughput_rps=0.0,
            cpu_percent=0.0,
            memory_percent=0.0,
            cache_hit_rate=0.0,
            error_rate=0.0,
            active_connections=0,
            queue_size=0
        )
        
        # État d'optimisation
        self.optimization_state = {
            'last_optimization': None,
            'current_strategy': self.optimization_strategy,
            'active_optimizations': [],
            'performance_score': 100.0
        }
        
        # Threads et verrous
        self.running = True
        self.lock = threading.RLock()
        
        # Initialiser les composants
        self._init_redis_connection()
        self._init_optimization_rules()
        self._start_background_threads()
        
        logger.info(f"Optimiseur API initialisé - Stratégie: {self.optimization_strategy.value}")
    
    def _init_redis_connection(self):
        """Initialise la connexion Redis"""
        self.redis_client = None
        
        if (self.cache_config.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.HYBRID] and 
            REDIS_AVAILABLE and self.cache_config.redis_url):
            try:
                self.redis_client = redis.from_url(self.cache_config.redis_url)
                self.redis_client.ping()
                logger.info("Connexion Redis établie pour l'optimisation")
            except Exception as e:
                logger.warning(f"Impossible de se connecter à Redis: {e}")
    
    def _init_optimization_rules(self):
        """Initialise les règles d'optimisation par défaut"""
        default_rules = [
            {
                'id': 'high_response_time',
                'name': 'Temps de réponse élevé',
                'condition': 'response_time_ms > 2000',
                'action': 'increase_cache_ttl',
                'priority': 1
            },
            {
                'id': 'high_cpu_usage',
                'name': 'Utilisation CPU élevée',
                'condition': 'cpu_percent > 80',
                'action': 'enable_aggressive_caching',
                'priority': 2
            },
            {
                'id': 'low_cache_hit_rate',
                'name': 'Taux de cache hit faible',
                'condition': 'cache_hit_rate < 0.5',
                'action': 'optimize_cache_strategy',
                'priority': 3
            },
            {
                'id': 'high_error_rate',
                'name': 'Taux d\'erreur élevé',
                'condition': 'error_rate > 0.05',
                'action': 'reduce_rate_limits',
                'priority': 1
            },
            {
                'id': 'memory_pressure',
                'name': 'Pression mémoire',
                'condition': 'memory_percent > 85',
                'action': 'clear_old_cache',
                'priority': 2
            }
        ]
        
        for rule_config in default_rules:
            rule = OptimizationRule(
                id=rule_config['id'],
                name=rule_config['name'],
                condition=rule_config['condition'],
                action=rule_config['action'],
                priority=rule_config['priority']
            )
            self.optimization_rules[rule.id] = rule
    
    def _start_background_threads(self):
        """Démarre les threads en arrière-plan"""
        # Thread de monitoring
        self.monitoring_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        self.monitoring_thread.start()
        
        # Thread d'optimisation
        if self.enable_auto_optimization:
            self.optimization_thread = threading.Thread(target=self._auto_optimize, daemon=True)
            self.optimization_thread.start()
        
        # Thread de nettoyage du cache
        self.cache_cleanup_thread = threading.Thread(target=self._cleanup_cache, daemon=True)
        self.cache_cleanup_thread.start()
    
    def _monitor_performance(self):
        """Monitore les performances en continu"""
        while self.running:
            try:
                # Collecter les métriques système
                cpu_percent = 0.0
                memory_percent = 0.0
                
                if PSUTIL_AVAILABLE:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                
                # Calculer les métriques de performance
                with self.lock:
                    # Calculer le throughput
                    now = datetime.now()
                    recent_requests = [r for r in self.request_queue 
                                     if (now - r['timestamp']).total_seconds() < 60]
                    throughput_rps = len(recent_requests) / 60.0
                    
                    # Calculer le temps de réponse moyen
                    if recent_requests:
                        avg_response_time = statistics.mean([r['duration_ms'] for r in recent_requests])
                    else:
                        avg_response_time = 0.0
                    
                    # Calculer le taux de cache hit
                    total_cache_requests = self.cache_stats['hits'] + self.cache_stats['misses']
                    cache_hit_rate = (self.cache_stats['hits'] / total_cache_requests 
                                    if total_cache_requests > 0 else 0.0)
                    
                    # Calculer le taux d'erreur
                    error_requests = [r for r in recent_requests if not r.get('success', True)]
                    error_rate = len(error_requests) / len(recent_requests) if recent_requests else 0.0
                    
                    # Mettre à jour les métriques actuelles
                    self.current_metrics = PerformanceMetrics(
                        timestamp=now,
                        response_time_ms=avg_response_time,
                        throughput_rps=throughput_rps,
                        cpu_percent=cpu_percent,
                        memory_percent=memory_percent,
                        cache_hit_rate=cache_hit_rate,
                        error_rate=error_rate,
                        active_connections=len(recent_requests),
                        queue_size=len(self.request_queue)
                    )
                    
                    # Ajouter à l'historique
                    self.performance_history.append(self.current_metrics)
                
                time.sleep(self.monitoring_interval)
            
            except Exception as e:
                logger.error(f"Erreur lors du monitoring: {e}")
                time.sleep(self.monitoring_interval)
    
    def _auto_optimize(self):
        """Optimisation automatique basée sur les règles"""
        while self.running:
            try:
                time.sleep(self.optimization_interval)
                
                with self.lock:
                    # Évaluer les règles d'optimisation
                    triggered_rules = self._evaluate_optimization_rules()
                    
                    # Appliquer les optimisations
                    for rule in triggered_rules:
                        self._apply_optimization(rule)
                    
                    # Calculer le score de performance
                    self._update_performance_score()
                    
                    # Ajuster la stratégie si nécessaire
                    if self.optimization_strategy == OptimizationStrategy.ADAPTIVE:
                        self._adapt_optimization_strategy()
            
            except Exception as e:
                logger.error(f"Erreur lors de l'optimisation automatique: {e}")
    
    def _evaluate_optimization_rules(self) -> List[OptimizationRule]:
        """Évalue les règles d'optimisation"""
        triggered_rules = []
        
        for rule in self.optimization_rules.values():
            if not rule.enabled:
                continue
            
            # Vérifier le cooldown
            if (rule.last_triggered and 
                (datetime.now() - rule.last_triggered).total_seconds() < rule.cooldown_seconds):
                continue
            
            # Évaluer la condition
            try:
                metrics_dict = {
                    'response_time_ms': self.current_metrics.response_time_ms,
                    'throughput_rps': self.current_metrics.throughput_rps,
                    'cpu_percent': self.current_metrics.cpu_percent,
                    'memory_percent': self.current_metrics.memory_percent,
                    'cache_hit_rate': self.current_metrics.cache_hit_rate,
                    'error_rate': self.current_metrics.error_rate,
                    'active_connections': self.current_metrics.active_connections,
                    'queue_size': self.current_metrics.queue_size
                }
                
                if eval(rule.condition, {"__builtins__": {}}, metrics_dict):
                    triggered_rules.append(rule)
            
            except Exception as e:
                logger.warning(f"Erreur lors de l'évaluation de la règle {rule.id}: {e}")
        
        # Trier par priorité
        return sorted(triggered_rules, key=lambda r: r.priority)
    
    def _apply_optimization(self, rule: OptimizationRule):
        """Applique une optimisation"""
        try:
            action = rule.action
            
            if action == 'increase_cache_ttl':
                self.cache_config.ttl_seconds = min(self.cache_config.ttl_seconds * 2, 86400)
                logger.info(f"TTL du cache augmenté à {self.cache_config.ttl_seconds}s")
            
            elif action == 'enable_aggressive_caching':
                self.cache_config.strategy = CacheStrategy.HYBRID
                self.compression_config.enabled = True
                logger.info("Cache agressif activé")
            
            elif action == 'optimize_cache_strategy':
                if self.cache_config.strategy == CacheStrategy.MEMORY_ONLY:
                    self.cache_config.strategy = CacheStrategy.HYBRID
                logger.info("Stratégie de cache optimisée")
            
            elif action == 'reduce_rate_limits':
                self.rate_limit_config.requests_per_second = max(
                    self.rate_limit_config.requests_per_second * 0.8, 10
                )
                logger.info(f"Limite de débit réduite à {self.rate_limit_config.requests_per_second} req/s")
            
            elif action == 'clear_old_cache':
                self._clear_old_cache_entries()
                logger.info("Anciennes entrées de cache supprimées")
            
            # Marquer la règle comme déclenchée
            rule.last_triggered = datetime.now()
            
            # Ajouter à l'historique des optimisations
            self.optimization_state['active_optimizations'].append({
                'rule_id': rule.id,
                'action': action,
                'timestamp': datetime.now().isoformat()
            })
            
            # Garder seulement les 10 dernières optimisations
            self.optimization_state['active_optimizations'] = \
                self.optimization_state['active_optimizations'][-10:]
        
        except Exception as e:
            logger.error(f"Erreur lors de l'application de l'optimisation {rule.action}: {e}")
    
    def _update_performance_score(self):
        """Met à jour le score de performance"""
        try:
            # Calculer le score basé sur plusieurs métriques
            response_time_score = max(0, 100 - (self.current_metrics.response_time_ms / 50))
            throughput_score = min(100, self.current_metrics.throughput_rps * 2)
            cache_score = self.current_metrics.cache_hit_rate * 100
            error_score = max(0, 100 - (self.current_metrics.error_rate * 2000))
            
            # Score pondéré
            self.optimization_state['performance_score'] = (
                response_time_score * 0.3 +
                throughput_score * 0.25 +
                cache_score * 0.25 +
                error_score * 0.2
            )
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score de performance: {e}")
    
    def _adapt_optimization_strategy(self):
        """Adapte la stratégie d'optimisation selon les performances"""
        try:
            score = self.optimization_state['performance_score']
            
            if score < 50:
                # Performance très faible, stratégie agressive
                new_strategy = OptimizationStrategy.AGGRESSIVE
            elif score < 75:
                # Performance moyenne, stratégie équilibrée
                new_strategy = OptimizationStrategy.BALANCED
            else:
                # Bonne performance, stratégie conservatrice
                new_strategy = OptimizationStrategy.CONSERVATIVE
            
            if new_strategy != self.optimization_state['current_strategy']:
                self.optimization_state['current_strategy'] = new_strategy
                self._apply_strategy_changes(new_strategy)
                logger.info(f"Stratégie d'optimisation adaptée: {new_strategy.value}")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'adaptation de stratégie: {e}")
    
    def _apply_strategy_changes(self, strategy: OptimizationStrategy):
        """Applique les changements de stratégie"""
        if strategy == OptimizationStrategy.AGGRESSIVE:
            self.cache_config.ttl_seconds = 7200  # 2h
            self.compression_config.enabled = True
            self.compression_config.compression_level = 9
            self.rate_limit_config.requests_per_second *= 1.5
        
        elif strategy == OptimizationStrategy.CONSERVATIVE:
            self.cache_config.ttl_seconds = 1800  # 30min
            self.compression_config.compression_level = 3
            self.rate_limit_config.requests_per_second *= 0.8
        
        # Balanced reste aux valeurs par défaut
    
    def _cleanup_cache(self):
        """Nettoie le cache périodiquement"""
        while self.running:
            try:
                time.sleep(3600)  # Toutes les heures
                
                with self.lock:
                    self._clear_old_cache_entries()
                    
                    # Vérifier la taille du cache
                    max_size_bytes = self.cache_config.max_size_mb * 1024 * 1024
                    
                    if self.cache_stats['size_bytes'] > max_size_bytes:
                        self._evict_cache_entries(max_size_bytes * 0.8)
            
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage du cache: {e}")
    
    def _clear_old_cache_entries(self):
        """Supprime les anciennes entrées de cache"""
        try:
            now = datetime.now()
            expired_keys = []
            
            for key, entry in self.memory_cache.items():
                if isinstance(entry, dict) and 'timestamp' in entry:
                    age = (now - entry['timestamp']).total_seconds()
                    if age > self.cache_config.ttl_seconds:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            # Recalculer la taille du cache
            self._update_cache_size()
            
            if expired_keys:
                logger.debug(f"Supprimé {len(expired_keys)} entrées de cache expirées")
        
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des entrées expirées: {e}")
    
    def _evict_cache_entries(self, target_size_bytes: float):
        """Évince les entrées de cache pour atteindre la taille cible"""
        try:
            # Trier par timestamp (LRU)
            sorted_entries = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].get('timestamp', datetime.min) if isinstance(x[1], dict) else datetime.min
            )
            
            current_size = self.cache_stats['size_bytes']
            
            for key, entry in sorted_entries:
                if current_size <= target_size_bytes:
                    break
                
                entry_size = len(str(entry).encode())
                del self.memory_cache[key]
                current_size -= entry_size
            
            self._update_cache_size()
            logger.info(f"Éviction du cache: taille réduite à {self.cache_stats['size_bytes']} bytes")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'éviction du cache: {e}")
    
    def _update_cache_size(self):
        """Met à jour la taille du cache"""
        try:
            total_size = sum(len(str(entry).encode()) for entry in self.memory_cache.values())
            self.cache_stats['size_bytes'] = total_size
        except Exception as e:
            logger.error(f"Erreur lors du calcul de la taille du cache: {e}")
    
    def compress_response(self, data: Any, accept_encoding: str = "") -> Tuple[bytes, str]:
        """
        Compresse une réponse selon la configuration
        
        Args:
            data: Données à comprimer
            accept_encoding: En-têtes Accept-Encoding du client
        
        Returns:
            Tuple (données compressées, type de compression)
        """
        try:
            if not self.compression_config.enabled:
                return str(data).encode(), "none"
            
            # Convertir en JSON si nécessaire
            if isinstance(data, (dict, list)):
                json_data = json.dumps(data, ensure_ascii=False)
            else:
                json_data = str(data)
            
            data_bytes = json_data.encode('utf-8')
            
            # Vérifier la taille minimale
            if len(data_bytes) < self.compression_config.min_size_bytes:
                return data_bytes, "none"
            
            # Déterminer le type de compression
            compression_type = self.compression_config.compression_type
            
            if compression_type == CompressionType.AUTO:
                if "gzip" in accept_encoding:
                    compression_type = CompressionType.GZIP
                elif "deflate" in accept_encoding:
                    compression_type = CompressionType.DEFLATE
                else:
                    compression_type = CompressionType.GZIP
            
            # Comprimer
            if compression_type == CompressionType.GZIP:
                compressed_data = gzip.compress(data_bytes, compresslevel=self.compression_config.compression_level)
                return compressed_data, "gzip"
            
            elif compression_type == CompressionType.DEFLATE:
                compressed_data = zlib.compress(data_bytes, level=self.compression_config.compression_level)
                return compressed_data, "deflate"
            
            else:
                return data_bytes, "none"
        
        except Exception as e:
            logger.error(f"Erreur lors de la compression: {e}")
            return str(data).encode(), "none"
    
    def check_rate_limit(self, identifier: str, request_time: datetime = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Vérifie la limitation de débit
        
        Args:
            identifier: Identifiant unique (IP, user_id, etc.)
            request_time: Timestamp de la requête
        
        Returns:
            Tuple (autorisé, informations de limite)
        """
        try:
            if request_time is None:
                request_time = datetime.now()
            
            bucket = self.rate_limit_buckets[identifier]
            
            if self.rate_limit_config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._check_sliding_window_rate_limit(bucket, request_time)
            
            elif self.rate_limit_config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._check_token_bucket_rate_limit(bucket, request_time)
            
            elif self.rate_limit_config.strategy == RateLimitStrategy.ADAPTIVE:
                return self._check_adaptive_rate_limit(bucket, request_time)
            
            else:  # FIXED
                return self._check_fixed_rate_limit(bucket, request_time)
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de limite de débit: {e}")
            return True, {}  # Autoriser en cas d'erreur
    
    def _check_sliding_window_rate_limit(self, bucket: Dict[str, Any], 
                                        request_time: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Vérifie la limite avec fenêtre glissante"""
        window_start = request_time - timedelta(seconds=self.rate_limit_config.window_size_seconds)
        
        # Nettoyer les anciennes requêtes
        if 'requests' not in bucket:
            bucket['requests'] = []
        
        bucket['requests'] = [req_time for req_time in bucket['requests'] if req_time > window_start]
        
        # Vérifier la limite
        current_count = len(bucket['requests'])
        limit = self.rate_limit_config.requests_per_second * self.rate_limit_config.window_size_seconds
        
        if current_count < limit:
            bucket['requests'].append(request_time)
            return True, {
                'allowed': True,
                'current_count': current_count + 1,
                'limit': limit,
                'reset_time': (request_time + timedelta(seconds=self.rate_limit_config.window_size_seconds)).isoformat()
            }
        else:
            return False, {
                'allowed': False,
                'current_count': current_count,
                'limit': limit,
                'retry_after': self.rate_limit_config.window_size_seconds
            }
    
    def _check_token_bucket_rate_limit(self, bucket: Dict[str, Any], 
                                      request_time: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Vérifie la limite avec seau à jetons"""
        if 'tokens' not in bucket:
            bucket['tokens'] = self.rate_limit_config.burst_size
            bucket['last_refill'] = request_time
        
        # Remplir le seau
        time_passed = (request_time - bucket['last_refill']).total_seconds()
        tokens_to_add = time_passed * self.rate_limit_config.requests_per_second
        bucket['tokens'] = min(self.rate_limit_config.burst_size, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = request_time
        
        # Consommer un jeton
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True, {
                'allowed': True,
                'tokens_remaining': bucket['tokens'],
                'burst_size': self.rate_limit_config.burst_size
            }
        else:
            return False, {
                'allowed': False,
                'tokens_remaining': bucket['tokens'],
                'retry_after': 1.0 / self.rate_limit_config.requests_per_second
            }
    
    def _check_fixed_rate_limit(self, bucket: Dict[str, Any], 
                               request_time: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Vérifie la limite fixe"""
        if 'count' not in bucket:
            bucket['count'] = 0
            bucket['window_start'] = request_time
        
        # Réinitialiser si nouvelle fenêtre
        if (request_time - bucket['window_start']).total_seconds() >= self.rate_limit_config.window_size_seconds:
            bucket['count'] = 0
            bucket['window_start'] = request_time
        
        # Vérifier la limite
        limit = self.rate_limit_config.requests_per_second * self.rate_limit_config.window_size_seconds
        
        if bucket['count'] < limit:
            bucket['count'] += 1
            return True, {
                'allowed': True,
                'current_count': bucket['count'],
                'limit': limit
            }
        else:
            return False, {
                'allowed': False,
                'current_count': bucket['count'],
                'limit': limit,
                'retry_after': self.rate_limit_config.window_size_seconds
            }
    
    def _check_adaptive_rate_limit(self, bucket: Dict[str, Any], 
                                  request_time: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Vérifie la limite adaptative"""
        # Ajuster la limite selon la charge système
        base_limit = self.rate_limit_config.requests_per_second
        
        # Réduire la limite si la performance est dégradée
        if self.current_metrics.response_time_ms > 1000:
            adjusted_limit = base_limit * 0.7
        elif self.current_metrics.cpu_percent > 80:
            adjusted_limit = base_limit * 0.8
        else:
            adjusted_limit = base_limit
        
        # Utiliser la logique de fenêtre glissante avec limite ajustée
        temp_config = self.rate_limit_config
        self.rate_limit_config.requests_per_second = adjusted_limit
        result = self._check_sliding_window_rate_limit(bucket, request_time)
        self.rate_limit_config = temp_config
        
        return result
    
    def cache_get(self, key: str) -> Optional[Any]:
        """
        Récupère une valeur du cache
        
        Args:
            key: Clé de cache
        
        Returns:
            Valeur mise en cache ou None
        """
        try:
            # Générer une clé de cache sécurisée
            cache_key = hashlib.sha256(key.encode()).hexdigest()
            
            # Chercher en mémoire d'abord
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                if isinstance(entry, dict) and 'timestamp' in entry:
                    age = (datetime.now() - entry['timestamp']).total_seconds()
                    if age <= self.cache_config.ttl_seconds:
                        self.cache_stats['hits'] += 1
                        return entry['data']
                    else:
                        del self.memory_cache[cache_key]
            
            # Chercher dans Redis si disponible
            if (self.redis_client and 
                self.cache_config.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.HYBRID]):
                
                redis_data = self.redis_client.get(f"opt_cache:{cache_key}")
                if redis_data:
                    try:
                        if self.cache_config.compression_enabled:
                            decompressed = gzip.decompress(redis_data)
                            data = json.loads(decompressed.decode())
                        else:
                            data = json.loads(redis_data.decode())
                        
                        # Mettre en cache mémoire aussi
                        if self.cache_config.strategy == CacheStrategy.HYBRID:
                            self.memory_cache[cache_key] = {
                                'data': data,
                                'timestamp': datetime.now()
                            }
                        
                        self.cache_stats['hits'] += 1
                        return data
                    except Exception as e:
                        logger.warning(f"Erreur lors de la désérialisation du cache Redis: {e}")
            
            # Cache miss
            self.cache_stats['misses'] += 1
            return None
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Stocke une valeur dans le cache
        
        Args:
            key: Clé de cache
            value: Valeur à stocker
            ttl: TTL personnalisé
        """
        try:
            cache_key = hashlib.sha256(key.encode()).hexdigest()
            ttl = ttl or self.cache_config.ttl_seconds
            
            # Stocker en mémoire
            if self.cache_config.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.HYBRID]:
                self.memory_cache[cache_key] = {
                    'data': value,
                    'timestamp': datetime.now()
                }
            
            # Stocker dans Redis
            if (self.redis_client and 
                self.cache_config.strategy in [CacheStrategy.REDIS_ONLY, CacheStrategy.HYBRID]):
                
                try:
                    json_data = json.dumps(value, ensure_ascii=False)
                    
                    if self.cache_config.compression_enabled:
                        compressed_data = gzip.compress(json_data.encode())
                        self.redis_client.setex(f"opt_cache:{cache_key}", ttl, compressed_data)
                    else:
                        self.redis_client.setex(f"opt_cache:{cache_key}", ttl, json_data)
                
                except Exception as e:
                    logger.warning(f"Erreur lors du stockage dans Redis: {e}")
            
            # Mettre à jour la taille du cache
            self._update_cache_size()
        
        except Exception as e:
            logger.error(f"Erreur lors du stockage en cache: {e}")
    
    def record_request(self, duration_ms: float, success: bool = True, 
                      metadata: Dict[str, Any] = None):
        """
        Enregistre une requête pour le monitoring
        
        Args:
            duration_ms: Durée de la requête en millisecondes
            success: Succès de la requête
            metadata: Métadonnées additionnelles
        """
        try:
            request_data = {
                'timestamp': datetime.now(),
                'duration_ms': duration_ms,
                'success': success,
                'metadata': metadata or {}
            }
            
            with self.lock:
                self.request_queue.append(request_data)
                
                # Garder seulement les 10000 dernières requêtes
                if len(self.request_queue) > 10000:
                    self.request_queue.popleft()
        
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de requête: {e}")
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """
        Retourne le statut d'optimisation
        
        Returns:
            Statut d'optimisation
        """
        with self.lock:
            return {
                'current_strategy': self.optimization_state['current_strategy'].value,
                'performance_score': self.optimization_state['performance_score'],
                'active_optimizations': self.optimization_state['active_optimizations'],
                'current_metrics': {
                    'response_time_ms': self.current_metrics.response_time_ms,
                    'throughput_rps': self.current_metrics.throughput_rps,
                    'cpu_percent': self.current_metrics.cpu_percent,
                    'memory_percent': self.current_metrics.memory_percent,
                    'cache_hit_rate': self.current_metrics.cache_hit_rate,
                    'error_rate': self.current_metrics.error_rate,
                    'active_connections': self.current_metrics.active_connections
                },
                'cache_stats': self.cache_stats,
                'configuration': {
                    'cache_strategy': self.cache_config.strategy.value,
                    'cache_ttl': self.cache_config.ttl_seconds,
                    'compression_enabled': self.compression_config.enabled,
                    'rate_limit_rps': self.rate_limit_config.requests_per_second,
                    'auto_optimization': self.enable_auto_optimization
                }
            }
    
    def export_optimization_data(self, output_path: str):
        """
        Exporte les données d'optimisation
        
        Args:
            output_path: Chemin du fichier d'export
        """
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'optimization_type': 'api_optimization',
                'version': '2.0.0'
            },
            'configuration': {
                'optimization_strategy': self.optimization_strategy.value,
                'monitoring_interval': self.monitoring_interval,
                'optimization_interval': self.optimization_interval,
                'enable_auto_optimization': self.enable_auto_optimization,
                'cache_config': {
                    'strategy': self.cache_config.strategy.value,
                    'ttl_seconds': self.cache_config.ttl_seconds,
                    'max_size_mb': self.cache_config.max_size_mb,
                    'compression_enabled': self.cache_config.compression_enabled
                },
                'compression_config': {
                    'enabled': self.compression_config.enabled,
                    'compression_type': self.compression_config.compression_type.value,
                    'min_size_bytes': self.compression_config.min_size_bytes,
                    'compression_level': self.compression_config.compression_level
                },
                'rate_limit_config': {
                    'requests_per_second': self.rate_limit_config.requests_per_second,
                    'burst_size': self.rate_limit_config.burst_size,
                    'window_size_seconds': self.rate_limit_config.window_size_seconds,
                    'strategy': self.rate_limit_config.strategy.value
                }
            },
            'current_status': self.get_optimization_status(),
            'optimization_rules': {
                rule_id: {
                    'name': rule.name,
                    'condition': rule.condition,
                    'action': rule.action,
                    'priority': rule.priority,
                    'enabled': rule.enabled,
                    'last_triggered': rule.last_triggered.isoformat() if rule.last_triggered else None
                }
                for rule_id, rule in self.optimization_rules.items()
            },
            'performance_history': [{
                'timestamp': metrics.timestamp.isoformat(),
                'response_time_ms': metrics.response_time_ms,
                'throughput_rps': metrics.throughput_rps,
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'cache_hit_rate': metrics.cache_hit_rate,
                'error_rate': metrics.error_rate,
                'active_connections': metrics.active_connections
            } for metrics in list(self.performance_history)[-100:]]  # 100 dernières métriques
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données d'optimisation exportées: {output_path}")
    
    def stop(self):
        """
        Arrête l'optimiseur API
        """
        self.running = False
        logger.info("Optimiseur API arrêté")

# Décorateur pour l'optimisation automatique
def optimize_endpoint(optimizer: APIOptimizer, cache_key_func: Callable = None, 
                     cache_ttl: int = None):
    """
    Décorateur pour optimiser automatiquement un endpoint
    
    Args:
        optimizer: Instance d'APIOptimizer
        cache_key_func: Fonction pour générer la clé de cache
        cache_ttl: TTL personnalisé pour le cache
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Générer la clé de cache
                if cache_key_func:
                    cache_key = cache_key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
                
                # Vérifier le cache
                cached_result = optimizer.cache_get(cache_key)
                if cached_result is not None:
                    duration_ms = (time.time() - start_time) * 1000
                    optimizer.record_request(duration_ms, True, {'cache_hit': True})
                    return cached_result
                
                # Exécuter la fonction
                result = func(*args, **kwargs)
                
                # Mettre en cache le résultat
                optimizer.cache_set(cache_key, result, cache_ttl)
                
                # Enregistrer la requête
                duration_ms = (time.time() - start_time) * 1000
                optimizer.record_request(duration_ms, True, {'cache_hit': False})
                
                return result
            
            except Exception as e:
                # Enregistrer l'erreur
                duration_ms = (time.time() - start_time) * 1000
                optimizer.record_request(duration_ms, False, {'error': str(e)})
                raise e
        
        return wrapper
    return decorator

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("⚡ Test de l'Optimisation des Performances API")
    
    # Configuration de test
    config = {
        "optimization_strategy": "adaptive",
        "monitoring_interval": 5,
        "optimization_interval": 30,
        "enable_auto_optimization": True,
        "cache_strategy": "hybrid",
        "cache_ttl": 1800,
        "cache_max_size_mb": 128,
        "cache_compression": True,
        "compression_enabled": True,
        "compression_type": "auto",
        "compression_min_size": 512,
        "rate_limit_rps": 50,
        "rate_limit_burst": 100,
        "rate_limit_strategy": "sliding_window"
    }
    
    print(f"\n📊 Configuration:")
    print(f"   Stratégie d'optimisation: {config['optimization_strategy']}")
    print(f"   Intervalle de monitoring: {config['monitoring_interval']}s")
    print(f"   Stratégie de cache: {config['cache_strategy']}")
    print(f"   Compression: {config['compression_enabled']}")
    print(f"   Limite de débit: {config['rate_limit_rps']} req/s")
    
    # Créer l'optimiseur
    optimizer = APIOptimizer(config)
    
    print(f"\n✅ Optimiseur API créé")
    
    # Test des fonctionnalités
    print(f"\n🧪 Test des fonctionnalités:")
    
    # Test 1: Cache
    print(f"\n💾 Test du cache:")
    
    # Stocker des données
    test_data = {
        "results": [f"result_{i}" for i in range(100)],
        "metadata": {"total": 100, "timestamp": datetime.now().isoformat()}
    }
    
    optimizer.cache_set("test_key_1", test_data)
    print(f"   ✓ Données stockées en cache")
    
    # Récupérer des données
    cached_data = optimizer.cache_get("test_key_1")
    cache_hit = cached_data is not None
    print(f"   Cache hit: {'✅ Oui' if cache_hit else '❌ Non'}")
    
    # Test avec clé inexistante
    missing_data = optimizer.cache_get("nonexistent_key")
    cache_miss = missing_data is None
    print(f"   Cache miss: {'✅ Oui' if cache_miss else '❌ Non'}")
    
    # Test 2: Compression
    print(f"\n🗜️ Test de compression:")
    
    large_data = {"data": "x" * 2000}  # Données > seuil de compression
    compressed, compression_type = optimizer.compress_response(large_data, "gzip")
    
    original_size = len(json.dumps(large_data).encode())
    compressed_size = len(compressed)
    compression_ratio = compressed_size / original_size
    
    print(f"   Taille originale: {original_size} bytes")
    print(f"   Taille compressée: {compressed_size} bytes")
    print(f"   Type de compression: {compression_type}")
    print(f"   Ratio de compression: {compression_ratio:.2f}")
    
    # Test 3: Limitation de débit
    print(f"\n🚦 Test de limitation de débit:")
    
    # Simuler des requêtes
    allowed_count = 0
    denied_count = 0
    
    for i in range(60):  # 60 requêtes
        allowed, info = optimizer.check_rate_limit("test_user_1")
        if allowed:
            allowed_count += 1
        else:
            denied_count += 1
        
        if i % 20 == 0:
            print(f"   Requête {i+1}: {'✅ Autorisée' if allowed else '❌ Refusée'}")
    
    print(f"   Total autorisées: {allowed_count}")
    print(f"   Total refusées: {denied_count}")
    
    # Test 4: Enregistrement de requêtes
    print(f"\n📊 Test d'enregistrement de requêtes:")
    
    # Simuler différents types de requêtes
    request_scenarios = [
        (100, True),   # Requête rapide réussie
        (500, True),   # Requête normale réussie
        (1500, True),  # Requête lente réussie
        (2500, False), # Requête très lente échouée
        (200, True),   # Requête rapide réussie
    ]
    
    for duration, success in request_scenarios:
        optimizer.record_request(duration, success, {"test": True})
    
    print(f"   ✓ {len(request_scenarios)} requêtes enregistrées")
    
    # Attendre que les métriques soient calculées
    time.sleep(3)
    
    # Test 5: Statut d'optimisation
    print(f"\n📈 Statut d'optimisation:")
    status = optimizer.get_optimization_status()
    
    print(f"   Stratégie actuelle: {status['current_strategy']}")
    print(f"   Score de performance: {status['performance_score']:.1f}/100")
    print(f"   Temps de réponse moyen: {status['current_metrics']['response_time_ms']:.1f}ms")
    print(f"   Throughput: {status['current_metrics']['throughput_rps']:.2f} req/s")
    print(f"   Taux de cache hit: {status['current_metrics']['cache_hit_rate']:.1%}")
    print(f"   Taux d'erreur: {status['current_metrics']['error_rate']:.1%}")
    
    if status['active_optimizations']:
        print(f"   Optimisations actives: {len(status['active_optimizations'])}")
        for opt in status['active_optimizations'][-3:]:  # 3 dernières
            print(f"     - {opt['rule_id']}: {opt['action']}")
    
    # Test 6: Décorateur d'optimisation
    print(f"\n🎯 Test du décorateur d'optimisation:")
    
    @optimize_endpoint(optimizer, lambda x: f"test_func_{x}")
    def test_function(param):
        time.sleep(0.1)  # Simuler du travail
        return {"result": f"processed_{param}", "timestamp": datetime.now().isoformat()}
    
    # Premier appel (cache miss)
    start_time = time.time()
    result1 = test_function("test_param")
    first_call_time = time.time() - start_time
    
    # Deuxième appel (cache hit)
    start_time = time.time()
    result2 = test_function("test_param")
    second_call_time = time.time() - start_time
    
    print(f"   Premier appel: {first_call_time:.3f}s (cache miss)")
    print(f"   Deuxième appel: {second_call_time:.3f}s (cache hit)")
    print(f"   Accélération: {first_call_time / second_call_time:.1f}x")
    
    # Test 7: Performance avec charge
    print(f"\n⚡ Test de performance sous charge:")
    
    start_time = time.time()
    
    # Simuler 1000 requêtes
    for i in range(1000):
        # Varier les temps de réponse
        duration = 50 + (i % 100) * 5  # 50-545ms
        success = i % 20 != 0  # 95% de succès
        
        optimizer.record_request(duration, success)
        
        # Tester le cache occasionnellement
        if i % 100 == 0:
            optimizer.cache_set(f"load_test_{i}", {"data": f"test_{i}"})
            optimizer.cache_get(f"load_test_{i}")
    
    load_test_time = time.time() - start_time
    print(f"   1000 requêtes traitées en {load_test_time:.3f}s")
    print(f"   Débit: {1000 / load_test_time:.1f} req/s")
    
    # Attendre que les métriques soient mises à jour
    time.sleep(3)
    
    # Statut final
    final_status = optimizer.get_optimization_status()
    print(f"   Score de performance final: {final_status['performance_score']:.1f}/100")
    print(f"   Cache hits: {final_status['cache_stats']['hits']}")
    print(f"   Cache misses: {final_status['cache_stats']['misses']}")
    
    if final_status['cache_stats']['hits'] + final_status['cache_stats']['misses'] > 0:
        hit_rate = final_status['cache_stats']['hits'] / (final_status['cache_stats']['hits'] + final_status['cache_stats']['misses'])
        print(f"   Taux de cache hit global: {hit_rate:.1%}")
    
    # Export des données
    export_path = "api_optimization_export.json"
    optimizer.export_optimization_data(export_path)
    print(f"\n💾 Données exportées: {export_path}")
    
    print(f"\n✅ Test de l'optimisation API terminé!")
    print(f"\n🎯 Objectif 24 - Optimiser performances API: IMPLÉMENTÉ")
    print(f"   ✓ Cache intelligent multi-niveaux (mémoire + Redis)")
    print(f"   ✓ Compression automatique des réponses (gzip, deflate)")
    print(f"   ✓ Limitation de débit adaptative (fenêtre glissante, seau à jetons)")
    print(f"   ✓ Monitoring en temps réel des performances")
    print(f"   ✓ Optimisation automatique basée sur des règles")
    print(f"   ✓ Stratégies d'optimisation adaptatives")
    print(f"   ✓ Décorateur pour optimisation automatique des endpoints")
    print(f"   ✓ Export des données d'optimisation")
    
    # Arrêter l'optimiseur
    optimizer.stop()

if __name__ == "__main__":
    main()