"""
Services API Endpoints
Service registration and discovery for AI agents
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field

from disco_backend.database.connection import get_db
from disco_backend.database.models import Service, Agent, APIKey
from disco_backend.core.security import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()

class ServiceRequest(BaseModel):
    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    category: Optional[str] = Field(None, description="Service category")
    price: float = Field(..., gt=0, description="Service price")
    currency: str = Field(default="USDC", description="Pricing currency")
    network: str = Field(default="polygon", description="Blockchain network")
    x402_endpoint: str = Field(..., description="x402 payment endpoint")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ServiceResponse(BaseModel):
    service_id: str
    agent_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    price: float
    currency: str
    network: str
    x402_endpoint: str
    payment_method: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class ServiceListResponse(BaseModel):
    services: List[ServiceResponse]
    total: int
    page: int
    limit: int
    has_more: bool

@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def register_service(
    service_request: ServiceRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Register a new service"""
    
    # Get agent for this API key
    stmt = select(Agent).where(Agent.api_key_id == api_key.id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found for this API key"
        )
    
    # Check if service ID already exists
    stmt = select(Service).where(Service.service_id == service_request.service_id)
    result = await db.execute(stmt)
    existing_service = result.scalar_one_or_none()
    
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service with ID '{service_request.service_id}' already exists"
        )
    
    # Create service
    service = Service(
        service_id=service_request.service_id,
        agent_id=agent.id,
        name=service_request.name,
        description=service_request.description,
        category=service_request.category,
        price=service_request.price,
        currency=service_request.currency,
        network=service_request.network,
        x402_endpoint=service_request.x402_endpoint,
        payment_method="crypto",
        is_active=True,
        metadata=service_request.metadata
    )
    
    db.add(service)
    await db.commit()
    await db.refresh(service)
    
    logger.info(f"Registered service {service_request.service_id} for agent {agent.agent_id}")
    
    return ServiceResponse(
        service_id=service.service_id,
        agent_id=agent.agent_id,
        name=service.name,
        description=service.description,
        category=service.category,
        price=service.price,
        currency=service.currency,
        network=service.network,
        x402_endpoint=service.x402_endpoint,
        payment_method=service.payment_method,
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at,
        metadata=service.metadata
    )

@router.get("/", response_model=ServiceListResponse)
async def discover_services(
    category: Optional[str] = Query(None, description="Filter by category"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    network: Optional[str] = Query(None, description="Filter by network"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    active_only: bool = Query(True, description="Only return active services"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Discover services with filtering"""
    
    # Base query with join to get agent info
    stmt = select(Service, Agent.agent_id).join(Agent, Service.agent_id == Agent.id)
    filters = []
    
    # Apply filters
    if active_only:
        filters.append(Service.is_active == True)
    
    if category:
        filters.append(Service.category == category)
    
    if currency:
        filters.append(Service.currency == currency)
    
    if network:
        filters.append(Service.network == network)
    
    if min_price is not None:
        filters.append(Service.price >= min_price)
    
    if max_price is not None:
        filters.append(Service.price <= max_price)
    
    if filters:
        stmt = stmt.where(and_(*filters))
    
    # Count total
    count_stmt = select(Service).join(Agent, Service.agent_id == Agent.id)
    if filters:
        count_stmt = count_stmt.where(and_(*filters))
    total_result = await db.execute(count_stmt)
    total = len(total_result.all())
    
    # Apply pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    
    # Order by creation date (newest first)
    stmt = stmt.order_by(Service.created_at.desc())
    
    # Execute query
    result = await db.execute(stmt)
    service_rows = result.all()
    
    # Convert to response format
    service_responses = [
        ServiceResponse(
            service_id=service.service_id,
            agent_id=agent_id,
            name=service.name,
            description=service.description,
            category=service.category,
            price=service.price,
            currency=service.currency,
            network=service.network,
            x402_endpoint=service.x402_endpoint,
            payment_method=service.payment_method,
            is_active=service.is_active,
            created_at=service.created_at,
            updated_at=service.updated_at,
            metadata=service.metadata
        )
        for service, agent_id in service_rows
    ]
    
    has_more = (offset + limit) < total
    
    return ServiceListResponse(
        services=service_responses,
        total=total,
        page=page,
        limit=limit,
        has_more=has_more
    )

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get service by ID"""
    
    # Get service with agent info
    stmt = select(Service, Agent.agent_id).join(
        Agent, Service.agent_id == Agent.id
    ).where(Service.service_id == service_id)
    
    result = await db.execute(stmt)
    service_row = result.first()
    
    if not service_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    service, agent_id = service_row
    
    return ServiceResponse(
        service_id=service.service_id,
        agent_id=agent_id,
        name=service.name,
        description=service.description,
        category=service.category,
        price=service.price,
        currency=service.currency,
        network=service.network,
        x402_endpoint=service.x402_endpoint,
        payment_method=service.payment_method,
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at,
        metadata=service.metadata
    )

@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: str,
    service_request: ServiceRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Update service information"""
    
    # Get agent for this API key
    stmt = select(Agent).where(Agent.api_key_id == api_key.id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found for this API key"
        )
    
    # Get existing service
    stmt = select(Service).where(
        and_(Service.service_id == service_id, Service.agent_id == agent.id)
    )
    result = await db.execute(stmt)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or not owned by this agent"
        )
    
    # Update fields
    service.name = service_request.name
    service.description = service_request.description
    service.category = service_request.category
    service.price = service_request.price
    service.currency = service_request.currency
    service.network = service_request.network
    service.x402_endpoint = service_request.x402_endpoint
    service.metadata = service_request.metadata
    
    await db.commit()
    await db.refresh(service)
    
    logger.info(f"Updated service {service_id}")
    
    return ServiceResponse(
        service_id=service.service_id,
        agent_id=agent.agent_id,
        name=service.name,
        description=service.description,
        category=service.category,
        price=service.price,
        currency=service.currency,
        network=service.network,
        x402_endpoint=service.x402_endpoint,
        payment_method=service.payment_method,
        is_active=service.is_active,
        created_at=service.created_at,
        updated_at=service.updated_at,
        metadata=service.metadata
    )

@router.delete("/{service_id}")
async def deactivate_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Deactivate a service"""
    
    # Get agent for this API key
    stmt = select(Agent).where(Agent.api_key_id == api_key.id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found for this API key"
        )
    
    # Get service
    stmt = select(Service).where(
        and_(Service.service_id == service_id, Service.agent_id == agent.id)
    )
    result = await db.execute(stmt)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or not owned by this agent"
        )
    
    # Deactivate service
    service.is_active = False
    await db.commit()
    
    logger.info(f"Deactivated service {service_id}")
    
    return {"status": "deactivated", "service_id": service_id} 