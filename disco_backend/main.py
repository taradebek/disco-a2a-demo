"""
Disco Backend - Main FastAPI Application
Production-ready x402 crypto payment API
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from disco_backend.api.payments import router as payments_router
from disco_backend.api.agents import router as agents_router
from disco_backend.api.services import router as services_router
from disco_backend.api.wallets import router as wallets_router
from disco_backend.api.x402 import router as x402_router
from disco_backend.database.connection import init_database, close_database
from disco_backend.core.config import settings
from disco_backend.core.security import verify_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🕺 Starting Disco Backend API...")
    await init_database()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Disco Backend API...")
    await close_database()
    logger.info("✅ Database connections closed")

# Create FastAPI app
app = FastAPI(
    title="Disco API",
    description="x402-enabled crypto payment infrastructure for AI agents",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(
    payments_router,
    prefix="/v1/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    agents_router,
    prefix="/v1/agents",
    tags=["agents"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    services_router,
    prefix="/v1/services",
    tags=["services"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    wallets_router,
    prefix="/v1/wallets",
    tags=["wallets"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    x402_router,
    prefix="/v1/x402",
    tags=["x402"],
    # x402 has its own auth
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "disco-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🕺 Disco API - x402 Crypto Payments for AI Agents",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "Contact support for documentation",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "disco_backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.ENVIRONMENT == "development",
        workers=1 if settings.ENVIRONMENT == "development" else 4
    ) 