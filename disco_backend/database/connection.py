"""
Database Connection Management
PostgreSQL with SQLAlchemy and asyncpg
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
import redis.asyncio as redis

from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""
    pass

# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    poolclass=NullPool if settings.is_development else None,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Redis connection
redis_client: redis.Redis = None

async def init_database():
    """Initialize database connections"""
    global redis_client
    
    # Initialize Redis
    redis_client = redis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_POOL_SIZE,
        decode_responses=True
    )
    
    # Test connections
    async with engine.begin() as conn:
        logger.info("✅ PostgreSQL connection established")
    
    await redis_client.ping()
    logger.info("✅ Redis connection established")

async def close_database():
    """Close database connections"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("✅ Redis connection closed")
    
    await engine.dispose()
    logger.info("✅ PostgreSQL connection closed")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_redis() -> redis.Redis:
    """Redis client dependency"""
    return redis_client 