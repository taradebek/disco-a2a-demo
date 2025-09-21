"""
Main Disco SDK Class - x402-Only         
        # Offline mode for testing
        self.offline_mode = offline_mode
        if offline_mode:
            self.base_url = "http://localhost:8000"
            print("🧪 Disco SDK running in offline mode - no network calls will be made")

Crypto-native payment infrastructure for AI agents using x402 protocol
"""

import asyncio
import aiohttp
import json
from typing import Optional, List, Dict, Any, Union
from urllib.parse import urljoin

from .models import (
    Payment, PaymentRequest, PaymentStatus, PaymentMethod, Currency,
    Agent, Service, Wallet, Transaction
)
from .exceptions import (
    DiscoError, AuthenticationError, PaymentError, InsufficientFundsError,
    AgentNotFoundError, ServiceNotFoundError, NetworkError, ServerError,
    RateLimitError, ValidationError
)
from .x402_integration import X402Client, X402Server


class Disco:
    """
    Main Disco SDK class for x402-based multi-agent payments
    
    Crypto-native revenue-based pricing model:
    - Sandbox: Free for testing
    - Live: 2.9% of transaction volume
    
    Supports: ETH, USDC, USDT, DAI, BTC
    Networks: Ethereum, Polygon, Arbitrum, Solana
    """
    
    def __init__(
        self, 
        api_key: str, 
        environment: str = "sandbox",
        base_url: Optional[str] = None,
        timeout: int = 30,
        default_network: str = "polygon",  # Cheaper gas fees
        offline_mode: bool = False,
        user_email: Optional[str] = None,
        organization: Optional[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize Disco SDK for x402 payments
        
        Args:
            api_key: Your Disco API key (dk_test_xxx or dk_live_xxx)
            environment: "sandbox" or "live"
            base_url: Custom API base URL (optional)
            timeout: Request timeout in seconds
            default_network: Default blockchain network
            offline_mode: For testing without network calls
            user_email: User email for tracking and support
            organization: Organization name for analytics
            user_metadata: Additional user metadata for tracking
        """
        self.api_key = api_key
        self.environment = environment
        self.timeout = timeout
        self.default_network = default_network
        self.user_email = user_email
        self.organization = organization
        self.user_metadata = user_metadata or {}
        
        # Validate API key format
        if environment == "live" and not api_key.startswith("dk_live_"):
            raise AuthenticationError("Live environment requires a live API key (dk_live_xxx)")
        elif environment == "sandbox" and not api_key.startswith("dk_test_"):
            raise AuthenticationError("Sandbox environment requires a test API key (dk_test_xxx)")
        
        # Set base URL
        if base_url:
            self.base_url = base_url
        elif environment == "live":
            self.base_url = "https://api.disco.ai/v1"
        else:
            self.base_url = "https://sandbox-api.disco.ai/v1"
        
        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Fee structure (hybrid: percentage + fixed)
        self.fee_percentage = 0.029 if environment == "live" else 0.0  # 2.9% for live, free for sandbox
        self.fee_fixed = 0.30 if environment == "live" else 0.0  # $0.30 per transaction for live, free for sandbox
        
        # x402 integration
        self.x402_client = X402Client(self)
        self.x402_server = None  # Will be initialized when needed
        
        # Supported currencies (crypto-only)
        self.supported_currencies = [
            Currency.ETH,    # Ethereum
            Currency.USDC,   # USD Coin
            Currency.BTC,    # Bitcoin
        ]
        
        # Supported networks
        self.supported_networks = [
            "ethereum",
            "polygon", 
            "arbitrum",
            "solana"
        ]
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"disco-sdk-python/1.0.0",
                "X-Disco-Network": self.default_network,
                "X-Disco-Environment": self.environment
            }
            
            # Add optional user identification headers
            if self.user_email:
                headers["X-User-Email"] = self.user_email
            if self.organization:
                headers["X-Organization"] = self.organization
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        return self._session
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Disco API"""
        session = await self._get_session()
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        try:
            async with session.request(
                method=method,
                url=url,
                json=data,
                params=params
            ) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    return response_data
                elif response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 429:
                    retry_after = response.headers.get('Retry-After')
                    raise RateLimitError(int(retry_after) if retry_after else None)
                elif response.status >= 500:
                    raise ServerError(response.status, response_data.get('message', 'Server error'))
                else:
                    error_msg = response_data.get('message', f'Request failed with status {response.status}')
                    raise DiscoError(error_msg, response_data.get('code'))
                    
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error: {str(e)}")
    
    # x402 Payment Methods
    
    async def pay(
        self,
        to_agent: str,
        amount: float,
        currency: Union[str, Currency] = Currency.USDC,  # Default to USDC for stability
        network: Optional[str] = None,
        description: Optional[str] = None,
        reference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Payment:
        """
        Send x402 payment to another agent
        
        Args:
            to_agent: ID of the receiving agent
            amount: Payment amount in crypto
            currency: Crypto currency (ETH, USDC, BTC)
            network: Blockchain network (defaults to self.default_network)
            description: Payment description
            reference: External reference ID
            metadata: Additional metadata
            
        Returns:
            Payment object with transaction details
        """
        if amount <= 0:
            raise ValidationError("amount", "Amount must be positive")
        
        # Validate currency
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        if currency_obj not in self.supported_currencies:
            raise ValidationError("currency", f"Currency {currency_obj} not supported. Supported: {self.supported_currencies}")
        
        # Validate network
        network = network or self.default_network
        if network not in self.supported_networks:
            raise ValidationError("network", f"Network {network} not supported. Supported: {self.supported_networks}")
        
        # Calculate Disco fee (hybrid: percentage + fixed)
        disco_fee_percentage = amount * self.fee_percentage
        disco_fee_fixed = self.fee_fixed
        disco_fee = disco_fee_percentage + disco_fee_fixed
        net_amount = amount - disco_fee
        
        payment_request = PaymentRequest(
            to_agent=to_agent,
            amount=amount,
            currency=currency_obj,
            method=PaymentMethod.CRYPTO,  # Always crypto for x402
            description=description,
            reference=reference,
            metadata={
                "network": network,
                "x402": True,
                **(metadata or {})
            }
        )
        
        response = await self._make_request(
            "POST", 
            "/payments", 
            data={
                **payment_request.dict(),
                "network": network
            }
        )
        
        # Add fee information to response
        response['disco_fee'] = disco_fee
        response['disco_fee_percentage_amount'] = disco_fee_percentage
        response['disco_fee_fixed_amount'] = disco_fee_fixed
        response['disco_fee_percentage'] = self.fee_percentage
        response['disco_fee_fixed'] = self.fee_fixed
        response['net_amount'] = net_amount
        response['network'] = network
        
        return Payment(**response)
    
    async def get_payment(self, payment_id: str) -> Payment:
        """Get payment by ID"""
        response = await self._make_request("GET", f"/payments/{payment_id}")
        return Payment(**response)
    
    async def list_payments(
        self,
        agent_id: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        currency: Optional[Currency] = None,
        network: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Payment]:
        """List payments with optional filters"""
        params = {"limit": limit, "offset": offset}
        if agent_id:
            params["agent_id"] = agent_id
        if status:
            params["status"] = status.value
        if currency:
            params["currency"] = currency.value
        if network:
            params["network"] = network
        
        response = await self._make_request("GET", "/payments", params=params)
        return [Payment(**payment) for payment in response.get("payments", [])]
    
    # Agent Methods
    
    async def register_agent(
        self,
        agent_id: str,
        name: str,
        description: Optional[str] = None,
        wallet_address: Optional[str] = None,  # Crypto wallet address
        capabilities: Optional[List[str]] = None,
        contact_email: Optional[str] = None,
        website_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """Register a new agent with crypto wallet"""
        agent_data = {
            "agent_id": agent_id,
            "name": name,
            "description": description,
            "wallet_address": wallet_address,
            "capabilities": capabilities or [],
            "contact_email": contact_email,
            "website_url": website_url,
            "metadata": {
                "supported_currencies": [c.value for c in self.supported_currencies],
                "supported_networks": self.supported_networks,
                **(metadata or {})
            }
        }
        
        response = await self._make_request("POST", "/agents", data=agent_data)
        return Agent(**response)
    
    async def get_agent(self, agent_id: str) -> Agent:
        """Get agent by ID"""
        response = await self._make_request("GET", f"/agents/{agent_id}")
        return Agent(**response)
    
    async def discover_agents(
        self,
        service_type: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        network: Optional[str] = None,
        currency: Optional[Currency] = None,
        limit: int = 100
    ) -> List[Agent]:
        """Discover agents by service type, network, or currency"""
        params = {"limit": limit}
        if service_type:
            params["service_type"] = service_type
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        if network:
            params["network"] = network
        if currency:
            params["currency"] = currency.value
        
        response = await self._make_request("GET", "/agents", params=params)
        return [Agent(**agent) for agent in response.get("agents", [])]
    
    # Service Methods (x402-focused)
    
    async def register_service(
        self,
        agent_id: str,
        name: str,
        description: str,
        price: float,
        currency: Union[str, Currency] = Currency.USDC,
        network: Optional[str] = None,
        unit: str = "request",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        x402_endpoint: Optional[str] = None  # HTTP endpoint for x402 payments
    ) -> Service:
        """Register a service for x402 payments"""
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        network = network or self.default_network
        
        service_data = {
            "agent_id": agent_id,
            "name": name,
            "description": description,
            "price": price,
            "currency": currency_obj.value,
            "network": network,
            "unit": unit,
            "category": category,
            "tags": tags or [],
            "x402_endpoint": x402_endpoint,
            "payment_method": "x402"
        }
        
        response = await self._make_request("POST", "/services", data=service_data)
        return Service(**response)
    
    async def get_service(self, service_id: str) -> Service:
        """Get service by ID"""
        response = await self._make_request("GET", f"/services/{service_id}")
        return Service(**response)
    
    async def discover_services(
        self,
        service_type: Optional[str] = None,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        currency: Optional[Currency] = None,
        network: Optional[str] = None,
        limit: int = 100
    ) -> List[Service]:
        """Discover x402 services with optional filters"""
        params = {"limit": limit, "payment_method": "x402"}
        if service_type:
            params["service_type"] = service_type
        if category:
            params["category"] = category
        if max_price:
            params["max_price"] = max_price
        if currency:
            params["currency"] = currency.value
        if network:
            params["network"] = network
        
        response = await self._make_request("GET", "/services", params=params)
        return [Service(**service) for service in response.get("services", [])]
    
    # Crypto Wallet Methods
    
    async def get_wallet(self, agent_id: str) -> Wallet:
        """Get crypto wallet for an agent"""
        response = await self._make_request("GET", f"/wallets/{agent_id}")
        return Wallet(**response)
    
    async def get_balance(self, agent_id: str, currency: Union[str, Currency] = Currency.USDC) -> float:
        """Get balance for specific crypto currency"""
        wallet = await self.get_wallet(agent_id)
        currency_key = Currency(currency) if isinstance(currency, str) else currency
        return wallet.balances.get(currency_key, 0.0)
    
    async def add_funds_crypto(
        self,
        agent_id: str,
        amount: float,
        currency: Union[str, Currency] = Currency.USDC,
        network: Optional[str] = None,
        from_address: Optional[str] = None
    ) -> Transaction:
        """Add crypto funds to agent wallet"""
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        network = network or self.default_network
        
        data = {
            "amount": amount,
            "currency": currency_obj.value,
            "network": network,
            "method": "crypto",
            "from_address": from_address
        }
        
        response = await self._make_request("POST", f"/wallets/{agent_id}/add-funds", data=data)
        return Transaction(**response)
    
    # x402 HTTP Methods
    
    def get_x402_client(self) -> X402Client:
        """Get x402 client for making HTTP payments"""
        return self.x402_client
    
    def get_x402_server(self, agent_id: str) -> X402Server:
        """Get x402 server for accepting HTTP payments"""
        if not self.x402_server:
            self.x402_server = X402Server(self, agent_id)
        return self.x402_server
    
    async def make_x402_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auto_pay: bool = True,
        max_payment: Optional[float] = None,
        currency: Union[str, Currency] = Currency.USDC
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with x402 payment handling"""
        return await self.x402_client.make_request(
            method=method,
            url=url,
            data=data,
            headers=headers,
            auto_pay=auto_pay,
            max_payment=max_payment
        )
    
    # Utility Methods
    
    def agent(self, agent_class):
        """Decorator to make any agent class Disco-enabled"""
        from .agent import DiscoAgent
        return DiscoAgent(agent_class, self)
    
    async def get_pricing(self, agent_id: str, service_type: str) -> Optional[Service]:
        """Get pricing for a specific service"""
        services = await self.discover_services(service_type=service_type)
        for service in services:
            if service.agent_id == agent_id:
                return service
        return None
    
    async def calculate_fees(self, amount: float, currency: Union[str, Currency] = Currency.USDC) -> Dict[str, float]:
        """Calculate Disco fees for a given amount (hybrid pricing model)"""
        disco_fee_percentage = amount * self.fee_percentage
        disco_fee_fixed = self.fee_fixed
        disco_fee = disco_fee_percentage + disco_fee_fixed
        net_amount = amount - disco_fee
        
        return {
            "gross_amount": amount,
            "disco_fee": disco_fee,
            "disco_fee_percentage_amount": disco_fee_percentage,
            "disco_fee_fixed_amount": disco_fee_fixed,
            "disco_fee_percentage": self.fee_percentage,
            "disco_fee_fixed": self.fee_fixed,
            "net_amount": net_amount,
            "currency": Currency(currency) if isinstance(currency, str) else currency.value
        }
    
    async def get_exchange_rate(self, from_currency: Currency, to_currency: Currency) -> float:
        """Get real-time crypto exchange rates"""
        response = await self._make_request("GET", f"/exchange-rates/{from_currency.value}/{to_currency.value}")
        return response["rate"]
    
    async def get_network_info(self, network: str) -> Dict[str, Any]:
        """Get blockchain network information (gas fees, block time, etc.)"""
        response = await self._make_request("GET", f"/networks/{network}")
        return response
    
    async def estimate_gas_fee(self, network: str, transaction_type: str = "transfer") -> Dict[str, float]:
        """Estimate gas fees for a transaction"""
        response = await self._make_request("GET", f"/networks/{network}/gas-estimate", params={
            "transaction_type": transaction_type
        })
        return response 