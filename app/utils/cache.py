import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class CacheManager:
    def __init__(self):
        self.redis_client = None
        self.default_ttl = settings.cache_ttl
    
    async def initialize(self):
        """Initialise la connexion Redis"""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
            logger.info("Cache manager initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize cache manager", error=str(e))
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        try:
            if not self.redis_client:
                return None
                
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value.decode('utf-8'))
            return None
        except Exception as e:
            logger.warning("Cache get error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache"""
        try:
            if not self.redis_client:
                return False
                
            serialized_value = json.dumps(value, default=str)
            ttl = ttl or self.default_ttl
            
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.warning("Cache set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Supprime une clé du cache"""
        try:
            if not self.redis_client:
                return False
                
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete error", key=key, error=str(e))
            return False
    
    async def clear_all(self) -> bool:
        """Vide tout le cache"""
        try:
            if not self.redis_client:
                return False
                
            await self.redis_client.flushdb()
            return True
        except Exception as e:
            logger.error("Cache clear error", error=str(e))
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé du cache"""
        try:
            if not self.redis_client:
                return {"status": "disconnected", "available": False}
            
            await self.redis_client.ping()
            info = await self.redis_client.info()
            
            return {
                "status": "connected",
                "available": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "status": "error",
                "available": False,
                "error": str(e)
            }

# Instance globale
cache_manager = CacheManager()