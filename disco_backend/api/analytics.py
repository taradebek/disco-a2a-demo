"""
Analytics API Endpoints
Provides usage analytics and user identification endpoints
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer
from disco_backend.core.security import verify_api_key, get_current_api_key
from disco_backend.services.analytics_service import analytics_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])
security = HTTPBearer()

@router.get("/usage")
async def get_usage_analytics(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    granularity: str = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    api_key: str = Depends(get_current_api_key)
):
    """Get comprehensive usage analytics for the authenticated API key"""
    
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
        
        # Get analytics data
        analytics_data = await analytics_service.get_usage_analytics(
            api_key_id=api_key,
            start_date=start_dt,
            end_date=end_dt,
            granularity=granularity
        )
        
        # Track this API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/usage",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=True
        )
        
        return analytics_data
        
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        
        # Track failed API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/usage",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail="Failed to retrieve usage analytics")

@router.get("/user-info")
async def get_user_identification(
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Get user identification and activity information"""
    
    try:
        user_info = await analytics_service.get_user_identification(api_key_id=api_key)
        
        if not user_info:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Track this API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/user-info",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=True
        )
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user identification: {e}")
        
        # Track failed API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/user-info",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail="Failed to retrieve user information")

@router.get("/platform")
async def get_platform_analytics(
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Get platform-wide analytics (admin only)"""
    
    try:
        # TODO: Add admin-only access control
        # For now, allow any valid API key to access platform analytics
        
        platform_data = await analytics_service.get_platform_analytics()
        
        # Track this API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/platform",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=True
        )
        
        return platform_data
        
    except Exception as e:
        logger.error(f"Error getting platform analytics: {e}")
        
        # Track failed API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/platform",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail="Failed to retrieve platform analytics")

@router.get("/export")
async def export_usage_data(
    request: Request,
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    api_key: str = Depends(get_current_api_key)
):
    """Export usage data in JSON or CSV format"""
    
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Get detailed analytics data
        analytics_data = await analytics_service.get_usage_analytics(
            api_key_id=api_key,
            start_date=start_dt,
            end_date=end_dt,
            granularity="daily"
        )
        
        user_info = await analytics_service.get_user_identification(api_key_id=api_key)
        
        export_data = {
            "export_metadata": {
                "api_key_id": api_key,
                "exported_at": datetime.utcnow().isoformat(),
                "format": format,
                "period": analytics_data.get("period", {})
            },
            "user_info": user_info,
            "analytics": analytics_data
        }
        
        # Track this API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/export",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=True
        )
        
        if format == "json":
            return export_data
        elif format == "csv":
            # TODO: Implement CSV export
            # For now, return JSON with a note
            export_data["note"] = "CSV export not yet implemented. Returning JSON format."
            return export_data
        
    except Exception as e:
        logger.error(f"Error exporting usage data: {e}")
        
        # Track failed API call
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/analytics/export",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail="Failed to export usage data")

# Middleware to automatically track all API requests
@router.middleware("http")
async def track_requests(request: Request, call_next):
    """Middleware to automatically track all API requests"""
    
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Extract API key from request (if available)
        api_key = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer " prefix
        
        if api_key:
            # Track successful request
            await analytics_service.track_api_usage(
                api_key_id=api_key,
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=response.status_code < 400,
                error_message=None if response.status_code < 400 else f"HTTP {response.status_code}",
                response_time_ms=response_time_ms
            )
        
        return response
        
    except Exception as e:
        # Track failed request
        end_time = datetime.utcnow()
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
            
            await analytics_service.track_api_usage(
                api_key_id=api_key,
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=False,
                error_message=str(e),
                response_time_ms=response_time_ms
            )
        
        raise 