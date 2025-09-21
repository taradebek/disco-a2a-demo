"""
Disco Backend Configuration
Environment-based configuration management
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    ALLOWED_HOSTS: str = Field(default="*", env="ALLOWED_HOSTS")
    ALLOWED_ORIGINS: str = Field(default="*", env="ALLOWED_ORIGINS")
    
    # Database Configuration
    DATABASE_URL: str = Field(default="test_value", env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Configuration
    REDIS_URL: str = Field(default="test_value", env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")
    
    # Security
    SECRET_KEY: str = Field(default="test_value", env="SECRET_KEY")
    API_KEY_PREFIX_LIVE: str = Field(default="dk_live_", env="API_KEY_PREFIX_LIVE")
    API_KEY_PREFIX_TEST: str = Field(default="dk_test_", env="API_KEY_PREFIX_TEST")
    
    # Blockchain Configuration
    ETHEREUM_RPC_URL: str = Field(default="test_value", env="ETHEREUM_RPC_URL")
    POLYGON_RPC_URL: str = Field(default="test_value", env="POLYGON_RPC_URL")
    ARBITRUM_RPC_URL: str = Field(default="test_value", env="ARBITRUM_RPC_URL")
    SOLANA_RPC_URL: str = Field(default="test_value", env="SOLANA_RPC_URL")
    
    # Blockchain Private Keys (for hot wallets)
    ETHEREUM_PRIVATE_KEY: str = Field(default="test_value", env="ETHEREUM_PRIVATE_KEY")
    POLYGON_PRIVATE_KEY: str = Field(default="test_value", env="POLYGON_PRIVATE_KEY")
    ARBITRUM_PRIVATE_KEY: str = Field(default="test_value", env="ARBITRUM_PRIVATE_KEY")
    SOLANA_PRIVATE_KEY: str = Field(default="test_value", env="SOLANA_PRIVATE_KEY")
    
    # External Services
    COINGECKO_API_KEY: Optional[str] = Field(default=None, env="COINGECKO_API_KEY")
    COINMARKETCAP_API_KEY: Optional[str] = Field(default=None, env="COINMARKETCAP_API_KEY")
    CHAINLINK_RPC_URL: Optional[str] = Field(default=None, env="CHAINLINK_RPC_URL")
    
    # x402 Configuration
    X402_FACILITATOR_URL: str = Field(default="test_value", env="X402_FACILITATOR_URL")
    X402_WEBHOOK_SECRET: str = Field(default="test_value", env="X402_WEBHOOK_SECRET")
    
    # Fee Configuration
    FEE_PERCENTAGE: float = Field(default=0.029, env="FEE_PERCENTAGE")  # 2.9%
    FEE_FIXED: float = Field(default=0.30, env="FEE_FIXED")  # $0.30
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=200, env="RATE_LIMIT_BURST")
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be development, staging, or production")
        return v
    
    @validator("ALLOWED_HOSTS", "ALLOWED_ORIGINS", pre=True)
    def parse_list_from_env(cls, v):
        if isinstance(v, list):
            return ",".join(v)
        if isinstance(v, str):
            return v
        return str(v)
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


    # Fee Collection Wallets
    ETHEREUM_FEE_WALLET: str = Field(default="test_value", env="ETHEREUM_FEE_WALLET")
    POLYGON_FEE_WALLET: str = Field(default="test_value", env="POLYGON_FEE_WALLET")
    ARBITRUM_FEE_WALLET: str = Field(default="test_value", env="ARBITRUM_FEE_WALLET")
    SOLANA_FEE_WALLET: str = Field(default="test_value", env="SOLANA_FEE_WALLET")
    
    # Treasury Wallet (for fee withdrawals)
    TREASURY_WALLET: str = Field(default="test_value", env="TREASURY_WALLET")


    @property
    def allowed_hosts_list(self) -> List[str]:
        """Convert ALLOWED_HOSTS string to list"""
        if isinstance(self.ALLOWED_HOSTS, list):
            return self.ALLOWED_HOSTS
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert ALLOWED_ORIGINS string to list"""
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

# Global settings instance
settings = Settings() 
    
