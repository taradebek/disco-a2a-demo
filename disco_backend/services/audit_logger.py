"""
Comprehensive audit logging service
Tracks all critical operations for security and compliance
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from disco_backend.database.connection import get_db
from disco_backend.database.models import AuditLog
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events"""
    # Authentication
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_USED = "api_key_used"
    
    # Payments
    PAYMENT_CREATED = "payment_created"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_CANCELLED = "payment_cancelled"
    FEE_COLLECTED = "fee_collected"
    
    # Agents
    AGENT_REGISTERED = "agent_registered"
    AGENT_UPDATED = "agent_updated"
    AGENT_DEACTIVATED = "agent_deactivated"
    
    # Services
    SERVICE_REGISTERED = "service_registered"
    SERVICE_UPDATED = "service_updated"
    SERVICE_DEACTIVATED = "service_deactivated"
    
    # Wallets
    WALLET_CREATED = "wallet_created"
    WALLET_FUNDED = "wallet_funded"
    WALLET_BALANCE_CHECKED = "wallet_balance_checked"
    
    # System
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    WEBHOOK_SENT = "webhook_sent"
    WEBHOOK_FAILED = "webhook_failed"
    EXCHANGE_RATE_FETCHED = "exchange_rate_fetched"
    
    # Security
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    FAILED_AUTHENTICATION = "failed_authentication"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

class AuditLogger:
    """Comprehensive audit logging service"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        
        # Set up audit-specific logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    async def log_event(self,
                       event_type: AuditEventType,
                       api_key_id: str,
                       user_id: Optional[str] = None,
                       resource_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None) -> None:
        """Log an audit event"""
        
        audit_data = {
            "event_type": event_type.value,
            "api_key_id": api_key_id,
            "user_id": user_id,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log to database
        await self._log_to_database(audit_data)
        
        # Log to structured logger
        self.logger.info(json.dumps(audit_data, default=str))
    
    async def _log_to_database(self, audit_data: Dict[str, Any]) -> None:
        """Log audit event to database"""
        
        try:
            audit_log = AuditLog(
                event_type=audit_data["event_type"],
                api_key_id=audit_data["api_key_id"],
                user_id=audit_data.get("user_id"),
                resource_id=audit_data.get("resource_id"),
                details=audit_data["details"],
                ip_address=audit_data.get("ip_address"),
                user_agent=audit_data.get("user_agent"),
                created_at=datetime.utcnow()
            )
            
            async with get_db() as db:
                db.add(audit_log)
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to log audit event to database: {e}")
    
    async def log_payment_event(self,
                               event_type: AuditEventType,
                               payment_id: str,
                               api_key_id: str,
                               amount: float,
                               currency: str,
                               from_agent: str,
                               to_agent: str,
                               network: str,
                               disco_fee: float,
                               ip_address: Optional[str] = None) -> None:
        """Log payment-related audit event"""
        
        details = {
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "network": network,
            "disco_fee": disco_fee
        }
        
        await self.log_event(
            event_type=event_type,
            api_key_id=api_key_id,
            resource_id=payment_id,
            details=details,
            ip_address=ip_address
        )
    
    async def log_agent_event(self,
                             event_type: AuditEventType,
                             agent_id: str,
                             api_key_id: str,
                             agent_name: str,
                             wallet_address: str,
                             ip_address: Optional[str] = None) -> None:
        """Log agent-related audit event"""
        
        details = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "wallet_address": wallet_address
        }
        
        await self.log_event(
            event_type=event_type,
            api_key_id=api_key_id,
            resource_id=agent_id,
            details=details,
            ip_address=ip_address
        )
    
    async def log_security_event(self,
                                event_type: AuditEventType,
                                api_key_id: str,
                                details: Dict[str, Any],
                                ip_address: Optional[str] = None) -> None:
        """Log security-related audit event"""
        
        await self.log_event(
            event_type=event_type,
            api_key_id=api_key_id,
            details=details,
            ip_address=ip_address
        )
    
    async def get_audit_logs(self,
                           api_key_id: str,
                           event_type: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 100) -> list:
        """Get audit logs for an API key"""
        
        async with get_db() as db:
            query = db.query(AuditLog).filter(
                AuditLog.api_key_id == api_key_id
            )
            
            if event_type:
                query = query.filter(AuditLog.event_type == event_type)
            
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
            
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)
            
            query = query.order_by(AuditLog.created_at.desc()).limit(limit)
            
            result = await query.all()
            return result
    
    async def get_security_events(self,
                                 hours: int = 24,
                                 limit: int = 100) -> list:
        """Get recent security events"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        security_events = [
            AuditEventType.SUSPICIOUS_ACTIVITY.value,
            AuditEventType.FAILED_AUTHENTICATION.value,
            AuditEventType.UNAUTHORIZED_ACCESS.value,
            AuditEventType.RATE_LIMIT_EXCEEDED.value
        ]
        
        async with get_db() as db:
            query = db.query(AuditLog).filter(
                AuditLog.event_type.in_(security_events),
                AuditLog.created_at >= cutoff_time
            )
            
            query = query.order_by(AuditLog.created_at.desc()).limit(limit)
            
            result = await query.all()
            return result

# Global instance
audit_logger = AuditLogger()
