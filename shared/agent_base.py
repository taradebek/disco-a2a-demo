import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from shared.models import AgentCard, A2AMessage, Task, TaskStatus, AgentEvent, EventType
from a2a_protocol.protocol import a2a_protocol
from a2a_protocol.event_broadcaster import event_broadcaster

class BaseAgent(ABC):
    """Base class for all A2A agents"""
    
    def __init__(self, agent_id: str, name: str, description: str, agent_card_path: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.agent_card_path = agent_card_path
        self.agent_card: Optional[AgentCard] = None
        self.is_running = False
        self.message_handlers: Dict[str, Callable] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.capabilities: Dict[str, Dict[str, Any]] = {}
        
    def _load_agent_card(self) -> AgentCard:
        """Load agent capabilities from JSON file"""
        with open(self.agent_card_path, 'r') as f:
            card_data = json.load(f)
        return AgentCard(**card_data)
    
    async def start(self):
        """Start the agent and register with A2A protocol"""
        self.agent_card = self._load_agent_card()
        self.is_running = True
        
        # Register with A2A protocol
        await a2a_protocol.register_agent(self.agent_card)
        
        # Initialize capabilities
        for capability in self.agent_card.capabilities:
            self.capabilities[capability.name] = {
                "description": capability.description,
                "input_schema": capability.input_schema,
                "output_schema": capability.output_schema
            }
        
        await self._log_event("discovery", {
            "status": "started",
            "capabilities": len(self.capabilities)
        }, f"{self.name} started and registered")
        
        print(f"🚀 {self.name} started and registered with A2A protocol")
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        await self._log_event("status_update", {
            "status": "stopped"
        }, f"{self.name} stopped")
        
        print(f"🛑 {self.name} stopped")
    
    async def _log_event(self, event_type: str, data: Dict[str, Any], description: str, success: bool = True):
        """Log an event to the event broadcaster"""
        await event_broadcaster.broadcast_event({
            "agent_id": self.agent_id,
            "event_type": event_type,
            "timestamp": datetime.now(),
            "data": data,
            "step_number": 0,
            "description": description,
            "success": success
        })
    
    def register_message_handler(self, content_type: str, handler: Callable):
        """Register a handler for specific message content types"""
        self.message_handlers[content_type] = handler
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """Register a handler for specific task types"""
        self.task_handlers[task_type] = handler
    
    async def send_message(self, 
                          to_agent: str, 
                          content: Any, 
                          content_type: str = "application/json",
                          task_id: Optional[str] = None,
                          correlation_id: Optional[str] = None) -> str:
        """Send a message to another agent"""
        message_id = await a2a_protocol.send_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            content_type=content_type,
            task_id=task_id,
            correlation_id=correlation_id
        )
        
        await self._log_event("message_sent", {
            "to_agent": to_agent,
            "message_id": message_id,
            "content_type": content_type
        }, f"Message sent to {to_agent}")
        
        return message_id
    
    async def send_response(self, 
                           original_message: A2AMessage, 
                           response_content: Any, 
                           content_type: str = "application/json") -> str:
        """Send a response to an original message"""
        response_id = await a2a_protocol.send_response(
            original_message, response_content, content_type
        )
        
        await self._log_event("message_sent", {
            "to_agent": original_message.from_agent,
            "response_id": response_id,
            "content_type": content_type
        }, f"Response sent to {original_message.from_agent}")
        
        return response_id
    
    async def create_task(self, 
                         task_name: str, 
                         description: str, 
                         data: Dict[str, Any] = None,
                         parent_task_id: Optional[str] = None) -> Task:
        """Create a new task"""
        task = await a2a_protocol.create_task(
            task_name=task_name,
            description=description,
            assigned_agent=self.agent_id,
            data=data,
            parent_task_id=parent_task_id
        )
        
        await self._log_event("task_created", {
            "task_id": task.task_id,
            "task_name": task_name
        }, f"Task '{task_name}' created")
        
        return task
    
    async def update_task_status(self, 
                                task_id: str, 
                                status: TaskStatus, 
                                data: Dict[str, Any] = None,
                                result: Dict[str, Any] = None) -> bool:
        """Update task status"""
        success = await a2a_protocol.update_task_status(task_id, status, data, result)
        
        if success:
            await self._log_event("status_update", {
                "task_id": task_id,
                "status": status,
                "data": data or {},
                "result": result or {}
            }, f"Task {task_id} status updated to {status}")
        
        return success
    
    async def discover_agents(self, 
                            capability_filter: Optional[str] = None,
                            agent_type: Optional[str] = None) -> List[AgentCard]:
        """Discover other agents"""
        agents = await a2a_protocol.discover_agents(
            self.agent_id, capability_filter, agent_type
        )
        
        await self._log_event("discovery", {
            "discovered_count": len(agents),
            "capability_filter": capability_filter,
            "agent_type": agent_type
        }, f"Discovered {len(agents)} agents")
        
        return agents
    
    async def process_messages(self):
        """Main message processing loop"""
        while self.is_running:
            try:
                message = await a2a_protocol.receive_message(self.agent_id)
                if message:
                    await self._handle_message(message)
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                await self._log_event("error", {
                    "error": str(e)
                }, f"Error processing messages: {str(e)}", success=False)
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _handle_message(self, message: A2AMessage):
        """Handle incoming messages"""
        content_type = message.parts[0].content_type
        
        await self._log_event("message_received", {
            "from_agent": message.from_agent,
            "message_id": message.message_id,
            "content_type": content_type
        }, f"Message received from {message.from_agent}")
        
        # Try to handle with registered handlers
        if content_type in self.message_handlers:
            try:
                await self.message_handlers[content_type](message)
            except Exception as e:
                await self._log_event("error", {
                    "error": str(e),
                    "message_id": message.message_id
                }, f"Error handling message: {str(e)}", success=False)
        else:
            # Default message handling
            await self._default_message_handler(message)
    
    async def _default_message_handler(self, message: A2AMessage):
        """Default message handler - can be overridden by subclasses"""
        content = message.parts[0].content
        
        await self._log_event("status_update", {
            "message_id": message.message_id,
            "content_type": message.parts[0].content_type
        }, f"Message processed with default handler")
    
    @abstractmethod
    async def initialize_capabilities(self):
        """Initialize agent-specific capabilities - must be implemented by subclasses"""
        pass
    
    async def get_capability_info(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific capability"""
        return self.capabilities.get(capability_name)
    
    async def list_capabilities(self) -> List[str]:
        """List all available capabilities"""
        return list(self.capabilities.keys())
    
    async def execute_capability(self, capability_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific capability with input data"""
        if capability_name not in self.capabilities:
            raise ValueError(f"Capability '{capability_name}' not found")
        
        # This would be implemented by subclasses for specific capabilities
        await self._log_event("capability_executed", {
            "capability": capability_name,
            "input_data": input_data
        }, f"Executed capability '{capability_name}'")
        
        return {"status": "executed", "capability": capability_name}
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "is_running": self.is_running,
            "capabilities": list(self.capabilities.keys()),
            "registered_handlers": {
                "message_handlers": list(self.message_handlers.keys()),
                "task_handlers": list(self.task_handlers.keys())
            }
        }
