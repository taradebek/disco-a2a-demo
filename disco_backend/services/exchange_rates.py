"""
Real-time cryptocurrency exchange rate service
Supports multiple providers with fallback and caching
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, List
import httpx
import redis.asyncio as redis
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class ExchangeRateService:
    """Real-time cryptocurrency exchange rate service"""
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 60  # 1 minute cache
        self.providers = [
            self._coingecko_provider,
            self._coinmarketcap_provider,
            self._cryptocompare_provider
        ]
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Exchange rate service initialized with Redis caching")
        except Exception as e:
            logger.warning(f"Redis not available for exchange rates: {e}")
            self.redis_client = None
    
    async def get_exchange_rate(self, from_currency: str, to_currency: str = "USD") -> Decimal:
        """Get exchange rate between two currencies"""
        cache_key = f"exchange_rate:{from_currency.upper()}:{to_currency.upper()}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached_rate = await self.redis_client.get(cache_key)
                if cached_rate:
                    return Decimal(cached_rate.decode())
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
        
        # Try providers in order
        for provider in self.providers:
            try:
                rate = await provider(from_currency, to_currency)
                if rate and rate > 0:
                    # Cache the result
                    if self.redis_client:
                        try:
                            await self.redis_client.setex(
                                cache_key, 
                                self.cache_ttl, 
                                str(rate)
                            )
                        except Exception as e:
                            logger.warning(f"Cache write failed: {e}")
                    
                    logger.info(f"Exchange rate {from_currency}/{to_currency}: {rate}")
                    return rate
            except Exception as e:
                logger.warning(f"Provider {provider.__name__} failed: {e}")
                continue
        
        raise Exception(f"Could not get exchange rate for {from_currency}/{to_currency}")
    
    async def get_multiple_rates(self, currencies: List[str], to_currency: str = "USD") -> Dict[str, Decimal]:
        """Get exchange rates for multiple currencies"""
        tasks = [self.get_exchange_rate(currency, to_currency) for currency in currencies]
        rates = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for currency, rate in zip(currencies, rates):
            if isinstance(rate, Exception):
                logger.error(f"Failed to get rate for {currency}: {rate}")
                result[currency] = None
            else:
                result[currency] = rate
        
        return result
    
    async def _coingecko_provider(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """CoinGecko API provider"""
        currency_map = {
            "USDC": "usd-coin",
            "ETH": "ethereum", 
            "BTC": "bitcoin",
            "MATIC": "matic-network",
            "SOL": "solana"
        }
        
        coin_id = currency_map.get(from_currency.upper())
        if not coin_id:
            return None
        
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": to_currency.lower(),
            "include_24hr_change": "false"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if coin_id in data and to_currency.lower() in data[coin_id]:
                return Decimal(str(data[coin_id][to_currency.lower()]))
        
        return None
    
    async def _coinmarketcap_provider(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """CoinMarketCap API provider (requires API key)"""
        if not settings.COINMARKETCAP_API_KEY:
            return None
        
        currency_map = {
            "USDC": "3408",
            "ETH": "1027",
            "BTC": "1", 
            "MATIC": "3890",
            "SOL": "5426"
        }
        
        currency_id = currency_map.get(from_currency.upper())
        if not currency_id:
            return None
        
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            "X-CMC_PRO_API_KEY": settings.COINMARKETCAP_API_KEY,
            "Accept": "application/json"
        }
        params = {
            "id": currency_id,
            "convert": to_currency.upper()
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and currency_id in data["data"]:
                quote = data["data"][currency_id]["quote"]
                if to_currency.upper() in quote:
                    return Decimal(str(quote[to_currency.upper()]["price"]))
        
        return None
    
    async def _cryptocompare_provider(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """CryptoCompare API provider"""
        url = "https://min-api.cryptocompare.com/data/price"
        params = {
            "fsym": from_currency.upper(),
            "tsyms": to_currency.upper()
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if to_currency.upper() in data:
                return Decimal(str(data[to_currency.upper()]))
        
        return None
    
    async def get_historical_rates(self, currency: str, days: int = 7) -> List[Dict]:
        """Get historical exchange rates"""
        cache_key = f"historical_rates:{currency}:{days}"
        
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    import json
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Historical cache read failed: {e}")
        
        # Get from CoinGecko
        currency_map = {
            "USDC": "usd-coin",
            "ETH": "ethereum",
            "BTC": "bitcoin", 
            "MATIC": "matic-network",
            "SOL": "solana"
        }
        
        coin_id = currency_map.get(currency.upper())
        if not coin_id:
            return []
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                historical_data = []
                if "prices" in data:
                    for price_data in data["prices"]:
                        historical_data.append({
                            "timestamp": price_data[0],
                            "price": float(price_data[1]),
                            "currency": currency.upper()
                        })
                
                # Cache for 1 hour
                if self.redis_client:
                    try:
                        import json
                        await self.redis_client.setex(
                            cache_key,
                            3600,  # 1 hour
                            json.dumps(historical_data)
                        )
                    except Exception as e:
                        logger.warning(f"Historical cache write failed: {e}")
                
                return historical_data
                
        except Exception as e:
            logger.error(f"Failed to get historical rates: {e}")
            return []

# Global instance
exchange_rate_service = ExchangeRateService()
