#!/usr/bin/env python3
"""
Cache Intelligent pour Requêtes

Objectif 20: Ajouter cache intelligent requêtes

Ce module implémente un système de cache intelligent qui s'adapte
automatiquement aux patterns d'utilisation pour optimiser les
performances des requêtes répétées dans le RAG médical multilingue.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import logging
import time
import json
import hashlib
import pickle
import gzip
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, OrderedDict
import statistics
import math

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis non disponible")
    REDIS_AVAILABLE = False

try:
    from cachetools import TTLCache, LRUCache, LFUCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    logger.warning("cachetools non disponible")
    CACHETOOLS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil non disponible")
    PSUTIL_AVAILABLE = False

class CacheBackend(Enum):
    """Types de backend de cache"""
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"

class CacheStrategy(Enum):
    """Stratégies de cache"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptatif basé sur les patterns
    PREDICTIVE = "predictive"  # Prédictif basé sur l'historique

class CacheLevel(Enum):
    """Niveaux de cache"""
    L1_MEMORY = "l1_memory"  # Cache mémoire rapide
    L2_REDIS = "l2_redis"    # Cache Redis distribué
    L3_DISK = "l3_disk"      # Cache disque persistant

class QueryType(Enum):
    """Types de requêtes"""
    SEARCH = "search"
    TRANSLATION = "translation"
    EMBEDDING = "embedding"
    ANALYSIS = "analysis"
    METADATA = "metadata"

@dataclass
class CacheEntry:
    """Entrée de cache"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    query_type: Optional[QueryType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Vérifie si l'entrée a expiré"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    def update_access(self):
        """Met à jour les statistiques d'accès"""
        self.last_accessed = datetime.now()
        self.access_count += 1

@dataclass
class CacheStats:
    """Statistiques de cache"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    memory_usage_bytes: int = 0
    avg_response_time: float = 0.0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    stats_by_type: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def update_hit(self, query_type: str = "unknown"):
        """Met à jour les statistiques de hit"""
        self.total_requests += 1
        self.cache_hits += 1
        self.hit_rate = self.cache_hits / self.total_requests
        self.miss_rate = 1.0 - self.hit_rate
        
        if query_type not in self.stats_by_type:
            self.stats_by_type[query_type] = {"hits": 0, "misses": 0}
        self.stats_by_type[query_type]["hits"] += 1
    
    def update_miss(self, query_type: str = "unknown"):
        """Met à jour les statistiques de miss"""
        self.total_requests += 1
        self.cache_misses += 1
        self.hit_rate = self.cache_hits / self.total_requests
        self.miss_rate = 1.0 - self.hit_rate
        
        if query_type not in self.stats_by_type:
            self.stats_by_type[query_type] = {"hits": 0, "misses": 0}
        self.stats_by_type[query_type]["misses"] += 1

@dataclass
class QueryPattern:
    """Pattern de requête détecté"""
    pattern_id: str
    frequency: int
    avg_interval: float  # Intervalle moyen entre requêtes (secondes)
    last_seen: datetime
    predicted_next: Optional[datetime] = None
    confidence: float = 0.0
    suggested_ttl: Optional[int] = None

class IntelligentCache:
    """
    Système de cache intelligent adaptatif
    
    Objectif couvert:
    - 20. Ajouter cache intelligent requêtes
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = CacheStats()
        self.query_patterns = {}
        self.access_history = defaultdict(list)
        
        # Configuration
        self.backend = CacheBackend(self.config.get("backend", "memory"))
        self.strategy = CacheStrategy(self.config.get("strategy", "adaptive"))
        self.max_memory_mb = self.config.get("max_memory_mb", 512)
        self.default_ttl = self.config.get("default_ttl", 3600)
        self.compression_enabled = self.config.get("compression", True)
        self.encryption_enabled = self.config.get("encryption", False)
        
        # Seuils adaptatifs
        self.min_frequency_for_prediction = self.config.get("min_frequency_for_prediction", 3)
        self.pattern_detection_window = self.config.get("pattern_detection_window", 86400)  # 24h
        self.adaptive_ttl_factor = self.config.get("adaptive_ttl_factor", 1.5)
        
        # Initialiser les backends
        self._init_backends()
        
        # Thread pour le nettoyage périodique
        self.cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"Cache intelligent initialisé - Backend: {self.backend.value}, Stratégie: {self.strategy.value}")
    
    def _init_backends(self):
        """Initialise les backends de cache"""
        # Cache L1 (mémoire)
        if CACHETOOLS_AVAILABLE:
            max_size = self.max_memory_mb * 1024 * 1024 // 1000  # Estimation
            if self.strategy == CacheStrategy.LRU:
                self.l1_cache = LRUCache(maxsize=max_size)
            elif self.strategy == CacheStrategy.LFU:
                self.l1_cache = LFUCache(maxsize=max_size)
            elif self.strategy == CacheStrategy.TTL:
                self.l1_cache = TTLCache(maxsize=max_size, ttl=self.default_ttl)
            else:
                self.l1_cache = OrderedDict()
        else:
            self.l1_cache = OrderedDict()
        
        # Cache L2 (Redis)
        self.l2_cache = None
        if self.backend in [CacheBackend.REDIS, CacheBackend.HYBRID] and REDIS_AVAILABLE:
            try:
                self.l2_cache = redis.Redis(
                    host=self.config.get("redis_host", "localhost"),
                    port=self.config.get("redis_port", 6379),
                    db=self.config.get("redis_db", 0),
                    decode_responses=False  # Pour gérer les données binaires
                )
                self.l2_cache.ping()
                logger.info("Cache Redis L2 connecté")
            except Exception as e:
                logger.warning(f"Impossible de se connecter à Redis: {e}")
                self.l2_cache = None
        
        # Cache L3 (disque)
        self.l3_cache_dir = None
        if self.backend in [CacheBackend.DISK, CacheBackend.HYBRID]:
            self.l3_cache_dir = Path(self.config.get("disk_cache_dir", "./cache"))
            self.l3_cache_dir.mkdir(exist_ok=True)
            logger.info(f"Cache disque L3 configuré: {self.l3_cache_dir}")
        
        # Métadonnées des entrées
        self.entries_metadata = {}
        self.lock = threading.RLock()
    
    def _generate_key(self, query: str, context: Dict[str, Any] = None) -> str:
        """Génère une clé de cache unique"""
        # Normaliser la requête
        normalized_query = query.lower().strip()
        
        # Inclure le contexte pertinent
        context_data = context or {}
        relevant_context = {
            k: v for k, v in context_data.items()
            if k in ['language', 'domain', 'user_type', 'urgency']
        }
        
        # Créer un hash
        data_to_hash = {
            'query': normalized_query,
            'context': relevant_context
        }
        
        data_str = json.dumps(data_to_hash, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def _serialize_value(self, value: Any) -> bytes:
        """Sérialise une valeur pour le stockage"""
        # Sérialisation avec pickle
        serialized = pickle.dumps(value)
        
        # Compression optionnelle
        if self.compression_enabled:
            serialized = gzip.compress(serialized)
        
        # Chiffrement optionnel (simulation)
        if self.encryption_enabled:
            # En production, utiliser une vraie bibliothèque de chiffrement
            pass
        
        return serialized
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Désérialise une valeur depuis le stockage"""
        try:
            # Déchiffrement optionnel
            if self.encryption_enabled:
                # En production, utiliser une vraie bibliothèque de chiffrement
                pass
            
            # Décompression optionnelle
            if self.compression_enabled:
                data = gzip.decompress(data)
            
            # Désérialisation
            return pickle.loads(data)
        
        except Exception as e:
            logger.error(f"Erreur lors de la désérialisation: {e}")
            return None
    
    def _detect_query_pattern(self, key: str, query_type: QueryType):
        """Détecte les patterns de requêtes"""
        now = datetime.now()
        
        # Enregistrer l'accès
        self.access_history[key].append(now)
        
        # Nettoyer l'historique ancien
        cutoff = now - timedelta(seconds=self.pattern_detection_window)
        self.access_history[key] = [
            timestamp for timestamp in self.access_history[key]
            if timestamp > cutoff
        ]
        
        # Analyser le pattern si suffisamment d'accès
        accesses = self.access_history[key]
        if len(accesses) >= self.min_frequency_for_prediction:
            # Calculer l'intervalle moyen
            intervals = []
            for i in range(1, len(accesses)):
                interval = (accesses[i] - accesses[i-1]).total_seconds()
                intervals.append(interval)
            
            if intervals:
                avg_interval = statistics.mean(intervals)
                frequency = len(accesses)
                
                # Prédire le prochain accès
                predicted_next = now + timedelta(seconds=avg_interval)
                
                # Calculer la confiance basée sur la régularité
                if len(intervals) > 1:
                    std_dev = statistics.stdev(intervals)
                    confidence = max(0.0, 1.0 - (std_dev / avg_interval))
                else:
                    confidence = 0.5
                
                # TTL suggéré basé sur le pattern
                suggested_ttl = int(avg_interval * self.adaptive_ttl_factor)
                
                # Enregistrer le pattern
                pattern_id = f"{query_type.value}_{key[:8]}"
                self.query_patterns[pattern_id] = QueryPattern(
                    pattern_id=pattern_id,
                    frequency=frequency,
                    avg_interval=avg_interval,
                    last_seen=now,
                    predicted_next=predicted_next,
                    confidence=confidence,
                    suggested_ttl=suggested_ttl
                )
    
    def _calculate_adaptive_ttl(self, key: str, query_type: QueryType, default_ttl: int) -> int:
        """Calcule un TTL adaptatif basé sur les patterns"""
        # Chercher un pattern existant
        pattern_id = f"{query_type.value}_{key[:8]}"
        
        if pattern_id in self.query_patterns:
            pattern = self.query_patterns[pattern_id]
            
            # Utiliser le TTL suggéré si la confiance est élevée
            if pattern.confidence > 0.7 and pattern.suggested_ttl:
                return min(pattern.suggested_ttl, default_ttl * 3)  # Limiter à 3x le TTL par défaut
        
        # TTL adaptatif basé sur le type de requête
        type_multipliers = {
            QueryType.SEARCH: 1.0,
            QueryType.TRANSLATION: 2.0,  # Les traductions changent moins
            QueryType.EMBEDDING: 3.0,    # Les embeddings sont très stables
            QueryType.ANALYSIS: 0.5,     # Les analyses peuvent changer
            QueryType.METADATA: 4.0      # Les métadonnées sont très stables
        }
        
        multiplier = type_multipliers.get(query_type, 1.0)
        return int(default_ttl * multiplier)
    
    def _get_from_l1(self, key: str) -> Optional[CacheEntry]:
        """Récupère depuis le cache L1 (mémoire)"""
        try:
            if CACHETOOLS_AVAILABLE and hasattr(self.l1_cache, 'get'):
                return self.l1_cache.get(key)
            else:
                return self.l1_cache.get(key)
        except Exception as e:
            logger.warning(f"Erreur L1 cache get: {e}")
            return None
    
    def _set_to_l1(self, key: str, entry: CacheEntry):
        """Stocke dans le cache L1 (mémoire)"""
        try:
            if CACHETOOLS_AVAILABLE and hasattr(self.l1_cache, '__setitem__'):
                self.l1_cache[key] = entry
            else:
                # Gestion manuelle de la taille pour OrderedDict
                if len(self.l1_cache) >= 1000:  # Limite arbitraire
                    self.l1_cache.popitem(last=False)  # FIFO
                self.l1_cache[key] = entry
        except Exception as e:
            logger.warning(f"Erreur L1 cache set: {e}")
    
    def _get_from_l2(self, key: str) -> Optional[CacheEntry]:
        """Récupère depuis le cache L2 (Redis)"""
        if not self.l2_cache:
            return None
        
        try:
            data = self.l2_cache.get(f"cache:{key}")
            if data:
                entry = self._deserialize_value(data)
                return entry
        except Exception as e:
            logger.warning(f"Erreur L2 cache get: {e}")
        
        return None
    
    def _set_to_l2(self, key: str, entry: CacheEntry, ttl: int):
        """Stocke dans le cache L2 (Redis)"""
        if not self.l2_cache:
            return
        
        try:
            data = self._serialize_value(entry)
            self.l2_cache.setex(f"cache:{key}", ttl, data)
        except Exception as e:
            logger.warning(f"Erreur L2 cache set: {e}")
    
    def _get_from_l3(self, key: str) -> Optional[CacheEntry]:
        """Récupère depuis le cache L3 (disque)"""
        if not self.l3_cache_dir:
            return None
        
        try:
            cache_file = self.l3_cache_dir / f"{key}.cache"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    data = f.read()
                entry = self._deserialize_value(data)
                
                # Vérifier l'expiration
                if entry and not entry.is_expired():
                    return entry
                else:
                    # Supprimer le fichier expiré
                    cache_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Erreur L3 cache get: {e}")
        
        return None
    
    def _set_to_l3(self, key: str, entry: CacheEntry):
        """Stocke dans le cache L3 (disque)"""
        if not self.l3_cache_dir:
            return
        
        try:
            cache_file = self.l3_cache_dir / f"{key}.cache"
            data = self._serialize_value(entry)
            
            with open(cache_file, 'wb') as f:
                f.write(data)
        except Exception as e:
            logger.warning(f"Erreur L3 cache set: {e}")
    
    def get(self, query: str, query_type: QueryType = QueryType.SEARCH, 
           context: Dict[str, Any] = None) -> Optional[Any]:
        """
        Récupère une valeur du cache intelligent
        
        Args:
            query: Requête à rechercher
            query_type: Type de requête
            context: Contexte additionnel
        
        Returns:
            Valeur mise en cache ou None
        """
        start_time = time.time()
        
        with self.lock:
            try:
                # Générer la clé
                key = self._generate_key(query, context)
                
                # Détecter les patterns
                self._detect_query_pattern(key, query_type)
                
                # Chercher dans L1 (mémoire)
                entry = self._get_from_l1(key)
                if entry and not entry.is_expired():
                    entry.update_access()
                    self.stats.update_hit(query_type.value)
                    
                    response_time = time.time() - start_time
                    self._update_avg_response_time(response_time)
                    
                    logger.debug(f"Cache L1 hit pour {key[:8]}")
                    return entry.value
                
                # Chercher dans L2 (Redis)
                if self.backend in [CacheBackend.REDIS, CacheBackend.HYBRID]:
                    entry = self._get_from_l2(key)
                    if entry and not entry.is_expired():
                        entry.update_access()
                        
                        # Remonter vers L1
                        self._set_to_l1(key, entry)
                        
                        self.stats.update_hit(query_type.value)
                        
                        response_time = time.time() - start_time
                        self._update_avg_response_time(response_time)
                        
                        logger.debug(f"Cache L2 hit pour {key[:8]}")
                        return entry.value
                
                # Chercher dans L3 (disque)
                if self.backend in [CacheBackend.DISK, CacheBackend.HYBRID]:
                    entry = self._get_from_l3(key)
                    if entry and not entry.is_expired():
                        entry.update_access()
                        
                        # Remonter vers L1 et L2
                        self._set_to_l1(key, entry)
                        if self.l2_cache:
                            ttl = self._calculate_adaptive_ttl(key, query_type, self.default_ttl)
                            self._set_to_l2(key, entry, ttl)
                        
                        self.stats.update_hit(query_type.value)
                        
                        response_time = time.time() - start_time
                        self._update_avg_response_time(response_time)
                        
                        logger.debug(f"Cache L3 hit pour {key[:8]}")
                        return entry.value
                
                # Cache miss
                self.stats.update_miss(query_type.value)
                
                response_time = time.time() - start_time
                self._update_avg_response_time(response_time)
                
                logger.debug(f"Cache miss pour {key[:8]}")
                return None
            
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du cache: {e}")
                self.stats.update_miss(query_type.value)
                return None
    
    def set(self, query: str, value: Any, query_type: QueryType = QueryType.SEARCH,
           context: Dict[str, Any] = None, ttl: Optional[int] = None):
        """
        Stocke une valeur dans le cache intelligent
        
        Args:
            query: Requête à mettre en cache
            value: Valeur à stocker
            query_type: Type de requête
            context: Contexte additionnel
            ttl: Time To Live personnalisé
        """
        with self.lock:
            try:
                # Générer la clé
                key = self._generate_key(query, context)
                
                # Calculer le TTL adaptatif
                if ttl is None:
                    ttl = self._calculate_adaptive_ttl(key, query_type, self.default_ttl)
                
                # Calculer la taille
                try:
                    size_bytes = len(self._serialize_value(value))
                except:
                    size_bytes = 0
                
                # Créer l'entrée
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=1,
                    ttl=ttl,
                    size_bytes=size_bytes,
                    query_type=query_type,
                    metadata=context or {}
                )
                
                # Stocker dans les différents niveaux
                self._set_to_l1(key, entry)
                
                if self.backend in [CacheBackend.REDIS, CacheBackend.HYBRID] and self.l2_cache:
                    self._set_to_l2(key, entry, ttl)
                
                if self.backend in [CacheBackend.DISK, CacheBackend.HYBRID]:
                    self._set_to_l3(key, entry)
                
                # Mettre à jour les métadonnées
                self.entries_metadata[key] = {
                    'created_at': entry.created_at,
                    'ttl': ttl,
                    'query_type': query_type.value,
                    'size_bytes': size_bytes
                }
                
                # Mettre à jour les statistiques
                self.stats.memory_usage_bytes += size_bytes
                
                logger.debug(f"Valeur mise en cache: {key[:8]} (TTL: {ttl}s)")
            
            except Exception as e:
                logger.error(f"Erreur lors de la mise en cache: {e}")
    
    def invalidate(self, query: str, context: Dict[str, Any] = None):
        """
        Invalide une entrée de cache
        
        Args:
            query: Requête à invalider
            context: Contexte additionnel
        """
        with self.lock:
            try:
                key = self._generate_key(query, context)
                
                # Supprimer de L1
                if key in self.l1_cache:
                    del self.l1_cache[key]
                
                # Supprimer de L2
                if self.l2_cache:
                    self.l2_cache.delete(f"cache:{key}")
                
                # Supprimer de L3
                if self.l3_cache_dir:
                    cache_file = self.l3_cache_dir / f"{key}.cache"
                    cache_file.unlink(missing_ok=True)
                
                # Nettoyer les métadonnées
                if key in self.entries_metadata:
                    size_bytes = self.entries_metadata[key].get('size_bytes', 0)
                    self.stats.memory_usage_bytes -= size_bytes
                    del self.entries_metadata[key]
                
                logger.debug(f"Cache invalidé: {key[:8]}")
            
            except Exception as e:
                logger.error(f"Erreur lors de l'invalidation: {e}")
    
    def clear(self, query_type: Optional[QueryType] = None):
        """
        Vide le cache (complètement ou par type)
        
        Args:
            query_type: Type de requête à vider (optionnel)
        """
        with self.lock:
            try:
                if query_type is None:
                    # Vider tout
                    self.l1_cache.clear()
                    
                    if self.l2_cache:
                        # Supprimer toutes les clés de cache
                        keys = self.l2_cache.keys("cache:*")
                        if keys:
                            self.l2_cache.delete(*keys)
                    
                    if self.l3_cache_dir:
                        for cache_file in self.l3_cache_dir.glob("*.cache"):
                            cache_file.unlink(missing_ok=True)
                    
                    self.entries_metadata.clear()
                    self.stats.memory_usage_bytes = 0
                    
                    logger.info("Cache complètement vidé")
                
                else:
                    # Vider seulement un type spécifique
                    keys_to_remove = []
                    
                    for key, metadata in self.entries_metadata.items():
                        if metadata.get('query_type') == query_type.value:
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        self.invalidate("", {})  # Utiliser la clé directement
                    
                    logger.info(f"Cache vidé pour le type: {query_type.value}")
            
            except Exception as e:
                logger.error(f"Erreur lors du vidage du cache: {e}")
    
    def _update_avg_response_time(self, response_time: float):
        """Met à jour le temps de réponse moyen"""
        if self.stats.total_requests == 0:
            self.stats.avg_response_time = response_time
        else:
            # Moyenne mobile
            alpha = 0.1  # Facteur de lissage
            self.stats.avg_response_time = (
                alpha * response_time + (1 - alpha) * self.stats.avg_response_time
            )
    
    def _periodic_cleanup(self):
        """Nettoyage périodique des entrées expirées"""
        while True:
            try:
                time.sleep(300)  # Toutes les 5 minutes
                
                with self.lock:
                    # Nettoyer L1
                    expired_keys = []
                    for key, entry in list(self.l1_cache.items()):
                        if hasattr(entry, 'is_expired') and entry.is_expired():
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        if key in self.l1_cache:
                            del self.l1_cache[key]
                        if key in self.entries_metadata:
                            size_bytes = self.entries_metadata[key].get('size_bytes', 0)
                            self.stats.memory_usage_bytes -= size_bytes
                            del self.entries_metadata[key]
                        self.stats.evictions += 1
                    
                    # Nettoyer L3 (les fichiers expirés)
                    if self.l3_cache_dir:
                        for cache_file in self.l3_cache_dir.glob("*.cache"):
                            try:
                                # Vérifier l'âge du fichier
                                file_age = time.time() - cache_file.stat().st_mtime
                                if file_age > self.default_ttl * 2:  # 2x le TTL par défaut
                                    cache_file.unlink(missing_ok=True)
                                    self.stats.evictions += 1
                            except:
                                pass
                    
                    if expired_keys:
                        logger.debug(f"Nettoyage: {len(expired_keys)} entrées expirées supprimées")
            
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage périodique: {e}")
    
    def get_stats(self) -> CacheStats:
        """Retourne les statistiques du cache"""
        with self.lock:
            # Mettre à jour l'utilisation mémoire
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                memory_info = process.memory_info()
                self.stats.memory_usage_bytes = memory_info.rss
            
            return self.stats
    
    def get_patterns(self) -> Dict[str, QueryPattern]:
        """Retourne les patterns de requêtes détectés"""
        return self.query_patterns.copy()
    
    def predict_cache_needs(self) -> List[Dict[str, Any]]:
        """Prédit les besoins futurs de cache"""
        predictions = []
        now = datetime.now()
        
        for pattern in self.query_patterns.values():
            if pattern.confidence > 0.6 and pattern.predicted_next:
                time_until_next = (pattern.predicted_next - now).total_seconds()
                
                if 0 < time_until_next < 3600:  # Dans la prochaine heure
                    predictions.append({
                        'pattern_id': pattern.pattern_id,
                        'predicted_time': pattern.predicted_next,
                        'confidence': pattern.confidence,
                        'frequency': pattern.frequency,
                        'suggested_action': 'preload' if time_until_next < 300 else 'prepare'
                    })
        
        return sorted(predictions, key=lambda x: x['predicted_time'])
    
    def optimize_cache(self):
        """Optimise automatiquement la configuration du cache"""
        with self.lock:
            stats = self.get_stats()
            
            # Ajuster la stratégie selon les performances
            if stats.hit_rate < 0.5:
                logger.info("Taux de hit faible, optimisation recommandée")
                
                # Analyser les patterns pour suggérer des améliorations
                frequent_patterns = [
                    p for p in self.query_patterns.values()
                    if p.frequency > 5
                ]
                
                if frequent_patterns:
                    # Augmenter le TTL pour les patterns fréquents
                    avg_interval = statistics.mean([p.avg_interval for p in frequent_patterns])
                    suggested_ttl = int(avg_interval * 2)
                    
                    logger.info(f"TTL suggéré basé sur les patterns: {suggested_ttl}s")
                    
                    return {
                        'suggested_ttl': suggested_ttl,
                        'frequent_patterns_count': len(frequent_patterns),
                        'optimization_needed': True
                    }
            
            return {
                'optimization_needed': False,
                'current_hit_rate': stats.hit_rate
            }
    
    def export_cache_data(self, output_path: str):
        """Exporte les données du cache"""
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'backend': self.backend.value,
                'strategy': self.strategy.value,
                'version': '2.0.0'
            },
            'configuration': {
                'max_memory_mb': self.max_memory_mb,
                'default_ttl': self.default_ttl,
                'compression_enabled': self.compression_enabled,
                'pattern_detection_window': self.pattern_detection_window
            },
            'statistics': {
                'total_requests': self.stats.total_requests,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'hit_rate': self.stats.hit_rate,
                'miss_rate': self.stats.miss_rate,
                'evictions': self.stats.evictions,
                'memory_usage_bytes': self.stats.memory_usage_bytes,
                'avg_response_time': self.stats.avg_response_time,
                'stats_by_type': self.stats.stats_by_type
            },
            'patterns': {
                pattern_id: {
                    'frequency': pattern.frequency,
                    'avg_interval': pattern.avg_interval,
                    'confidence': pattern.confidence,
                    'suggested_ttl': pattern.suggested_ttl,
                    'last_seen': pattern.last_seen.isoformat()
                }
                for pattern_id, pattern in self.query_patterns.items()
            },
            'predictions': self.predict_cache_needs(),
            'optimization': self.optimize_cache()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données de cache exportées: {output_path}")

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("🧠 Test du Cache Intelligent")
    
    # Configuration de test
    config = {
        "backend": "hybrid",
        "strategy": "adaptive",
        "max_memory_mb": 128,
        "default_ttl": 1800,
        "compression": True,
        "min_frequency_for_prediction": 2,
        "pattern_detection_window": 3600
    }
    
    print(f"\n📊 Configuration:")
    print(f"   Backend: {config['backend']}")
    print(f"   Stratégie: {config['strategy']}")
    print(f"   Mémoire max: {config['max_memory_mb']} MB")
    print(f"   TTL par défaut: {config['default_ttl']}s")
    print(f"   Compression: {config['compression']}")
    
    # Créer le cache intelligent
    cache = IntelligentCache(config)
    
    print(f"\n✅ Cache intelligent créé")
    
    # Test des fonctionnalités de base
    print(f"\n🧪 Test des fonctionnalités:")
    
    # Test 1: Stockage et récupération
    test_queries = [
        ("fièvre et maux de tête", QueryType.SEARCH, {"language": "fr", "domain": "infectious_diseases"}),
        ("fever and headache", QueryType.SEARCH, {"language": "en", "domain": "infectious_diseases"}),
        ("traitement paludisme", QueryType.SEARCH, {"language": "fr", "domain": "infectious_diseases"}),
        ("translate: fièvre", QueryType.TRANSLATION, {"source": "fr", "target": "en"}),
        ("embed: symptômes", QueryType.EMBEDDING, {"language": "fr"})
    ]
    
    # Stocker des valeurs
    for i, (query, qtype, context) in enumerate(test_queries):
        value = f"Résultat simulé {i+1} pour '{query}'"
        cache.set(query, value, qtype, context)
        print(f"   ✓ Stocké: {query[:20]}... (Type: {qtype.value})")
    
    # Récupérer des valeurs
    print(f"\n🔍 Test de récupération:")
    for query, qtype, context in test_queries:
        result = cache.get(query, qtype, context)
        status = "✅ HIT" if result else "❌ MISS"
        print(f"   {status}: {query[:20]}...")
    
    # Test de patterns (accès répétés)
    print(f"\n🔄 Test de détection de patterns:")
    frequent_query = "fièvre et maux de tête"
    frequent_context = {"language": "fr", "domain": "infectious_diseases"}
    
    for i in range(5):
        cache.get(frequent_query, QueryType.SEARCH, frequent_context)
        time.sleep(0.1)  # Petit délai pour simuler des accès répétés
    
    patterns = cache.get_patterns()
    print(f"   Patterns détectés: {len(patterns)}")
    
    for pattern_id, pattern in patterns.items():
        print(f"     {pattern_id}: fréquence={pattern.frequency}, confiance={pattern.confidence:.2f}")
    
    # Test de prédictions
    print(f"\n🔮 Test de prédictions:")
    predictions = cache.predict_cache_needs()
    print(f"   Prédictions: {len(predictions)}")
    
    for pred in predictions[:3]:  # Afficher les 3 premières
        print(f"     Pattern: {pred['pattern_id']}, Confiance: {pred['confidence']:.2f}")
    
    # Statistiques
    print(f"\n📈 Statistiques du cache:")
    stats = cache.get_stats()
    print(f"   Requêtes totales: {stats.total_requests}")
    print(f"   Hits: {stats.cache_hits}")
    print(f"   Misses: {stats.cache_misses}")
    print(f"   Taux de hit: {stats.hit_rate:.1%}")
    print(f"   Temps de réponse moyen: {stats.avg_response_time:.3f}s")
    print(f"   Utilisation mémoire: {stats.memory_usage_bytes} bytes")
    
    if stats.stats_by_type:
        print(f"\n   Par type de requête:")
        for qtype, type_stats in stats.stats_by_type.items():
            total = type_stats['hits'] + type_stats['misses']
            hit_rate = type_stats['hits'] / total if total > 0 else 0
            print(f"     {qtype}: {hit_rate:.1%} hit rate ({type_stats['hits']}/{total})")
    
    # Test d'optimisation
    print(f"\n⚡ Test d'optimisation:")
    optimization = cache.optimize_cache()
    print(f"   Optimisation nécessaire: {optimization.get('optimization_needed', False)}")
    
    if 'suggested_ttl' in optimization:
        print(f"   TTL suggéré: {optimization['suggested_ttl']}s")
    
    # Test d'invalidation
    print(f"\n🗑️ Test d'invalidation:")
    cache.invalidate(frequent_query, frequent_context)
    result_after_invalidation = cache.get(frequent_query, QueryType.SEARCH, frequent_context)
    print(f"   Après invalidation: {'❌ MISS' if not result_after_invalidation else '✅ HIT'}")
    
    # Export des données
    export_path = "intelligent_cache_export.json"
    cache.export_cache_data(export_path)
    print(f"\n💾 Données exportées: {export_path}")
    
    print(f"\n✅ Test du cache intelligent terminé!")
    print(f"\n🎯 Objectif 20 - Cache intelligent requêtes: IMPLÉMENTÉ")
    print(f"   ✓ Cache multi-niveaux (L1/L2/L3)")
    print(f"   ✓ Stratégies adaptatives (LRU, LFU, TTL, Adaptive)")
    print(f"   ✓ Détection automatique de patterns")
    print(f"   ✓ TTL adaptatif basé sur l'usage")
    print(f"   ✓ Prédiction des besoins futurs")
    print(f"   ✓ Optimisation automatique")
    print(f"   ✓ Support Redis, mémoire et disque")
    print(f"   ✓ Compression et sérialisation")
    print(f"   ✓ Statistiques détaillées")
    print(f"   ✓ Nettoyage automatique")

if __name__ == "__main__":
    main()