import redis
import json
import logging
from typing import Any, Optional, Union
from datetime import timedelta

from ..config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis cache manager for the feedback API"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Caching disabled.")
            self.redis_client = None
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage in Redis"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (int, float, bool)):
            return str(value)
        else:
            return str(value)
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis storage"""
        if not value:
            return None
        
        try:
            # Try to parse as JSON first
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Return as string if not JSON
            return value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set a value in cache with optional TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds or timedelta object
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            serialized_value = self._serialize_value(value)
            
            if ttl is None:
                ttl = settings.CACHE_TTL
            elif isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            result = self.redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"Cached key '{key}' with TTL {ttl}s")
            return result
        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {e}")
            return False
    
    def get(self, key: str) -> Any:
        """
        Get a value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/error
        """
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is not None:
                logger.debug(f"Cache hit for key '{key}'")
                return self._deserialize_value(value)
            else:
                logger.debug(f"Cache miss for key '{key}'")
                return None
        except Exception as e:
            logger.error(f"Error getting cache key '{key}': {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"Deleted cache key '{key}'")
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Error checking cache key '{key}': {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in cache
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment or None if error
        """
        if not self.redis_client:
            return None
        
        try:
            result = self.redis_client.incrby(key, amount)
            logger.debug(f"Incremented cache key '{key}' by {amount}")
            return result
        except Exception as e:
            logger.error(f"Error incrementing cache key '{key}': {e}")
            return None
    
    def set_hash(self, key: str, mapping: dict, ttl: Optional[int] = None) -> bool:
        """
        Set multiple fields in a hash
        
        Args:
            key: Hash key
            mapping: Dictionary of field-value pairs
            ttl: Optional TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            # Serialize all values in the mapping
            serialized_mapping = {
                field: self._serialize_value(value) 
                for field, value in mapping.items()
            }
            
            self.redis_client.hset(key, mapping=serialized_mapping)
            
            if ttl:
                self.redis_client.expire(key, ttl)
            
            logger.debug(f"Set hash '{key}' with {len(mapping)} fields")
            return True
        except Exception as e:
            logger.error(f"Error setting hash '{key}': {e}")
            return False
    
    def get_hash(self, key: str, field: Optional[str] = None) -> Any:
        """
        Get field(s) from a hash
        
        Args:
            key: Hash key
            field: Specific field to get (if None, gets all fields)
            
        Returns:
            Field value, dict of all fields, or None
        """
        if not self.redis_client:
            return None
        
        try:
            if field:
                value = self.redis_client.hget(key, field)
                return self._deserialize_value(value) if value else None
            else:
                hash_data = self.redis_client.hgetall(key)
                return {
                    k: self._deserialize_value(v) 
                    for k, v in hash_data.items()
                } if hash_data else None
        except Exception as e:
            logger.error(f"Error getting hash '{key}': {e}")
            return None
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern
        
        Args:
            pattern: Redis pattern (e.g., "user:*", "stats:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} keys matching pattern '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error invalidating pattern '{pattern}': {e}")
            return 0
    
    def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.redis_client:
            return {"status": "disabled"}
        
        try:
            info = self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}


# Global cache instance
cache = CacheManager()


def cache_key(*args: str) -> str:
    """
    Generate a cache key from multiple parts
    
    Args:
        *args: Parts to join for the cache key
        
    Returns:
        Formatted cache key
    """
    return ":".join(str(arg) for arg in args)


def cached_result(key_prefix: str, ttl: int = None):
    """
    Decorator to cache function results
    
    Args:
        key_prefix: Prefix for the cache key
        ttl: Time to live in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            
            # Add positional arguments to key
            if args:
                key_parts.extend(str(arg) for arg in args)
            
            # Add keyword arguments to key
            if kwargs:
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key_str = cache_key(*key_parts)
            
            # Try to get from cache first
            result = cache.get(cache_key_str)
            if result is not None:
                logger.debug(f"Cache hit for function {func.__name__}")
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key_str, result, ttl)
            
            logger.debug(f"Cached result for function {func.__name__}")
            return result
        
        return wrapper
    return decorator