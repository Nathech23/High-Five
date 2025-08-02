#!/usr/bin/env python3
"""
Cache de Résultats avec TTL

Objectif 21: Implémenter cache résultats TTL

Ce module implémente un système de cache de résultats avec Time To Live (TTL)
automatique, optimisé pour les résultats de recherche médicale multilingue
avec gestion intelligente de l'expiration et de la cohérence des données.

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
import uuid

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
    from cachetools import TTLCache
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

class ResultType(Enum):
    """Types de résultats"""
    SEARCH_RESULTS = "search_results"
    TRANSLATION_RESULTS = "translation_results"
    EMBEDDING_RESULTS = "embedding_results"
    ANALYSIS_RESULTS = "analysis_results"
    AGGREGATED_RESULTS = "aggregated_results"
    FILTERED_RESULTS = "filtered_results"

class CacheLevel(Enum):
    """Niveaux de priorité du cache"""
    HIGH = "high"        # Résultats critiques, TTL long
    MEDIUM = "medium"    # Résultats standards
    LOW = "low"          # Résultats temporaires, TTL court
    VOLATILE = "volatile" # Résultats très temporaires

class ExpirationStrategy(Enum):
    """Stratégies d'expiration"""
    FIXED_TTL = "fixed_ttl"           # TTL fixe
    ADAPTIVE_TTL = "adaptive_ttl"     # TTL adaptatif basé sur l'usage
    SLIDING_TTL = "sliding_ttl"       # TTL qui se renouvelle à chaque accès
    CONDITIONAL_TTL = "conditional_ttl" # TTL basé sur des conditions
    SMART_TTL = "smart_ttl"           # TTL intelligent basé sur le contenu

class InvalidationTrigger(Enum):
    """Déclencheurs d'invalidation"""
    TIME_BASED = "time_based"         # Basé sur le temps
    ACCESS_BASED = "access_based"     # Basé sur le nombre d'accès
    CONTENT_BASED = "content_based"   # Basé sur le changement de contenu
    DEPENDENCY_BASED = "dependency_based" # Basé sur les dépendances
    MANUAL = "manual"                 # Invalidation manuelle

@dataclass
class ResultMetadata:
    """Métadonnées d'un résultat"""
    result_id: str
    result_type: ResultType
    cache_level: CacheLevel
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int = 3600
    expiration_strategy: ExpirationStrategy = ExpirationStrategy.FIXED_TTL
    size_bytes: int = 0
    checksum: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_query: Optional[str] = None
    language: Optional[str] = None
    domain: Optional[str] = None
    confidence_score: float = 1.0
    
    def is_expired(self) -> bool:
        """Vérifie si le résultat a expiré"""
        now = datetime.now()
        
        if self.expiration_strategy == ExpirationStrategy.FIXED_TTL:
            return (now - self.created_at).total_seconds() > self.ttl_seconds
        
        elif self.expiration_strategy == ExpirationStrategy.SLIDING_TTL:
            return (now - self.last_accessed).total_seconds() > self.ttl_seconds
        
        elif self.expiration_strategy == ExpirationStrategy.ADAPTIVE_TTL:
            # TTL adaptatif basé sur la fréquence d'accès
            if self.access_count > 10:
                adaptive_ttl = self.ttl_seconds * 2  # Doubler le TTL pour les résultats populaires
            elif self.access_count < 3:
                adaptive_ttl = self.ttl_seconds // 2  # Réduire le TTL pour les résultats peu utilisés
            else:
                adaptive_ttl = self.ttl_seconds
            
            return (now - self.created_at).total_seconds() > adaptive_ttl
        
        elif self.expiration_strategy == ExpirationStrategy.SMART_TTL:
            # TTL intelligent basé sur le type et la confiance
            base_ttl = self.ttl_seconds
            
            # Ajuster selon le type de résultat
            type_multipliers = {
                ResultType.SEARCH_RESULTS: 1.0,
                ResultType.TRANSLATION_RESULTS: 2.0,  # Les traductions sont plus stables
                ResultType.EMBEDDING_RESULTS: 3.0,    # Les embeddings sont très stables
                ResultType.ANALYSIS_RESULTS: 0.5,     # Les analyses peuvent changer
                ResultType.AGGREGATED_RESULTS: 1.5,   # Les agrégations sont assez stables
                ResultType.FILTERED_RESULTS: 0.8      # Les filtres peuvent changer
            }
            
            # Ajuster selon la confiance
            confidence_multiplier = self.confidence_score
            
            smart_ttl = base_ttl * type_multipliers.get(self.result_type, 1.0) * confidence_multiplier
            
            return (now - self.created_at).total_seconds() > smart_ttl
        
        return False
    
    def update_access(self):
        """Met à jour les statistiques d'accès"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def calculate_checksum(self, data: Any) -> str:
        """Calcule le checksum des données"""
        try:
            data_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(data_str.encode()).hexdigest()
        except:
            return hashlib.md5(str(data).encode()).hexdigest()

@dataclass
class CachedResult:
    """Résultat mis en cache"""
    metadata: ResultMetadata
    data: Any
    compressed: bool = False
    
    def get_data(self) -> Any:
        """Récupère les données (avec décompression si nécessaire)"""
        if self.compressed and isinstance(self.data, bytes):
            try:
                decompressed = gzip.decompress(self.data)
                return pickle.loads(decompressed)
            except:
                return self.data
        return self.data
    
    def set_data(self, data: Any, compress: bool = False):
        """Définit les données (avec compression si nécessaire)"""
        if compress:
            try:
                serialized = pickle.dumps(data)
                self.data = gzip.compress(serialized)
                self.compressed = True
                self.metadata.size_bytes = len(self.data)
            except:
                self.data = data
                self.compressed = False
                self.metadata.size_bytes = len(str(data).encode())
        else:
            self.data = data
            self.compressed = False
            self.metadata.size_bytes = len(str(data).encode())
        
        # Mettre à jour le checksum
        self.metadata.checksum = self.metadata.calculate_checksum(data)

@dataclass
class CacheStats:
    """Statistiques du cache de résultats"""
    total_results: int = 0
    active_results: int = 0
    expired_results: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    invalidations: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_ttl_seconds: float = 0.0
    hit_rate: float = 0.0
    stats_by_type: Dict[str, Dict[str, int]] = field(default_factory=dict)
    stats_by_level: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def update_hit(self, result_type: ResultType, cache_level: CacheLevel):
        """Met à jour les statistiques de hit"""
        self.cache_hits += 1
        total_requests = self.cache_hits + self.cache_misses
        self.hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        # Par type
        type_key = result_type.value
        if type_key not in self.stats_by_type:
            self.stats_by_type[type_key] = {"hits": 0, "misses": 0}
        self.stats_by_type[type_key]["hits"] += 1
        
        # Par niveau
        level_key = cache_level.value
        if level_key not in self.stats_by_level:
            self.stats_by_level[level_key] = {"hits": 0, "misses": 0}
        self.stats_by_level[level_key]["hits"] += 1
    
    def update_miss(self, result_type: ResultType, cache_level: CacheLevel):
        """Met à jour les statistiques de miss"""
        self.cache_misses += 1
        total_requests = self.cache_hits + self.cache_misses
        self.hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        # Par type
        type_key = result_type.value
        if type_key not in self.stats_by_type:
            self.stats_by_type[type_key] = {"hits": 0, "misses": 0}
        self.stats_by_type[type_key]["misses"] += 1
        
        # Par niveau
        level_key = cache_level.value
        if level_key not in self.stats_by_level:
            self.stats_by_level[level_key] = {"hits": 0, "misses": 0}
        self.stats_by_level[level_key]["misses"] += 1

class ResultCache:
    """
    Système de cache de résultats avec TTL intelligent
    
    Objectif couvert:
    - 21. Implémenter cache résultats TTL
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = CacheStats()
        
        # Configuration
        self.max_size_mb = self.config.get("max_size_mb", 1024)
        self.default_ttl = self.config.get("default_ttl", 3600)
        self.compression_threshold = self.config.get("compression_threshold", 1024)  # bytes
        self.cleanup_interval = self.config.get("cleanup_interval", 300)  # secondes
        self.enable_redis = self.config.get("enable_redis", False)
        self.enable_persistence = self.config.get("enable_persistence", True)
        
        # TTL par type de résultat
        self.ttl_by_type = {
            ResultType.SEARCH_RESULTS: self.config.get("search_ttl", 1800),      # 30 min
            ResultType.TRANSLATION_RESULTS: self.config.get("translation_ttl", 7200),  # 2h
            ResultType.EMBEDDING_RESULTS: self.config.get("embedding_ttl", 14400),     # 4h
            ResultType.ANALYSIS_RESULTS: self.config.get("analysis_ttl", 900),         # 15 min
            ResultType.AGGREGATED_RESULTS: self.config.get("aggregated_ttl", 3600),   # 1h
            ResultType.FILTERED_RESULTS: self.config.get("filtered_ttl", 1200)        # 20 min
        }
        
        # TTL par niveau de cache
        self.ttl_by_level = {
            CacheLevel.HIGH: self.config.get("high_level_ttl", 14400),    # 4h
            CacheLevel.MEDIUM: self.config.get("medium_level_ttl", 3600), # 1h
            CacheLevel.LOW: self.config.get("low_level_ttl", 900),        # 15 min
            CacheLevel.VOLATILE: self.config.get("volatile_level_ttl", 300) # 5 min
        }
        
        # Stockage principal
        self.cache_store: Dict[str, CachedResult] = {}
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)
        self.tag_index: Dict[str, List[str]] = defaultdict(list)
        
        # Initialiser les backends
        self._init_backends()
        
        # Thread de nettoyage
        self.cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self.cleanup_thread.start()
        
        # Verrous
        self.lock = threading.RLock()
        
        logger.info(f"Cache de résultats initialisé - Taille max: {self.max_size_mb}MB")
    
    def _init_backends(self):
        """Initialise les backends de stockage"""
        # Backend Redis
        self.redis_client = None
        if self.enable_redis and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=self.config.get("redis_host", "localhost"),
                    port=self.config.get("redis_port", 6379),
                    db=self.config.get("redis_db", 1),  # DB différente du cache intelligent
                    decode_responses=False
                )
                self.redis_client.ping()
                logger.info("Backend Redis connecté pour le cache de résultats")
            except Exception as e:
                logger.warning(f"Impossible de se connecter à Redis: {e}")
                self.redis_client = None
        
        # Backend persistant
        self.persistence_dir = None
        if self.enable_persistence:
            self.persistence_dir = Path(self.config.get("persistence_dir", "./result_cache"))
            self.persistence_dir.mkdir(exist_ok=True)
            logger.info(f"Persistance activée: {self.persistence_dir}")
    
    def _generate_result_id(self, query: str, result_type: ResultType, 
                           context: Dict[str, Any] = None) -> str:
        """Génère un ID unique pour un résultat"""
        # Normaliser les données
        normalized_data = {
            'query': query.lower().strip(),
            'type': result_type.value,
            'context': context or {}
        }
        
        # Créer un hash
        data_str = json.dumps(normalized_data, sort_keys=True)
        hash_obj = hashlib.sha256(data_str.encode())
        return f"result_{hash_obj.hexdigest()[:16]}"
    
    def _calculate_ttl(self, result_type: ResultType, cache_level: CacheLevel, 
                      custom_ttl: Optional[int] = None) -> int:
        """Calcule le TTL approprié"""
        if custom_ttl is not None:
            return custom_ttl
        
        # TTL basé sur le type
        type_ttl = self.ttl_by_type.get(result_type, self.default_ttl)
        
        # TTL basé sur le niveau
        level_ttl = self.ttl_by_level.get(cache_level, self.default_ttl)
        
        # Prendre le maximum pour être conservateur
        return max(type_ttl, level_ttl)
    
    def _should_compress(self, data: Any) -> bool:
        """Détermine si les données doivent être compressées"""
        try:
            size = len(str(data).encode())
            return size > self.compression_threshold
        except:
            return False
    
    def _save_to_redis(self, result_id: str, cached_result: CachedResult):
        """Sauvegarde dans Redis"""
        if not self.redis_client:
            return
        
        try:
            # Sérialiser le résultat complet
            serialized = pickle.dumps(cached_result)
            
            # Utiliser le TTL du métadata
            ttl = cached_result.metadata.ttl_seconds
            
            # Stocker avec expiration
            self.redis_client.setex(f"result:{result_id}", ttl, serialized)
            
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde Redis: {e}")
    
    def _load_from_redis(self, result_id: str) -> Optional[CachedResult]:
        """Charge depuis Redis"""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get(f"result:{result_id}")
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.warning(f"Erreur lors du chargement Redis: {e}")
        
        return None
    
    def _save_to_disk(self, result_id: str, cached_result: CachedResult):
        """Sauvegarde sur disque"""
        if not self.persistence_dir:
            return
        
        try:
            file_path = self.persistence_dir / f"{result_id}.pkl"
            
            with open(file_path, 'wb') as f:
                pickle.dump(cached_result, f)
            
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde disque: {e}")
    
    def _load_from_disk(self, result_id: str) -> Optional[CachedResult]:
        """Charge depuis le disque"""
        if not self.persistence_dir:
            return None
        
        try:
            file_path = self.persistence_dir / f"{result_id}.pkl"
            
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    cached_result = pickle.load(f)
                
                # Vérifier l'expiration
                if not cached_result.metadata.is_expired():
                    return cached_result
                else:
                    # Supprimer le fichier expiré
                    file_path.unlink(missing_ok=True)
            
        except Exception as e:
            logger.warning(f"Erreur lors du chargement disque: {e}")
        
        return None
    
    def store_result(self, query: str, data: Any, result_type: ResultType,
                    cache_level: CacheLevel = CacheLevel.MEDIUM,
                    ttl: Optional[int] = None,
                    expiration_strategy: ExpirationStrategy = ExpirationStrategy.FIXED_TTL,
                    context: Dict[str, Any] = None,
                    dependencies: List[str] = None,
                    tags: List[str] = None,
                    confidence_score: float = 1.0) -> str:
        """
        Stocke un résultat dans le cache
        
        Args:
            query: Requête source
            data: Données à mettre en cache
            result_type: Type de résultat
            cache_level: Niveau de priorité
            ttl: TTL personnalisé
            expiration_strategy: Stratégie d'expiration
            context: Contexte additionnel
            dependencies: Dépendances
            tags: Tags pour l'indexation
            confidence_score: Score de confiance
        
        Returns:
            ID du résultat stocké
        """
        with self.lock:
            try:
                # Générer l'ID
                result_id = self._generate_result_id(query, result_type, context)
                
                # Calculer le TTL
                calculated_ttl = self._calculate_ttl(result_type, cache_level, ttl)
                
                # Créer les métadonnées
                metadata = ResultMetadata(
                    result_id=result_id,
                    result_type=result_type,
                    cache_level=cache_level,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    ttl_seconds=calculated_ttl,
                    expiration_strategy=expiration_strategy,
                    dependencies=dependencies or [],
                    tags=tags or [],
                    source_query=query,
                    language=context.get('language') if context else None,
                    domain=context.get('domain') if context else None,
                    confidence_score=confidence_score
                )
                
                # Créer le résultat mis en cache
                cached_result = CachedResult(metadata=metadata, data=None)
                
                # Définir les données (avec compression si nécessaire)
                should_compress = self._should_compress(data)
                cached_result.set_data(data, compress=should_compress)
                
                # Stocker en mémoire
                self.cache_store[result_id] = cached_result
                
                # Mettre à jour les index
                if dependencies:
                    for dep in dependencies:
                        self.dependency_graph[dep].append(result_id)
                
                if tags:
                    for tag in tags:
                        self.tag_index[tag].append(result_id)
                
                # Sauvegarder dans les backends
                if self.redis_client:
                    self._save_to_redis(result_id, cached_result)
                
                if self.persistence_dir:
                    self._save_to_disk(result_id, cached_result)
                
                # Mettre à jour les statistiques
                self.stats.total_results += 1
                self.stats.active_results += 1
                self.stats.total_size_bytes += cached_result.metadata.size_bytes
                
                # Recalculer le TTL moyen
                if self.stats.active_results > 0:
                    total_ttl = sum(
                        result.metadata.ttl_seconds 
                        for result in self.cache_store.values()
                        if not result.metadata.is_expired()
                    )
                    self.stats.avg_ttl_seconds = total_ttl / self.stats.active_results
                
                logger.debug(f"Résultat stocké: {result_id} (TTL: {calculated_ttl}s, Taille: {cached_result.metadata.size_bytes} bytes)")
                
                return result_id
            
            except Exception as e:
                logger.error(f"Erreur lors du stockage du résultat: {e}")
                return ""
    
    def get_result(self, query: str, result_type: ResultType, 
                  context: Dict[str, Any] = None) -> Optional[Any]:
        """
        Récupère un résultat du cache
        
        Args:
            query: Requête source
            result_type: Type de résultat
            context: Contexte additionnel
        
        Returns:
            Données mises en cache ou None
        """
        with self.lock:
            try:
                # Générer l'ID
                result_id = self._generate_result_id(query, result_type, context)
                
                # Chercher en mémoire
                cached_result = self.cache_store.get(result_id)
                
                if cached_result:
                    # Vérifier l'expiration
                    if cached_result.metadata.is_expired():
                        # Supprimer le résultat expiré
                        self._remove_result(result_id)
                        self.stats.expired_results += 1
                        self.stats.update_miss(result_type, CacheLevel.MEDIUM)
                        return None
                    
                    # Mettre à jour l'accès
                    cached_result.metadata.update_access()
                    
                    # Statistiques
                    self.stats.update_hit(result_type, cached_result.metadata.cache_level)
                    
                    logger.debug(f"Cache hit: {result_id}")
                    return cached_result.get_data()
                
                # Chercher dans Redis
                if self.redis_client:
                    cached_result = self._load_from_redis(result_id)
                    if cached_result and not cached_result.metadata.is_expired():
                        # Remettre en mémoire
                        self.cache_store[result_id] = cached_result
                        cached_result.metadata.update_access()
                        
                        self.stats.update_hit(result_type, cached_result.metadata.cache_level)
                        logger.debug(f"Cache hit Redis: {result_id}")
                        return cached_result.get_data()
                
                # Chercher sur disque
                if self.persistence_dir:
                    cached_result = self._load_from_disk(result_id)
                    if cached_result and not cached_result.metadata.is_expired():
                        # Remettre en mémoire et Redis
                        self.cache_store[result_id] = cached_result
                        if self.redis_client:
                            self._save_to_redis(result_id, cached_result)
                        
                        cached_result.metadata.update_access()
                        
                        self.stats.update_hit(result_type, cached_result.metadata.cache_level)
                        logger.debug(f"Cache hit disque: {result_id}")
                        return cached_result.get_data()
                
                # Cache miss
                self.stats.update_miss(result_type, CacheLevel.MEDIUM)
                logger.debug(f"Cache miss: {result_id}")
                return None
            
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du résultat: {e}")
                self.stats.update_miss(result_type, CacheLevel.MEDIUM)
                return None
    
    def _remove_result(self, result_id: str):
        """Supprime un résultat du cache"""
        try:
            # Supprimer de la mémoire
            if result_id in self.cache_store:
                cached_result = self.cache_store[result_id]
                self.stats.total_size_bytes -= cached_result.metadata.size_bytes
                self.stats.active_results -= 1
                del self.cache_store[result_id]
            
            # Supprimer de Redis
            if self.redis_client:
                self.redis_client.delete(f"result:{result_id}")
            
            # Supprimer du disque
            if self.persistence_dir:
                file_path = self.persistence_dir / f"{result_id}.pkl"
                file_path.unlink(missing_ok=True)
            
            # Nettoyer les index
            for dep_list in self.dependency_graph.values():
                if result_id in dep_list:
                    dep_list.remove(result_id)
            
            for tag_list in self.tag_index.values():
                if result_id in tag_list:
                    tag_list.remove(result_id)
        
        except Exception as e:
            logger.warning(f"Erreur lors de la suppression: {e}")
    
    def invalidate_result(self, query: str, result_type: ResultType, 
                         context: Dict[str, Any] = None):
        """
        Invalide un résultat spécifique
        
        Args:
            query: Requête source
            result_type: Type de résultat
            context: Contexte additionnel
        """
        with self.lock:
            result_id = self._generate_result_id(query, result_type, context)
            self._remove_result(result_id)
            self.stats.invalidations += 1
            logger.debug(f"Résultat invalidé: {result_id}")
    
    def invalidate_by_dependency(self, dependency: str):
        """
        Invalide tous les résultats dépendant d'une ressource
        
        Args:
            dependency: Nom de la dépendance
        """
        with self.lock:
            if dependency in self.dependency_graph:
                result_ids = self.dependency_graph[dependency].copy()
                
                for result_id in result_ids:
                    self._remove_result(result_id)
                    self.stats.invalidations += 1
                
                logger.info(f"Invalidation par dépendance '{dependency}': {len(result_ids)} résultats")
    
    def invalidate_by_tag(self, tag: str):
        """
        Invalide tous les résultats avec un tag spécifique
        
        Args:
            tag: Tag à invalider
        """
        with self.lock:
            if tag in self.tag_index:
                result_ids = self.tag_index[tag].copy()
                
                for result_id in result_ids:
                    self._remove_result(result_id)
                    self.stats.invalidations += 1
                
                logger.info(f"Invalidation par tag '{tag}': {len(result_ids)} résultats")
    
    def invalidate_by_type(self, result_type: ResultType):
        """
        Invalide tous les résultats d'un type spécifique
        
        Args:
            result_type: Type de résultat à invalider
        """
        with self.lock:
            result_ids = [
                result_id for result_id, cached_result in self.cache_store.items()
                if cached_result.metadata.result_type == result_type
            ]
            
            for result_id in result_ids:
                self._remove_result(result_id)
                self.stats.invalidations += 1
            
            logger.info(f"Invalidation par type '{result_type.value}': {len(result_ids)} résultats")
    
    def clear_cache(self, cache_level: Optional[CacheLevel] = None):
        """
        Vide le cache (complètement ou par niveau)
        
        Args:
            cache_level: Niveau à vider (optionnel)
        """
        with self.lock:
            if cache_level is None:
                # Vider tout
                result_ids = list(self.cache_store.keys())
                
                for result_id in result_ids:
                    self._remove_result(result_id)
                
                self.dependency_graph.clear()
                self.tag_index.clear()
                
                logger.info(f"Cache complètement vidé: {len(result_ids)} résultats")
            
            else:
                # Vider seulement un niveau
                result_ids = [
                    result_id for result_id, cached_result in self.cache_store.items()
                    if cached_result.metadata.cache_level == cache_level
                ]
                
                for result_id in result_ids:
                    self._remove_result(result_id)
                
                logger.info(f"Cache vidé pour le niveau '{cache_level.value}': {len(result_ids)} résultats")
    
    def _periodic_cleanup(self):
        """Nettoyage périodique des résultats expirés"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                
                with self.lock:
                    expired_ids = []
                    
                    for result_id, cached_result in list(self.cache_store.items()):
                        if cached_result.metadata.is_expired():
                            expired_ids.append(result_id)
                    
                    for result_id in expired_ids:
                        self._remove_result(result_id)
                        self.stats.expired_results += 1
                        self.stats.evictions += 1
                    
                    if expired_ids:
                        logger.debug(f"Nettoyage: {len(expired_ids)} résultats expirés supprimés")
                    
                    # Vérifier la limite de taille
                    max_size_bytes = self.max_size_mb * 1024 * 1024
                    
                    if self.stats.total_size_bytes > max_size_bytes:
                        # Supprimer les résultats les moins récemment utilisés
                        sorted_results = sorted(
                            self.cache_store.items(),
                            key=lambda x: x[1].metadata.last_accessed
                        )
                        
                        while (self.stats.total_size_bytes > max_size_bytes * 0.8 and 
                               sorted_results):
                            result_id, _ = sorted_results.pop(0)
                            self._remove_result(result_id)
                            self.stats.evictions += 1
                        
                        logger.info(f"Éviction par taille: limite de {self.max_size_mb}MB atteinte")
            
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage périodique: {e}")
    
    def get_stats(self) -> CacheStats:
        """Retourne les statistiques du cache"""
        with self.lock:
            # Mettre à jour les compteurs actifs
            active_count = 0
            total_size = 0
            
            for cached_result in self.cache_store.values():
                if not cached_result.metadata.is_expired():
                    active_count += 1
                    total_size += cached_result.metadata.size_bytes
            
            self.stats.active_results = active_count
            self.stats.total_size_bytes = total_size
            
            return self.stats
    
    def get_result_info(self, query: str, result_type: ResultType, 
                       context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Retourne les informations sur un résultat mis en cache
        
        Args:
            query: Requête source
            result_type: Type de résultat
            context: Contexte additionnel
        
        Returns:
            Informations sur le résultat ou None
        """
        with self.lock:
            result_id = self._generate_result_id(query, result_type, context)
            
            if result_id in self.cache_store:
                cached_result = self.cache_store[result_id]
                metadata = cached_result.metadata
                
                return {
                    'result_id': result_id,
                    'result_type': metadata.result_type.value,
                    'cache_level': metadata.cache_level.value,
                    'created_at': metadata.created_at.isoformat(),
                    'last_accessed': metadata.last_accessed.isoformat(),
                    'access_count': metadata.access_count,
                    'ttl_seconds': metadata.ttl_seconds,
                    'expiration_strategy': metadata.expiration_strategy.value,
                    'size_bytes': metadata.size_bytes,
                    'is_expired': metadata.is_expired(),
                    'dependencies': metadata.dependencies,
                    'tags': metadata.tags,
                    'language': metadata.language,
                    'domain': metadata.domain,
                    'confidence_score': metadata.confidence_score,
                    'compressed': cached_result.compressed
                }
            
            return None
    
    def list_results(self, result_type: Optional[ResultType] = None,
                    cache_level: Optional[CacheLevel] = None,
                    tag: Optional[str] = None,
                    include_expired: bool = False) -> List[Dict[str, Any]]:
        """
        Liste les résultats mis en cache selon des critères
        
        Args:
            result_type: Filtrer par type (optionnel)
            cache_level: Filtrer par niveau (optionnel)
            tag: Filtrer par tag (optionnel)
            include_expired: Inclure les résultats expirés
        
        Returns:
            Liste des informations sur les résultats
        """
        with self.lock:
            results = []
            
            for result_id, cached_result in self.cache_store.items():
                metadata = cached_result.metadata
                
                # Filtrer par expiration
                if not include_expired and metadata.is_expired():
                    continue
                
                # Filtrer par type
                if result_type and metadata.result_type != result_type:
                    continue
                
                # Filtrer par niveau
                if cache_level and metadata.cache_level != cache_level:
                    continue
                
                # Filtrer par tag
                if tag and tag not in metadata.tags:
                    continue
                
                results.append({
                    'result_id': result_id,
                    'result_type': metadata.result_type.value,
                    'cache_level': metadata.cache_level.value,
                    'created_at': metadata.created_at.isoformat(),
                    'last_accessed': metadata.last_accessed.isoformat(),
                    'access_count': metadata.access_count,
                    'ttl_seconds': metadata.ttl_seconds,
                    'size_bytes': metadata.size_bytes,
                    'is_expired': metadata.is_expired(),
                    'tags': metadata.tags,
                    'language': metadata.language,
                    'domain': metadata.domain,
                    'confidence_score': metadata.confidence_score
                })
            
            return sorted(results, key=lambda x: x['last_accessed'], reverse=True)
    
    def export_cache_data(self, output_path: str):
        """Exporte les données du cache"""
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'cache_type': 'result_cache',
                'version': '2.0.0'
            },
            'configuration': {
                'max_size_mb': self.max_size_mb,
                'default_ttl': self.default_ttl,
                'compression_threshold': self.compression_threshold,
                'cleanup_interval': self.cleanup_interval,
                'enable_redis': self.enable_redis,
                'enable_persistence': self.enable_persistence,
                'ttl_by_type': {k.value: v for k, v in self.ttl_by_type.items()},
                'ttl_by_level': {k.value: v for k, v in self.ttl_by_level.items()}
            },
            'statistics': {
                'total_results': self.stats.total_results,
                'active_results': self.stats.active_results,
                'expired_results': self.stats.expired_results,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'hit_rate': self.stats.hit_rate,
                'invalidations': self.stats.invalidations,
                'evictions': self.stats.evictions,
                'total_size_bytes': self.stats.total_size_bytes,
                'avg_ttl_seconds': self.stats.avg_ttl_seconds,
                'stats_by_type': self.stats.stats_by_type,
                'stats_by_level': self.stats.stats_by_level
            },
            'results_summary': self.list_results(include_expired=True),
            'dependency_graph': dict(self.dependency_graph),
            'tag_index': dict(self.tag_index)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Données du cache de résultats exportées: {output_path}")

# Test de démonstration
def main():
    """Fonction de test principale"""
    print("💾 Test du Cache de Résultats avec TTL")
    
    # Configuration de test
    config = {
        "max_size_mb": 64,
        "default_ttl": 1800,
        "compression_threshold": 512,
        "cleanup_interval": 60,
        "enable_redis": False,
        "enable_persistence": True,
        "search_ttl": 900,
        "translation_ttl": 3600,
        "embedding_ttl": 7200,
        "analysis_ttl": 600,
        "high_level_ttl": 7200,
        "medium_level_ttl": 1800,
        "low_level_ttl": 600,
        "volatile_level_ttl": 300
    }
    
    print(f"\n📊 Configuration:")
    print(f"   Taille max: {config['max_size_mb']} MB")
    print(f"   TTL par défaut: {config['default_ttl']}s")
    print(f"   Seuil compression: {config['compression_threshold']} bytes")
    print(f"   Intervalle nettoyage: {config['cleanup_interval']}s")
    
    # Créer le cache de résultats
    cache = ResultCache(config)
    
    print(f"\n✅ Cache de résultats créé")
    
    # Test des fonctionnalités
    print(f"\n🧪 Test des fonctionnalités:")
    
    # Test 1: Stockage de différents types de résultats
    test_cases = [
        {
            'query': 'fièvre et maux de tête',
            'data': {
                'results': [
                    {'title': 'Paludisme', 'score': 0.95, 'content': 'Le paludisme est une maladie...'},
                    {'title': 'Grippe', 'score': 0.87, 'content': 'La grippe est une infection...'}
                ],
                'total_found': 2,
                'search_time': 0.15
            },
            'type': ResultType.SEARCH_RESULTS,
            'level': CacheLevel.HIGH,
            'context': {'language': 'fr', 'domain': 'infectious_diseases'},
            'tags': ['medical', 'symptoms', 'fever'],
            'confidence': 0.95
        },
        {
            'query': 'translate: fièvre -> fever',
            'data': {
                'source_text': 'fièvre',
                'translated_text': 'fever',
                'source_lang': 'fr',
                'target_lang': 'en',
                'confidence': 0.98
            },
            'type': ResultType.TRANSLATION_RESULTS,
            'level': CacheLevel.MEDIUM,
            'context': {'source': 'fr', 'target': 'en'},
            'tags': ['translation', 'medical_terms'],
            'confidence': 0.98
        },
        {
            'query': 'embed: symptômes paludisme',
            'data': {
                'embedding': [0.1, 0.2, 0.3] * 100,  # Simulation d'un embedding
                'model': 'multilingual-medical-v2',
                'dimensions': 300
            },
            'type': ResultType.EMBEDDING_RESULTS,
            'level': CacheLevel.HIGH,
            'context': {'language': 'fr', 'model': 'multilingual-medical-v2'},
            'tags': ['embedding', 'medical'],
            'confidence': 1.0
        },
        {
            'query': 'analyze: patient symptoms',
            'data': {
                'analysis': {
                    'primary_diagnosis': 'Malaria',
                    'confidence': 0.89,
                    'differential_diagnoses': ['Typhoid', 'Dengue'],
                    'recommended_tests': ['Blood smear', 'RDT']
                },
                'processing_time': 2.3
            },
            'type': ResultType.ANALYSIS_RESULTS,
            'level': CacheLevel.LOW,
            'context': {'patient_id': 'P123', 'doctor_id': 'D456'},
            'tags': ['analysis', 'diagnosis'],
            'confidence': 0.89
        }
    ]
    
    # Stocker les résultats
    stored_ids = []
    for i, case in enumerate(test_cases):
        result_id = cache.store_result(
            query=case['query'],
            data=case['data'],
            result_type=case['type'],
            cache_level=case['level'],
            context=case['context'],
            tags=case['tags'],
            confidence_score=case['confidence']
        )
        stored_ids.append(result_id)
        print(f"   ✓ Stocké: {case['type'].value} - {case['query'][:30]}...")
    
    # Test 2: Récupération des résultats
    print(f"\n🔍 Test de récupération:")
    for case in test_cases:
        result = cache.get_result(
            query=case['query'],
            result_type=case['type'],
            context=case['context']
        )
        status = "✅ HIT" if result else "❌ MISS"
        print(f"   {status}: {case['type'].value} - {case['query'][:30]}...")
    
    # Test 3: Informations sur les résultats
    print(f"\n📋 Informations sur les résultats:")
    for case in test_cases[:2]:  # Afficher les 2 premiers
        info = cache.get_result_info(
            query=case['query'],
            result_type=case['type'],
            context=case['context']
        )
        if info:
            print(f"   {case['type'].value}:")
            print(f"     ID: {info['result_id'][:16]}...")
            print(f"     Niveau: {info['cache_level']}")
            print(f"     TTL: {info['ttl_seconds']}s")
            print(f"     Taille: {info['size_bytes']} bytes")
            print(f"     Accès: {info['access_count']}")
            print(f"     Compressé: {info['compressed']}")
            print(f"     Confiance: {info['confidence_score']}")
    
    # Test 4: Listing des résultats
    print(f"\n📝 Liste des résultats:")
    all_results = cache.list_results()
    print(f"   Total: {len(all_results)} résultats")
    
    # Par type
    for result_type in ResultType:
        type_results = cache.list_results(result_type=result_type)
        if type_results:
            print(f"   {result_type.value}: {len(type_results)} résultats")
    
    # Par niveau
    for cache_level in CacheLevel:
        level_results = cache.list_results(cache_level=cache_level)
        if level_results:
            print(f"   {cache_level.value}: {len(level_results)} résultats")
    
    # Test 5: Test des stratégies d'expiration
    print(f"\n⏰ Test des stratégies d'expiration:")
    
    # Résultat avec TTL court pour test
    short_ttl_id = cache.store_result(
        query="test expiration rapide",
        data={"test": "données temporaires"},
        result_type=ResultType.ANALYSIS_RESULTS,
        cache_level=CacheLevel.VOLATILE,
        ttl=2,  # 2 secondes
        expiration_strategy=ExpirationStrategy.FIXED_TTL
    )
    
    print(f"   ✓ Résultat avec TTL court stocké")
    
    # Vérifier immédiatement
    result = cache.get_result("test expiration rapide", ResultType.ANALYSIS_RESULTS)
    print(f"   Immédiatement: {'✅ Trouvé' if result else '❌ Non trouvé'}")
    
    # Attendre l'expiration
    print(f"   Attente de l'expiration (3s)...")
    time.sleep(3)
    
    result = cache.get_result("test expiration rapide", ResultType.ANALYSIS_RESULTS)
    print(f"   Après expiration: {'✅ Trouvé' if result else '❌ Expiré (attendu)'}")
    
    # Test 6: Invalidation
    print(f"\n🗑️ Test d'invalidation:")
    
    # Invalidation par tag
    cache.invalidate_by_tag('medical')
    print(f"   ✓ Invalidation par tag 'medical'")
    
    # Vérifier l'invalidation
    result = cache.get_result(
        query='fièvre et maux de tête',
        result_type=ResultType.SEARCH_RESULTS,
        context={'language': 'fr', 'domain': 'infectious_diseases'}
    )
    print(f"   Après invalidation: {'✅ Trouvé' if result else '❌ Invalidé (attendu)'}")
    
    # Test 7: Statistiques
    print(f"\n📈 Statistiques du cache:")
    stats = cache.get_stats()
    print(f"   Résultats totaux: {stats.total_results}")
    print(f"   Résultats actifs: {stats.active_results}")
    print(f"   Résultats expirés: {stats.expired_results}")
    print(f"   Hits: {stats.cache_hits}")
    print(f"   Misses: {stats.cache_misses}")
    print(f"   Taux de hit: {stats.hit_rate:.1%}")
    print(f"   Invalidations: {stats.invalidations}")
    print(f"   Évictions: {stats.evictions}")
    print(f"   Taille totale: {stats.total_size_bytes} bytes")
    print(f"   TTL moyen: {stats.avg_ttl_seconds:.1f}s")
    
    if stats.stats_by_type:
        print(f"\n   Par type:")
        for result_type, type_stats in stats.stats_by_type.items():
            total = type_stats['hits'] + type_stats['misses']
            hit_rate = type_stats['hits'] / total if total > 0 else 0
            print(f"     {result_type}: {hit_rate:.1%} hit rate ({type_stats['hits']}/{total})")
    
    if stats.stats_by_level:
        print(f"\n   Par niveau:")
        for cache_level, level_stats in stats.stats_by_level.items():
            total = level_stats['hits'] + level_stats['misses']
            hit_rate = level_stats['hits'] / total if total > 0 else 0
            print(f"     {cache_level}: {hit_rate:.1%} hit rate ({level_stats['hits']}/{total})")
    
    # Test 8: Performance avec de nombreux résultats
    print(f"\n⚡ Test de performance:")
    
    start_time = time.time()
    
    # Stocker 100 résultats
    for i in range(100):
        cache.store_result(
            query=f"requête test {i}",
            data={"id": i, "data": f"données test {i}" * 10},
            result_type=ResultType.SEARCH_RESULTS,
            cache_level=CacheLevel.MEDIUM,
            context={"test_id": i}
        )
    
    store_time = time.time() - start_time
    print(f"   Stockage de 100 résultats: {store_time:.3f}s")
    
    # Récupérer 100 résultats
    start_time = time.time()
    hits = 0
    
    for i in range(100):
        result = cache.get_result(
            query=f"requête test {i}",
            result_type=ResultType.SEARCH_RESULTS,
            context={"test_id": i}
        )
        if result:
            hits += 1
    
    retrieve_time = time.time() - start_time
    print(f"   Récupération de 100 résultats: {retrieve_time:.3f}s")
    print(f"   Taux de hit: {hits}/100 ({hits}%)")
    
    # Export des données
    export_path = "result_cache_export.json"
    cache.export_cache_data(export_path)
    print(f"\n💾 Données exportées: {export_path}")
    
    # Statistiques finales
    final_stats = cache.get_stats()
    print(f"\n📊 Statistiques finales:")
    print(f"   Résultats totaux: {final_stats.total_results}")
    print(f"   Résultats actifs: {final_stats.active_results}")
    print(f"   Taux de hit global: {final_stats.hit_rate:.1%}")
    print(f"   Taille totale: {final_stats.total_size_bytes / 1024:.1f} KB")
    
    print(f"\n✅ Test du cache de résultats terminé!")
    print(f"\n🎯 Objectif 21 - Cache résultats TTL: IMPLÉMENTÉ")
    print(f"   ✓ Cache multi-niveaux (mémoire, Redis, disque)")
    print(f"   ✓ Stratégies d'expiration multiples (Fixed, Adaptive, Sliding, Smart)")
    print(f"   ✓ TTL adaptatif par type et niveau")
    print(f"   ✓ Compression automatique des gros résultats")
    print(f"   ✓ Invalidation par dépendance, tag, type")
    print(f"   ✓ Nettoyage automatique des résultats expirés")
    print(f"   ✓ Gestion de la taille maximale avec éviction LRU")
    print(f"   ✓ Persistance sur disque et Redis")
    print(f"   ✓ Statistiques détaillées par type et niveau")
    print(f"   ✓ Métadonnées riches (tags, dépendances, confiance)")

if __name__ == "__main__":
    main()