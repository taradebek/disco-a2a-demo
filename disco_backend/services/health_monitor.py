"""
Health monitoring and circuit breaker service
Monitors system health and implements circuit breakers for external services
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import httpx
import redis.asyncio as redis
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if service recovered

class HealthMonitor:
    """System health monitoring and circuit breaker"""
    
    def __init__(self):
        self.redis_client = None
        self.health_checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            "blockchain_ethereum": self._check_ethereum,
            "blockchain_polygon": self._check_polygon,
            "blockchain_arbitrum": self._check_arbitrum,
            "blockchain_solana": self._check_solana,
            "exchange_rates": self._check_exchange_rates,
            "webhook_delivery": self._check_webhook_delivery
        }
        
        self.circuit_breakers = {
            "ethereum": {"state": CircuitState.CLOSED, "failures": 0, "last_failure": None},
            "polygon": {"state": CircuitState.CLOSED, "failures": 0, "last_failure": None},
            "arbitrum": {"state": CircuitState.CLOSED, "failures": 0, "last_failure": None},
            "solana": {"state": CircuitState.CLOSED, "failures": 0, "last_failure": None},
            "exchange_rates": {"state": CircuitState.CLOSED, "failures": 0, "last_failure": None}
        }
        
        self.circuit_config = {
            "failure_threshold": 5,      # Open circuit after 5 failures
            "recovery_timeout": 60,      # Try to close after 60 seconds
            "success_threshold": 3       # Close circuit after 3 successes
        }
    
    async def initialize(self):
        """Initialize health monitoring"""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Health monitor initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis not available for health monitoring: {e}")
            self.redis_client = None
    
    async def check_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        
        health_results = {}
        overall_status = HealthStatus.HEALTHY
        
        # Run all health checks
        for check_name, check_func in self.health_checks.items():
            try:
                result = await check_func()
                health_results[check_name] = result
                
                # Update overall status
                if result["status"] == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result["status"] == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                health_results[check_name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_status = HealthStatus.UNHEALTHY
        
        # Check circuit breakers
        circuit_status = await self._check_circuit_breakers()
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": health_results,
            "circuit_breakers": circuit_status
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from disco_backend.database.connection import get_db
            async with get_db() as db:
                await db.execute("SELECT 1")
            
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Database connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            if not self.redis_client:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Redis not configured",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            await self.redis_client.ping()
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Redis connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_ethereum(self) -> Dict[str, Any]:
        """Check Ethereum network connectivity"""
        return await self._check_blockchain("ethereum", settings.ETHEREUM_RPC_URL)
    
    async def _check_polygon(self) -> Dict[str, Any]:
        """Check Polygon network connectivity"""
        return await self._check_blockchain("polygon", settings.POLYGON_RPC_URL)
    
    async def _check_arbitrum(self) -> Dict[str, Any]:
        """Check Arbitrum network connectivity"""
        return await self._check_blockchain("arbitrum", settings.ARBITRUM_RPC_URL)
    
    async def _check_solana(self) -> Dict[str, Any]:
        """Check Solana network connectivity"""
        return await self._check_blockchain("solana", settings.SOLANA_RPC_URL)
    
    async def _check_blockchain(self, network: str, rpc_url: str) -> Dict[str, Any]:
        """Check blockchain network connectivity"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if network == "solana":
                    # Solana RPC call
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getHealth"
                    }
                    response = await client.post(rpc_url, json=payload)
                else:
                    # Ethereum-compatible RPC call
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_blockNumber",
                        "params": []
                    }
                    response = await client.post(rpc_url, json=payload)
                
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    raise Exception(f"RPC error: {data['error']}")
                
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": f"{network.title()} network accessible",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": f"{network.title()} network error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_exchange_rates(self) -> Dict[str, Any]:
        """Check exchange rate service"""
        try:
            from disco_backend.services.exchange_rates import exchange_rate_service
            
            # Try to get a simple exchange rate
            rate = await exchange_rate_service.get_exchange_rate("USDC", "USD")
            
            if rate and rate > 0:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": f"Exchange rates working (USDC/USD: {rate})",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": "Exchange rates returned invalid data",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": f"Exchange rate service error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_webhook_delivery(self) -> Dict[str, Any]:
        """Check webhook delivery service"""
        try:
            from disco_backend.services.webhook_service import webhook_service
            
            # Check if webhook service is initialized
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Webhook service available",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "error": f"Webhook service error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check circuit breaker states"""
        return {
            name: {
                "state": breaker["state"].value,
                "failures": breaker["failures"],
                "last_failure": breaker["last_failure"].isoformat() if breaker["last_failure"] else None
            }
            for name, breaker in self.circuit_breakers.items()
        }
    
    async def record_success(self, service: str) -> None:
        """Record successful operation for circuit breaker"""
        if service not in self.circuit_breakers:
            return
        
        breaker = self.circuit_breakers[service]
        
        if breaker["state"] == CircuitState.HALF_OPEN:
            # Count successes in half-open state
            if "successes" not in breaker:
                breaker["successes"] = 0
            breaker["successes"] += 1
            
            # Close circuit if enough successes
            if breaker["successes"] >= self.circuit_config["success_threshold"]:
                breaker["state"] = CircuitState.CLOSED
                breaker["failures"] = 0
                breaker["successes"] = 0
                logger.info(f"Circuit breaker for {service} closed")
        
        elif breaker["state"] == CircuitState.CLOSED:
            # Reset failure count on success
            breaker["failures"] = 0
    
    async def record_failure(self, service: str) -> None:
        """Record failed operation for circuit breaker"""
        if service not in self.circuit_breakers:
            return
        
        breaker = self.circuit_breakers[service]
        breaker["failures"] += 1
        breaker["last_failure"] = datetime.utcnow()
        
        # Open circuit if threshold reached
        if breaker["failures"] >= self.circuit_config["failure_threshold"]:
            breaker["state"] = CircuitState.OPEN
            logger.warning(f"Circuit breaker for {service} opened due to failures")
    
    async def is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open"""
        if service not in self.circuit_breakers:
            return False
        
        breaker = self.circuit_breakers[service]
        
        if breaker["state"] == CircuitState.OPEN:
            # Check if we should try half-open
            if breaker["last_failure"]:
                time_since_failure = (datetime.utcnow() - breaker["last_failure"]).total_seconds()
                if time_since_failure >= self.circuit_config["recovery_timeout"]:
                    breaker["state"] = CircuitState.HALF_OPEN
                    breaker["successes"] = 0
                    logger.info(f"Circuit breaker for {service} moved to half-open")
                    return False
            
            return True
        
        return False

# Global instance
health_monitor = HealthMonitor()
