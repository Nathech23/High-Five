#!/usr/bin/env python3
"""
Multilevel Cache - Objectif 12

Implémente un système de cache intelligent multi-niveaux pour optimiser
les performances du RAG avec cache L1 (mémoire), L2 (Redis), L3 (disque).

Auteur: Équipe Hackathon Hôpital Général de Douala
Version: 3.0.0
"""

import os
import json
import time
import hashlib
import pickle
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import gzip

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vérification des dépendances optionnelles
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis non disponible - cache L2 désactivé")

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False
    logger.warning("lz4 non disponible - compression alternative utilisée")

class CacheLevel(Enum):
    """Niveaux de cache"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DISK = "l3_disk"

class CacheStrategy(Enum):
    """Stratégies de cache"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptatif basé sur les patterns

class CompressionType(Enum):
    """Types de compression"""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    PICKLE = "pickle"

@dataclass
class CacheEntry:
    """Entrée de cache"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: Optional[int]
    size_bytes: int
    compression: CompressionType
    metadata: Dict[str, Any]
    
    def is_expired(self) -> bool:
        """Vérifie si l'entrée a expiré"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
        
    def update_access(self):
        """Met à jour les statistiques d'accès"""
        self.last_accessed = datetime.now()
        self.access_count += 1

@dataclass
class CacheStats:
    """Statistiques de cache"""
    level: CacheLevel
    total_requests: int
    hits: int
    misses: int
    evictions: int
    size_bytes: int
    entry_count: int
    hit_rate: float
    average_access_time_ms: float
    compression_ratio: float

class CacheCompressor:
    """Gestionnaire de compression pour le cache"""
    
    @staticmethod
    def compress(data: Any, compression_type: CompressionType) -> Tuple[bytes, int]:
        """Compresse les données"""
        if compression_type == CompressionType.NONE:
            if isinstance(data, str):
                serialized = data.encode('utf-8')
            else:
                serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
            return serialized, len(serialized)
            
        elif compression_type == CompressionType.PICKLE:
            serialized = pickle.dumps(data)
            return serialized, len(serialized)
            
        elif compression_type == CompressionType.GZIP:
            if isinstance(data, str):
                serialized = data.encode('utf-8')
            else:
                serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
            compressed = gzip.compress(serialized)
            return compressed, len(serialized)
            
        elif compression_type == CompressionType.LZ4 and LZ4_AVAILABLE:
            if isinstance(data, str):
                serialized = data.encode('utf-8')
            else:
                serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
            compressed = lz4.frame.compress(serialized)
            return compressed, len(serialized)
            
        else:
            # Fallback vers pickle
            serialized = pickle.dumps(data)
            return serialized, len(serialized)
            
    @staticmethod
    def decompress(compressed_data: bytes, compression_type: CompressionType, is_json: bool = True) -> Any:
        """Décompresse les données"""
        if compression_type == CompressionType.NONE:
            if is_json:
                return json.loads(compressed_data.decode('utf-8'))
            else:
                return compressed_data.decode('utf-8')
                
        elif compression_type == CompressionType.PICKLE:
            return pickle.loads(compressed_data)
            
        elif compression_type == CompressionType.GZIP:
            decompressed = gzip.decompress(compressed_data)
            if is_json:
                return json.loads(decompressed.decode('utf-8'))
            else:
                return decompressed.decode('utf-8')
                
        elif compression_type == CompressionType.LZ4 and LZ4_AVAILABLE:
            decompressed = lz4.frame.decompress(compressed_data)
            if is_json:
                return json.loads(decompressed.decode('utf-8'))
            else:
                return decompressed.decode('utf-8')
                
        else:
            # Fallback vers pickle
            return pickle.loads(compressed_data)

class L1MemoryCache:
    """Cache L1 en mémoire"""
    
    def __init__(self, max_size_mb: int = 256, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.strategy = strategy
        self.entries: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # Pour LRU
        self.lock = threading.RLock()
        
        self.stats = CacheStats(
            level=CacheLevel.L1_MEMORY,
            total_requests=0,
            hits=0,
            misses=0,
            evictions=0,
            size_bytes=0,
            entry_count=0,
            hit_rate=0.0,
            average_access_time_ms=0.0,
            compression_ratio=1.0
        )
        
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache L1"""
        start_time = time.time()
        
        with self.lock:
            self.stats.total_requests += 1
            
            if key in self.entries:
                entry = self.entries[key]
                
                # Vérification d'expiration
                if entry.is_expired():
                    self._remove_entry(key)
                    self.stats.misses += 1
                    return None
                    
                # Mise à jour des statistiques d'accès
                entry.update_access()
                
                # Mise à jour de l'ordre d'accès pour LRU
                if self.strategy == CacheStrategy.LRU:
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.access_order.append(key)
                    
                self.stats.hits += 1
                self._update_stats(time.time() - start_time)
                
                return entry.value
            else:
                self.stats.misses += 1
                self._update_stats(time.time() - start_time)
                return None
                
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None, 
           compression: CompressionType = CompressionType.NONE) -> bool:
        """Stocke une valeur dans le cache L1"""
        with self.lock:
            # Compression et calcul de taille
            compressed_data, original_size = CacheCompressor.compress(value, compression)
            size_bytes = len(compressed_data)
            
            # Vérification de l'espace disponible
            if not self._ensure_space(size_bytes):
                return False
                
            # Création de l'entrée
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                ttl_seconds=ttl_seconds,
                size_bytes=size_bytes,
                compression=compression,
                metadata={"original_size": original_size}
            )
            
            # Suppression de l'ancienne entrée si elle existe
            if key in self.entries:
                self._remove_entry(key)
                
            # Ajout de la nouvelle entrée
            self.entries[key] = entry
            self.access_order.append(key)
            
            # Mise à jour des statistiques
            self.stats.size_bytes += size_bytes
            self.stats.entry_count += 1
            
            return True
            
    def _ensure_space(self, required_bytes: int) -> bool:
        """S'assure qu'il y a assez d'espace"""
        while (self.stats.size_bytes + required_bytes > self.max_size_bytes and 
               self.entries):
            
            if self.strategy == CacheStrategy.LRU:
                # Éviction LRU
                if self.access_order:
                    oldest_key = self.access_order[0]
                    self._remove_entry(oldest_key)
                    self.stats.evictions += 1
                else:
                    break
                    
            elif self.strategy == CacheStrategy.LFU:
                # Éviction LFU
                min_access_key = min(self.entries.keys(), 
                                   key=lambda k: self.entries[k].access_count)
                self._remove_entry(min_access_key)
                self.stats.evictions += 1
                
            else:
                # Éviction par TTL ou première entrée
                if self.access_order:
                    oldest_key = self.access_order[0]
                    self._remove_entry(oldest_key)
                    self.stats.evictions += 1
                else:
                    break
                    
        return self.stats.size_bytes + required_bytes <= self.max_size_bytes
        
    def _remove_entry(self, key: str):
        """Supprime une entrée"""
        if key in self.entries:
            entry = self.entries[key]
            self.stats.size_bytes -= entry.size_bytes
            self.stats.entry_count -= 1
            del self.entries[key]
            
        if key in self.access_order:
            self.access_order.remove(key)
            
    def _update_stats(self, access_time_seconds: float):
        """Met à jour les statistiques"""
        if self.stats.total_requests > 0:
            self.stats.hit_rate = self.stats.hits / self.stats.total_requests
            
        # Moyenne mobile du temps d'accès
        access_time_ms = access_time_seconds * 1000
        if self.stats.average_access_time_ms == 0:
            self.stats.average_access_time_ms = access_time_ms
        else:
            self.stats.average_access_time_ms = (
                self.stats.average_access_time_ms * 0.9 + access_time_ms * 0.1
            )
            
    def clear(self):
        """Vide le cache"""
        with self.lock:
            self.entries.clear()
            self.access_order.clear()
            self.stats.size_bytes = 0
            self.stats.entry_count = 0
            
    def cleanup_expired(self) -> int:
        """Nettoie les entrées expirées"""
        with self.lock:
            expired_keys = []
            for key, entry in self.entries.items():
                if entry.is_expired():
                    expired_keys.append(key)
                    
            for key in expired_keys:
                self._remove_entry(key)
                
            return len(expired_keys)

class L2RedisCache:
    """Cache L2 avec Redis"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 db: int = 0, max_size_mb: int = 1024):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.redis_client = None
        self.available = False
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=host, port=port, db=db, 
                    decode_responses=False,  # Pour gérer les données binaires
                    socket_timeout=1.0
                )
                # Test de connexion
                self.redis_client.ping()
                self.available = True
                logger.info("Cache L2 Redis connecté")
            except Exception as e:
                logger.warning(f"Redis non disponible: {e}")
                self.available = False
        else:
            logger.warning("Redis non installé - cache L2 désactivé")
            
        self.stats = CacheStats(
            level=CacheLevel.L2_REDIS,
            total_requests=0,
            hits=0,
            misses=0,
            evictions=0,
            size_bytes=0,
            entry_count=0,
            hit_rate=0.0,
            average_access_time_ms=0.0,
            compression_ratio=1.0
        )
        
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache L2"""
        if not self.available:
            return None
            
        start_time = time.time()
        self.stats.total_requests += 1
        
        try:
            # Récupération des données et métadonnées
            data = self.redis_client.get(f"data:{key}")
            meta = self.redis_client.get(f"meta:{key}")
            
            if data is not None and meta is not None:
                # Désérialisation des métadonnées
                metadata = json.loads(meta.decode('utf-8'))
                
                # Vérification d'expiration
                if metadata.get('ttl_seconds'):
                    created_at = datetime.fromisoformat(metadata['created_at'])
                    if datetime.now() > created_at + timedelta(seconds=metadata['ttl_seconds']):
                        self.delete(key)
                        self.stats.misses += 1
                        return None
                        
                # Décompression
                compression_type = CompressionType(metadata.get('compression', 'none'))
                value = CacheCompressor.decompress(data, compression_type)
                
                # Mise à jour des statistiques d'accès
                metadata['last_accessed'] = datetime.now().isoformat()
                metadata['access_count'] = metadata.get('access_count', 0) + 1
                
                self.redis_client.set(f"meta:{key}", json.dumps(metadata))
                
                self.stats.hits += 1
                self._update_stats(time.time() - start_time)
                
                return value
            else:
                self.stats.misses += 1
                self._update_stats(time.time() - start_time)
                return None
                
        except Exception as e:
            logger.error(f"Erreur cache L2 get: {e}")
            self.stats.misses += 1
            return None
            
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
           compression: CompressionType = CompressionType.GZIP) -> bool:
        """Stocke une valeur dans le cache L2"""
        if not self.available:
            return False
            
        try:
            # Compression
            compressed_data, original_size = CacheCompressor.compress(value, compression)
            
            # Métadonnées
            metadata = {
                'created_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'access_count': 1,
                'ttl_seconds': ttl_seconds,
                'size_bytes': len(compressed_data),
                'original_size': original_size,
                'compression': compression.value
            }
            
            # Stockage
            pipe = self.redis_client.pipeline()
            pipe.set(f"data:{key}", compressed_data)
            pipe.set(f"meta:{key}", json.dumps(metadata))
            
            if ttl_seconds:
                pipe.expire(f"data:{key}", ttl_seconds)
                pipe.expire(f"meta:{key}", ttl_seconds)
                
            pipe.execute()
            
            # Mise à jour des statistiques
            self.stats.size_bytes += len(compressed_data)
            self.stats.entry_count += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur cache L2 put: {e}")
            return False
            
    def delete(self, key: str) -> bool:
        """Supprime une entrée du cache L2"""
        if not self.available:
            return False
            
        try:
            pipe = self.redis_client.pipeline()
            pipe.delete(f"data:{key}")
            pipe.delete(f"meta:{key}")
            result = pipe.execute()
            
            return any(result)
            
        except Exception as e:
            logger.error(f"Erreur cache L2 delete: {e}")
            return False
            
    def _update_stats(self, access_time_seconds: float):
        """Met à jour les statistiques"""
        if self.stats.total_requests > 0:
            self.stats.hit_rate = self.stats.hits / self.stats.total_requests
            
        access_time_ms = access_time_seconds * 1000
        if self.stats.average_access_time_ms == 0:
            self.stats.average_access_time_ms = access_time_ms
        else:
            self.stats.average_access_time_ms = (
                self.stats.average_access_time_ms * 0.9 + access_time_ms * 0.1
            )

class L3DiskCache:
    """Cache L3 sur disque"""
    
    def __init__(self, cache_dir: str = "./cache_l3", max_size_mb: int = 2048):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.RLock()
        
        self.stats = CacheStats(
            level=CacheLevel.L3_DISK,
            total_requests=0,
            hits=0,
            misses=0,
            evictions=0,
            size_bytes=0,
            entry_count=0,
            hit_rate=0.0,
            average_access_time_ms=0.0,
            compression_ratio=1.0
        )
        
        # Calcul de la taille actuelle
        self._calculate_current_size()
        
    def _calculate_current_size(self):
        """Calcule la taille actuelle du cache"""
        total_size = 0
        entry_count = 0
        
        for file_path in self.cache_dir.glob("*.cache"):
            try:
                total_size += file_path.stat().st_size
                entry_count += 1
            except:
                pass
                
        self.stats.size_bytes = total_size
        self.stats.entry_count = entry_count
        
    def _get_file_path(self, key: str) -> Path:
        """Génère le chemin de fichier pour une clé"""
        # Hash de la clé pour éviter les problèmes de noms de fichiers
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
        
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache L3"""
        start_time = time.time()
        
        with self.lock:
            self.stats.total_requests += 1
            
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                self.stats.misses += 1
                self._update_stats(time.time() - start_time)
                return None
                
            try:
                with open(file_path, 'rb') as f:
                    # Lecture des métadonnées (première ligne)
                    metadata_line = f.readline()
                    metadata = json.loads(metadata_line.decode('utf-8'))
                    
                    # Vérification d'expiration
                    if metadata.get('ttl_seconds'):
                        created_at = datetime.fromisoformat(metadata['created_at'])
                        if datetime.now() > created_at + timedelta(seconds=metadata['ttl_seconds']):
                            file_path.unlink()
                            self.stats.misses += 1
                            self._update_stats(time.time() - start_time)
                            return None
                            
                    # Lecture des données
                    compressed_data = f.read()
                    
                # Décompression
                compression_type = CompressionType(metadata.get('compression', 'gzip'))
                value = CacheCompressor.decompress(compressed_data, compression_type)
                
                # Mise à jour des statistiques d'accès
                metadata['last_accessed'] = datetime.now().isoformat()
                metadata['access_count'] = metadata.get('access_count', 0) + 1
                
                # Réécriture du fichier avec métadonnées mises à jour
                with open(file_path, 'wb') as f:
                    f.write((json.dumps(metadata) + '\n').encode('utf-8'))
                    f.write(compressed_data)
                    
                self.stats.hits += 1
                self._update_stats(time.time() - start_time)
                
                return value
                
            except Exception as e:
                logger.error(f"Erreur lecture cache L3: {e}")
                # Suppression du fichier corrompu
                try:
                    file_path.unlink()
                except:
                    pass
                self.stats.misses += 1
                self._update_stats(time.time() - start_time)
                return None
                
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
           compression: CompressionType = CompressionType.GZIP) -> bool:
        """Stocke une valeur dans le cache L3"""
        with self.lock:
            try:
                # Compression
                compressed_data, original_size = CacheCompressor.compress(value, compression)
                
                # Métadonnées
                metadata = {
                    'key': key,
                    'created_at': datetime.now().isoformat(),
                    'last_accessed': datetime.now().isoformat(),
                    'access_count': 1,
                    'ttl_seconds': ttl_seconds,
                    'size_bytes': len(compressed_data),
                    'original_size': original_size,
                    'compression': compression.value
                }
                
                metadata_bytes = (json.dumps(metadata) + '\n').encode('utf-8')
                total_size = len(metadata_bytes) + len(compressed_data)
                
                # Vérification de l'espace
                if not self._ensure_space(total_size):
                    return False
                    
                # Écriture du fichier
                file_path = self._get_file_path(key)
                with open(file_path, 'wb') as f:
                    f.write(metadata_bytes)
                    f.write(compressed_data)
                    
                # Mise à jour des statistiques
                self.stats.size_bytes += total_size
                self.stats.entry_count += 1
                
                return True
                
            except Exception as e:
                logger.error(f"Erreur écriture cache L3: {e}")
                return False
                
    def _ensure_space(self, required_bytes: int) -> bool:
        """S'assure qu'il y a assez d'espace"""
        while (self.stats.size_bytes + required_bytes > self.max_size_bytes):
            # Éviction LRU basée sur la date de dernier accès
            oldest_file = None
            oldest_time = datetime.now()
            
            for file_path in self.cache_dir.glob("*.cache"):
                try:
                    with open(file_path, 'rb') as f:
                        metadata_line = f.readline()
                        metadata = json.loads(metadata_line.decode('utf-8'))
                        last_accessed = datetime.fromisoformat(metadata['last_accessed'])
                        
                        if last_accessed < oldest_time:
                            oldest_time = last_accessed
                            oldest_file = file_path
                except:
                    # Fichier corrompu, le marquer pour suppression
                    oldest_file = file_path
                    break
                    
            if oldest_file:
                try:
                    file_size = oldest_file.stat().st_size
                    oldest_file.unlink()
                    self.stats.size_bytes -= file_size
                    self.stats.entry_count -= 1
                    self.stats.evictions += 1
                except:
                    pass
            else:
                break
                
        return self.stats.size_bytes + required_bytes <= self.max_size_bytes
        
    def _update_stats(self, access_time_seconds: float):
        """Met à jour les statistiques"""
        if self.stats.total_requests > 0:
            self.stats.hit_rate = self.stats.hits / self.stats.total_requests
            
        access_time_ms = access_time_seconds * 1000
        if self.stats.average_access_time_ms == 0:
            self.stats.average_access_time_ms = access_time_ms
        else:
            self.stats.average_access_time_ms = (
                self.stats.average_access_time_ms * 0.9 + access_time_ms * 0.1
            )

class MultilevelCache:
    """Cache intelligent multi-niveaux"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "l1_size_mb": 256,
            "l2_size_mb": 1024,
            "l3_size_mb": 2048,
            "l1_strategy": CacheStrategy.LRU,
            "default_ttl_seconds": 3600,
            "compression_enabled": True,
            "auto_promotion": True,
            "cleanup_interval_seconds": 300
        }
        
        # Initialisation des niveaux de cache
        self.l1_cache = L1MemoryCache(
            max_size_mb=self.config["l1_size_mb"],
            strategy=self.config.get("l1_strategy", CacheStrategy.LRU)
        )
        
        self.l2_cache = L2RedisCache(
            max_size_mb=self.config["l2_size_mb"]
        )
        
        self.l3_cache = L3DiskCache(
            max_size_mb=self.config["l3_size_mb"]
        )
        
        # Statistiques globales
        self.global_stats = {
            "total_requests": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "total_misses": 0,
            "promotions": 0,
            "average_latency_ms": 0.0
        }
        
        # Thread de nettoyage
        self.cleanup_thread = None
        self.running = False
        
        logger.info("MultilevelCache initialisé")
        
    def start_cleanup_thread(self):
        """Démarre le thread de nettoyage automatique"""
        if self.cleanup_thread is None or not self.cleanup_thread.is_alive():
            self.running = True
            self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self.cleanup_thread.start()
            logger.info("Thread de nettoyage démarré")
            
    def stop_cleanup_thread(self):
        """Arrête le thread de nettoyage"""
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
            logger.info("Thread de nettoyage arrêté")
            
    def _cleanup_worker(self):
        """Worker de nettoyage automatique"""
        while self.running:
            try:
                # Nettoyage des entrées expirées
                expired_l1 = self.l1_cache.cleanup_expired()
                if expired_l1 > 0:
                    logger.info(f"Nettoyage L1: {expired_l1} entrées expirées")
                    
                time.sleep(self.config["cleanup_interval_seconds"])
                
            except Exception as e:
                logger.error(f"Erreur nettoyage: {e}")
                time.sleep(60)  # Attendre 1 minute en cas d'erreur
                
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache multi-niveaux"""
        start_time = time.time()
        self.global_stats["total_requests"] += 1
        
        # Tentative L1 (mémoire)
        value = self.l1_cache.get(key)
        if value is not None:
            self.global_stats["l1_hits"] += 1
            self._update_global_stats(time.time() - start_time)
            return value
            
        # Tentative L2 (Redis)
        value = self.l2_cache.get(key)
        if value is not None:
            self.global_stats["l2_hits"] += 1
            
            # Promotion vers L1 si activée
            if self.config["auto_promotion"]:
                self.l1_cache.put(key, value, compression=CompressionType.NONE)
                self.global_stats["promotions"] += 1
                
            self._update_global_stats(time.time() - start_time)
            return value
            
        # Tentative L3 (disque)
        value = self.l3_cache.get(key)
        if value is not None:
            self.global_stats["l3_hits"] += 1
            
            # Promotion vers L2 et L1 si activée
            if self.config["auto_promotion"]:
                if self.l2_cache.available:
                    self.l2_cache.put(key, value, compression=CompressionType.GZIP)
                self.l1_cache.put(key, value, compression=CompressionType.NONE)
                self.global_stats["promotions"] += 1
                
            self._update_global_stats(time.time() - start_time)
            return value
            
        # Aucun cache n'a la valeur
        self.global_stats["total_misses"] += 1
        self._update_global_stats(time.time() - start_time)
        return None
        
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache multi-niveaux"""
        if ttl_seconds is None:
            ttl_seconds = self.config["default_ttl_seconds"]
            
        success = True
        
        # Stockage dans tous les niveaux
        # L1: sans compression pour la vitesse
        if not self.l1_cache.put(key, value, ttl_seconds, CompressionType.NONE):
            success = False
            
        # L2: avec compression
        if self.l2_cache.available:
            if not self.l2_cache.put(key, value, ttl_seconds, CompressionType.GZIP):
                success = False
                
        # L3: avec compression maximale
        if not self.l3_cache.put(key, value, ttl_seconds, CompressionType.GZIP):
            success = False
            
        return success
        
    def delete(self, key: str) -> bool:
        """Supprime une valeur de tous les niveaux de cache"""
        success = True
        
        # Suppression de L1
        with self.l1_cache.lock:
            if key in self.l1_cache.entries:
                self.l1_cache._remove_entry(key)
            else:
                success = False
                
        # Suppression de L2
        if self.l2_cache.available:
            if not self.l2_cache.delete(key):
                success = False
                
        # Suppression de L3
        file_path = self.l3_cache._get_file_path(key)
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                success = False
        else:
            success = False
            
        return success
        
    def _update_global_stats(self, access_time_seconds: float):
        """Met à jour les statistiques globales"""
        access_time_ms = access_time_seconds * 1000
        
        if self.global_stats["average_latency_ms"] == 0:
            self.global_stats["average_latency_ms"] = access_time_ms
        else:
            self.global_stats["average_latency_ms"] = (
                self.global_stats["average_latency_ms"] * 0.9 + access_time_ms * 0.1
            )
            
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes du cache"""
        total_requests = self.global_stats["total_requests"]
        
        if total_requests == 0:
            return {
                "global": self.global_stats,
                "l1": asdict(self.l1_cache.stats),
                "l2": asdict(self.l2_cache.stats),
                "l3": asdict(self.l3_cache.stats)
            }
            
        # Calcul des taux de hit par niveau
        l1_hit_rate = self.global_stats["l1_hits"] / total_requests
        l2_hit_rate = self.global_stats["l2_hits"] / total_requests
        l3_hit_rate = self.global_stats["l3_hits"] / total_requests
        total_hit_rate = (l1_hit_rate + l2_hit_rate + l3_hit_rate)
        
        global_stats = self.global_stats.copy()
        global_stats.update({
            "l1_hit_rate": l1_hit_rate,
            "l2_hit_rate": l2_hit_rate,
            "l3_hit_rate": l3_hit_rate,
            "total_hit_rate": total_hit_rate,
            "miss_rate": self.global_stats["total_misses"] / total_requests
        })
        
        return {
            "global": global_stats,
            "l1": asdict(self.l1_cache.stats),
            "l2": asdict(self.l2_cache.stats),
            "l3": asdict(self.l3_cache.stats)
        }
        
    def get_cache_health(self) -> Dict[str, Any]:
        """Évalue la santé du cache"""
        stats = self.get_cache_statistics()
        global_stats = stats["global"]
        
        health = {
            "overall_health": "unknown",
            "hit_rate_health": "unknown",
            "latency_health": "unknown",
            "capacity_health": "unknown",
            "recommendations": []
        }
        
        if global_stats["total_requests"] == 0:
            health["overall_health"] = "no_data"
            return health
            
        # Évaluation du taux de hit
        total_hit_rate = global_stats["total_hit_rate"]
        if total_hit_rate >= 0.8:
            health["hit_rate_health"] = "excellent"
        elif total_hit_rate >= 0.6:
            health["hit_rate_health"] = "good"
        elif total_hit_rate >= 0.4:
            health["hit_rate_health"] = "fair"
        else:
            health["hit_rate_health"] = "poor"
            health["recommendations"].append("Augmenter la taille du cache ou réviser la stratégie")
            
        # Évaluation de la latence
        avg_latency = global_stats["average_latency_ms"]
        if avg_latency <= 1.0:
            health["latency_health"] = "excellent"
        elif avg_latency <= 5.0:
            health["latency_health"] = "good"
        elif avg_latency <= 10.0:
            health["latency_health"] = "fair"
        else:
            health["latency_health"] = "poor"
            health["recommendations"].append("Optimiser les performances du cache")
            
        # Évaluation de la capacité
        l1_usage = stats["l1"]["size_bytes"] / self.l1_cache.max_size_bytes
        if l1_usage <= 0.8:
            health["capacity_health"] = "good"
        elif l1_usage <= 0.95:
            health["capacity_health"] = "warning"
            health["recommendations"].append("Surveiller l'usage mémoire L1")
        else:
            health["capacity_health"] = "critical"
            health["recommendations"].append("Augmenter la taille du cache L1")
            
        # Santé globale
        health_scores = {
            "excellent": 4, "good": 3, "fair": 2, "poor": 1, "critical": 0, "warning": 2
        }
        
        avg_health = (
            health_scores.get(health["hit_rate_health"], 0) +
            health_scores.get(health["latency_health"], 0) +
            health_scores.get(health["capacity_health"], 0)
        ) / 3
        
        if avg_health >= 3.5:
            health["overall_health"] = "excellent"
        elif avg_health >= 2.5:
            health["overall_health"] = "good"
        elif avg_health >= 1.5:
            health["overall_health"] = "fair"
        else:
            health["overall_health"] = "poor"
            
        return health
        
    def export_data(self, output_path: str) -> Dict[str, Any]:
        """Exporte les données du cache"""
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "cache_version": "3.0.0",
                "objective": "Objectif 12 - Cache intelligent multi-niveaux"
            },
            "configuration": self.config,
            "statistics": self.get_cache_statistics(),
            "health": self.get_cache_health()
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
            return {
                "success": True,
                "file_path": output_path,
                "cache_levels": 3,
                "total_requests": self.global_stats["total_requests"]
            }
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def main():
    """Fonction principale de démonstration"""
    print("🗄️ Multilevel Cache - Objectif 12")
    print("Cache intelligent multi-niveaux (L1/L2/L3)")
    print("=" * 50)
    
    # Initialisation
    cache = MultilevelCache({
        "l1_size_mb": 64,  # Réduit pour la démo
        "l2_size_mb": 128,
        "l3_size_mb": 256,
        "default_ttl_seconds": 1800,
        "compression_enabled": True,
        "auto_promotion": True
    })
    
    # Démarrage du nettoyage automatique
    cache.start_cleanup_thread()
    
    # Données de test
    test_data = {
        "patient_001": {
            "nom": "Dupont",
            "diagnostic": "Hypertension artérielle",
            "traitement": "Amlodipine 5mg",
            "notes": "Patient suivi depuis 2 ans, bon contrôle tensionnel"
        },
        "protocole_paludisme": {
            "pathologie": "Paludisme à P. falciparum",
            "traitement_premiere_ligne": "Artemether-Lumefantrine",
            "posologie": "20mg/120mg, 6 comprimés sur 3 jours",
            "surveillance": "Contrôle à J3, J7, J14"
        },
        "guidelines_covid": {
            "version": "2024.1",
            "symptomes": ["fièvre", "toux", "dyspnée", "anosmie"],
            "diagnostic": "Test antigénique ou PCR",
            "isolement": "7 jours minimum"
        }
    }
    
    print(f"\n💾 Test de stockage de {len(test_data)} éléments...")
    
    # Test de stockage
    for key, value in test_data.items():
        success = cache.put(key, value, ttl_seconds=3600)
        print(f"Stockage {key}: {'✅' if success else '❌'}")
        
    # Test de récupération
    print("\n🔍 Test de récupération...")
    
    for key in test_data.keys():
        start_time = time.time()
        value = cache.get(key)
        latency = (time.time() - start_time) * 1000
        
        if value:
            print(f"✅ {key}: {latency:.2f}ms")
        else:
            print(f"❌ {key}: non trouvé")
            
    # Test de performance avec données répétées
    print("\n⚡ Test de performance (accès répétés)...")
    
    performance_results = []
    test_key = "patient_001"
    
    for i in range(10):
        start_time = time.time()
        value = cache.get(test_key)
        latency = (time.time() - start_time) * 1000
        performance_results.append(latency)
        
    avg_latency = sum(performance_results) / len(performance_results)
    min_latency = min(performance_results)
    max_latency = max(performance_results)
    
    print(f"Latence moyenne: {avg_latency:.2f}ms")
    print(f"Latence min/max: {min_latency:.2f}ms / {max_latency:.2f}ms")
    
    # Statistiques détaillées
    print("\n📊 Statistiques du cache...")
    stats = cache.get_cache_statistics()
    
    global_stats = stats["global"]
    print(f"Requêtes totales: {global_stats['total_requests']}")
    print(f"Taux de hit L1: {global_stats.get('l1_hit_rate', 0):.2%}")
    print(f"Taux de hit L2: {global_stats.get('l2_hit_rate', 0):.2%}")
    print(f"Taux de hit L3: {global_stats.get('l3_hit_rate', 0):.2%}")
    print(f"Taux de hit total: {global_stats.get('total_hit_rate', 0):.2%}")
    print(f"Promotions: {global_stats['promotions']}")
    
    # Détails par niveau
    print("\nDétails par niveau:")
    for level in ["l1", "l2", "l3"]:
        level_stats = stats[level]
        print(f"  {level.upper()}: {level_stats['entry_count']} entrées, "
              f"{level_stats['size_bytes']/1024:.1f}KB, "
              f"hit rate {level_stats['hit_rate']:.2%}")
              
    # Santé du cache
    print("\n🏥 Santé du cache...")
    health = cache.get_cache_health()
    print(f"Santé globale: {health['overall_health']}")
    print(f"Santé hit rate: {health['hit_rate_health']}")
    print(f"Santé latence: {health['latency_health']}")
    print(f"Santé capacité: {health['capacity_health']}")
    
    if health["recommendations"]:
        print("Recommandations:")
        for rec in health["recommendations"]:
            print(f"  • {rec}")
    else:
        print("✅ Aucune recommandation - cache optimal")
        
    # Test de suppression
    print("\n🗑️ Test de suppression...")
    test_delete_key = "patient_001"
    success = cache.delete(test_delete_key)
    print(f"Suppression {test_delete_key}: {'✅' if success else '❌'}")
    
    # Vérification de la suppression
    value = cache.get(test_delete_key)
    print(f"Vérification suppression: {'✅ Supprimé' if value is None else '❌ Encore présent'}")
    
    # Export des données
    print("\n💾 Export des données...")
    export_result = cache.export_data("multilevel_cache_export.json")
    if export_result["success"]:
        print(f"Données exportées: {export_result['cache_levels']} niveaux")
        print(f"Requêtes totales: {export_result['total_requests']}")
        
    # Arrêt du nettoyage
    cache.stop_cleanup_thread()
    
    # Évaluation finale
    final_stats = cache.get_cache_statistics()
    final_hit_rate = final_stats["global"].get("total_hit_rate", 0)
    final_latency = final_stats["global"]["average_latency_ms"]
    
    print("\n🎯 Évaluation finale:")
    if final_hit_rate >= 0.8 and final_latency <= 5.0:
        print("✅ Objectif 12 ATTEINT - Cache multi-niveaux performant!")
    elif final_hit_rate >= 0.6:
        print("⚠️ Objectif partiellement atteint - Optimisations possibles")
    else:
        print("❌ Objectif non atteint - Révision de la stratégie nécessaire")
        
    print(f"📊 Taux de hit final: {final_hit_rate:.1%}")
    print(f"⚡ Latence moyenne: {final_latency:.2f}ms")
    print(f"🗄️ Cache multi-niveaux opérationnel avec {len(stats)} niveaux")

if __name__ == "__main__":
    main()