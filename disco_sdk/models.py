"""
Disco SDK Data Models
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
    """Available payment methods"""
    WALLET = "wallet"          # Disco wallet balance
    ACH = "ach"               # Bank transfer
    WIRE = "wire"             # Wire transfer
    CARD = "card"             # Credit/debit card
    CRYPTO = "crypto"         # Cryptocurrency
    SWIFT = "swift"           # International wire


class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CHF = "CHF"
    # Crypto
    BTC = "BTC"
    ETH = "ETH"
    USDC = "USDC"


class Payment(BaseModel):
    """Payment transaction model"""
    payment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: str
    amount: float = Field(gt=0, description="Payment amount (must be positive)")
    currency: Currency = Currency.USD
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod = PaymentMethod.WALLET
    description: Optional[str] = None
    reference: Optional[str] = None  # External reference ID
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Financial details (hybrid pricing model)
    disco_fee: Optional[float] = None  # Total Disco fee (percentage + fixed)
    disco_fee_percentage_amount: Optional[float] = None  # Percentage fee amount
    disco_fee_fixed_amount: Optional[float] = None  # Fixed fee amount ($0.30)
    disco_fee_percentage: Optional[float] = None  # Fee percentage rate (2.9%)
    disco_fee_fixed: Optional[float] = None  # Fixed fee rate ($0.30)
    net_amount: Optional[float] = None  # Amount after fees
    exchange_rate: Optional[float] = None  # For currency conversions
    
    # Transaction details
    transaction_id: Optional[str] = None  # External transaction ID
    receipt_url: Optional[str] = None


class PaymentRequest(BaseModel):
    """Request to create a payment"""
    to_agent: str
    amount: float = Field(gt=0, description="Payment amount (must be positive)")
    currency: Currency = Currency.USD
    method: PaymentMethod = PaymentMethod.WALLET
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
    
    # Contact info
    contact_email: Optional[str] = None
    website_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Service(BaseModel):
    """Service offered by an agent"""
    service_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    name: str
    description: str
    price: float = Field(ge=0, description="Service price")
    currency: Currency = Currency.USD
    unit: str = "request"  # per request, per word, per minute, etc.
    
    # Service details
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True
    
    # Pricing model
    pricing_model: str = "fixed"  # fixed, per_unit, tiered
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Wallet(BaseModel):
    """Agent wallet model"""
    wallet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    balances: Dict[Currency, float] = Field(default_factory=dict)
    
    # Wallet status
    is_active: bool = True
    is_verified: bool = False
    
    # Limits
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Transaction(BaseModel):
    """Transaction history model"""
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    payment_id: str
    agent_id: str
    type: str  # "debit", "credit", "fee"
    amount: float
    currency: Currency
    balance_after: float
    description: str
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