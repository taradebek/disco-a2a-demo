"""
Disco SDK Exceptions
"""


class DiscoError(Exception):
    """Base exception for all Disco SDK errors"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code or "DISCO_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(DiscoError):
    """Raised when API key authentication fails"""
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class PaymentError(DiscoError):
    """Base class for payment-related errors"""
    pass


class InsufficientFundsError(PaymentError):
    """Raised when agent has insufficient funds for payment"""
    def __init__(self, required: float, available: float, currency: str = "USD"):
        message = f"Insufficient funds: required {required} {currency}, available {available} {currency}"
        super().__init__(message, "INSUFFICIENT_FUNDS", {
            "required": required,
            "available": available,
            "currency": currency
        })


class PaymentMethodError(PaymentError):
    """Raised when payment method is invalid or unavailable"""
    def __init__(self, method: str, message: str = None):
        message = message or f"Payment method '{method}' is not available"
        super().__init__(message, "PAYMENT_METHOD_ERROR", {"method": method})


class AgentNotFoundError(DiscoError):
    """Raised when agent is not found"""
    def __init__(self, agent_id: str):
        message = f"Agent '{agent_id}' not found"
        super().__init__(message, "AGENT_NOT_FOUND", {"agent_id": agent_id})


class ServiceNotFoundError(DiscoError):
    """Raised when service is not found"""
    def __init__(self, service_id: str = None, service_type: str = None):
        if service_id:
            message = f"Service '{service_id}' not found"
            details = {"service_id": service_id}
        else:
            message = f"Service type '{service_type}' not found"
            details = {"service_type": service_type}
        super().__init__(message, "SERVICE_NOT_FOUND", details)


class RateLimitError(DiscoError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, retry_after: int = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, "RATE_LIMIT_EXCEEDED", {"retry_after": retry_after})


class ValidationError(DiscoError):
    """Raised when input validation fails"""
    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error for '{field}': {message}", "VALIDATION_ERROR", {
            "field": field,
            "validation_message": message
        })


class NetworkError(DiscoError):
    """Raised when network/API communication fails"""
    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message, "NETWORK_ERROR")


class ServerError(DiscoError):
    """Raised when server returns 5xx error"""
    def __init__(self, status_code: int, message: str = "Server error occurred"):
        super().__init__(f"Server error ({status_code}): {message}", "SERVER_ERROR", {
            "status_code": status_code
        })


class WebhookError(DiscoError):
    """Raised when webhook processing fails"""
    def __init__(self, message: str = "Webhook processing failed"):
        super().__init__(message, "WEBHOOK_ERROR")
