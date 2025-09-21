"""
Webhook service for payment notifications
Handles webhook delivery, retries, and signature verification
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from disco_backend.database.models import WebhookEvent
from disco_backend.database.connection import get_db
from disco_backend.core.config import settings

logger = logging.getLogger(__name__)

class WebhookService:
    """Webhook delivery and management service"""
    
    def __init__(self):
        self.max_retries = 5
        self.retry_delays = [1, 5, 15, 60, 300]  # seconds
        self.timeout = 30  # seconds
        
    async def send_webhook(self, 
                          url: str, 
                          event_type: str, 
                          data: Dict[str, Any],
                          api_key_id: str) -> bool:
        """Send webhook notification"""
        
        # Create webhook event record
        webhook_event = WebhookEvent(
            api_key_id=api_key_id,
            event_type=event_type,
            payload=data,
            webhook_url=url,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        # Save to database
        async with get_db() as db:
            db.add(webhook_event)
            await db.commit()
            await db.refresh(webhook_event)
        
        # Send webhook
        success = await self._deliver_webhook(webhook_event)
        
        # Update status
        async with get_db() as db:
            webhook_event.status = "delivered" if success else "failed"
            webhook_event.delivered_at = datetime.utcnow() if success else None
            await db.commit()
        
        return success
    
    async def _deliver_webhook(self, webhook_event: WebhookEvent) -> bool:
        """Deliver webhook with retries"""
        
        for attempt in range(self.max_retries):
            try:
                # Create signature
                signature = self._create_signature(
                    webhook_event.payload,
                    settings.WEBHOOK_SECRET
                )
                
                headers = {
                    "Content-Type": "application/json",
                    "X-Disco-Event": webhook_event.event_type,
                    "X-Disco-Signature": signature,
                    "X-Disco-Delivery": str(webhook_event.id),
                    "User-Agent": "Disco-Webhook/1.0"
                }
                
                # Send request
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        webhook_event.webhook_url,
                        json=webhook_event.payload,
                        headers=headers
                    )
                    
                    # Check if successful
                    if 200 <= response.status_code < 300:
                        logger.info(f"Webhook delivered successfully: {webhook_event.id}")
                        return True
                    else:
                        logger.warning(f"Webhook failed with status {response.status_code}: {webhook_event.id}")
                        
            except Exception as e:
                logger.error(f"Webhook delivery attempt {attempt + 1} failed: {e}")
            
            # Wait before retry
            if attempt < self.max_retries - 1:
                delay = self.retry_delays[attempt]
                logger.info(f"Retrying webhook in {delay} seconds: {webhook_event.id}")
                await asyncio.sleep(delay)
        
        logger.error(f"Webhook delivery failed after {self.max_retries} attempts: {webhook_event.id}")
        return False
    
    def _create_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Create HMAC signature for webhook"""
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        provided_signature = signature.replace("sha256=", "")
        return hmac.compare_digest(expected_signature, provided_signature)
    
    async def get_webhook_events(self, 
                                api_key_id: str,
                                event_type: Optional[str] = None,
                                status: Optional[str] = None,
                                limit: int = 100) -> List[WebhookEvent]:
        """Get webhook events for an API key"""
        
        async with get_db() as db:
            query = db.query(WebhookEvent).filter(
                WebhookEvent.api_key_id == api_key_id
            )
            
            if event_type:
                query = query.filter(WebhookEvent.event_type == event_type)
            
            if status:
                query = query.filter(WebhookEvent.status == status)
            
            query = query.order_by(WebhookEvent.created_at.desc()).limit(limit)
            
            result = await query.all()
            return result
    
    async def retry_failed_webhooks(self, hours: int = 24) -> int:
        """Retry failed webhooks from the last N hours"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with get_db() as db:
            failed_webhooks = await db.query(WebhookEvent).filter(
                WebhookEvent.status == "failed",
                WebhookEvent.created_at >= cutoff_time
            ).all()
        
        retry_count = 0
        for webhook in failed_webhooks:
            success = await self._deliver_webhook(webhook)
            if success:
                retry_count += 1
                # Update status
                async with get_db() as db:
                    webhook.status = "delivered"
                    webhook.delivered_at = datetime.utcnow()
                    await db.commit()
        
        logger.info(f"Retried {retry_count} failed webhooks")
        return retry_count
    
    async def get_webhook_stats(self, api_key_id: str) -> Dict[str, Any]:
        """Get webhook statistics for an API key"""
        
        async with get_db() as db:
            # Total webhooks
            total = await db.query(WebhookEvent).filter(
                WebhookEvent.api_key_id == api_key_id
            ).count()
            
            # Delivered webhooks
            delivered = await db.query(WebhookEvent).filter(
                WebhookEvent.api_key_id == api_key_id,
                WebhookEvent.status == "delivered"
            ).count()
            
            # Failed webhooks
            failed = await db.query(WebhookEvent).filter(
                WebhookEvent.api_key_id == api_key_id,
                WebhookEvent.status == "failed"
            ).count()
            
            # Pending webhooks
            pending = await db.query(WebhookEvent).filter(
                WebhookEvent.api_key_id == api_key_id,
                WebhookEvent.status == "pending"
            ).count()
        
        return {
            "total_webhooks": total,
            "delivered": delivered,
            "failed": failed,
            "pending": pending,
            "success_rate": (delivered / total * 100) if total > 0 else 0
        }

# Global instance
webhook_service = WebhookService()
