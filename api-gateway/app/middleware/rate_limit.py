import time
import redis
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import hashlib

from ..config import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app):
        super().__init__(app)
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for rate limiting")
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Rate limiting disabled.")
            self.redis_client = None
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Skip if Redis is not available
        if not self.redis_client:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_id(request)
        
        # Check rate limit
        if not self.is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.get_remaining_requests(client_id)
        reset_time = self.get_reset_time(client_id)
        
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Use IP address as primary identifier
        client_ip = request.client.host
        
        # Add user agent for better fingerprinting
        user_agent = request.headers.get("user-agent", "")
        
        # Create hash for privacy
        identifier = f"{client_ip}:{user_agent}"
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request"""
        try:
            key = f"rate_limit:{client_id}"
            current_time = int(time.time())
            window_start = current_time - settings.RATE_LIMIT_WINDOW
            
            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_requests = self.redis_client.zcard(key)
            
            if current_requests >= settings.RATE_LIMIT_REQUESTS:
                return False
            
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            
            # Set expiry for cleanup
            self.redis_client.expire(key, settings.RATE_LIMIT_WINDOW)
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Allow request if Redis fails
            return True
    
    def get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client"""
        try:
            key = f"rate_limit:{client_id}"
            current_time = int(time.time())
            window_start = current_time - settings.RATE_LIMIT_WINDOW
            
            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_requests = self.redis_client.zcard(key)
            
            return max(0, settings.RATE_LIMIT_REQUESTS - current_requests)
            
        except Exception as e:
            logger.error(f"Error getting remaining requests: {e}")
            return settings.RATE_LIMIT_REQUESTS
    
    def get_reset_time(self, client_id: str) -> int:
        """Get reset time for rate limit window"""
        try:
            key = f"rate_limit:{client_id}"
            
            # Get oldest request in current window
            oldest_requests = self.redis_client.zrange(key, 0, 0, withscores=True)
            
            if oldest_requests:
                oldest_time = int(oldest_requests[0][1])
                return oldest_time + settings.RATE_LIMIT_WINDOW
            else:
                return int(time.time()) + settings.RATE_LIMIT_WINDOW
                
        except Exception as e:
            logger.error(f"Error getting reset time: {e}")
            return int(time.time()) + settings.RATE_LIMIT_WINDOW