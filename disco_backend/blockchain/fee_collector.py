"""
Disco Fee Collection System
Automatically collects fees from each transaction
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from disco_backend.blockchain.payment_processor import PaymentProcessor
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class FeeCollectionError(Exception):
    """Fee collection error"""
    pass

class DiscoFeeCollector:
    """Collects Disco fees from transactions"""
    
    def __init__(self):
        self.payment_processor = PaymentProcessor()
        self.disco_wallets = self._get_disco_wallets()
    
    def _get_disco_wallets(self) -> Dict[str, str]:
        """Get Disco's fee collection wallets for each network"""
        return {
            'ethereum': settings.ETHEREUM_FEE_WALLET,
            'polygon': settings.POLYGON_FEE_WALLET,
            'arbitrum': settings.ARBITRUM_FEE_WALLET,
            'solana': settings.SOLANA_FEE_WALLET,
        }
    
    async def collect_fees(
        self,
        payment_amount: Decimal,
        currency: str,
        network: str,
        from_address: str,
        to_address: str,
        disco_fee: Decimal,
        disco_fee_percentage_amount: Decimal,
        disco_fee_fixed_amount: Decimal
    ) -> Dict[str, Any]:
        """Collect Disco fees from a payment transaction"""
        
        if disco_fee <= 0:
            logger.info("No fees to collect for this transaction")
            return {"status": "no_fees", "collected_amount": 0}
        
        # Get Disco's fee collection wallet for this network
        disco_wallet = self.disco_wallets.get(network)
        if not disco_wallet:
            raise FeeCollectionError(f"No fee collection wallet configured for {network}")
        
        try:
            # Method 1: Split Payment (Recommended)
            # Send net_amount to recipient and disco_fee to Disco in same transaction
            collection_result = await self._split_payment(
                payment_amount=payment_amount,
                currency=currency,
                network=network,
                from_address=from_address,
                recipient_address=to_address,
                disco_address=disco_wallet,
                net_amount=payment_amount - disco_fee,
                disco_fee=disco_fee
            )
            
            logger.info(f"Collected Disco fees: {disco_fee} {currency} on {network}")
            
            return {
                "status": "collected",
                "method": "split_payment",
                "collected_amount": float(disco_fee),
                "currency": currency,
                "network": network,
                "disco_wallet": disco_wallet,
                "transaction_hash": collection_result.get("transaction_hash"),
                "fee_breakdown": {
                    "percentage_fee": float(disco_fee_percentage_amount),
                    "fixed_fee": float(disco_fee_fixed_amount),
                    "total_fee": float(disco_fee)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to collect fees: {e}")
            raise FeeCollectionError(f"Fee collection failed: {e}")
    
    async def _split_payment(
        self,
        payment_amount: Decimal,
        currency: str,
        network: str,
        from_address: str,
        recipient_address: str,
        disco_address: str,
        net_amount: Decimal,
        disco_fee: Decimal
    ) -> Dict[str, Any]:
        """Split payment between recipient and Disco"""
        
        # For ERC-20 tokens, we can use a smart contract to split in one transaction
        # For native currencies, we need two separate transactions
        
        if currency in ['ETH', 'MATIC', 'SOL']:
            # Native currency - send two separate transactions
            return await self._split_native_payment(
                currency=currency,
                network=network,
                from_address=from_address,
                recipient_address=recipient_address,
                disco_address=disco_address,
                net_amount=net_amount,
                disco_fee=disco_fee
            )
        else:
            # ERC-20 token - use smart contract for atomic split
            return await self._split_token_payment(
                currency=currency,
                network=network,
                from_address=from_address,
                recipient_address=recipient_address,
                disco_address=disco_address,
                net_amount=net_amount,
                disco_fee=disco_fee
            )
    
    async def _split_native_payment(
        self,
        currency: str,
        network: str,
        from_address: str,
        recipient_address: str,
        disco_address: str,
        net_amount: Decimal,
        disco_fee: Decimal
    ) -> Dict[str, Any]:
        """Split native currency payment"""
        
        # Get private key for from_address (in production, this would be managed securely)
        private_key = self._get_private_key_for_address(from_address, network)
        
        # Send net amount to recipient
        recipient_tx = await self.payment_processor.send_payment(
            from_address=from_address,
            to_address=recipient_address,
            amount=net_amount,
            currency=currency,
            network=network,
            private_key=private_key
        )
        
        # Send fee to Disco
        fee_tx = await self.payment_processor.send_payment(
            from_address=from_address,
            to_address=disco_address,
            amount=disco_fee,
            currency=currency,
            network=network,
            private_key=private_key
        )
        
        return {
            "transaction_hash": f"{recipient_tx['transaction_hash']},{fee_tx['transaction_hash']}",
            "recipient_tx": recipient_tx['transaction_hash'],
            "fee_tx": fee_tx['transaction_hash'],
            "method": "dual_transaction"
        }
    
    async def _split_token_payment(
        self,
        currency: str,
        network: str,
        from_address: str,
        recipient_address: str,
        disco_address: str,
        net_amount: Decimal,
        disco_fee: Decimal
    ) -> Dict[str, Any]:
        """Split ERC-20 token payment using smart contract"""
        
        # In production, this would call a smart contract that:
        # 1. Transfers net_amount to recipient
        # 2. Transfers disco_fee to Disco
        # 3. All in one atomic transaction
        
        # For now, simulate the smart contract call
        logger.info(f"Smart contract split: {net_amount} to {recipient_address}, {disco_fee} to {disco_address}")
        
        return {
            "transaction_hash": f"split_tx_{datetime.utcnow().timestamp()}",
            "method": "smart_contract_split",
            "contract_address": self._get_split_contract_address(network)
        }
    
    def _get_private_key_for_address(self, address: str, network: str) -> str:
        """Get private key for address (in production, use secure key management)"""
        
        # In production, this would:
        # 1. Look up the address in a secure key management system
        # 2. Use hardware security modules (HSM)
        # 3. Never store private keys in plain text
        
        private_keys = {
            'ethereum': settings.ETHEREUM_PRIVATE_KEY,
            'polygon': settings.POLYGON_PRIVATE_KEY,
            'arbitrum': settings.ARBITRUM_PRIVATE_KEY,
            'solana': settings.SOLANA_PRIVATE_KEY,
        }
        
        return private_keys.get(network, "")
    
    def _get_split_contract_address(self, network: str) -> str:
        """Get smart contract address for payment splitting"""
        
        # In production, these would be deployed smart contracts
        contracts = {
            'ethereum': '0x...',  # Deployed split contract
            'polygon': '0x...',   # Deployed split contract
            'arbitrum': '0x...',  # Deployed split contract
        }
        
        return contracts.get(network, "")
    
    async def get_fee_collection_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        currency: Optional[str] = None,
        network: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of collected fees"""
        
        # In production, this would query the database for fee collection records
        # For now, return a placeholder
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_fees_collected": 0.0,
            "currency": currency or "all",
            "network": network or "all",
            "breakdown": {
                "percentage_fees": 0.0,
                "fixed_fees": 0.0,
                "transaction_count": 0
            }
        }
    
    async def withdraw_fees_to_treasury(
        self,
        currency: str,
        network: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Withdraw collected fees to Disco's treasury wallet"""
        
        disco_wallet = self.disco_wallets.get(network)
        if not disco_wallet:
            raise FeeCollectionError(f"No fee collection wallet for {network}")
        
        # Get current balance
        balance = await self.payment_processor.get_balance(
            address=disco_wallet,
            currency=currency,
            network=network
        )
        
        withdraw_amount = amount or balance
        
        if balance < withdraw_amount:
            raise FeeCollectionError(f"Insufficient balance: {balance} < {withdraw_amount}")
        
        # In production, this would transfer to a cold storage treasury wallet
        logger.info(f"Withdrawing {withdraw_amount} {currency} from {disco_wallet} to treasury")
        
        return {
            "status": "withdrawn",
            "amount": float(withdraw_amount),
            "currency": currency,
            "network": network,
            "from_wallet": disco_wallet,
            "to_treasury": "treasury_wallet_address"
        }
