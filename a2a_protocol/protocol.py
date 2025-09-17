import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from shared.models import AgentCard, Task, A2AMessage, MessagePart, TaskStatus, AgentEvent
from .event_broadcaster import event_broadcaster
from .task_manager import task_manager
from .message_handler import message_handler

class A2AProtocol:
    def __init__(self):
        self.registered_agents: Dict[str, AgentCard] = {}
        self.agent_status: Dict[str, str] = {}  # agent_id -> status
        self.capability_index: Dict[str, List[str]] = {}  # capability_name -> list of agent_ids
        self.protocol_version = "1.0.0"
    
    async def register_agent(self, agent_card: AgentCard) -> bool:
        """Register an agent with its capabilities"""
        self.registered_agents[agent_card.agent_id] = agent_card
        self.agent_status[agent_card.agent_id] = agent_card.status
        
        # Index capabilities for faster discovery
        for capability in agent_card.capabilities:
            capability_name = capability.name.lower()
            if capability_name not in self.capability_index:
                self.capability_index[capability_name] = []
            self.capability_index[capability_name].append(agent_card.agent_id)
        
        await event_broadcaster.broadcast_event({
            "agent_id": agent_card.agent_id,
            "event_type": "discovery",
            "timestamp": datetime.now(),
            "data": {
                "capabilities": len(agent_card.capabilities),
                "agent_name": agent_card.name,
                "status": agent_card.status
            },
            "step_number": 0,
            "description": f"Agent {agent_card.name} registered with {len(agent_card.capabilities)} capabilities",
            "success": True
        })
        
        return True
    
    async def discover_agents(self, 
                            requesting_agent_id: str, 
                            capability_filter: Optional[str] = None,
                            agent_type: Optional[str] = None) -> List[AgentCard]:
        """Discover agents with specific capabilities or type"""
        discovered = []
        
        for agent_id, agent_card in self.registered_agents.items():
            if agent_id == requesting_agent_id:
                continue
            
            # Filter by agent type (if specified)
            if agent_type and agent_type.lower() not in agent_card.name.lower():
                continue
            
            # Filter by capability (if specified)
            if capability_filter:
                capability_found = False
                for capability in agent_card.capabilities:
                    if capability_filter.lower() in capability.name.lower():
                        capability_found = True
                        break
                
                if not capability_found:
                    continue
            
            discovered.append(agent_card)
        
        await event_broadcaster.broadcast_event({
            "agent_id": requesting_agent_id,
            "event_type": "discovery",
            "timestamp": datetime.now(),
            "data": {
                "discovered_count": len(discovered),
                "capability_filter": capability_filter,
                "agent_type": agent_type
            },
            "step_number": 0,
            "description": f"Discovered {len(discovered)} agents matching criteria",
            "success": True
        })
        
        return discovered
    
    async def create_task(self, 
                         task_name: str, 
                         description: str, 
                         assigned_agent: Optional[str] = None, 
                         data: Dict[str, Any] = None,
                         parent_task_id: Optional[str] = None) -> Task:
        """Create a new task using the task manager"""
        return await task_manager.create_task(
            name=task_name,
            description=description,
            assigned_agent=assigned_agent,
            data=data,
            parent_task_id=parent_task_id
        )
    
    async def update_task_status(self, 
                                task_id: str, 
                                status: TaskStatus, 
                                data: Dict[str, Any] = None,
                                result: Dict[str, Any] = None) -> bool:
        """Update task status using the task manager"""
        return await task_manager.update_task_status(task_id, status, data, result)
    
    async def send_message(self, 
                          from_agent: str, 
                          to_agent: str, 
                          content: Any, 
                          content_type: str = "application/json",
                          task_id: Optional[str] = None,
                          correlation_id: Optional[str] = None,
                          timeout: Optional[int] = None) -> str:
        """Send a message between agents using the message handler"""
        from datetime import timedelta
        timeout_delta = timedelta(seconds=timeout) if timeout else None
        
        return await message_handler.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            content_type=content_type,
            task_id=task_id,
            correlation_id=correlation_id,
            timeout=timeout_delta
        )
    
    async def receive_message(self, agent_id: str) -> Optional[A2AMessage]:
        """Receive messages for a specific agent using the message handler"""
        return await message_handler.receive_message(agent_id)
    
    async def send_response(self, 
                           original_message: A2AMessage, 
                           response_content: Any, 
                           content_type: str = "application/json") -> str:
        """Send a response to an original message"""
        return await message_handler.send_response(original_message, response_content, content_type)
    
    async def wait_for_response(self, 
                               correlation_id: str, 
                               timeout: Optional[int] = None) -> Optional[A2AMessage]:
        """Wait for a response to a specific correlation_id"""
        from datetime import timedelta
        timeout_delta = timedelta(seconds=timeout) if timeout else None
        
        return await message_handler.wait_for_response(correlation_id, timeout_delta)
    
    def get_agent_capabilities(self, agent_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get capabilities of a specific agent"""
        if agent_id in self.registered_agents:
            return [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "input_schema": cap.input_schema,
                    "output_schema": cap.output_schema
                }
                for cap in self.registered_agents[agent_id].capabilities
            ]
        return None
    
    async def get_agent_status(self, agent_id: str) -> Optional[str]:
        """Get current status of an agent"""
        return self.agent_status.get(agent_id)
    
    async def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status"""
        if agent_id in self.registered_agents:
            self.agent_status[agent_id] = status
            
            await event_broadcaster.broadcast_event({
                "agent_id": agent_id,
                "event_type": "status_update",
                "timestamp": datetime.now(),
                "data": {"status": status},
                "step_number": 0,
                "description": f"Agent {agent_id} status updated to {status}",
                "success": True
            })
            
            return True
        return False
    
    async def get_capability_providers(self, capability_name: str) -> List[str]:
        """Get all agents that provide a specific capability"""
        capability_name = capability_name.lower()
        return self.capability_index.get(capability_name, [])
    
    async def get_protocol_statistics(self) -> Dict[str, Any]:
        """Get comprehensive protocol statistics"""
        task_stats = await task_manager.get_task_statistics()
        message_stats = await message_handler.get_message_statistics()
        
        return {
            "protocol_version": self.protocol_version,
            "registered_agents": len(self.registered_agents),
            "agent_status": self.agent_status,
            "capability_index_size": len(self.capability_index),
            "task_statistics": task_stats,
            "message_statistics": message_stats
        }
    
    async def cleanup_expired_resources(self):
        """Clean up expired messages and other resources"""
        await message_handler.cleanup_expired_messages()
    
    async def get_agent_conversation(self, agent1: str, agent2: str) -> List[Dict[str, Any]]:
        """Get conversation history between two agents"""
        return await message_handler.get_agent_conversation(agent1, agent2)
    
    async def get_task_hierarchy(self, root_task_id: str) -> Dict[str, Any]:
        """Get complete task hierarchy starting from a root task"""
        return await task_manager.get_task_hierarchy(root_task_id)
    
    async def cancel_task_cascade(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel a task and all its dependent tasks"""
        return await task_manager.cancel_task(task_id, reason)

# Global A2A protocol instance
a2a_protocol = A2AProtocol()
