"""
Agent API Endpoints
Agent registration, discovery, and management
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
from disco_backend.database.models import Agent, APIKey
from disco_backend.core.security import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()

class AgentRequest(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Agent capabilities")
    wallet_address: str = Field(..., description="Crypto wallet address")
    supported_currencies: List[str] = Field(default=["USDC", "ETH"], description="Supported currencies")
    supported_networks: List[str] = Field(default=["polygon", "ethereum"], description="Supported networks")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AgentResponse(BaseModel):
    agent_id: str
    name: str
    description: Optional[str]
    capabilities: Dict[str, Any]
    wallet_address: str
    supported_currencies: Dict[str, Any]
    supported_networks: Dict[str, Any]
    is_active: bool
    last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int
    page: int
    limit: int
    has_more: bool

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    agent_request: AgentRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Register a new agent"""
    
    # Check if agent ID already exists
    stmt = select(Agent).where(Agent.agent_id == agent_request.agent_id)
    result = await db.execute(stmt)
    existing_agent = result.scalar_one_or_none()
    
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with ID '{agent_request.agent_id}' already exists"
        )
    
    # Create agent
    agent = Agent(
        agent_id=agent_request.agent_id,
        api_key_id=api_key.id,
        name=agent_request.name,
        description=agent_request.description,
        capabilities=agent_request.capabilities,
        wallet_address=agent_request.wallet_address,
        supported_currencies={"currencies": agent_request.supported_currencies},
        supported_networks={"networks": agent_request.supported_networks},
        is_active=True,
        last_seen_at=datetime.utcnow(),
        metadata=agent_request.metadata
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Registered agent {agent_request.agent_id}")
    
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        capabilities=agent.capabilities,
        wallet_address=agent.wallet_address,
        supported_currencies=agent.supported_currencies,
        supported_networks=agent.supported_networks,
        is_active=agent.is_active,
        last_seen_at=agent.last_seen_at,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        metadata=agent.metadata
    )

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Get agent by ID"""
    
    stmt = select(Agent).where(Agent.agent_id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        capabilities=agent.capabilities,
        wallet_address=agent.wallet_address,
        supported_currencies=agent.supported_currencies,
        supported_networks=agent.supported_networks,
        is_active=agent.is_active,
        last_seen_at=agent.last_seen_at,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        metadata=agent.metadata
    )

@router.get("/", response_model=AgentListResponse)
async def discover_agents(
    capability: Optional[str] = Query(None, description="Filter by capability"),
    currency: Optional[str] = Query(None, description="Filter by supported currency"),
    network: Optional[str] = Query(None, description="Filter by supported network"),
    active_only: bool = Query(True, description="Only return active agents"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Discover agents with filtering"""
    
    # Base query
    stmt = select(Agent)
    filters = []
    
    # Apply filters
    if active_only:
        filters.append(Agent.is_active == True)
    
    if capability:
        filters.append(Agent.capabilities.op('?')(capability))
    
    if currency:
        filters.append(Agent.supported_currencies.op('?')('currencies'))
    
    if network:
        filters.append(Agent.supported_networks.op('?')('networks'))
    
    if filters:
        stmt = stmt.where(and_(*filters))
    
    # Count total
    count_stmt = stmt
    total_result = await db.execute(count_stmt)
    total = len(total_result.all())
    
    # Apply pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    
    # Order by last seen (most recent first)
    stmt = stmt.order_by(Agent.last_seen_at.desc().nullslast())
    
    # Execute query
    result = await db.execute(stmt)
    agents = result.scalars().all()
    
    # Convert to response format
    agent_responses = [
        AgentResponse(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            capabilities=agent.capabilities,
            wallet_address=agent.wallet_address,
            supported_currencies=agent.supported_currencies,
            supported_networks=agent.supported_networks,
            is_active=agent.is_active,
            last_seen_at=agent.last_seen_at,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            metadata=agent.metadata
        )
        for agent in agents
    ]
    
    has_more = (offset + limit) < total
    
    return AgentListResponse(
        agents=agent_responses,
        total=total,
        page=page,
        limit=limit,
        has_more=has_more
    )

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_request: AgentRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Update agent information"""
    
    # Get existing agent
    stmt = select(Agent).where(
        and_(Agent.agent_id == agent_id, Agent.api_key_id == api_key.id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not owned by this API key"
        )
    
    # Update fields
    agent.name = agent_request.name
    agent.description = agent_request.description
    agent.capabilities = agent_request.capabilities
    agent.wallet_address = agent_request.wallet_address
    agent.supported_currencies = {"currencies": agent_request.supported_currencies}
    agent.supported_networks = {"networks": agent_request.supported_networks}
    agent.metadata = agent_request.metadata
    agent.last_seen_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Updated agent {agent_id}")
    
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        capabilities=agent.capabilities,
        wallet_address=agent.wallet_address,
        supported_currencies=agent.supported_currencies,
        supported_networks=agent.supported_networks,
        is_active=agent.is_active,
        last_seen_at=agent.last_seen_at,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        metadata=agent.metadata
    )

@router.post("/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Update agent last seen timestamp"""
    
    # Get agent
    stmt = select(Agent).where(
        and_(Agent.agent_id == agent_id, Agent.api_key_id == api_key.id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not owned by this API key"
        )
    
    # Update last seen
    agent.last_seen_at = datetime.utcnow()
    await db.commit()
    
    return {"status": "ok", "last_seen_at": agent.last_seen_at}

@router.delete("/{agent_id}")
async def deactivate_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(verify_api_key)
):
    """Deactivate an agent"""
    
    # Get agent
    stmt = select(Agent).where(
        and_(Agent.agent_id == agent_id, Agent.api_key_id == api_key.id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not owned by this API key"
        )
    
    # Deactivate agent
    agent.is_active = False
    await db.commit()
    
    logger.info(f"Deactivated agent {agent_id}")
    
    return {"status": "deactivated", "agent_id": agent_id} 