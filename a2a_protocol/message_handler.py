import uuid
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from shared.models import A2AMessage, MessagePart, AgentEvent
from .event_broadcaster import event_broadcaster

class MessageHandler:
    def __init__(self):
        self.message_queue: List[A2AMessage] = []
        self.message_history: List[A2AMessage] = []
        self.message_handlers: Dict[str, Callable] = {}  # content_type -> handler function
        self.pending_responses: Dict[str, str] = {}  # correlation_id -> message_id
        self.message_timeouts: Dict[str, datetime] = {}  # message_id -> timeout datetime
        self.default_timeout = timedelta(minutes=5)
    
    async def send_message(self, 
                          from_agent: str, 
                          to_agent: str, 
                          content: Any, 
                          content_type: str = "application/json",
                          task_id: Optional[str] = None,
                          correlation_id: Optional[str] = None,
                          timeout: Optional[timedelta] = None) -> str:
        """Send a message between agents with optional correlation tracking"""
        message_id = str(uuid.uuid4())
        
        # If no correlation_id provided, use message_id
        if not correlation_id:
            correlation_id = message_id
        
        message = A2AMessage(
            message_id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            task_id=task_id,
            parts=[MessagePart(content_type=content_type, content=content)],
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        self.message_queue.append(message)
        self.message_history.append(message)
        
        # Set up timeout tracking
        timeout_datetime = datetime.now() + (timeout or self.default_timeout)
        self.message_timeouts[message_id] = timeout_datetime
        
        await event_broadcaster.broadcast_event({
            "agent_id": from_agent,
            "event_type": "message_sent",
            "timestamp": datetime.now(),
            "data": {
                "to_agent": to_agent,
                "message_id": message_id,
                "content_type": content_type,
                "correlation_id": correlation_id,
                "task_id": task_id
            },
            "step_number": 0,
            "description": f"Message sent from {from_agent} to {to_agent}",
            "success": True
        })
        
        return message_id
    
    async def receive_message(self, agent_id: str) -> Optional[A2AMessage]:
        """Receive messages for a specific agent"""
        for i, message in enumerate(self.message_queue):
            if message.to_agent == agent_id:
                # Remove from queue
                received_message = self.message_queue.pop(i)
                
                # Remove timeout tracking
                if message.message_id in self.message_timeouts:
                    del self.message_timeouts[message.message_id]
                
                await event_broadcaster.broadcast_event({
                    "agent_id": agent_id,
                    "event_type": "message_received",
                    "timestamp": datetime.now(),
                    "data": {
                        "from_agent": message.from_agent,
                        "message_id": message.message_id,
                        "correlation_id": message.correlation_id,
                        "task_id": message.task_id
                    },
                    "step_number": 0,
                    "description": f"Message received from {message.from_agent}",
                    "success": True
                })
                
                return received_message
        
        return None
    
    async def send_response(self, 
                           original_message: A2AMessage, 
                           response_content: Any, 
                           content_type: str = "application/json") -> str:
        """Send a response to an original message using correlation_id"""
        return await self.send_message(
            from_agent=original_message.to_agent,
            to_agent=original_message.from_agent,
            content=response_content,
            content_type=content_type,
            task_id=original_message.task_id,
            correlation_id=original_message.correlation_id
        )
    
    async def wait_for_response(self, 
                               correlation_id: str, 
                               timeout: Optional[timedelta] = None) -> Optional[A2AMessage]:
        """Wait for a response to a specific correlation_id"""
        timeout_datetime = datetime.now() + (timeout or self.default_timeout)
        
        while datetime.now() < timeout_datetime:
            # Check message history for response
            for message in reversed(self.message_history):
                if (message.correlation_id == correlation_id and 
                    message.timestamp > datetime.now() - timedelta(seconds=1)):
                    return message
            
            await asyncio.sleep(0.1)
        
        return None
    
    def register_message_handler(self, content_type: str, handler: Callable):
        """Register a handler for specific content types"""
        self.message_handlers[content_type] = handler
    
    async def process_message(self, message: A2AMessage) -> Optional[Any]:
        """Process a message using registered handlers"""
        content_type = message.parts[0].content_type
        
        if content_type in self.message_handlers:
            try:
                return await self.message_handlers[content_type](message)
            except Exception as e:
                await event_broadcaster.broadcast_event({
                    "agent_id": message.to_agent,
                    "event_type": "error",
                    "timestamp": datetime.now(),
                    "data": {"error": str(e), "message_id": message.message_id},
                    "step_number": 0,
                    "description": f"Error processing message: {str(e)}",
                    "success": False
                })
                return None
        
        return None
    
    async def cleanup_expired_messages(self):
        """Clean up expired messages from the queue"""
        now = datetime.now()
        expired_messages = []
        
        for message_id, timeout_datetime in self.message_timeouts.items():
            if now > timeout_datetime:
                expired_messages.append(message_id)
        
        for message_id in expired_messages:
            # Find and remove expired message from queue
            for i, message in enumerate(self.message_queue):
                if message.message_id == message_id:
                    expired_message = self.message_queue.pop(i)
                    
                    await event_broadcaster.broadcast_event({
                        "agent_id": "system",
                        "event_type": "error",
                        "timestamp": datetime.now(),
                        "data": {"message_id": message_id, "reason": "timeout"},
                        "step_number": 0,
                        "description": f"Message {message_id} expired and removed from queue",
                        "success": False
                    })
                    break
            
            del self.message_timeouts[message_id]
    
    async def get_message_statistics(self) -> Dict[str, Any]:
        """Get statistics about messages"""
        total_messages = len(self.message_history)
        queued_messages = len(self.message_queue)
        
        # Count by content type
        content_type_counts = {}
        for message in self.message_history:
            content_type = message.parts[0].content_type
            content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
        
        # Count by agent
        agent_message_counts = {}
        for message in self.message_history:
            from_agent = message.from_agent
            agent_message_counts[from_agent] = agent_message_counts.get(from_agent, 0) + 1
        
        return {
            "total_messages": total_messages,
            "queued_messages": queued_messages,
            "content_type_breakdown": content_type_counts,
            "agent_message_counts": agent_message_counts,
            "pending_timeouts": len(self.message_timeouts)
        }
    
    async def get_agent_conversation(self, agent1: str, agent2: str) -> List[Dict[str, Any]]:
        """Get conversation history between two agents"""
        conversation = []
        
        for message in self.message_history:
            if ((message.from_agent == agent1 and message.to_agent == agent2) or
                (message.from_agent == agent2 and message.to_agent == agent1)):
                conversation.append({
                    "message_id": message.message_id,
                    "from_agent": message.from_agent,
                    "to_agent": message.to_agent,
                    "timestamp": message.timestamp.isoformat(),
                    "content_type": message.parts[0].content_type,
                    "content": message.parts[0].content,
                    "correlation_id": message.correlation_id,
                    "task_id": message.task_id
                })
        
        return sorted(conversation, key=lambda x: x["timestamp"])

# Global message handler instance
message_handler = MessageHandler()
