"""
x402 Protocol Integration for Disco SDK

Integrates Coinbase's x402 payment protocol for standardized HTTP 402 micropayments
https://github.com/coinbase/x402
"""

import json
import base64
import aiohttp
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from .models import Payment, PaymentStatus, Currency
from .exceptions import PaymentError, NetworkError


class X402PaymentRequirements:
    """
    x402 PaymentRequirements structure
    Based on Coinbase x402 specification
    """
    
    def __init__(
        self,
        scheme: str,
        network: str,
        max_amount_required: str,
        resource: str,
        description: str,
        mime_type: str,
        pay_to: str,
        max_timeout_seconds: int,
        asset: str,
        extra: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ):
        self.scheme = scheme
        self.network = network
        self.max_amount_required = max_amount_required
        self.resource = resource
        self.description = description
        self.mime_type = mime_type
        self.pay_to = pay_to
        self.max_timeout_seconds = max_timeout_seconds
        self.asset = asset
        self.extra = extra or {}
        self.output_schema = output_schema

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "maxAmountRequired": self.max_amount_required,
            "resource": self.resource,
            "description": self.description,
            "mimeType": self.mime_type,
            "payTo": self.pay_to,
            "maxTimeoutSeconds": self.max_timeout_seconds,
            "asset": self.asset,
            "extra": self.extra,
            "outputSchema": self.output_schema
        }


class X402PaymentPayload:
    """
    x402 Payment Payload structure
    Sent in X-PAYMENT header as base64 encoded JSON
    """
    
    def __init__(
        self,
        x402_version: int,
        scheme: str,
        network: str,
        payload: Dict[str, Any]
    ):
        self.x402_version = x402_version
        self.scheme = scheme
        self.network = network
        self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x402Version": self.x402_version,
            "scheme": self.scheme,
            "network": self.network,
            "payload": self.payload
        }

    def to_header(self) -> str:
        """Convert to base64 encoded JSON for X-PAYMENT header"""
        json_str = json.dumps(self.to_dict())
        return base64.b64encode(json_str.encode()).decode()


class X402Client:
    """
    x402 Protocol Client for Disco agents
    
    Handles HTTP 402 Payment Required responses using x402 standard
    """
    
    def __init__(self, disco_client, facilitator_url: Optional[str] = None):
        self.disco = disco_client
        self.facilitator_url = facilitator_url or "https://facilitator.disco.ai"
        self.x402_version = 1
        self.payment_cache: Dict[str, str] = {}  # URL -> payment token cache

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
        Make HTTP request with x402 payment handling
        
        Follows the x402 protocol flow:
        1. Make initial request
        2. Handle 402 Payment Required response
        3. Create payment payload
        4. Retry request with X-PAYMENT header
        """
        headers = headers or {}
        
        # Check payment cache
        if url in self.payment_cache:
            headers["X-PAYMENT"] = self.payment_cache[url]

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data, headers=headers) as response:
                
                # Handle 402 Payment Required
                if response.status == 402 and auto_pay:
                    payment_required = await response.json()
                    payment_header = await self._handle_x402_response(
                        payment_required, url, max_payment
                    )
                    
                    if payment_header:
                        # Cache payment and retry
                        headers["X-PAYMENT"] = payment_header
                        self.payment_cache[url] = payment_header
                        
                        # Retry with payment
                        async with session.request(method, url, json=data, headers=headers) as retry_response:
                            return retry_response
                    else:
                        raise PaymentError("x402 payment processing failed")
                
                return response

    async def _handle_x402_response(
        self,
        payment_required: Dict[str, Any],
        url: str,
        max_payment: Optional[float] = None
    ) -> Optional[str]:
        """
        Handle x402 Payment Required Response
        
        Expected format:
        {
            "x402Version": 1,
            "accepts": [paymentRequirements],
            "error": "string"
        }
        """
        try:
            x402_version = payment_required.get("x402Version", 1)
            accepts = payment_required.get("accepts", [])
            
            if not accepts:
                raise PaymentError("No payment requirements in 402 response")
            
            # Select first supported payment requirement
            # TODO: Add logic to select best option based on user preferences
            payment_req_data = accepts[0]
            payment_req = X402PaymentRequirements(**payment_req_data)
            
            # Check maximum payment limit
            max_amount_wei = int(payment_req.max_amount_required)
            max_amount_eth = max_amount_wei / 10**18  # Convert from wei to ETH
            
            if max_payment and max_amount_eth > max_payment:
                raise PaymentError(f"Payment amount {max_amount_eth} ETH exceeds maximum {max_payment} ETH")
            
            # Create payment through Disco
            disco_payment = await self.disco.pay(
                to_agent=payment_req.pay_to,  # Use payTo address as agent ID
                amount=max_amount_eth,
                currency=Currency.ETH,  # Assuming ETH for now
                description=payment_req.description,
                reference=url,
                metadata={
                    "x402": True,
                    "scheme": payment_req.scheme,
                    "network": payment_req.network,
                    "resource": payment_req.resource
                }
            )
            
            # Create x402 payment payload
            payment_payload = self._create_payment_payload(
                payment_req, disco_payment, x402_version
            )
            
            return payment_payload.to_header()
            
        except Exception as e:
            raise PaymentError(f"Failed to process x402 payment: {str(e)}")

    def _create_payment_payload(
        self,
        payment_req: X402PaymentRequirements,
        disco_payment: Payment,
        x402_version: int
    ) -> X402PaymentPayload:
        """
        Create x402 Payment Payload based on scheme
        
        For 'exact' scheme on EVM networks, creates EIP-3009 compliant payload
        """
        if payment_req.scheme == "exact" and payment_req.network in ["ethereum", "polygon"]:
            # EIP-3009 compliant payload for exact payments
            payload = {
                "from": disco_payment.from_agent,  # Payer address
                "to": payment_req.pay_to,          # Recipient address
                "value": payment_req.max_amount_required,  # Amount in wei
                "validAfter": int(datetime.now().timestamp()),
                "validBefore": int((datetime.now() + timedelta(hours=1)).timestamp()),
                "nonce": disco_payment.payment_id,  # Use payment ID as nonce
                "v": 27,  # Signature components (would be real in production)
                "r": "0x" + "0" * 64,
                "s": "0x" + "0" * 64
            }
        else:
            # Generic payload for other schemes
            payload = {
                "payment_id": disco_payment.payment_id,
                "amount": payment_req.max_amount_required,
                "signature": "disco_signature_placeholder"
            }
        
        return X402PaymentPayload(
            x402_version=x402_version,
            scheme=payment_req.scheme,
            network=payment_req.network,
            payload=payload
        )


class X402Server:
    """
    x402 Protocol Server for Disco agents offering web services
    
    Enables agents to return proper x402 Payment Required responses
    """
    
    def __init__(self, disco_client, agent_id: str, facilitator_url: Optional[str] = None):
        self.disco = disco_client
        self.agent_id = agent_id
        self.facilitator_url = facilitator_url or "https://facilitator.disco.ai"
        self.x402_version = 1
        self.service_prices: Dict[str, float] = {}

    def create_payment_required_response(
        self,
        service_type: str,
        amount_eth: float,
        resource_url: str,
        description: str,
        mime_type: str = "application/json",
        scheme: str = "exact",
        network: str = "ethereum"
    ) -> Dict[str, Any]:
        """
        Create x402 Payment Required Response
        
        Returns proper x402 format for 402 responses
        """
        self.service_prices[service_type] = amount_eth
        
        # Convert ETH to wei
        amount_wei = str(int(amount_eth * 10**18))
        
        payment_requirements = X402PaymentRequirements(
            scheme=scheme,
            network=network,
            max_amount_required=amount_wei,
            resource=resource_url,
            description=description,
            mime_type=mime_type,
            pay_to=self.agent_id,  # Agent receives payment
            max_timeout_seconds=300,  # 5 minutes
            asset="0x0000000000000000000000000000000000000000",  # ETH address
            extra={
                "name": "Ethereum",
                "version": "1"
            }
        )
        
        return {
            "x402Version": self.x402_version,
            "accepts": [payment_requirements.to_dict()],
            "error": None
        }

    async def verify_payment(
        self,
        x_payment_header: str,
        service_type: str,
        resource_url: str
    ) -> bool:
        """
        Verify x402 payment using facilitator or local verification
        """
        try:
            # Decode X-PAYMENT header
            payment_json = base64.b64decode(x_payment_header).decode()
            payment_data = json.loads(payment_json)
            
            payment_payload = X402PaymentPayload(**payment_data)
            
            # Get expected payment requirements
            expected_amount = self.service_prices.get(service_type, 0)
            payment_req = X402PaymentRequirements(
                scheme=payment_payload.scheme,
                network=payment_payload.network,
                max_amount_required=str(int(expected_amount * 10**18)),
                resource=resource_url,
                description=f"{service_type} service",
                mime_type="application/json",
                pay_to=self.agent_id,
                max_timeout_seconds=300,
                asset="0x0000000000000000000000000000000000000000"
            )
            
            # Verify with facilitator
            verification = await self._verify_with_facilitator(
                x_payment_header, payment_req
            )
            
            return verification.get("isValid", False)
            
        except Exception as e:
            print(f"Payment verification failed: {e}")
            return False

    async def _verify_with_facilitator(
        self,
        payment_header: str,
        payment_requirements: X402PaymentRequirements
    ) -> Dict[str, Any]:
        """
        Verify payment with x402 facilitator server
        
        POST /verify endpoint
        """
        verify_data = {
            "x402Version": self.x402_version,
            "paymentHeader": payment_header,
            "paymentRequirements": payment_requirements.to_dict()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.facilitator_url}/verify",
                json=verify_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"isValid": False, "invalidReason": "Facilitator error"}

    async def settle_payment(
        self,
        payment_header: str,
        payment_requirements: X402PaymentRequirements
    ) -> Dict[str, Any]:
        """
        Settle payment with x402 facilitator server
        
        POST /settle endpoint
        """
        settle_data = {
            "x402Version": self.x402_version,
            "paymentHeader": payment_header,
            "paymentRequirements": payment_requirements.to_dict()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.facilitator_url}/settle",
                json=settle_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "success": False,
                        "error": "Settlement failed",
                        "txHash": None,
                        "networkId": None
                    }


# FastAPI integration for x402
def fastapi_x402_dependency(disco_client, service_type: str, amount_eth: float):
    """
    FastAPI dependency for x402 payment protection
    
    Usage:
        @app.get("/translate")
        async def translate(
            request: Request,
            payment_valid: bool = Depends(fastapi_x402_dependency(disco, 'translation', 0.001))
        ):
            return {"translated": "Hola mundo"}
    """
    async def x402_dependency(request):
        from fastapi import HTTPException
        
        server = X402Server(disco_client, disco_client.agent_id)
        
        # Check for X-PAYMENT header
        x_payment = request.headers.get('x-payment')
        
        if not x_payment:
            # Return x402 Payment Required response
            payment_required = server.create_payment_required_response(
                service_type=service_type,
                amount_eth=amount_eth,
                resource_url=str(request.url),
                description=f"{service_type} service payment"
            )
            raise HTTPException(
                status_code=402,
                detail=payment_required,
                headers={"Content-Type": "application/json"}
            )
        
        # Verify payment
        is_valid = await server.verify_payment(
            x_payment, service_type, str(request.url)
        )
        
        if not is_valid:
            payment_required = server.create_payment_required_response(
                service_type=service_type,
                amount_eth=amount_eth,
                resource_url=str(request.url),
                description=f"{service_type} service payment"
            )
            raise HTTPException(
                status_code=402,
                detail=payment_required,
                headers={"Content-Type": "application/json"}
            )
        
        return True
    
    return x402_dependency 