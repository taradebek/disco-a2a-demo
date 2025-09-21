"""
Disco SDK - Multi-Agent Payment Infrastructure

Enable your AI agents to pay each other seamlessly.
"""

from .disco import Disco
from .agent import DiscoAgent
from .models import Payment, PaymentRequest, PaymentStatus, PaymentMethod, Agent, Service
from .exceptions import DiscoError, PaymentError, AuthenticationError, InsufficientFundsError

__version__ = "1.0.0"
__author__ = "Disco Team"
__email__ = "developers@disco.ai"

__all__ = [
    "Disco",
    "DiscoAgent", 
    "Payment",
    "PaymentRequest",
    "PaymentStatus",
    "PaymentMethod",
    "Agent",
    "Service",
    "DiscoError",
    "PaymentError",
    "AuthenticationError",
    "InsufficientFundsError"
]
