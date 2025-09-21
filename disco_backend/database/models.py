"""
Database Models
SQLAlchemy models for Disco backend
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from disco_backend.database.connection import Base

# Enums
payment_status_enum = ENUM(
    'pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded',
    name='payment_status_enum'
)

payment_method_enum = ENUM(
    'crypto', name='payment_method_enum'
)

currency_enum = ENUM(
    'ETH', 'USDC', 'BTC', name='currency_enum'
)

network_enum = ENUM(
    'ethereum', 'polygon', 'arbitrum', 'solana', name='network_enum'
)

class APIKey(Base):
    """API Keys for authentication"""
    __tablename__ = "api_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(255))  # Hashed API key
    environment: Mapped[str] = mapped_column(String(50))  # live, test
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Metadata
    name: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    request_count: Mapped[int] = mapped_column(default=0)
    
    # Enhanced user tracking
    user_email: Mapped[Optional[str]] = mapped_column(String(255))
    organization: Mapped[Optional[str]] = mapped_column(String(255))
    user_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Usage limits and quotas
    rate_limit_per_hour: Mapped[int] = mapped_column(default=1000)
    monthly_quota: Mapped[Optional[int]] = mapped_column()
    current_month_usage: Mapped[int] = mapped_column(default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="api_key")

class Agent(Base):
    """AI Agents registered in the system"""
    __tablename__ = "agents"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
    
    # Agent details
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    capabilities: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Wallet information
    wallet_address: Mapped[str] = mapped_column(String(255), index=True)
    supported_currencies: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    supported_networks: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    api_key = relationship("APIKey", back_populates="agents")
    wallets = relationship("Wallet", back_populates="agent")
    payments_sent = relationship("Payment", foreign_keys="Payment.from_agent_id", back_populates="from_agent")
    payments_received = relationship("Payment", foreign_keys="Payment.to_agent_id", back_populates="to_agent")
    services_offered = relationship("Service", back_populates="agent")

class Service(Base):
    """Services offered by agents"""
    __tablename__ = "services"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    
    # Service details
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Pricing
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(currency_enum)
    network: Mapped[str] = mapped_column(network_enum)
    
    # x402 configuration
    x402_endpoint: Mapped[str] = mapped_column(String(500))
    payment_method: Mapped[str] = mapped_column(payment_method_enum, default='crypto')
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Metadata
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="services_offered")

class Wallet(Base):
    """Agent crypto wallets"""
    __tablename__ = "wallets"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    
    # Wallet details
    address: Mapped[str] = mapped_column(String(255), index=True)
    network: Mapped[str] = mapped_column(network_enum)
    wallet_type: Mapped[str] = mapped_column(String(50), default='hot')  # hot, cold, multisig
    
    # Security
    is_multisig: Mapped[bool] = mapped_column(Boolean, default=False)
    required_signatures: Mapped[Optional[int]] = mapped_column(default=1)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Metadata
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="wallets")
    balances = relationship("WalletBalance", back_populates="wallet")

class WalletBalance(Base):
    """Real-time wallet balances"""
    __tablename__ = "wallet_balances"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id"))
    
    # Balance details
    currency: Mapped[str] = mapped_column(currency_enum)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    reserved: Mapped[float] = mapped_column(Float, default=0.0)  # Reserved for pending transactions
    available: Mapped[float] = mapped_column(Float, default=0.0)  # Available for spending
    
    # Last update
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_sync_block: Mapped[Optional[int]] = mapped_column(default=0)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="balances")
    
    __table_args__ = (
        Index('idx_wallet_currency', 'wallet_id', 'currency', unique=True),
    )

class Payment(Base):
    """Payment transactions"""
    __tablename__ = "payments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Payment parties
    from_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    to_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    
    # Payment details
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(currency_enum)
    network: Mapped[str] = mapped_column(network_enum)
    method: Mapped[str] = mapped_column(payment_method_enum, default='crypto')
    
    # Fee breakdown (hybrid model)
    disco_fee: Mapped[float] = mapped_column(Float, default=0.0)
    disco_fee_percentage_amount: Mapped[float] = mapped_column(Float, default=0.0)
    disco_fee_fixed_amount: Mapped[float] = mapped_column(Float, default=0.0)
    disco_fee_percentage: Mapped[float] = mapped_column(Float, default=0.029)
    disco_fee_fixed: Mapped[float] = mapped_column(Float, default=0.30)
    net_amount: Mapped[float] = mapped_column(Float)
    
    # Status
    status: Mapped[str] = mapped_column(payment_status_enum, default='pending')
    
    # Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    reference: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Blockchain details
    transaction_hash: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    block_number: Mapped[Optional[int]] = mapped_column()
    gas_used: Mapped[Optional[int]] = mapped_column()
    gas_price: Mapped[Optional[float]] = mapped_column(Float)
    
    # x402 details
    x402_payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    x402_signature: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Relationships
    from_agent = relationship("Agent", foreign_keys=[from_agent_id], back_populates="payments_sent")
    to_agent = relationship("Agent", foreign_keys=[to_agent_id], back_populates="payments_received")
    
    __table_args__ = (
        Index('idx_payment_status', 'status'),
        Index('idx_payment_created_at', 'created_at'),
        Index('idx_payment_agents', 'from_agent_id', 'to_agent_id'),
    )

class Transaction(Base):
    """Blockchain transaction records"""
    __tablename__ = "transactions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Transaction details
    hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    network: Mapped[str] = mapped_column(network_enum)
    block_number: Mapped[Optional[int]] = mapped_column()
    block_hash: Mapped[Optional[str]] = mapped_column(String(255))
    transaction_index: Mapped[Optional[int]] = mapped_column()
    
    # Addresses
    from_address: Mapped[str] = mapped_column(String(255), index=True)
    to_address: Mapped[str] = mapped_column(String(255), index=True)
    
    # Value and gas
    value: Mapped[float] = mapped_column(Float)
    gas_limit: Mapped[int] = mapped_column()
    gas_used: Mapped[Optional[int]] = mapped_column()
    gas_price: Mapped[float] = mapped_column(Float)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default='pending')  # pending, confirmed, failed
    confirmations: Mapped[int] = mapped_column(default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_transaction_network', 'network'),
        Index('idx_transaction_addresses', 'from_address', 'to_address'),
        Index('idx_transaction_status', 'status'),
    )

class WebhookEvent(Base):
    """Webhook events for external notifications"""
    __tablename__ = "webhook_events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))  # payment, agent, wallet
    resource_id: Mapped[str] = mapped_column(String(255), index=True)
    
    # Webhook details
    webhook_url: Mapped[str] = mapped_column(String(500))
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON)
    
    # Delivery status
    status: Mapped[str] = mapped_column(String(50), default='pending')  # pending, sent, failed
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=3)
    
    # Response details
    response_status: Mapped[Optional[int]] = mapped_column()
    response_body: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_webhook_status', 'status'),
        Index('idx_webhook_scheduled', 'scheduled_at'),
        Index('idx_webhook_resource', 'resource_type', 'resource_id'),
    ) 

class AuditLog(Base):
    """Comprehensive audit logging for all SDK operations"""
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event identification
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    api_key_id: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Request details
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    sdk_version: Mapped[Optional[str]] = mapped_column(String(50))
    environment: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Event details
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Status
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_api_key', 'api_key_id'),
        Index('idx_audit_timestamp', 'created_at'),
        Index('idx_audit_user', 'user_id'),
    )

class UsageStatistics(Base):
    """Aggregated usage statistics for analytics"""
    __tablename__ = "usage_statistics"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[str] = mapped_column(String(255), index=True)
    
    # Time period
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_type: Mapped[str] = mapped_column(String(20))  # daily, weekly, monthly
    
    # Usage metrics
    total_requests: Mapped[int] = mapped_column(default=0)
    unique_agents: Mapped[int] = mapped_column(default=0)
    total_payments: Mapped[int] = mapped_column(default=0)
    payment_volume: Mapped[float] = mapped_column(Float, default=0.0)
    fees_collected: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Service usage
    services_created: Mapped[int] = mapped_column(default=0)
    services_consumed: Mapped[int] = mapped_column(default=0)
    
    # Error metrics
    error_count: Mapped[int] = mapped_column(default=0)
    error_rate: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Metadata
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_usage_api_key_date', 'api_key_id', 'date'),
        Index('idx_usage_period', 'period_type', 'date'),
    ) 