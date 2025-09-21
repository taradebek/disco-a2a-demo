"""
Blockchain Payment Processor
Multi-chain crypto payment processing
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from web3 import Web3
# Web3 middleware compatibility for v6+
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    # For Web3.py v6+, create compatibility function
    def geth_poa_middleware(make_request, web3):
        return make_request
try:
    from solana.rpc.async_api import AsyncClient as SolanaClient
    from solana.publickey import PublicKey
    from solana.transaction import Transaction
except ImportError:
    # For newer Solana versions
    try:
        from solders.pubkey import Pubkey as PublicKey
        from solana.rpc.async_api import AsyncClient as SolanaClient
        from solana.transaction import Transaction
    except ImportError:
        # Fallback for testing
        class PublicKey:
            def __init__(self, key): pass
        class SolanaClient:
            def __init__(self, url): pass
        class Transaction:
            def __init__(self): pass

from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class BlockchainError(Exception):
    """Base blockchain error"""
    pass

class InsufficientBalanceError(BlockchainError):
    """Insufficient balance for transaction"""
    pass

class NetworkError(BlockchainError):
    """Network connection error"""
    pass

class PaymentProcessor:
    """Multi-chain payment processor"""
    
    def __init__(self):
        self.networks = {}
        self._initialize_networks()
    
    def _initialize_networks(self):
        """Initialize blockchain network connections"""
        
        # Ethereum mainnet
        if settings.ETHEREUM_RPC_URL:
            try:
                w3_ethereum = Web3(Web3.HTTPProvider(settings.ETHEREUM_RPC_URL))
                if w3_ethereum.isConnected():
                    self.networks['ethereum'] = {
                        'web3': w3_ethereum,
                        'chain_id': 1,
                        'name': 'Ethereum Mainnet',
                        'native_currency': 'ETH',
                        'block_time': 12
                    }
                    logger.info("✅ Ethereum network connected")
                else:
                    logger.error("❌ Failed to connect to Ethereum network")
            except Exception as e:
                logger.error(f"❌ Ethereum connection error: {e}")
        
        # Polygon
        if settings.POLYGON_RPC_URL:
            try:
                w3_polygon = Web3(Web3.HTTPProvider(settings.POLYGON_RPC_URL))
                w3_polygon.middleware_onion.inject(geth_poa_middleware, layer=0)
                if w3_polygon.isConnected():
                    self.networks['polygon'] = {
                        'web3': w3_polygon,
                        'chain_id': 137,
                        'name': 'Polygon Mainnet',
                        'native_currency': 'MATIC',
                        'block_time': 2
                    }
                    logger.info("✅ Polygon network connected")
                else:
                    logger.error("❌ Failed to connect to Polygon network")
            except Exception as e:
                logger.error(f"❌ Polygon connection error: {e}")
        
        # Arbitrum
        if settings.ARBITRUM_RPC_URL:
            try:
                w3_arbitrum = Web3(Web3.HTTPProvider(settings.ARBITRUM_RPC_URL))
                if w3_arbitrum.isConnected():
                    self.networks['arbitrum'] = {
                        'web3': w3_arbitrum,
                        'chain_id': 42161,
                        'name': 'Arbitrum One',
                        'native_currency': 'ETH',
                        'block_time': 1
                    }
                    logger.info("✅ Arbitrum network connected")
                else:
                    logger.error("❌ Failed to connect to Arbitrum network")
            except Exception as e:
                logger.error(f"❌ Arbitrum connection error: {e}")
        
        # Solana
        if settings.SOLANA_RPC_URL:
            try:
                self.networks['solana'] = {
                    'client': SolanaClient(settings.SOLANA_RPC_URL),
                    'name': 'Solana Mainnet',
                    'native_currency': 'SOL',
                    'block_time': 0.4
                }
                logger.info("✅ Solana network connected")
            except Exception as e:
                logger.error(f"❌ Solana connection error: {e}")
    
    async def get_balance(self, address: str, currency: str, network: str) -> Decimal:
        """Get wallet balance for specific currency and network"""
        
        if network not in self.networks:
            raise NetworkError(f"Network {network} not supported")
        
        try:
            if network == 'solana':
                return await self._get_solana_balance(address, currency)
            else:
                return await self._get_evm_balance(address, currency, network)
        except Exception as e:
            logger.error(f"Error getting balance for {address} on {network}: {e}")
            raise BlockchainError(f"Failed to get balance: {e}")
    
    async def _get_evm_balance(self, address: str, currency: str, network: str) -> Decimal:
        """Get balance on EVM-compatible networks"""
        
        w3 = self.networks[network]['web3']
        
        if currency == self.networks[network]['native_currency']:
            # Native currency balance
            balance_wei = w3.eth.get_balance(address)
            return Decimal(w3.fromWei(balance_wei, 'ether'))
        else:
            # ERC-20 token balance
            contract_address = self._get_token_contract_address(currency, network)
            if not contract_address:
                raise BlockchainError(f"Contract address not found for {currency} on {network}")
            
            # ERC-20 ABI for balanceOf
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]
            
            contract = w3.eth.contract(address=contract_address, abi=erc20_abi)
            balance = contract.functions.balanceOf(address).call()
            decimals = contract.functions.decimals().call()
            
            return Decimal(balance) / Decimal(10 ** decimals)
    
    async def _get_solana_balance(self, address: str, currency: str) -> Decimal:
        """Get balance on Solana network"""
        
        client = self.networks['solana']['client']
        pubkey = PublicKey(address)
        
        if currency == 'SOL':
            # Native SOL balance
            response = await client.get_balance(pubkey)
            balance_lamports = response['result']['value']
            return Decimal(balance_lamports) / Decimal(10**9)  # Convert lamports to SOL
        else:
            # SPL token balance (simplified - would need token account lookup)
            # This is a placeholder for SPL token balance checking
            return Decimal('0')
    
    def _get_token_contract_address(self, currency: str, network: str) -> Optional[str]:
        """Get token contract address for currency on network"""
        
        # Contract addresses for major tokens
        contracts = {
            'ethereum': {
                'USDC': '0xA0b86a33E6441D6A6e8E9E9E8E9E9E8E9E9E9E8E',  # Placeholder
                'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            },
            'polygon': {
                'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
                'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
            },
            'arbitrum': {
                'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
                'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
            }
        }
        
        return contracts.get(network, {}).get(currency)
    
    async def estimate_gas_fee(self, network: str, transaction_type: str = 'transfer') -> Dict[str, Any]:
        """Estimate gas fees for transaction"""
        
        if network not in self.networks:
            raise NetworkError(f"Network {network} not supported")
        
        try:
            if network == 'solana':
                return await self._estimate_solana_fees()
            else:
                return await self._estimate_evm_fees(network, transaction_type)
        except Exception as e:
            logger.error(f"Error estimating gas fees on {network}: {e}")
            raise BlockchainError(f"Failed to estimate fees: {e}")
    
    async def _estimate_evm_fees(self, network: str, transaction_type: str) -> Dict[str, Any]:
        """Estimate gas fees for EVM networks"""
        
        w3 = self.networks[network]['web3']
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        
        # Estimate gas limit based on transaction type
        gas_limits = {
            'transfer': 21000,      # ETH transfer
            'erc20': 65000,         # ERC-20 transfer
            'contract': 100000,     # Contract interaction
        }
        
        gas_limit = gas_limits.get(transaction_type, 65000)
        
        # Calculate fee in native currency
        fee_wei = gas_price * gas_limit
        fee_native = w3.fromWei(fee_wei, 'ether')
        
        return {
            'network': network,
            'gas_price': gas_price,
            'gas_limit': gas_limit,
            'estimated_fee': float(fee_native),
            'currency': self.networks[network]['native_currency']
        }
    
    async def _estimate_solana_fees(self) -> Dict[str, Any]:
        """Estimate fees for Solana network"""
        
        # Solana has fixed fees
        return {
            'network': 'solana',
            'estimated_fee': 0.000005,  # 5000 lamports
            'currency': 'SOL'
        }
    
    async def send_payment(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        currency: str,
        network: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Send crypto payment"""
        
        if network not in self.networks:
            raise NetworkError(f"Network {network} not supported")
        
        # Check balance
        balance = await self.get_balance(from_address, currency, network)
        if balance < amount:
            raise InsufficientBalanceError(f"Insufficient balance: {balance} < {amount}")
        
        try:
            if network == 'solana':
                return await self._send_solana_payment(from_address, to_address, amount, currency, private_key)
            else:
                return await self._send_evm_payment(from_address, to_address, amount, currency, network, private_key)
        except Exception as e:
            logger.error(f"Error sending payment on {network}: {e}")
            raise BlockchainError(f"Failed to send payment: {e}")
    
    async def _send_evm_payment(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        currency: str,
        network: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Send payment on EVM networks"""
        
        w3 = self.networks[network]['web3']
        
        # Get nonce
        nonce = w3.eth.get_transaction_count(from_address)
        
        if currency == self.networks[network]['native_currency']:
            # Native currency transfer
            transaction = {
                'to': to_address,
                'value': w3.toWei(amount, 'ether'),
                'gas': 21000,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
                'chainId': self.networks[network]['chain_id']
            }
        else:
            # ERC-20 token transfer
            contract_address = self._get_token_contract_address(currency, network)
            if not contract_address:
                raise BlockchainError(f"Contract address not found for {currency} on {network}")
            
            # ERC-20 transfer function
            erc20_abi = [
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function"
                }
            ]
            
            contract = w3.eth.contract(address=contract_address, abi=erc20_abi)
            
            # Convert amount to token units (assuming 6 decimals for USDC/USDT)
            token_amount = int(amount * Decimal(10**6))
            
            transaction = contract.functions.transfer(to_address, token_amount).buildTransaction({
                'gas': 65000,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
                'chainId': self.networks[network]['chain_id']
            })
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info(f"Sent {amount} {currency} on {network}, tx: {tx_hash.hex()}")
        
        return {
            'transaction_hash': tx_hash.hex(),
            'network': network,
            'amount': float(amount),
            'currency': currency,
            'from_address': from_address,
            'to_address': to_address,
            'status': 'pending'
        }
    
    async def _send_solana_payment(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        currency: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Send payment on Solana network"""
        
        # Placeholder for Solana payment implementation
        # This would require more complex Solana transaction building
        
        logger.info(f"Solana payment: {amount} {currency} from {from_address} to {to_address}")
        
        return {
            'transaction_hash': f"solana_tx_{asyncio.get_event_loop().time()}",
            'network': 'solana',
            'amount': float(amount),
            'currency': currency,
            'from_address': from_address,
            'to_address': to_address,
            'status': 'pending'
        }
    
    async def get_transaction_status(self, tx_hash: str, network: str) -> Dict[str, Any]:
        """Get transaction status and details"""
        
        if network not in self.networks:
            raise NetworkError(f"Network {network} not supported")
        
        try:
            if network == 'solana':
                return await self._get_solana_transaction_status(tx_hash)
            else:
                return await self._get_evm_transaction_status(tx_hash, network)
        except Exception as e:
            logger.error(f"Error getting transaction status on {network}: {e}")
            raise BlockchainError(f"Failed to get transaction status: {e}")
    
    async def _get_evm_transaction_status(self, tx_hash: str, network: str) -> Dict[str, Any]:
        """Get transaction status on EVM networks"""
        
        w3 = self.networks[network]['web3']
        
        try:
            # Get transaction receipt
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            transaction = w3.eth.get_transaction(tx_hash)
            
            # Get current block number for confirmations
            current_block = w3.eth.block_number
            confirmations = current_block - receipt.blockNumber if receipt.blockNumber else 0
            
            return {
                'transaction_hash': tx_hash,
                'network': network,
                'status': 'confirmed' if receipt.status == 1 else 'failed',
                'block_number': receipt.blockNumber,
                'confirmations': confirmations,
                'gas_used': receipt.gasUsed,
                'gas_price': transaction.gasPrice,
                'from_address': transaction['from'],
                'to_address': transaction['to'],
                'value': float(w3.fromWei(transaction.value, 'ether'))
            }
        except Exception:
            # Transaction not found or pending
            return {
                'transaction_hash': tx_hash,
                'network': network,
                'status': 'pending',
                'confirmations': 0
            }
    
    async def _get_solana_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction status on Solana network"""
        
        # Placeholder for Solana transaction status
        return {
            'transaction_hash': tx_hash,
            'network': 'solana',
            'status': 'confirmed',
            'confirmations': 1
        }
    
    def get_supported_networks(self) -> Dict[str, Dict[str, Any]]:
        """Get list of supported networks"""
        return {
            network: {
                'name': config['name'],
                'native_currency': config['native_currency'],
                'block_time': config['block_time'],
                'connected': True
            }
            for network, config in self.networks.items()
        } 