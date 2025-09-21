"""
HTTP 402 (Payment Required) Protocol Integration for Disco SDK

This module adds HTTP 402 support to Disco agents, enabling web-based micropayments
following the HTTP 402 Payment Required standard.
"""

import aiohttp
import json
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

from .models import Payment, PaymentStatus, Currency
from .exceptions import PaymentError, NetworkError


class HTTP402Handler:
    """
    HTTP 402 Payment Required handler for Disco agents
    
    Enables agents to automatically handle 402 responses and process payments
    """
    
    def __init__(self, disco_client):
        self.disco = disco_client
        self.payment_cache = {}  # Cache payment tokens
    
    async def make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auto_pay: bool = True,
        max_payment: Optional[float] = None
    ) -> aiohttp.ClientResponse:
        """
        Make HTTP request with automatic 402 payment handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            data: Request data
            headers: Request headers
            auto_pay: Automatically handle 402 responses
            max_payment: Maximum payment amount to authorize
            
        Returns:
            HTTP response after payment (if required)
        """
        headers = headers or {}
        
        # Check if we have a cached payment token for this URL
        if url in self.payment_cache:
            headers["Payment-Token"] = self.payment_cache[url]
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data, headers=headers) as response:
                
                # Handle 402 Payment Required
                if response.status == 402 and auto_pay:
                    payment_info = await self._handle_402_response(response, max_payment)
                    
                    if payment_info:
                        # Cache payment token and retry request
                        headers["Payment-Token"] = payment_info["payment_token"]
                        self.payment_cache[url] = payment_info["payment_token"]
                        
                        # Retry original request with payment
                        async with session.request(method, url, json=data, headers=headers) as retry_response:
                            return retry_response
                    else:
                        raise PaymentError("Payment required but auto-payment failed")
                
                return response
    
    async def _handle_402_response(
        self, 
        response: aiohttp.ClientResponse,
        max_payment: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Handle HTTP 402 Payment Required response
        
        Expected 402 response format:
        {
            "error": "payment_required",
            "amount": 0.50,
            "currency": "USD",
            "agent_id": "service_provider",
            "service_type": "translation",
            "payment_url": "https://disco.ai/pay/abc123",
            "description": "Translation service payment"
        }
        """
        try:
            payment_info = await response.json()
            
            amount = payment_info.get("amount")
            currency = payment_info.get("currency", "USD")
            agent_id = payment_info.get("agent_id")
            
            if not amount or not agent_id:
                raise PaymentError("Invalid 402 response: missing amount or agent_id")
            
            # Check maximum payment limit
            if max_payment and amount > max_payment:
                raise PaymentError(f"Payment amount ${amount} exceeds maximum ${max_payment}")
            
            # Process payment through Disco
            payment = await self.disco.pay(
                to_agent=agent_id,
                amount=amount,
                currency=currency,
                description=payment_info.get("description", "HTTP 402 service payment"),
                reference=payment_info.get("payment_url"),
                metadata={
                    "http_402": True,
                    "service_type": payment_info.get("service_type"),
                    "original_url": str(response.url)
                }
            )
            
            return {
                "payment_id": payment.payment_id,
                "payment_token": payment.payment_id,  # Use payment ID as token
                "amount": amount,
                "currency": currency
            }
            
        except Exception as e:
            raise PaymentError(f"Failed to process 402 payment: {str(e)}")
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """HTTP GET with 402 support"""
        return await self.make_request("GET", url, **kwargs)
    
    async def post(self, url: str, data: Dict[str, Any] = None, **kwargs) -> aiohttp.ClientResponse:
        """HTTP POST with 402 support"""
        return await self.make_request("POST", url, data=data, **kwargs)


class PaymentRequiredServer:
    """
    Server-side HTTP 402 handler for Disco agents offering web services
    
    Enables agents to return 402 responses and validate payments
    """
    
    def __init__(self, disco_client, agent_id: str):
        self.disco = disco_client
        self.agent_id = agent_id
        self.service_prices = {}  # service_type -> price
    
    def require_payment(
        self,
        service_type: str,
        amount: float,
        currency: str = "USD",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate HTTP 402 Payment Required response
        
        Returns:
            402 response data to send to client
        """
        self.service_prices[service_type] = amount
        
        return {
            "error": "payment_required",
            "status_code": 402,
            "amount": amount,
            "currency": currency,
            "agent_id": self.agent_id,
            "service_type": service_type,
            "description": description or f"{service_type} service payment",
            "payment_url": f"https://disco.ai/pay/{self.agent_id}/{service_type}",
            "headers": {
                "Content-Type": "application/json",
                "WWW-Authenticate": f'Disco realm="{service_type}", amount={amount}, currency={currency}'
            }
        }
    
    async def validate_payment(self, payment_token: str, service_type: str) -> bool:
        """
        Validate payment token for service access
        
        Args:
            payment_token: Payment token from client (usually payment_id)
            service_type: Type of service being accessed
            
        Returns:
            True if payment is valid, False otherwise
        """
        try:
            # Get payment details
            payment = await self.disco.get_payment(payment_token)
            
            # Validate payment
            if (payment.to_agent == self.agent_id and 
                payment.status == PaymentStatus.COMPLETED and
                payment.metadata.get("service_type") == service_type):
                
                expected_amount = self.service_prices.get(service_type)
                if expected_amount and payment.amount >= expected_amount:
                    return True
            
            return False
            
        except Exception:
            return False


# Flask/FastAPI integration helpers
def flask_402_decorator(disco_client, service_type: str, amount: float):
    """
    Flask decorator for HTTP 402 payment protection
    
    Usage:
        @app.route('/translate')
        @flask_402_decorator(disco, 'translation', 0.50)
        def translate():
            return {"translated": "Hola mundo"}
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            server = PaymentRequiredServer(disco_client, disco_client.agent_id)
            
            # Check for payment token
            payment_token = request.headers.get('Payment-Token')
            
            if not payment_token:
                # Return 402 Payment Required
                payment_required = server.require_payment(service_type, amount)
                return jsonify(payment_required), 402
            
            # Validate payment
            import asyncio
            if not asyncio.run(server.validate_payment(payment_token, service_type)):
                payment_required = server.require_payment(service_type, amount)
                return jsonify(payment_required), 402
            
            # Payment valid, proceed with service
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def fastapi_402_dependency(disco_client, service_type: str, amount: float):
    """
    FastAPI dependency for HTTP 402 payment protection
    
    Usage:
        @app.get("/translate")
        async def translate(
            payment_valid: bool = Depends(fastapi_402_dependency(disco, 'translation', 0.50))
        ):
            return {"translated": "Hola mundo"}
    """
    async def payment_dependency(request):
        from fastapi import HTTPException
        
        server = PaymentRequiredServer(disco_client, disco_client.agent_id)
        
        # Check for payment token
        payment_token = request.headers.get('payment-token')
        
        if not payment_token:
            # Return 402 Payment Required
            payment_required = server.require_payment(service_type, amount)
            raise HTTPException(
                status_code=402,
                detail=payment_required,
                headers=payment_required["headers"]
            )
        
        # Validate payment
        if not await server.validate_payment(payment_token, service_type):
            payment_required = server.require_payment(service_type, amount)
            raise HTTPException(
                status_code=402,
                detail=payment_required,
                headers=payment_required["headers"]
            )
        
        return True
    
    return payment_dependency 