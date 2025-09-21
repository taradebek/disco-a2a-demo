"""
User Registration and Management API
Handles user registration, API key creation, and user identification
"""

import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, Depends, Request
from disco_backend.database.connection import get_db
from disco_backend.database.models import APIKey
from disco_backend.services.analytics_service import analytics_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

class UserRegistration(BaseModel):
    """User registration request model"""
    email: EmailStr
    organization: Optional[str] = None
    name: Optional[str] = None
    use_case: Optional[str] = None
    expected_volume: Optional[str] = None
    environment: str = "sandbox"  # sandbox or live
    metadata: Optional[Dict[str, Any]] = None

class APIKeyResponse(BaseModel):
    """API key creation response model"""
    api_key: str
    key_id: str
    environment: str
    created_at: str
    user_email: str
    organization: Optional[str]
    rate_limit_per_hour: int
    monthly_quota: Optional[int]

class UserProfile(BaseModel):
    """User profile update model"""
    organization: Optional[str] = None
    name: Optional[str] = None
    use_case: Optional[str] = None
    expected_volume: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.post("/register", response_model=APIKeyResponse)
async def register_user(
    user_data: UserRegistration,
    request: Request
):
    """Register a new user and create an API key"""
    
    try:
        async with get_db() as db:
            # Check if user already exists
            existing_user = await db.query(APIKey).filter(
                APIKey.user_email == user_data.email,
                APIKey.environment == user_data.environment
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=409,
                    detail=f"User with email {user_data.email} already has a {user_data.environment} API key"
                )
            
            # Generate API key
            key_prefix = "dk_live_" if user_data.environment == "live" else "dk_test_"
            raw_key = key_prefix + secrets.token_urlsafe(32)
            
            # Hash the API key for storage
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            key_id = f"{key_prefix}{secrets.token_hex(8)}"
            
            # Set usage limits based on environment
            rate_limit = 10000 if user_data.environment == "live" else 1000
            monthly_quota = 1000000 if user_data.environment == "live" else None
            
            # Create API key record
            api_key_record = APIKey(
                key_id=key_id,
                key_hash=key_hash,
                environment=user_data.environment,
                user_email=user_data.email,
                organization=user_data.organization,
                name=f"{user_data.name or 'API Key'} - {user_data.environment}",
                description=f"API key for {user_data.email}",
                rate_limit_per_hour=rate_limit,
                monthly_quota=monthly_quota,
                user_metadata={
                    "name": user_data.name,
                    "use_case": user_data.use_case,
                    "expected_volume": user_data.expected_volume,
                    "registration_ip": request.client.host if request.client else None,
                    "registration_user_agent": request.headers.get("User-Agent"),
                    **(user_data.metadata or {})
                }
            )
            
            db.add(api_key_record)
            await db.commit()
            await db.refresh(api_key_record)
            
            # Track registration event
            await analytics_service.track_api_usage(
                api_key_id=key_id,
                endpoint="/users/register",
                method="POST",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=True
            )
            
            logger.info(f"New user registered: {user_data.email} ({user_data.environment})")
            
            return APIKeyResponse(
                api_key=raw_key,  # Return the actual key only once
                key_id=key_id,
                environment=user_data.environment,
                created_at=api_key_record.created_at.isoformat(),
                user_email=user_data.email,
                organization=user_data.organization,
                rate_limit_per_hour=rate_limit,
                monthly_quota=monthly_quota
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Failed to register user")

@router.get("/profile")
async def get_user_profile(
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Get current user's profile information"""
    
    try:
        user_info = await analytics_service.get_user_identification(api_key_id=api_key)
        
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Track API usage
        await analytics_service.track_api_usage(
            api_key_id=api_key,
            endpoint="/users/profile",
            method="GET",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            success=True
        )
        
        return user_info["api_key_info"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user profile")

@router.put("/profile")
async def update_user_profile(
    profile_data: UserProfile,
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Update user profile information"""
    
    try:
        async with get_db() as db:
            api_key_record = await db.query(APIKey).filter(APIKey.key_id == api_key).first()
            
            if not api_key_record:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Update fields
            if profile_data.organization is not None:
                api_key_record.organization = profile_data.organization
            
            if profile_data.name is not None:
                api_key_record.user_metadata = {
                    **api_key_record.user_metadata,
                    "name": profile_data.name
                }
            
            if profile_data.use_case is not None:
                api_key_record.user_metadata = {
                    **api_key_record.user_metadata,
                    "use_case": profile_data.use_case
                }
            
            if profile_data.expected_volume is not None:
                api_key_record.user_metadata = {
                    **api_key_record.user_metadata,
                    "expected_volume": profile_data.expected_volume
                }
            
            if profile_data.metadata:
                api_key_record.user_metadata = {
                    **api_key_record.user_metadata,
                    **profile_data.metadata
                }
            
            api_key_record.updated_at = datetime.utcnow()
            
            await db.commit()
            
            # Track API usage
            await analytics_service.track_api_usage(
                api_key_id=api_key,
                endpoint="/users/profile",
                method="PUT",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=True
            )
            
            return {"message": "Profile updated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@router.post("/api-key/regenerate")
async def regenerate_api_key(
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Regenerate API key for security purposes"""
    
    try:
        async with get_db() as db:
            api_key_record = await db.query(APIKey).filter(APIKey.key_id == api_key).first()
            
            if not api_key_record:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Generate new API key
            key_prefix = f"dk_{api_key_record.environment}_"
            raw_key = key_prefix + secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            
            # Update the hash
            api_key_record.key_hash = key_hash
            api_key_record.updated_at = datetime.utcnow()
            
            # Add regeneration to metadata
            api_key_record.user_metadata = {
                **api_key_record.user_metadata,
                "last_regenerated": datetime.utcnow().isoformat(),
                "regeneration_ip": request.client.host if request.client else None
            }
            
            await db.commit()
            
            # Track API usage
            await analytics_service.track_api_usage(
                api_key_id=api_key,
                endpoint="/users/api-key/regenerate",
                method="POST",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=True
            )
            
            logger.info(f"API key regenerated for user: {api_key_record.user_email}")
            
            return {
                "message": "API key regenerated successfully",
                "new_api_key": raw_key,
                "key_id": api_key_record.key_id,
                "regenerated_at": api_key_record.updated_at.isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate API key")

@router.delete("/api-key")
async def deactivate_api_key(
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Deactivate the current API key"""
    
    try:
        async with get_db() as db:
            api_key_record = await db.query(APIKey).filter(APIKey.key_id == api_key).first()
            
            if not api_key_record:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Deactivate the API key
            api_key_record.is_active = False
            api_key_record.updated_at = datetime.utcnow()
            
            # Add deactivation to metadata
            api_key_record.user_metadata = {
                **api_key_record.user_metadata,
                "deactivated_at": datetime.utcnow().isoformat(),
                "deactivation_ip": request.client.host if request.client else None
            }
            
            await db.commit()
            
            # Track API usage
            await analytics_service.track_api_usage(
                api_key_id=api_key,
                endpoint="/users/api-key",
                method="DELETE",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=True
            )
            
            logger.info(f"API key deactivated for user: {api_key_record.user_email}")
            
            return {"message": "API key deactivated successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate API key")

@router.get("/usage-limits")
async def get_usage_limits(
    request: Request,
    api_key: str = Depends(get_current_api_key)
):
    """Get current usage limits and quotas"""
    
    try:
        async with get_db() as db:
            api_key_record = await db.query(APIKey).filter(APIKey.key_id == api_key).first()
            
            if not api_key_record:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Calculate usage percentages
            hourly_usage_pct = 0  # Would need to calculate from recent logs
            monthly_usage_pct = 0
            if api_key_record.monthly_quota:
                monthly_usage_pct = (api_key_record.current_month_usage / api_key_record.monthly_quota) * 100
            
            # Track API usage
            await analytics_service.track_api_usage(
                api_key_id=api_key,
                endpoint="/users/usage-limits",
                method="GET",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                success=True
            )
            
            return {
                "rate_limit_per_hour": api_key_record.rate_limit_per_hour,
                "monthly_quota": api_key_record.monthly_quota,
                "current_month_usage": api_key_record.current_month_usage,
                "monthly_usage_percentage": round(monthly_usage_pct, 2),
                "total_requests": api_key_record.request_count,
                "environment": api_key_record.environment
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage limits: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve usage limits") 