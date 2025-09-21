"""
x402 Protocol API Endpoints
HTTP 402 payment protocol implementation
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from disco_backend.x402.facilitator import X402Facilitator, X402Error
from disco_backend.blockchain.payment_processor import PaymentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
x402_facilitator = X402Facilitator()
payment_processor = PaymentProcessor()

class X402PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., description="Payment currency")
    network: str = Field(..., description="Blockchain network")
    from_address: str = Field(..., description="Payer wallet address")
    to_address: str = Field(..., description="Recipient wallet address")
    description: Optional[str] = Field(None, description="Payment description")

class X402VerificationRequest(BaseModel):
    signature: str = Field(..., description="Payment signature")
    transaction_hash: Optional[str] = Field(None, description="Blockchain transaction hash")

@router.post("/payment-requests")
async def create_x402_payment_request(
    request: X402PaymentRequest
):
    """Create x402 payment request"""
    
    try:
        x402_payment_id = await x402_facilitator.create_payment_request(
            amount=request.amount,
            currency=request.currency,
            network=request.network,
            from_address=request.from_address,
            to_address=request.to_address,
            payment_id=f"x402_{request.from_address[:8]}"
        )
        
        return {
            "x402_payment_id": x402_payment_id,
            "status": "pending",
            "amount": request.amount,
            "currency": request.currency,
            "network": request.network,
            "expires_in_minutes": 15
        }
        
    except Exception as e:
        logger.error(f"Failed to create x402 payment request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment request: {e}"
        )

@router.get("/payment-requests/{x402_payment_id}")
async def get_x402_payment_status(x402_payment_id: str):
    """Get x402 payment request status"""
    
    try:
        payment_status = await x402_facilitator.get_payment_status(x402_payment_id)
        return payment_status
        
    except X402Error as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {e}"
        )

@router.post("/payment-requests/{x402_payment_id}/verify")
async def verify_x402_payment(
    x402_payment_id: str,
    verification: X402VerificationRequest
):
    """Verify x402 payment"""
    
    try:
        verification_result = await x402_facilitator.verify_payment(
            x402_payment_id=x402_payment_id,
            signature=verification.signature,
            transaction_hash=verification.transaction_hash
        )
        
        return verification_result
        
    except X402Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to verify payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {e}"
        )

@router.post("/payment-requests/{x402_payment_id}/settle")
async def settle_x402_payment(x402_payment_id: str):
    """Settle verified x402 payment"""
    
    try:
        settlement_result = await x402_facilitator.settle_payment(x402_payment_id)
        return settlement_result
        
    except X402Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to settle payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment settlement failed: {e}"
        )

@router.post("/payment-requests/{x402_payment_id}/cancel")
async def cancel_x402_payment(x402_payment_id: str):
    """Cancel pending x402 payment"""
    
    try:
        cancellation_result = await x402_facilitator.cancel_payment(x402_payment_id)
        return cancellation_result
        
    except X402Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to cancel payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment cancellation failed: {e}"
        )

@router.get("/supported")
async def get_x402_supported_features():
    """Get supported x402 features and capabilities"""
    
    return x402_facilitator.get_supported_features()

@router.post("/webhooks/verify")
async def verify_x402_webhook(request: Request):
    """Verify x402 webhook signature"""
    
    # Get signature from headers
    signature = request.headers.get("X-Disco-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing webhook signature"
        )
    
    # Get payload
    payload = await request.body()
    
    try:
        is_valid = await x402_facilitator.verify_webhook_signature(
            payload=payload.decode(),
            signature=signature
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        return {"status": "verified", "signature_valid": True}
        
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook verification failed: {e}"
        )

@router.get("/networks")
async def get_supported_networks():
    """Get supported blockchain networks"""
    
    networks = payment_processor.get_supported_networks()
    return {
        "supported_networks": networks,
        "default_network": "polygon",
        "recommended_networks": ["polygon", "arbitrum"]
    }

@router.get("/networks/{network}/fees")
async def estimate_network_fees(network: str):
    """Estimate transaction fees for network"""
    
    try:
        fee_estimate = await payment_processor.estimate_gas_fee(
            network=network,
            transaction_type="erc20"
        )
        
        return fee_estimate
        
    except Exception as e:
        logger.error(f"Failed to estimate fees for {network}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to estimate fees: {e}"
        )
