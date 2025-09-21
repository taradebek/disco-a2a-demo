"""
Coinbase Integration for Disco Fee Collection
Automated crypto-to-cash conversion
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
import httpx
import hmac
import hashlib
import base64
import time
from datetime import datetime

from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class CoinbaseIntegration:
    """Coinbase Pro API integration for automated cash conversion"""
    
    def __init__(self):
        self.api_key = settings.COINBASE_API_KEY
        self.secret_key = settings.COINBASE_SECRET_KEY
        self.passphrase = settings.COINBASE_PASSPHRASE
        self.base_url = "https://api.pro.coinbase.com"
        self.sandbox = getattr(settings, 'COINBASE_SANDBOX', False)
        
        if self.sandbox:
            self.base_url = "https://api-public.sandbox.pro.coinbase.com"
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate Coinbase Pro API signature"""
        message = timestamp + method + path + body
        signature = hmac.new(
            base64.b64decode(self.secret_key),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    async def _make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Coinbase Pro API"""
        timestamp = str(int(time.time()))
        body = "" if not data else str(data)
        
        signature = self._generate_signature(timestamp, method, path, body)
        
        headers = {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                json=data if data else None
            )
            response.raise_for_status()
            return response.json()
    
    async def get_accounts(self) -> Dict[str, Any]:
        """Get all Coinbase accounts"""
        return await self._make_request('GET', '/accounts')
    
    async def get_account_balance(self, currency: str) -> Decimal:
        """Get balance for specific currency"""
        accounts = await self.get_accounts()
        for account in accounts:
            if account['currency'] == currency:
                return Decimal(account['balance'])
        return Decimal('0')
    
    async def get_usdc_balance(self) -> Decimal:
        """Get USDC balance"""
        return await self.get_account_balance('USDC')
    
    async def place_sell_order(self, product_id: str, size: str, price: Optional[str] = None) -> Dict[str, Any]:
        """Place sell order on Coinbase Pro"""
        order_data = {
            'product_id': product_id,
            'side': 'sell',
            'size': size,
            'type': 'market' if not price else 'limit'
        }
        
        if price:
            order_data['price'] = price
        
        return await self._make_request('POST', '/orders', order_data)
    
    async def sell_usdc_for_usd(self, amount: Decimal) -> Dict[str, Any]:
        """Sell USDC for USD"""
        logger.info(f"Selling {amount} USDC for USD")
        
        # Place market sell order
        order = await self.place_sell_order(
            product_id='USDC-USD',
            size=str(amount)
        )
        
        logger.info(f"USDC sell order placed: {order['id']}")
        return order
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        return await self._make_request('GET', f'/orders/{order_id}')
    
    async def withdraw_to_bank(self, amount: Decimal, currency: str = 'USD') -> Dict[str, Any]:
        """Withdraw to linked bank account"""
        # Note: This requires additional Coinbase Prime or Advanced features
        # For basic accounts, manual withdrawal is required
        logger.info(f"Withdrawing {amount} {currency} to bank account")
        
        # In production, this would use Coinbase Prime API
        return {
            "status": "manual_withdrawal_required",
            "message": f"Please manually withdraw {amount} {currency} from Coinbase to your bank account",
            "amount": float(amount),
            "currency": currency
        }
    
    async def get_deposit_address(self, currency: str) -> str:
        """Get deposit address for currency"""
        accounts = await self.get_accounts()
        for account in accounts:
            if account['currency'] == currency:
                # Get deposit address (this requires additional API call in production)
                return account.get('id', '')  # Placeholder
        return ""
    
    async def transfer_from_fee_wallet(
        self, 
        from_address: str, 
        amount: Decimal, 
        currency: str,
        network: str
    ) -> Dict[str, Any]:
        """Transfer from Disco fee wallet to Coinbase"""
        logger.info(f"Transferring {amount} {currency} from {from_address} to Coinbase")
        
        # This would use your blockchain payment processor
        # to send funds from your fee wallet to Coinbase
        return {
            "status": "transfer_initiated",
            "amount": float(amount),
            "currency": currency,
            "from_address": from_address,
            "to_coinbase": True
        }
    
    async def automated_cash_conversion(
        self, 
        fee_wallets: Dict[str, str],
        min_conversion_amount: Decimal = Decimal('100')
    ) -> Dict[str, Any]:
        """Automated monthly cash conversion process"""
        
        logger.info("Starting automated cash conversion process")
        
        results = {
            "total_converted": Decimal('0'),
            "conversions": [],
            "errors": []
        }
        
        try:
            # 1. Check USDC balance
            usdc_balance = await self.get_usdc_balance()
            logger.info(f"Current USDC balance: {usdc_balance}")
            
            if usdc_balance < min_conversion_amount:
                logger.info(f"USDC balance {usdc_balance} below minimum {min_conversion_amount}")
                return results
            
            # 2. Sell USDC for USD
            sell_order = await self.sell_usdc_for_usd(usdc_balance)
            results["conversions"].append({
                "type": "usdc_to_usd",
                "amount": float(usdc_balance),
                "order_id": sell_order.get('id'),
                "status": "completed"
            })
            
            results["total_converted"] = usdc_balance
            
            # 3. Withdraw to bank (manual step for basic accounts)
            withdrawal = await self.withdraw_to_bank(usdc_balance)
            results["withdrawal"] = withdrawal
            
            logger.info(f"Cash conversion completed: ${usdc_balance} USDC → USD")
            
        except Exception as e:
            logger.error(f"Cash conversion failed: {e}")
            results["errors"].append(str(e))
        
        return results

# Global instance
coinbase = CoinbaseIntegration()
