"""
Security and Authentication
API key validation, rate limiting, and security measures
"""

import hashlib
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis

from disco_backend.database.connection import get_db, get_redis
from disco_backend.database.models import APIKey
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

class SecurityError(Exception):
    """Base security exception"""
    pass

class RateLimitError(SecurityError):
    """Rate limit exceeded"""
    pass

class InvalidAPIKeyError(SecurityError):
    """Invalid API key"""
    pass

def generate_api_key(environment: str = "test") -> tuple[str, str]:
    """Generate a new API key pair (public key, secret hash)"""
    # Generate random key
    key_suffix = secrets.token_urlsafe(32)
    
    # Create full key with prefix
    prefix = settings.API_KEY_PREFIX_LIVE if environment == "live" else settings.API_KEY_PREFIX_TEST
    full_key = f"{prefix}{key_suffix}"
    
    # Hash the key for storage
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    return full_key, key_hash

def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

async def get_api_key_from_db(key_hash: str, db: AsyncSession) -> Optional[APIKey]:
    """Get API key from database by hash"""
    stmt = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def update_api_key_usage(api_key: APIKey, db: AsyncSession):
    """Update API key usage statistics"""
    stmt = update(APIKey).where(
        APIKey.id == api_key.id
    ).values(
        last_used_at=datetime.utcnow(),
        request_count=APIKey.request_count + 1
    )
    await db.execute(stmt)

async def check_rate_limit(
    api_key: APIKey, 
    request: Request, 
    redis_client: redis.Redis
) -> bool:
    """Check if request is within rate limits"""
    # Create rate limit key
    client_ip = request.client.host
    rate_key = f"rate_limit:{api_key.key_id}:{client_ip}"
    
    # Get current request count
    current_requests = await redis_client.get(rate_key)
    
    if current_requests is None:
        # First request in this minute
        await redis_client.setex(rate_key, 60, 1)
        return True
    
    current_count = int(current_requests)
    
    # Check if over limit
    if current_count >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
        # Check if we can allow burst
        burst_key = f"rate_burst:{api_key.key_id}:{client_ip}"
        burst_requests = await redis_client.get(burst_key)
        
        if burst_requests is None:
            burst_count = 0
        else:
            burst_count = int(burst_requests)
        
        if burst_count >= settings.RATE_LIMIT_BURST:
            logger.warning(f"Rate limit exceeded for API key {api_key.key_id} from {client_ip}")
            return False
        
        # Allow burst, but track it
        await redis_client.setex(burst_key, 3600, burst_count + 1)  # Track for 1 hour
    
    # Increment request count
    await redis_client.incr(rate_key)
    return True

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> APIKey:
    """Verify API key and return associated key object"""
    
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    # Validate API key format
    if not (api_key.startswith(settings.API_KEY_PREFIX_LIVE) or 
            api_key.startswith(settings.API_KEY_PREFIX_TEST)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Hash the key
    key_hash = hash_api_key(api_key)
    
    # Get from database
    api_key_obj = await get_api_key_from_db(key_hash, db)
    if not api_key_obj:
        logger.warning(f"Invalid API key used: {api_key[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check rate limits
    if not await check_rate_limit(api_key_obj, request, redis_client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS_PER_MINUTE),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    # Update usage statistics
    await update_api_key_usage(api_key_obj, db)
    
    # Add to request state for use in endpoints
    request.state.api_key = api_key_obj
    request.state.environment = api_key_obj.environment
    
    logger.info(f"API key authenticated: {api_key_obj.key_id}")
    return api_key_obj

def require_live_environment(api_key: APIKey = Depends(verify_api_key)):
    """Require live environment API key"""
    if api_key.environment != "live":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live environment API key required for this operation"
        )
    return api_key

def require_test_environment(api_key: APIKey = Depends(verify_api_key)):
    """Require test environment API key"""
    if api_key.environment != "test":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test environment API key required for this operation"
        )
    return api_key

async def create_api_key(
    name: str,
    description: str,
    environment: str,
    permissions: Dict[str, Any],
    db: AsyncSession
) -> tuple[str, APIKey]:
    """Create a new API key"""
    
    # Generate key pair
    public_key, key_hash = generate_api_key(environment)
    
    # Create key ID (first 8 chars of hash)
    key_id = key_hash[:8]
    
    # Create database record
    api_key = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        environment=environment,
        name=name,
        description=description,
        permissions=permissions,
        is_active=True
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    logger.info(f"Created API key: {key_id} for environment: {environment}")
    return public_key, api_key

async def revoke_api_key(key_id: str, db: AsyncSession) -> bool:
    """Revoke an API key"""
    stmt = update(APIKey).where(
        APIKey.key_id == key_id
    ).values(
        is_active=False
    )
    result = await db.execute(stmt)
    await db.commit()
    
    if result.rowcount > 0:
        logger.info(f"Revoked API key: {key_id}")
        return True
    return False

class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response 