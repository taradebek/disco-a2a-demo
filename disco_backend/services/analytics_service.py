"""
Analytics Service for SDK Usage Tracking
Provides comprehensive usage analytics and insights
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import func, desc, and_
from disco_backend.database.connection import get_db
from disco_backend.database.models import (
    APIKey, Agent, Payment, Service, AuditLog, UsageStatistics
)
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for tracking and analyzing SDK usage"""
    
    async def track_api_usage(self, 
                             api_key_id: str,
                             endpoint: str,
                             method: str,
                             ip_address: Optional[str] = None,
                             user_agent: Optional[str] = None,
                             success: bool = True,
                             error_message: Optional[str] = None,
                             response_time_ms: Optional[float] = None) -> None:
        """Track API usage for analytics"""
        
        try:
            # Create audit log entry
            audit_log = AuditLog(
                event_type="api_request",
                api_key_id=api_key_id,
                ip_address=ip_address,
                user_agent=user_agent,
                sdk_version=self._extract_sdk_version(user_agent),
                success=success,
                error_message=error_message,
                details={
                    "endpoint": endpoint,
                    "method": method,
                    "response_time_ms": response_time_ms
                }
            )
            
            async with get_db() as db:
                db.add(audit_log)
                
                # Update API key usage statistics
                api_key = await db.query(APIKey).filter(APIKey.key_id == api_key_id).first()
                if api_key:
                    api_key.request_count += 1
                    api_key.last_used_at = datetime.utcnow()
                    api_key.current_month_usage += 1
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to track API usage: {e}")
    
    async def get_usage_analytics(self, 
                                 api_key_id: str,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None,
                                 granularity: str = "daily") -> Dict[str, Any]:
        """Get comprehensive usage analytics for an API key"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        async with get_db() as db:
            # Basic usage metrics
            total_requests = await db.query(func.count(AuditLog.id)).filter(
                AuditLog.api_key_id == api_key_id,
                AuditLog.created_at.between(start_date, end_date)
            ).scalar()
            
            # Error rate
            error_count = await db.query(func.count(AuditLog.id)).filter(
                AuditLog.api_key_id == api_key_id,
                AuditLog.success == False,
                AuditLog.created_at.between(start_date, end_date)
            ).scalar()
            
            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
            
            # Unique agents
            unique_agents = await db.query(func.count(func.distinct(Agent.id))).filter(
                Agent.api_key_id == api_key_id
            ).scalar()
            
            # Payment metrics
            payment_stats = await db.query(
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('volume'),
                func.sum(Payment.disco_fee).label('fees')
            ).join(Agent, Payment.from_agent_id == Agent.id).filter(
                Agent.api_key_id == api_key_id,
                Payment.created_at.between(start_date, end_date)
            ).first()
            
            # Service metrics
            services_created = await db.query(func.count(Service.id)).join(
                Agent, Service.agent_id == Agent.id
            ).filter(
                Agent.api_key_id == api_key_id,
                Service.created_at.between(start_date, end_date)
            ).scalar()
            
            # Time-series data
            time_series = await self._get_time_series_data(
                db, api_key_id, start_date, end_date, granularity
            )
            
            # Top endpoints
            top_endpoints = await self._get_top_endpoints(
                db, api_key_id, start_date, end_date
            )
            
            # Geographic distribution
            geo_distribution = await self._get_geographic_distribution(
                db, api_key_id, start_date, end_date
            )
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "granularity": granularity
                },
                "overview": {
                    "total_requests": total_requests or 0,
                    "error_count": error_count or 0,
                    "error_rate": round(error_rate, 2),
                    "unique_agents": unique_agents or 0,
                    "services_created": services_created or 0
                },
                "payments": {
                    "count": payment_stats.count or 0 if payment_stats else 0,
                    "volume": float(payment_stats.volume or 0) if payment_stats else 0,
                    "fees_collected": float(payment_stats.fees or 0) if payment_stats else 0
                },
                "time_series": time_series,
                "top_endpoints": top_endpoints,
                "geographic_distribution": geo_distribution
            }
    
    async def get_user_identification(self, api_key_id: str) -> Dict[str, Any]:
        """Get user identification information"""
        
        async with get_db() as db:
            api_key = await db.query(APIKey).filter(APIKey.key_id == api_key_id).first()
            
            if not api_key:
                return {}
            
            # Recent activity
            recent_activity = await db.query(AuditLog).filter(
                AuditLog.api_key_id == api_key_id
            ).order_by(desc(AuditLog.created_at)).limit(10).all()
            
            # Unique IP addresses
            unique_ips = await db.query(func.distinct(AuditLog.ip_address)).filter(
                AuditLog.api_key_id == api_key_id,
                AuditLog.ip_address.isnot(None)
            ).all()
            
            # User agents (SDK versions)
            sdk_versions = await db.query(
                AuditLog.sdk_version, 
                func.count(AuditLog.id).label('count')
            ).filter(
                AuditLog.api_key_id == api_key_id,
                AuditLog.sdk_version.isnot(None)
            ).group_by(AuditLog.sdk_version).all()
            
            return {
                "api_key_info": {
                    "key_id": api_key.key_id,
                    "environment": api_key.environment,
                    "user_email": api_key.user_email,
                    "organization": api_key.organization,
                    "created_at": api_key.created_at.isoformat(),
                    "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                    "total_requests": api_key.request_count,
                    "current_month_usage": api_key.current_month_usage,
                    "user_metadata": api_key.user_metadata
                },
                "activity": {
                    "unique_ip_count": len(unique_ips),
                    "unique_ips": [ip[0] for ip in unique_ips if ip[0]],
                    "sdk_versions": [{"version": v.sdk_version, "usage_count": v.count} for v in sdk_versions],
                    "recent_activity": [
                        {
                            "event_type": log.event_type,
                            "timestamp": log.created_at.isoformat(),
                            "ip_address": log.ip_address,
                            "success": log.success
                        } for log in recent_activity
                    ]
                }
            }
    
    async def get_platform_analytics(self) -> Dict[str, Any]:
        """Get platform-wide analytics"""
        
        async with get_db() as db:
            # Total users
            total_users = await db.query(func.count(func.distinct(APIKey.id))).scalar()
            
            # Active users (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users = await db.query(func.count(func.distinct(APIKey.id))).filter(
                APIKey.last_used_at >= thirty_days_ago
            ).scalar()
            
            # Total payments and volume
            payment_stats = await db.query(
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('volume'),
                func.sum(Payment.disco_fee).label('fees')
            ).first()
            
            # SDK version distribution
            sdk_versions = await db.query(
                AuditLog.sdk_version,
                func.count(func.distinct(AuditLog.api_key_id)).label('users')
            ).filter(
                AuditLog.sdk_version.isnot(None),
                AuditLog.created_at >= thirty_days_ago
            ).group_by(AuditLog.sdk_version).all()
            
            # Top organizations
            top_orgs = await db.query(
                APIKey.organization,
                func.count(APIKey.id).label('users'),
                func.sum(APIKey.request_count).label('total_requests')
            ).filter(
                APIKey.organization.isnot(None)
            ).group_by(APIKey.organization).order_by(
                desc(func.sum(APIKey.request_count))
            ).limit(10).all()
            
            return {
                "users": {
                    "total": total_users or 0,
                    "active_30d": active_users or 0,
                    "activation_rate": round((active_users / total_users * 100) if total_users > 0 else 0, 2)
                },
                "payments": {
                    "total_count": payment_stats.count or 0 if payment_stats else 0,
                    "total_volume": float(payment_stats.volume or 0) if payment_stats else 0,
                    "total_fees": float(payment_stats.fees or 0) if payment_stats else 0
                },
                "sdk_adoption": [
                    {"version": v.sdk_version, "users": v.users} for v in sdk_versions
                ],
                "top_organizations": [
                    {
                        "name": org.organization,
                        "users": org.users,
                        "total_requests": org.total_requests
                    } for org in top_orgs
                ]
            }
    
    async def _get_time_series_data(self, db, api_key_id: str, start_date: datetime, 
                                   end_date: datetime, granularity: str) -> List[Dict[str, Any]]:
        """Get time-series usage data"""
        
        # Determine time bucket based on granularity
        if granularity == "hourly":
            time_bucket = func.date_trunc('hour', AuditLog.created_at)
        elif granularity == "daily":
            time_bucket = func.date_trunc('day', AuditLog.created_at)
        elif granularity == "weekly":
            time_bucket = func.date_trunc('week', AuditLog.created_at)
        else:  # monthly
            time_bucket = func.date_trunc('month', AuditLog.created_at)
        
        results = await db.query(
            time_bucket.label('period'),
            func.count(AuditLog.id).label('requests'),
            func.count(func.distinct(AuditLog.ip_address)).label('unique_ips'),
            func.sum(func.case([(AuditLog.success == False, 1)], else_=0)).label('errors')
        ).filter(
            AuditLog.api_key_id == api_key_id,
            AuditLog.created_at.between(start_date, end_date)
        ).group_by(time_bucket).order_by(time_bucket).all()
        
        return [
            {
                "period": result.period.isoformat(),
                "requests": result.requests,
                "unique_ips": result.unique_ips,
                "errors": result.errors or 0,
                "error_rate": round((result.errors or 0) / result.requests * 100, 2) if result.requests > 0 else 0
            } for result in results
        ]
    
    async def _get_top_endpoints(self, db, api_key_id: str, start_date: datetime, 
                                end_date: datetime) -> List[Dict[str, Any]]:
        """Get most frequently used endpoints"""
        
        results = await db.query(
            func.json_extract_path_text(AuditLog.details, 'endpoint').label('endpoint'),
            func.count(AuditLog.id).label('count'),
            func.avg(func.cast(func.json_extract_path_text(AuditLog.details, 'response_time_ms'), Float)).label('avg_response_time')
        ).filter(
            AuditLog.api_key_id == api_key_id,
            AuditLog.created_at.between(start_date, end_date),
            AuditLog.details.has_key('endpoint')
        ).group_by(
            func.json_extract_path_text(AuditLog.details, 'endpoint')
        ).order_by(desc(func.count(AuditLog.id))).limit(10).all()
        
        return [
            {
                "endpoint": result.endpoint,
                "count": result.count,
                "avg_response_time_ms": round(result.avg_response_time or 0, 2)
            } for result in results
        ]
    
    async def _get_geographic_distribution(self, db, api_key_id: str, start_date: datetime,
                                         end_date: datetime) -> List[Dict[str, Any]]:
        """Get geographic distribution of requests"""
        
        results = await db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.api_key_id == api_key_id,
            AuditLog.created_at.between(start_date, end_date),
            AuditLog.ip_address.isnot(None)
        ).group_by(AuditLog.ip_address).order_by(desc(func.count(AuditLog.id))).limit(20).all()
        
        return [
            {
                "ip_address": result.ip_address,
                "request_count": result.count
            } for result in results
        ]
    
    def _extract_sdk_version(self, user_agent: Optional[str]) -> Optional[str]:
        """Extract SDK version from User-Agent header"""
        if not user_agent:
            return None
        
        # Parse disco-sdk-python/1.0.0 format
        if "disco-sdk-python/" in user_agent:
            try:
                return user_agent.split("disco-sdk-python/")[1].split()[0]
            except (IndexError, AttributeError):
                return None
        
        return None

# Global instance
analytics_service = AnalyticsService() 