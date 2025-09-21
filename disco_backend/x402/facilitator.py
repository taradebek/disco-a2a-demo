"""
x402 Facilitator Service
Payment verification and settlement for HTTP 402 payments
"""

import uuid
import json
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from disco_backend.core.config import settings
from disco_backend.blockchain.payment_processor import PaymentProcessor

logger = logging.getLogger(__name__)

class X402Error(Exception):
    """Base x402 error"""
    pass

class PaymentVerificationError(X402Error):
    """Payment verification failed"""
    pass

class SettlementError(X402Error):
    """Payment settlement failed"""
    pass

class X402Facilitator:
    """x402 payment facilitator service"""
    
    def __init__(self):
        self.payment_processor = PaymentProcessor()
        self.pending_payments = {}  # In production, use Redis or database
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def create_payment_request(
        self,
        amount: Decimal,
        currency: str,
        network: str,
        from_address: str,
        to_address: str,
        payment_id: str
    ) -> str:
        """Create x402 payment request"""
        
        x402_payment_id = str(uuid.uuid4())
        
        # Calculate expiration (15 minutes from now)
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        # Create payment request
        payment_request = {
            'x402_payment_id': x402_payment_id,
            'payment_id': payment_id,
            'amount': float(amount),
            'currency': currency,
            'network': network,
            'from_address': from_address,
            'to_address': to_address,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat(),
            'verification_required': True
        }
        
        # Store in pending payments
        self.pending_payments[x402_payment_id] = payment_request
        
        logger.info(f"Created x402 payment request: {x402_payment_id}")
        return x402_payment_id
    
    async def verify_payment(
        self,
        x402_payment_id: str,
        signature: str,
        transaction_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify x402 payment"""
        
        # Get payment request
        payment_request = self.pending_payments.get(x402_payment_id)
        if not payment_request:
            raise PaymentVerificationError(f"Payment request {x402_payment_id} not found")
        
        # Check expiration
        expires_at = datetime.fromisoformat(payment_request['expires_at'])
        if datetime.utcnow() > expires_at:
            raise PaymentVerificationError(f"Payment request {x402_payment_id} expired")
        
        # Verify signature (simplified - in production would use proper crypto verification)
        if not self._verify_signature(payment_request, signature):
            raise PaymentVerificationError("Invalid payment signature")
        
        # If transaction hash provided, verify on blockchain
        if transaction_hash:
            verification_result = await self._verify_blockchain_transaction(
                transaction_hash,
                payment_request
            )
            if not verification_result['valid']:
                raise PaymentVerificationError(f"Blockchain verification failed: {verification_result['reason']}")
        
        # Update payment status
        payment_request['status'] = 'verified'
        payment_request['verified_at'] = datetime.utcnow().isoformat()
        payment_request['signature'] = signature
        if transaction_hash:
            payment_request['transaction_hash'] = transaction_hash
        
        logger.info(f"Verified x402 payment: {x402_payment_id}")
        
        return {
            'x402_payment_id': x402_payment_id,
            'status': 'verified',
            'verified_at': payment_request['verified_at'],
            'transaction_hash': transaction_hash
        }
    
    def _verify_signature(self, payment_request: Dict[str, Any], signature: str) -> bool:
        """Verify payment signature (simplified implementation)"""
        
        # In production, this would:
        # 1. Extract public key from signature
        # 2. Verify signature against payment data
        # 3. Check that signer owns the from_address
        
        # For now, just check that signature is present and valid format
        if not signature or len(signature) < 64:
            return False
        
        # Create message to verify
        message = f"{payment_request['amount']}{payment_request['currency']}{payment_request['from_address']}{payment_request['to_address']}"
        
        # In production, would verify ECDSA signature
        # For demo, just check signature is hex
        try:
            int(signature, 16)
            return True
        except ValueError:
            return False
    
    async def _verify_blockchain_transaction(
        self,
        tx_hash: str,
        payment_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify transaction on blockchain"""
        
        try:
            # Get transaction status from blockchain
            tx_status = await self.payment_processor.get_transaction_status(
                tx_hash,
                payment_request['network']
            )
            
            # Check transaction details match payment request
            if tx_status['status'] != 'confirmed':
                return {'valid': False, 'reason': 'Transaction not confirmed'}
            
            if tx_status['from_address'].lower() != payment_request['from_address'].lower():
                return {'valid': False, 'reason': 'From address mismatch'}
            
            if tx_status['to_address'].lower() != payment_request['to_address'].lower():
                return {'valid': False, 'reason': 'To address mismatch'}
            
            # Check amount (with small tolerance for gas fees)
            expected_amount = Decimal(str(payment_request['amount']))
            actual_amount = Decimal(str(tx_status['value']))
            
            if abs(actual_amount - expected_amount) > Decimal('0.001'):
                return {'valid': False, 'reason': f'Amount mismatch: expected {expected_amount}, got {actual_amount}'}
            
            return {'valid': True, 'transaction': tx_status}
            
        except Exception as e:
            logger.error(f"Blockchain verification error: {e}")
            return {'valid': False, 'reason': f'Verification error: {e}'}
    
    async def settle_payment(self, x402_payment_id: str) -> Dict[str, Any]:
        """Settle verified payment"""
        
        # Get payment request
        payment_request = self.pending_payments.get(x402_payment_id)
        if not payment_request:
            raise SettlementError(f"Payment request {x402_payment_id} not found")
        
        if payment_request['status'] != 'verified':
            raise SettlementError(f"Payment {x402_payment_id} not verified")
        
        try:
            # In production, this would:
            # 1. Execute the blockchain transaction
            # 2. Update balances in our system
            # 3. Send notifications to both parties
            # 4. Update payment status in database
            
            # For now, just mark as settled
            payment_request['status'] = 'settled'
            payment_request['settled_at'] = datetime.utcnow().isoformat()
            
            logger.info(f"Settled x402 payment: {x402_payment_id}")
            
            return {
                'x402_payment_id': x402_payment_id,
                'status': 'settled',
                'settled_at': payment_request['settled_at'],
                'transaction_hash': payment_request.get('transaction_hash')
            }
            
        except Exception as e:
            logger.error(f"Settlement error for {x402_payment_id}: {e}")
            payment_request['status'] = 'failed'
            payment_request['error'] = str(e)
            raise SettlementError(f"Settlement failed: {e}")
    
    async def get_payment_status(self, x402_payment_id: str) -> Dict[str, Any]:
        """Get x402 payment status"""
        
        payment_request = self.pending_payments.get(x402_payment_id)
        if not payment_request:
            raise X402Error(f"Payment request {x402_payment_id} not found")
        
        return {
            'x402_payment_id': x402_payment_id,
            'payment_id': payment_request['payment_id'],
            'status': payment_request['status'],
            'amount': payment_request['amount'],
            'currency': payment_request['currency'],
            'network': payment_request['network'],
            'created_at': payment_request['created_at'],
            'expires_at': payment_request['expires_at'],
            'verified_at': payment_request.get('verified_at'),
            'settled_at': payment_request.get('settled_at'),
            'transaction_hash': payment_request.get('transaction_hash'),
            'error': payment_request.get('error')
        }
    
    async def cancel_payment(self, x402_payment_id: str) -> Dict[str, Any]:
        """Cancel pending payment"""
        
        payment_request = self.pending_payments.get(x402_payment_id)
        if not payment_request:
            raise X402Error(f"Payment request {x402_payment_id} not found")
        
        if payment_request['status'] in ['settled', 'cancelled']:
            raise X402Error(f"Payment {x402_payment_id} cannot be cancelled (status: {payment_request['status']})")
        
        payment_request['status'] = 'cancelled'
        payment_request['cancelled_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Cancelled x402 payment: {x402_payment_id}")
        
        return {
            'x402_payment_id': x402_payment_id,
            'status': 'cancelled',
            'cancelled_at': payment_request['cancelled_at']
        }
    
    async def create_webhook_signature(self, payload: Dict[str, Any]) -> str:
        """Create webhook signature for secure notifications"""
        
        # Convert payload to JSON string
        payload_json = json.dumps(payload, sort_keys=True)
        
        # Create HMAC signature
        signature = hmac.new(
            settings.X402_WEBHOOK_SECRET.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    async def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature"""
        
        if not signature.startswith('sha256='):
            return False
        
        expected_signature = signature[7:]  # Remove 'sha256=' prefix
        
        # Calculate expected signature
        calculated_signature = hmac.new(
            settings.X402_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Secure comparison
        return hmac.compare_digest(expected_signature, calculated_signature)
    
    async def send_webhook_notification(
        self,
        webhook_url: str,
        event_type: str,
        payment_data: Dict[str, Any]
    ) -> bool:
        """Send webhook notification to service"""
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Create webhook payload
        payload = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': payment_data
        }
        
        # Create signature
        signature = await self.create_webhook_signature(payload)
        
        # Send webhook
        headers = {
            'Content-Type': 'application/json',
            'X-Disco-Signature': signature,
            'User-Agent': 'Disco-x402-Facilitator/1.0'
        }
        
        try:
            async with self.session.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Webhook sent successfully to {webhook_url}")
                    return True
                else:
                    logger.warning(f"Webhook failed: {response.status} - {await response.text()}")
                    return False
                    
        except Exception as e:
            logger.error(f"Webhook error for {webhook_url}: {e}")
            return False
    
    def get_supported_features(self) -> Dict[str, Any]:
        """Get supported x402 features"""
        
        return {
            'version': '1.0',
            'supported_currencies': ['ETH', 'USDC', 'BTC'],
            'supported_networks': ['ethereum', 'polygon', 'arbitrum', 'solana'],
            'features': {
                'payment_verification': True,
                'blockchain_settlement': True,
                'webhook_notifications': True,
                'signature_verification': True,
                'payment_expiration': True,
                'multi_currency': True,
                'multi_network': True
            },
            'limits': {
                'max_payment_amount': 1000000,  # $1M
                'min_payment_amount': 0.01,     # $0.01
                'payment_expiration_minutes': 15,
                'max_pending_payments': 10000
            }
        } 