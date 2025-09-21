"""
Payment API Endpoints
x402-enabled crypto payment processing
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel, Field

from disco_backend.database.connection import get_db
from disco_backend.database.models import Payment, Agent, APIKey
from disco_backend.core.security import verify_api_key
from disco_backend.blockchain.payment_processor import PaymentProcessor
from disco_backend.blockchain.fee_collector import DiscoFeeCollector
from disco_backend.x402.facilitator import X402Facilitator
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for request/response
class PaymentRequest(BaseModel):
    to_agent: str = Field(..., description="Target agent ID")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USDC", description="Currency (ETH, USDC, BTC)")
    network: str = Field(default="polygon", description="Blockchain network")
    description: Optional[str] = Field(None, description="Payment description")
    reference: Optional[str] = Field(None, description="External reference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class PaymentResponse(BaseModel):
    payment_id: str
    from_agent: str
    to_agent: str
    amount: float
    currency: str
    network: str
    status: str
    
    # Fee breakdown (hybrid model)
    disco_fee: float
    disco_fee_percentage_amount: float
    disco_fee_fixed_amount: float
    disco_fee_percentage: float
    disco_fee_fixed: float
    net_amount: float
    
    # Optional fields
    description: Optional[str] = None
    reference: Optional[str] = None
    transaction_hash: Optional[str] = None
    x402_payment_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PaymentListResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    limit: int
    has_more: bool

# Initialize services
payment_processor = PaymentProcessor()
fee_collector = DiscoFeeCollector()
x402_facilitator = X402Facilitator()

@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_request: PaymentRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Create a new crypto payment"""
    
    # Get sender agent (from API key)
    stmt = select(Agent).where(Agent.api_key_id == api_key.id)
    result = await db.execute(stmt)
    from_agent = result.scalar_one_or_none()
    
    if not from_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender agent not found"
        )
    
    # Get recipient agent
    stmt = select(Agent).where(Agent.agent_id == payment_request.to_agent)
    result = await db.execute(stmt)
    to_agent = result.scalar_one_or_none()
    
    if not to_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient agent not found"
        )
    
    # Validate currency and network
    supported_currencies = ["ETH", "USDC", "BTC"]
    supported_networks = ["ethereum", "polygon", "arbitrum", "solana"]
    
    if payment_request.currency not in supported_currencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency {payment_request.currency} not supported. Supported: {supported_currencies}"
        )
    
    if payment_request.network not in supported_networks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Network {payment_request.network} not supported. Supported: {supported_networks}"
        )
    
    # Calculate fees (hybrid model)
    fee_percentage = settings.FEE_PERCENTAGE if api_key.environment == "live" else 0.0
    fee_fixed = settings.FEE_FIXED if api_key.environment == "live" else 0.0
    
    disco_fee_percentage_amount = payment_request.amount * fee_percentage
    disco_fee_fixed_amount = fee_fixed
    disco_fee = disco_fee_percentage_amount + disco_fee_fixed_amount
    net_amount = payment_request.amount - disco_fee
    
    # Create payment record
    payment = Payment(
        payment_id=str(uuid.uuid4()),
        from_agent_id=from_agent.id,
        to_agent_id=to_agent.id,
        amount=payment_request.amount,
        currency=payment_request.currency,
        network=payment_request.network,
        method="crypto",
        disco_fee=disco_fee,
        disco_fee_percentage_amount=disco_fee_percentage_amount,
        disco_fee_fixed_amount=disco_fee_fixed_amount,
        disco_fee_percentage=fee_percentage,
        disco_fee_fixed=fee_fixed,
        net_amount=net_amount,
        status="pending",
        description=payment_request.description,
        reference=payment_request.reference,
        metadata={
            **payment_request.metadata,
            "api_key_environment": api_key.environment,
            "x402": True
        }
    )
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    # Process payment asynchronously
    try:
        # Collect Disco fees first
        fee_collection_result = await fee_collector.collect_fees(
            payment_amount=Decimal(str(payment_request.amount)),
            currency=payment_request.currency,
            network=payment_request.network,
            from_address=from_agent.wallet_address,
            to_address=to_agent.wallet_address,
            disco_fee=Decimal(str(disco_fee)),
            disco_fee_percentage_amount=Decimal(str(disco_fee_percentage_amount)),
            disco_fee_fixed_amount=Decimal(str(disco_fee_fixed_amount))
        )
        
        # Update payment with fee collection details
        payment.metadata.update({
            "fee_collection": fee_collection_result,
            "fee_collected_at": datetime.utcnow().isoformat()
        })
        
        # For x402, we create a payment request that can be verified later
        x402_payment_id = await x402_facilitator.create_payment_request(
            amount=net_amount,
            currency=payment_request.currency,
            network=payment_request.network,
            from_address=from_agent.wallet_address,
            to_address=to_agent.wallet_address,
            payment_id=payment.payment_id
        )
        
        # Update payment with x402 ID
        payment.x402_payment_id = x402_payment_id
        payment.status = "processing"
        payment.processed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(payment)
        
        logger.info(f"Created payment {payment.payment_id} with x402 ID {x402_payment_id}")
        
    except Exception as e:
        logger.error(f"Failed to process payment {payment.payment_id}: {e}")
        payment.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed"
        )
    
    # Return response
    return PaymentResponse(
        payment_id=payment.payment_id,
        from_agent=from_agent.agent_id,
        to_agent=to_agent.agent_id,
        amount=payment.amount,
        currency=payment.currency,
        network=payment.network,
        status=payment.status,
        disco_fee=payment.disco_fee,
        disco_fee_percentage_amount=payment.disco_fee_percentage_amount,
        disco_fee_fixed_amount=payment.disco_fee_fixed_amount,
        disco_fee_percentage=payment.disco_fee_percentage,
        disco_fee_fixed=payment.disco_fee_fixed,
        net_amount=payment.net_amount,
        description=payment.description,
        reference=payment.reference,
        transaction_hash=payment.transaction_hash,
        x402_payment_id=payment.x402_payment_id,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
        completed_at=payment.completed_at,
        metadata=payment.metadata
    )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get payment by ID"""
    
    # Get payment with agent information
    stmt = select(Payment, Agent.agent_id.label("from_agent_id_str"), Agent.agent_id.label("to_agent_id_str")).join(
        Agent, Payment.from_agent_id == Agent.id
    ).where(Payment.payment_id == payment_id)
    
    result = await db.execute(stmt)
    payment_row = result.first()
    
    if not payment_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment = payment_row[0]
    
    # Get agent IDs
    from_agent_stmt = select(Agent.agent_id).where(Agent.id == payment.from_agent_id)
    to_agent_stmt = select(Agent.agent_id).where(Agent.id == payment.to_agent_id)
    
    from_result = await db.execute(from_agent_stmt)
    to_result = await db.execute(to_agent_stmt)
    
    from_agent_id = from_result.scalar_one()
    to_agent_id = to_result.scalar_one()
    
    return PaymentResponse(
        payment_id=payment.payment_id,
        from_agent=from_agent_id,
        to_agent=to_agent_id,
        amount=payment.amount,
        currency=payment.currency,
        network=payment.network,
        status=payment.status,
        disco_fee=payment.disco_fee,
        disco_fee_percentage_amount=payment.disco_fee_percentage_amount,
        disco_fee_fixed_amount=payment.disco_fee_fixed_amount,
        disco_fee_percentage=payment.disco_fee_percentage,
        disco_fee_fixed=payment.disco_fee_fixed,
        net_amount=payment.net_amount,
        description=payment.description,
        reference=payment.reference,
        transaction_hash=payment.transaction_hash,
        x402_payment_id=payment.x402_payment_id,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
        completed_at=payment.completed_at,
        metadata=payment.metadata
    )

@router.get("/", response_model=PaymentListResponse)
async def list_payments(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    network: Optional[str] = Query(None, description="Filter by network"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """List payments with filtering and pagination"""
    
    # Base query
    stmt = select(Payment).join(Agent, Payment.from_agent_id == Agent.id)
    
    # Apply filters
    filters = []
    
    if agent_id:
        filters.append(
            or_(
                Agent.agent_id == agent_id,  # From agent
                Payment.to_agent_id.in_(
                    select(Agent.id).where(Agent.agent_id == agent_id)
                )  # To agent
            )
        )
    
    if status:
        filters.append(Payment.status == status)
    
    if currency:
        filters.append(Payment.currency == currency)
    
    if network:
        filters.append(Payment.network == network)
    
    if filters:
        stmt = stmt.where(and_(*filters))
    
    # Count total
    count_stmt = select(Payment).where(and_(*filters)) if filters else select(Payment)
    total_result = await db.execute(count_stmt)
    total = len(total_result.all())
    
    # Apply pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    
    # Order by creation date (newest first)
    stmt = stmt.order_by(Payment.created_at.desc())
    
    # Execute query
    result = await db.execute(stmt)
    payments = result.scalars().all()
    
    # Convert to response format
    payment_responses = []
    for payment in payments:
        # Get agent IDs
        from_agent_stmt = select(Agent.agent_id).where(Agent.id == payment.from_agent_id)
        to_agent_stmt = select(Agent.agent_id).where(Agent.id == payment.to_agent_id)
        
        from_result = await db.execute(from_agent_stmt)
        to_result = await db.execute(to_agent_stmt)
        
        from_agent_id = from_result.scalar_one()
        to_agent_id = to_result.scalar_one()
        
        payment_responses.append(PaymentResponse(
            payment_id=payment.payment_id,
            from_agent=from_agent_id,
            to_agent=to_agent_id,
            amount=payment.amount,
            currency=payment.currency,
            network=payment.network,
            status=payment.status,
            disco_fee=payment.disco_fee,
            disco_fee_percentage_amount=payment.disco_fee_percentage_amount,
            disco_fee_fixed_amount=payment.disco_fee_fixed_amount,
            disco_fee_percentage=payment.disco_fee_percentage,
            disco_fee_fixed=payment.disco_fee_fixed,
            net_amount=payment.net_amount,
            description=payment.description,
            reference=payment.reference,
            transaction_hash=payment.transaction_hash,
            x402_payment_id=payment.x402_payment_id,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
            completed_at=payment.completed_at,
            metadata=payment.metadata
        ))
    
    has_more = (offset + limit) < total
    
    return PaymentListResponse(
        payments=payment_responses,
        total=total,
        page=page,
        limit=limit,
        has_more=has_more
    )

@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Cancel a pending payment"""
    
    # Get payment
    stmt = select(Payment).where(Payment.payment_id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check if payment can be cancelled
    if payment.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment with status '{payment.status}' cannot be cancelled"
        )
    
    # Cancel payment
    payment.status = "cancelled"
    await db.commit()
    await db.refresh(payment)
    
    logger.info(f"Cancelled payment {payment_id}")
    
    # Get agent IDs for response
    from_agent_stmt = select(Agent.agent_id).where(Agent.id == payment.from_agent_id)
    to_agent_stmt = select(Agent.agent_id).where(Agent.id == payment.to_agent_id)
    
    from_result = await db.execute(from_agent_stmt)
    to_result = await db.execute(to_agent_stmt)
    
    from_agent_id = from_result.scalar_one()
    to_agent_id = to_result.scalar_one()
    
    return PaymentResponse(
        payment_id=payment.payment_id,
        from_agent=from_agent_id,
        to_agent=to_agent_id,
        amount=payment.amount,
        currency=payment.currency,
        network=payment.network,
        status=payment.status,
        disco_fee=payment.disco_fee,
        disco_fee_percentage_amount=payment.disco_fee_percentage_amount,
        disco_fee_fixed_amount=payment.disco_fee_fixed_amount,
        disco_fee_percentage=payment.disco_fee_percentage,
        disco_fee_fixed=payment.disco_fee_fixed,
        net_amount=payment.net_amount,
        description=payment.description,
        reference=payment.reference,
        transaction_hash=payment.transaction_hash,
        x402_payment_id=payment.x402_payment_id,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
        completed_at=payment.completed_at,
        metadata=payment.metadata
    ) 