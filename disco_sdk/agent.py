"""
Disco Agent - x402-enabled agent wrapper
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable, Union
from .models import Payment, Service, Wallet, Currency, PaymentMethod
from .exceptions import DiscoError, InsufficientFundsError


class DiscoAgent:
    """
    x402-enabled agent wrapper
    
    Wraps any agent class to add Disco x402 payment capabilities
    """
    
    def __init__(self, agent=None, agent_id=None, api_key=None, wallet_address=None, agent_class=None, disco_client=None):
        """
        Initialize Disco-enabled agent
        
        Args:
            agent: The agent instance to wrap (new interface)
            agent_id: Unique agent identifier (new interface)
            api_key: Disco API key (new interface)
            wallet_address: Wallet address (new interface)
            agent_class: The original agent class to wrap (legacy)
            disco_client: Disco SDK client instance (legacy)
        """
        # Support both new and legacy interfaces
        if agent is not None:
            # New interface
            from . import Disco
            self.disco = Disco(api_key=api_key, environment="sandbox") if api_key else None
            self.agent_class = agent.__class__
            self.agent_instance = agent
            self.agent_id = agent_id or getattr(agent, 'agent_id', agent.__class__.__name__.lower())
            self.name = getattr(agent, 'name', agent.__class__.__name__)
            self.description = getattr(agent, 'description', None)
            self.wallet_address = wallet_address or getattr(agent, 'wallet_address', None)
        else:
            # Legacy interface
            self.disco = disco_client
            self.agent_class = agent_class
            self.agent_id = getattr(agent_class, 'agent_id', agent_class.__name__.lower())
            self.name = getattr(agent_class, 'name', agent_class.__name__)
            self.description = getattr(agent_class, 'description', None)
            self.wallet_address = getattr(agent_class, 'wallet_address', None)
            # Agent instance
            self.agent_instance = agent_class() if callable(agent_class) else agent_class
        
        # Payment capabilities
        self.wallet: Optional[Wallet] = None
        self.services: List[Service] = []
        self.payment_handlers: Dict[str, Callable] = {}
        
        # Revenue tracking (in crypto)
        self.total_earned = {}  # {currency: amount}
        self.total_spent = {}   # {currency: amount}
        self.transaction_count = 0
        
        # x402 server for HTTP endpoints
        self.x402_server = None
    
    async def initialize(self):
        """Initialize the agent's Disco x402 capabilities"""
        try:
            # Register agent with Disco
            await self.disco.register_agent(
                agent_id=self.agent_id,
                name=self.name,
                description=self.description,
                wallet_address=self.wallet_address
            )
            
            # Get or create wallet
            try:
                self.wallet = await self.disco.get_wallet(self.agent_id)
            except DiscoError:
                # Wallet doesn't exist, it will be created on first transaction
                pass
            
            # Initialize x402 server
            self.x402_server = self.disco.get_x402_server(self.agent_id)
            
            print(f"🕺 Agent '{self.name}' joined the disco floor with x402 support!")
            
        except Exception as e:
            print(f"❌ Failed to initialize agent '{self.name}': {e}")
            raise
    
    async def pay_for_service(
        self,
        service_agent: str,
        service_type: str,
        amount: Optional[float] = None,
        currency: Union[str, Currency] = Currency.USDC,
        network: Optional[str] = None,
        description: Optional[str] = None,
        **service_params
    ) -> Payment:
        """
        Pay another agent for a service using x402 protocol
        
        Args:
            service_agent: ID of the service provider agent
            service_type: Type of service being purchased
            amount: Payment amount (if None, will look up service pricing)
            currency: Crypto currency (USDC, ETH, BTC)
            network: Blockchain network
            description: Payment description
            **service_params: Additional parameters for the service
            
        Returns:
            Payment object with transaction details
        """
        # If amount not provided, get pricing from service
        if amount is None:
            pricing = await self.disco.get_pricing(service_agent, service_type)
            if not pricing:
                raise DiscoError(f"No pricing found for service '{service_type}' from agent '{service_agent}'")
            amount = pricing.price
            currency = pricing.currency
        
        # Check balance before payment
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        balance = await self.disco.get_balance(self.agent_id, currency_obj)
        if balance < amount:
            raise InsufficientFundsError(amount, balance, str(currency_obj))
        
        # Process payment through x402
        payment = await self.disco.pay(
            to_agent=service_agent,
            amount=amount,
            currency=currency_obj,
            network=network,
            description=description or f"{service_type} service from {service_agent}",
            metadata={
                "service_type": service_type,
                "service_params": service_params,
                "x402": True
            }
        )
        
        # Update spending tracking
        currency_key = str(currency_obj)
        if currency_key not in self.total_spent:
            self.total_spent[currency_key] = 0.0
        self.total_spent[currency_key] += amount
        self.transaction_count += 1
        
        print(f"💰 {self.name} paid {amount} {currency_obj} to {service_agent} for {service_type}")
        
        return payment
    
    async def offer_service(
        self,
        service_type: str,
        price: float,
        description: str,
        currency: Union[str, Currency] = Currency.USDC,
        network: Optional[str] = None,
        unit: str = "request",
        category: Optional[str] = None,
        handler: Optional[Callable] = None,
        x402_endpoint: Optional[str] = None
    ) -> Service:
        """
        Offer a paid service to other agents via x402
        
        Args:
            service_type: Type of service being offered
            price: Price per unit in crypto
            description: Service description
            currency: Crypto currency (USDC, ETH, BTC)
            network: Blockchain network
            unit: Pricing unit (request, word, minute, etc.)
            category: Service category
            handler: Function to handle service requests
            x402_endpoint: HTTP endpoint for x402 payments
            
        Returns:
            Service object
        """
        service = await self.disco.register_service(
            agent_id=self.agent_id,
            name=service_type,
            description=description,
            price=price,
            currency=currency,
            network=network,
            unit=unit,
            category=category,
            x402_endpoint=x402_endpoint
        )
        
        self.services.append(service)
        
        # Register payment handler if provided
        if handler:
            self.payment_handlers[service_type] = handler
        
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        print(f"🎵 {self.name} now offers '{service_type}' for {price} {currency_obj} per {unit}")
        
        return service
    
    async def handle_payment_received(self, payment: Payment):
        """
        Handle incoming x402 payment for services
        
        This method is called when the agent receives a payment
        """
        # Update earning tracking
        net_amount = payment.net_amount or payment.amount
        currency_key = str(payment.currency)
        
        if currency_key not in self.total_earned:
            self.total_earned[currency_key] = 0.0
        self.total_earned[currency_key] += net_amount
        self.transaction_count += 1
        
        # Get service details from payment metadata
        service_type = payment.metadata.get('service_type')
        service_params = payment.metadata.get('service_params', {})
        
        print(f"💸 {self.name} received {net_amount} {payment.currency} for {service_type}")
        
        # Call service handler if available
        if service_type and service_type in self.payment_handlers:
            handler = self.payment_handlers[service_type]
            try:
                result = await handler(payment, service_params)
                print(f"✅ {self.name} completed service '{service_type}'")
                return result
            except Exception as e:
                print(f"❌ {self.name} failed to complete service '{service_type}': {e}")
                raise
    
    async def get_wallet_balance(self, currency: Union[str, Currency] = Currency.USDC) -> float:
        """Get current crypto wallet balance"""
        return await self.disco.get_balance(self.agent_id, currency)
    
    async def add_funds(
        self,
        amount: float,
        currency: Union[str, Currency] = Currency.USDC,
        network: Optional[str] = None,
        from_address: Optional[str] = None
    ):
        """Add crypto funds to agent wallet"""
        transaction = await self.disco.add_funds_crypto(
            agent_id=self.agent_id,
            amount=amount,
            currency=currency,
            network=network,
            from_address=from_address
        )
        
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        print(f"💳 {self.name} added {amount} {currency_obj} to wallet")
        return transaction
    
    async def get_earnings_summary(self) -> Dict[str, Any]:
        """Get earnings and spending summary across all currencies"""
        balances = {}
        for currency in self.disco.supported_currencies:
            balance = await self.get_wallet_balance(currency)
            if balance > 0:
                balances[str(currency)] = balance
        
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "current_balances": balances,
            "total_earned": self.total_earned,
            "total_spent": self.total_spent,
            "transaction_count": self.transaction_count,
            "services_offered": len(self.services),
            "supported_currencies": [str(c) for c in self.disco.supported_currencies],
            "supported_networks": self.disco.supported_networks
        }
    
    async def discover_services(
        self,
        service_type: Optional[str] = None,
        max_price: Optional[float] = None,
        currency: Optional[Currency] = None,
        network: Optional[str] = None
    ) -> List[Service]:
        """Discover available x402 services from other agents"""
        return await self.disco.discover_services(
            service_type=service_type,
            max_price=max_price,
            currency=currency,
            network=network
        )
    
    async def find_cheapest_service(self, service_type: str, currency: Optional[Currency] = None) -> Optional[Service]:
        """Find the cheapest provider for a specific service type"""
        services = await self.discover_services(service_type=service_type, currency=currency)
        if not services:
            return None
        
        return min(services, key=lambda s: s.price)
    
    async def make_x402_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        auto_pay: bool = True,
        max_payment: Optional[float] = None,
        currency: Union[str, Currency] = Currency.USDC
    ):
        """Make HTTP request with x402 payment handling"""
        return await self.disco.make_x402_request(
            method=method,
            url=url,
            data=data,
            auto_pay=auto_pay,
            max_payment=max_payment,
            currency=currency
        )
    
    async def create_x402_endpoint(
        self,
        service_type: str,
        price: float,
        currency: Union[str, Currency] = Currency.USDC,
        network: Optional[str] = None
    ) -> str:
        """Create x402 payment required response for HTTP endpoint"""
        if not self.x402_server:
            raise DiscoError("x402 server not initialized. Call initialize() first.")
        
        currency_obj = Currency(currency) if isinstance(currency, str) else currency
        
        # Convert to appropriate units for blockchain
        if currency_obj == Currency.ETH:
            # Convert ETH to wei
            amount_wei = price * 10**18
        elif currency_obj in [Currency.USDC]:
            # USDC has 6 decimals
            amount_wei = price * 10**6
        else:
            amount_wei = price
        
        payment_required = self.x402_server.create_payment_required_response(
            service_type=service_type,
            amount_eth=price if currency_obj == Currency.ETH else price / 1000,  # Simplified conversion
            resource_url=f"/{service_type}",
            description=f"{service_type} service payment",
            network=network or self.disco.default_network
        )
        
        return payment_required
    
    async def get_network_fees(self, network: Optional[str] = None) -> Dict[str, float]:
        """Get current network gas fees"""
        network = network or self.disco.default_network
        return await self.disco.estimate_gas_fee(network)
    
    async def get_exchange_rate(self, from_currency: Currency, to_currency: Currency) -> float:
        """Get real-time exchange rate between crypto currencies"""
        return await self.disco.get_exchange_rate(from_currency, to_currency)
    
    def __getattr__(self, name):
        """Delegate attribute access to the wrapped agent instance"""
        return getattr(self.agent_instance, name)
    
    def __call__(self, *args, **kwargs):
        """Make the wrapper callable if the original agent is callable"""
        if callable(self.agent_instance):
            return self.agent_instance(*args, **kwargs)
        else:
            raise TypeError(f"'{self.agent_class.__name__}' object is not callable")


# Decorator function for easy agent wrapping
def disco_agent(disco_client):
    """
    Decorator to make any agent class Disco x402-enabled
    
    Usage:
        @disco_agent(disco)
        class MyAgent:
            def __init__(self):
                self.agent_id = "my_agent"
                self.name = "My Agent"
                self.wallet_address = "0x..."  # Optional crypto wallet
    """
    def decorator(agent_class):
        return DiscoAgent(agent_class, disco_client)
    return decorator 