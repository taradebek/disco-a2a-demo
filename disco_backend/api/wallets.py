"""
Wallet API Endpoints
Crypto wallet management for AI agents
"""

import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field

from disco_backend.database.connection import get_db
from disco_backend.database.models import Wallet, WalletBalance, Agent, APIKey
from disco_backend.core.security import verify_api_key
from disco_backend.blockchain.payment_processor import PaymentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize payment processor
payment_processor = PaymentProcessor()

class WalletResponse(BaseModel):
    wallet_id: str
    agent_id: str
    address: str
    network: str
    wallet_type: str
    is_multisig: bool
    required_signatures: Optional[int]
    is_active: bool
    balances: Dict[str, Dict[str, float]]  # currency -> {balance, available, reserved}
    created_at: str
    updated_at: str

class WalletBalanceResponse(BaseModel):
    currency: str
    balance: float
    reserved: float
    available: float
    last_updated_at: str
    network: str

@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get wallet details with balances"""
    
    # Get wallet
    stmt = select(Wallet, Agent.agent_id).join(
        Agent, Wallet.agent_id == Agent.id
    ).where(Wallet.wallet_id == wallet_id)
    
    result = await db.execute(stmt)
    wallet_row = result.first()
    
    if not wallet_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    wallet, agent_id = wallet_row
    
    # Get wallet balances
    balances_stmt = select(WalletBalance).where(WalletBalance.wallet_id == wallet.id)
    balances_result = await db.execute(balances_stmt)
    balances = balances_result.scalars().all()
    
    # Format balances
    balance_dict = {}
    for balance in balances:
        balance_dict[balance.currency] = {
            "balance": balance.balance,
            "available": balance.available,
            "reserved": balance.reserved
        }
    
    return WalletResponse(
        wallet_id=wallet.wallet_id,
        agent_id=agent_id,
        address=wallet.address,
        network=wallet.network,
        wallet_type=wallet.wallet_type,
        is_multisig=wallet.is_multisig,
        required_signatures=wallet.required_signatures,
        is_active=wallet.is_active,
        balances=balance_dict,
        created_at=wallet.created_at.isoformat(),
        updated_at=wallet.updated_at.isoformat()
    )

@router.get("/{wallet_id}/balance", response_model=List[WalletBalanceResponse])
async def get_wallet_balances(
    wallet_id: str,
    currency: Optional[str] = Query(None, description="Filter by currency"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get wallet balances for all currencies"""
    
    # Get wallet
    stmt = select(Wallet).where(Wallet.wallet_id == wallet_id)
    result = await db.execute(stmt)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Get balances
    balances_stmt = select(WalletBalance).where(WalletBalance.wallet_id == wallet.id)
    if currency:
        balances_stmt = balances_stmt.where(WalletBalance.currency == currency)
    
    balances_result = await db.execute(balances_stmt)
    balances = balances_result.scalars().all()
    
    return [
        WalletBalanceResponse(
            currency=balance.currency,
            balance=balance.balance,
            reserved=balance.reserved,
            available=balance.available,
            last_updated_at=balance.last_updated_at.isoformat(),
            network=wallet.network
        )
        for balance in balances
    ]

@router.post("/{wallet_id}/sync")
async def sync_wallet_balances(
    wallet_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Sync wallet balances with blockchain"""
    
    # Get wallet
    stmt = select(Wallet).where(Wallet.wallet_id == wallet_id)
    result = await db.execute(stmt)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    try:
        # Get supported currencies for this network
        supported_currencies = ["ETH", "USDC", "BTC"] if wallet.network != "solana" else ["SOL"]
        
        synced_balances = {}
        
        for currency in supported_currencies:
            try:
                # Get balance from blockchain
                balance = await payment_processor.get_balance(
                    address=wallet.address,
                    currency=currency,
                    network=wallet.network
                )
                
                # Update or create balance record
                balance_stmt = select(WalletBalance).where(
                    and_(
                        WalletBalance.wallet_id == wallet.id,
                        WalletBalance.currency == currency
                    )
                )
                balance_result = await db.execute(balance_stmt)
                wallet_balance = balance_result.scalar_one_or_none()
                
                if wallet_balance:
                    wallet_balance.balance = float(balance)
                    wallet_balance.available = float(balance) - wallet_balance.reserved
                else:
                    wallet_balance = WalletBalance(
                        wallet_id=wallet.id,
                        currency=currency,
                        balance=float(balance),
                        reserved=0.0,
                        available=float(balance)
                    )
                    db.add(wallet_balance)
                
                synced_balances[currency] = float(balance)
                
            except Exception as e:
                logger.warning(f"Failed to sync {currency} balance: {e}")
                synced_balances[currency] = "error"
        
        await db.commit()
        
        return {
            "wallet_id": wallet_id,
            "network": wallet.network,
            "synced_balances": synced_balances,
            "status": "synced"
        }
        
    except Exception as e:
        logger.error(f"Failed to sync wallet balances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync balances: {e}"
        )

@router.get("/{wallet_id}/transactions")
async def get_wallet_transactions(
    wallet_id: str,
    currency: Optional[str] = Query(None, description="Filter by currency"),
    limit: int = Query(50, ge=1, le=100, description="Number of transactions"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get wallet transaction history"""
    
    # Get wallet
    stmt = select(Wallet).where(Wallet.wallet_id == wallet_id)
    result = await db.execute(stmt)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # In production, this would query the Transaction table
    # For now, return placeholder data
    
    return {
        "wallet_id": wallet_id,
        "address": wallet.address,
        "network": wallet.network,
        "transactions": [],
        "total": 0,
        "message": "Transaction history not yet implemented"
    }

@router.post("/{wallet_id}/deposit")
async def create_deposit_address(
    wallet_id: str,
    currency: str = Query(..., description="Currency to deposit"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Create deposit instructions for wallet"""
    
    # Get wallet
    stmt = select(Wallet).where(Wallet.wallet_id == wallet_id)
    result = await db.execute(stmt)
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Return deposit instructions
    return {
        "wallet_id": wallet_id,
        "deposit_address": wallet.address,
        "network": wallet.network,
        "currency": currency,
        "instructions": f"Send {currency} to {wallet.address} on {wallet.network} network",
        "minimum_deposit": 0.01 if currency == "ETH" else 1.0,
        "confirmation_blocks": 12 if wallet.network == "ethereum" else 1
    }

@router.get("/", response_model=List[WalletResponse])
async def list_agent_wallets(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    network: Optional[str] = Query(None, description="Filter by network"),
    active_only: bool = Query(True, description="Only active wallets"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """List wallets for authenticated user's agents"""
    
    # Base query
    stmt = select(Wallet, Agent.agent_id).join(Agent, Wallet.agent_id == Agent.id)
    filters = []
    
    # Filter by API key
    filters.append(Agent.api_key_id == api_key.id)
    
    if agent_id:
        filters.append(Agent.agent_id == agent_id)
    
    if network:
        filters.append(Wallet.network == network)
    
    if active_only:
        filters.append(Wallet.is_active == True)
    
    stmt = stmt.where(and_(*filters))
    
    result = await db.execute(stmt)
    wallet_rows = result.all()
    
    # Get balances for each wallet
    wallets = []
    for wallet, agent_id in wallet_rows:
        # Get balances
        balances_stmt = select(WalletBalance).where(WalletBalance.wallet_id == wallet.id)
        balances_result = await db.execute(balances_stmt)
        balances = balances_result.scalars().all()
        
        balance_dict = {}
        for balance in balances:
            balance_dict[balance.currency] = {
                "balance": balance.balance,
                "available": balance.available,
                "reserved": balance.reserved
            }
        
        wallets.append(WalletResponse(
            wallet_id=wallet.wallet_id,
            agent_id=agent_id,
            address=wallet.address,
            network=wallet.network,
            wallet_type=wallet.wallet_type,
            is_multisig=wallet.is_multisig,
            required_signatures=wallet.required_signatures,
            is_active=wallet.is_active,
            balances=balance_dict,
            created_at=wallet.created_at.isoformat(),
            updated_at=wallet.updated_at.isoformat()
        ))
    
    return wallets
