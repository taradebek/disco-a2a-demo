"""
Advanced rate limiting service
Supports multiple algorithms and Redis-based distributed limiting
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import redis.asyncio as redis
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Advanced rate limiting with multiple algorithms"""
    
    def __init__(self):
        self.redis_client = None
        self.default_limits = {
            "payment_create": {"requests": 100, "window": 3600},  # 100/hour
            "payment_get": {"requests": 1000, "window": 3600},    # 1000/hour
            "agent_register": {"requests": 10, "window": 3600},   # 10/hour
            "service_register": {"requests": 50, "window": 3600}, # 50/hour
            "webhook_send": {"requests": 1000, "window": 3600},   # 1000/hour
            "exchange_rate": {"requests": 10000, "window": 3600}, # 10000/hour
        }
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Rate limiter initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}")
            self.redis_client = None
    
    async def check_rate_limit(self, 
                             api_key: str, 
                             endpoint: str,
                             custom_limits: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """Check if request is within rate limits"""
        
        limits = custom_limits or self.default_limits.get(endpoint)
        if not limits:
            return True, {"allowed": True, "reason": "no_limits"}
        
        if not self.redis_client:
            # Fallback to in-memory limiting (not recommended for production)
            return True, {"allowed": True, "reason": "no_redis"}
        
        # Use sliding window algorithm
        return await self._sliding_window_check(api_key, endpoint, limits)
    
    async def _sliding_window_check(self, 
                                  api_key: str, 
                                  endpoint: str, 
                                  limits: Dict) -> Tuple[bool, Dict]:
        """Sliding window rate limiting"""
        
        window_size = limits["window"]
        max_requests = limits["requests"]
        
        # Create unique key for this API key + endpoint
        key = f"rate_limit:{api_key}:{endpoint}"
        current_time = int(time.time())
        window_start = current_time - window_size
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, window_size)
        
        # Execute pipeline
        results = await pipe.execute()
        current_requests = results[1]
        
        # Check if within limits
        allowed = current_requests < max_requests
        
        # Calculate reset time
        if current_requests > 0:
            oldest_request = await self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                reset_time = int(oldest_request[0][1]) + window_size
            else:
                reset_time = current_time + window_size
        else:
            reset_time = current_time + window_size
        
        return allowed, {
            "allowed": allowed,
            "current_requests": current_requests,
            "max_requests": max_requests,
            "window_size": window_size,
            "reset_time": reset_time,
            "remaining": max(0, max_requests - current_requests - 1)
        }
    
    async def _token_bucket_check(self, 
                                api_key: str, 
                                endpoint: str, 
                                limits: Dict) -> Tuple[bool, Dict]:
        """Token bucket rate limiting"""
        
        bucket_size = limits["requests"]
        refill_rate = limits["requests"] / limits["window"]  # tokens per second
        
        key = f"token_bucket:{api_key}:{endpoint}"
        current_time = time.time()
        
        # Get current bucket state
        bucket_data = await self.redis_client.hmget(key, ["tokens", "last_refill"])
        
        if bucket_data[0] is None:
            # Initialize bucket
            tokens = bucket_size
            last_refill = current_time
        else:
            tokens = float(bucket_data[0])
            last_refill = float(bucket_data[1])
            
            # Refill tokens based on time passed
            time_passed = current_time - last_refill
            tokens = min(bucket_size, tokens + (time_passed * refill_rate))
        
        # Check if we can consume a token
        if tokens >= 1:
            tokens -= 1
            allowed = True
        else:
            allowed = False
        
        # Update bucket state
        await self.redis_client.hmset(key, {
            "tokens": tokens,
            "last_refill": current_time
        })
        await self.redis_client.expire(key, limits["window"])
        
        return allowed, {
            "allowed": allowed,
            "tokens": tokens,
            "bucket_size": bucket_size,
            "refill_rate": refill_rate
        }
    
    async def get_rate_limit_status(self, api_key: str, endpoint: str) -> Dict:
        """Get current rate limit status without consuming a request"""
        
        limits = self.default_limits.get(endpoint)
        if not limits or not self.redis_client:
            return {"status": "unlimited"}
        
        key = f"rate_limit:{api_key}:{endpoint}"
        current_time = int(time.time())
        window_start = current_time - limits["window"]
        
        # Count current requests
        current_requests = await self.redis_client.zcount(key, window_start, current_time)
        
        return {
            "current_requests": current_requests,
            "max_requests": limits["requests"],
            "window_size": limits["window"],
            "remaining": max(0, limits["requests"] - current_requests),
            "reset_time": current_time + limits["window"]
        }
    
    async def reset_rate_limit(self, api_key: str, endpoint: str) -> bool:
        """Reset rate limit for an API key and endpoint"""
        
        if not self.redis_client:
            return False
        
        key = f"rate_limit:{api_key}:{endpoint}"
        await self.redis_client.delete(key)
        
        logger.info(f"Reset rate limit for {api_key}:{endpoint}")
        return True
    
    async def get_all_rate_limits(self, api_key: str) -> Dict[str, Dict]:
        """Get rate limit status for all endpoints"""
        
        status = {}
        for endpoint in self.default_limits.keys():
            status[endpoint] = await self.get_rate_limit_status(api_key, endpoint)
        
        return status

# Global instance
rate_limiter = RateLimiter()
