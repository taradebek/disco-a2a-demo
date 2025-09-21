"""
Disco SDK Data Models - x402 Crypto-Native
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class PaymentStatus(str, Enum):
    """Payment processing status"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Available payment methods - crypto only"""
    WALLET = "wallet"          # Disco wallet balance
    CRYPTO = "crypto"          # Direct crypto transfer
    X402 = "x402"             # x402 protocol payment


class Currency(str, Enum):
    """Supported crypto currencies"""
    # Major cryptocurrencies
    ETH = "ETH"
    BTC = "BTC"
    
    # Stablecoins
    USDC = "USDC"
    USDT = "USDT"
    DAI = "DAI"
    
    # Layer 2 tokens
    MATIC = "MATIC"  # Polygon
    ARB = "ARB"      # Arbitrum


class Network(str, Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    SOLANA = "solana"
    BASE = "base"


class X402Scheme(str, Enum):
    """x402 payment schemes"""
    EXACT = "exact"        # Exact amount payment
    UPTO = "upto"          # Up to amount payment
    STREAMING = "streaming" # Streaming payment


class Payment(BaseModel):
    """Payment transaction model - x402 crypto-native"""
    payment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: str
    amount: float = Field(gt=0, description="Payment amount (must be positive)")
    currency: Currency = Currency.USDC  # Default to USDC stablecoin
    network: Network = Network.ETHEREUM  # Default to Ethereum
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod = PaymentMethod.X402
    description: Optional[str] = None
    reference: Optional[str] = None  # External reference ID
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # x402 specific fields
    x402_version: int = 1
    scheme: X402Scheme = X402Scheme.EXACT
    tx_hash: Optional[str] = None  # Blockchain transaction hash
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    
    # Financial details
    disco_fee: Optional[float] = None  # Disco's percentage fee
    disco_fee_percentage: Optional[float] = None  # Fee percentage applied
    net_amount: Optional[float] = None  # Amount after fees
    
    # x402 payment payload
    x402_payload: Optional[Dict[str, Any]] = None


class PaymentRequest(BaseModel):
    """Request to create a payment - x402 crypto-native"""
    to_agent: str
    amount: float = Field(gt=0, description="Payment amount (must be positive)")
    currency: Currency = Currency.USDC
    network: Network = Network.ETHEREUM
    method: PaymentMethod = PaymentMethod.X402
    scheme: X402Scheme = X402Scheme.EXACT
    description: Optional[str] = None
    reference: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    """Agent registration model"""
    agent_id: str
    name: str
    description: Optional[str] = None
    owner_id: str  # Developer/organization ID
    capabilities: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    
    # Agent status
    is_active: bool = True
    is_verified: bool = False
    
    # Crypto wallet addresses
    wallet_addresses: Dict[Network, str] = Field(default_factory=dict)
    
    # Contact info
    contact_email: Optional[str] = None
    website_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Service(BaseModel):
    """Service offered by an agent - crypto pricing"""
    service_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    name: str
    description: str
    price: float = Field(ge=0, description="Service price")
    currency: Currency = Currency.USDC  # Default to USDC
    network: Network = Network.ETHEREUM  # Default to Ethereum
    unit: str = "request"  # per request, per word, per minute, etc.
    
    # Service details
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True
    
    # Pricing model
    pricing_model: str = "fixed"  # fixed, per_unit, tiered
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # x402 integration
    x402_enabled: bool = True
    x402_scheme: X402Scheme = X402Scheme.EXACT
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Wallet(BaseModel):
    """Agent wallet model - crypto multi-network"""
    wallet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    
    # Multi-network balances
    balances: Dict[Network, Dict[Currency, float]] = Field(default_factory=dict)
    
    # Wallet status
    is_active: bool = True
    is_verified: bool = False
    
    # Network-specific addresses
    addresses: Dict[Network, str] = Field(default_factory=dict)
    
    # Limits (in USD equivalent)
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Transaction(BaseModel):
    """Transaction history model - crypto focused"""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    payment_id: str
    agent_id: str
    type: str  # "debit", "credit", "fee"
    amount: float
    currency: Currency
    network: Network
    balance_after: float
    description: str
    tx_hash: Optional[str] = None  # Blockchain transaction hash
    timestamp: datetime = Field(default_factory=datetime.now)


class ApiKey(BaseModel):
    """API key model for developers"""
    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key_prefix: str  # "dk_live_" or "dk_test_"
    key_hash: str  # Hashed version of the full key
    name: str
    owner_id: str
    
    # Permissions
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True
    
    # Usage tracking
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class WebhookEvent(BaseModel):
    """Webhook event model"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # "payment.completed", "payment.failed", etc.
    data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3


class X402PaymentRequirements(BaseModel):
    """x402 Payment Requirements - following Coinbase spec"""
    scheme: X402Scheme
    network: Network
    max_amount_required: str  # Amount in wei/smallest unit
    resource: str
    description: str
    mime_type: str = "application/json"
    pay_to: str  # Agent wallet address
    max_timeout_seconds: int = 300
    asset: str  # Token contract address
    extra: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None


class X402PaymentPayload(BaseModel):
    """x402 Payment Payload - following Coinbase spec"""
    x402_version: int = 1
    scheme: X402Scheme
    network: Network
    payload: Dict[str, Any]  # Scheme-specific payload


class FacilitatorConfig(BaseModel):
    """x402 Facilitator configuration"""
    facilitator_url: str
    supported_networks: List[Network]
    supported_currencies: List[Currency]
    supported_schemes: List[X402Scheme]
    is_active: bool = True
