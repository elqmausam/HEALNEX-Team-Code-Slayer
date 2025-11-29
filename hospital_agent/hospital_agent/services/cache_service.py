# hospital_agent/services/cache_service.py
"""
High-performance Redis cache service with connection pooling
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service with connection pooling"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            self.connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                max_connections=settings.CACHE_MAX_CONNECTIONS,
                decode_responses=True
            )
            
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
    
    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            return await self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        try:
            if ttl:
                await self.redis_client.setex(key, ttl, value)
            else:
                await self.redis_client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str) -> int:
        """Increment counter"""
        try:
            return await self.redis_client.incr(key)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    async def get_many(self, keys: list) -> dict:
        """Get multiple keys at once"""
        try:
            values = await self.redis_client.mget(keys)
            return dict(zip(keys, values))
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set JSON serializable object"""
        return await self.set(key, json.dumps(value), ttl)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON object"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON for key {key}")
        return None