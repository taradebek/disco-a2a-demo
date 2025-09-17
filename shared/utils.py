import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from shared.models import AgentCard, Task, TaskStatus, A2AMessage, MessagePart

class AgentCardBuilder:
    """Builder class for creating AgentCard objects"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = []
        self.version = "1.0.0"
        self.status = "active"
    
    def add_capability(self, 
                      name: str, 
                      description: str, 
                      input_schema: Dict[str, Any], 
                      output_schema: Dict[str, Any]) -> 'AgentCardBuilder':
        """Add a capability to the agent card"""
        from shared.models import AgentCapability
        
        capability = AgentCapability(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema
        )
        self.capabilities.append(capability)
        return self
    
    def set_version(self, version: str) -> 'AgentCardBuilder':
        """Set the agent version"""
        self.version = version
        return self
    
    def set_status(self, status: str) -> 'AgentCardBuilder':
        """Set the agent status"""
        self.status = status
        return self
    
    def build(self) -> AgentCard:
        """Build the AgentCard object"""
        return AgentCard(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            version=self.version,
            status=self.status
        )
    
    def save_to_file(self, file_path: str):
        """Save the agent card to a JSON file"""
        agent_card = self.build()
        card_data = {
            "agent_id": agent_card.agent_id,
            "name": agent_card.name,
            "description": agent_card.description,
            "version": agent_card.version,
            "status": agent_card.status,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "input_schema": cap.input_schema,
                    "output_schema": cap.output_schema
                }
                for cap in agent_card.capabilities
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(card_data, f, indent=2)

class TaskBuilder:
    """Builder class for creating Task objects"""
    
    def __init__(self, name: str, description: str):
        self.task_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.assigned_agent = None
        self.data = {}
        self.result = None
    
    def set_assigned_agent(self, agent_id: str) -> 'TaskBuilder':
        """Set the assigned agent"""
        self.assigned_agent = agent_id
        return self
    
    def set_status(self, status: TaskStatus) -> 'TaskBuilder':
        """Set the task status"""
        self.status = status
        self.updated_at = datetime.now()
        return self
    
    def add_data(self, key: str, value: Any) -> 'TaskBuilder':
        """Add data to the task"""
        self.data[key] = value
        return self
    
    def set_result(self, result: Dict[str, Any]) -> 'TaskBuilder':
        """Set the task result"""
        self.result = result
        return self
    
    def build(self) -> Task:
        """Build the Task object"""
        return Task(
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            assigned_agent=self.assigned_agent,
            data=self.data,
            result=self.result
        )

class MessageBuilder:
    """Builder class for creating A2AMessage objects"""
    
    def __init__(self, from_agent: str, to_agent: str):
        self.message_id = str(uuid.uuid4())
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.task_id = None
        self.parts = []
        self.timestamp = datetime.now()
        self.correlation_id = None
    
    def set_task_id(self, task_id: str) -> 'MessageBuilder':
        """Set the task ID"""
        self.task_id = task_id
        return self
    
    def set_correlation_id(self, correlation_id: str) -> 'MessageBuilder':
        """Set the correlation ID"""
        self.correlation_id = correlation_id
        return self
    
    def add_part(self, content: Any, content_type: str = "application/json", metadata: Dict[str, Any] = None) -> 'MessageBuilder':
        """Add a message part"""
        part = MessagePart(
            content_type=content_type,
            content=content,
            metadata=metadata or {}
        )
        self.parts.append(part)
        return self
    
    def add_text_part(self, text: str, metadata: Dict[str, Any] = None) -> 'MessageBuilder':
        """Add a text message part"""
        return self.add_part(text, "text/plain", metadata)
    
    def add_json_part(self, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> 'MessageBuilder':
        """Add a JSON message part"""
        return self.add_part(data, "application/json", metadata)
    
    def add_binary_part(self, data: bytes, content_type: str = "application/octet-stream", metadata: Dict[str, Any] = None) -> 'MessageBuilder':
        """Add a binary message part"""
        return self.add_part(data, content_type, metadata)
    
    def build(self) -> A2AMessage:
        """Build the A2AMessage object"""
        return A2AMessage(
            message_id=self.message_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            task_id=self.task_id,
            parts=self.parts,
            timestamp=self.timestamp,
            correlation_id=self.correlation_id
        )

class ProtocolValidator:
    """Utility class for validating A2A protocol messages and data"""
    
    @staticmethod
    def validate_agent_card(card_data: Dict[str, Any]) -> List[str]:
        """Validate agent card data and return list of errors"""
        errors = []
        
        required_fields = ["agent_id", "name", "description", "capabilities"]
        for field in required_fields:
            if field not in card_data:
                errors.append(f"Missing required field: {field}")
        
        if "capabilities" in card_data:
            if not isinstance(card_data["capabilities"], list):
                errors.append("Capabilities must be a list")
            else:
                for i, cap in enumerate(card_data["capabilities"]):
                    if not isinstance(cap, dict):
                        errors.append(f"Capability {i} must be a dictionary")
                        continue
                    
                    cap_required = ["name", "description", "input_schema", "output_schema"]
                    for field in cap_required:
                        if field not in cap:
                            errors.append(f"Capability {i} missing required field: {field}")
        
        return errors
    
    @staticmethod
    def validate_message(message: A2AMessage) -> List[str]:
        """Validate A2A message and return list of errors"""
        errors = []
        
        if not message.message_id:
            errors.append("Message ID is required")
        
        if not message.from_agent:
            errors.append("From agent is required")
        
        if not message.to_agent:
            errors.append("To agent is required")
        
        if not message.parts:
            errors.append("Message must have at least one part")
        
        for i, part in enumerate(message.parts):
            if not part.content_type:
                errors.append(f"Part {i} content type is required")
            
            if part.content is None:
                errors.append(f"Part {i} content is required")
        
        return errors
    
    @staticmethod
    def validate_task(task: Task) -> List[str]:
        """Validate task and return list of errors"""
        errors = []
        
        if not task.task_id:
            errors.append("Task ID is required")
        
        if not task.name:
            errors.append("Task name is required")
        
        if not task.description:
            errors.append("Task description is required")
        
        if not isinstance(task.status, TaskStatus):
            errors.append("Invalid task status")
        
        return errors

class ProtocolSerializer:
    """Utility class for serializing and deserializing protocol objects"""
    
    @staticmethod
    def serialize_agent_card(card: AgentCard) -> Dict[str, Any]:
        """Serialize AgentCard to dictionary"""
        return {
            "agent_id": card.agent_id,
            "name": card.name,
            "description": card.description,
            "version": card.version,
            "status": card.status,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "input_schema": cap.input_schema,
                    "output_schema": cap.output_schema
                }
                for cap in card.capabilities
            ]
        }
    
    @staticmethod
    def serialize_message(message: A2AMessage) -> Dict[str, Any]:
        """Serialize A2AMessage to dictionary"""
        return {
            "message_id": message.message_id,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "task_id": message.task_id,
            "parts": [
                {
                    "content_type": part.content_type,
                    "content": part.content,
                    "metadata": part.metadata
                }
                for part in message.parts
            ],
            "timestamp": message.timestamp.isoformat(),
            "correlation_id": message.correlation_id
        }
    
    @staticmethod
    def serialize_task(task: Task) -> Dict[str, Any]:
        """Serialize Task to dictionary"""
        return {
            "task_id": task.task_id,
            "name": task.name,
            "description": task.description,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "assigned_agent": task.assigned_agent,
            "data": task.data,
            "result": task.result
        }

class ProtocolLogger:
    """Utility class for logging protocol events"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.log_entries = []
    
    def log_event(self, event_type: str, description: str, data: Dict[str, Any] = None, success: bool = True):
        """Log an event"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "event_type": event_type,
            "description": description,
            "data": data or {},
            "success": success
        }
        self.log_entries.append(entry)
        
        # Print to console for debugging
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} [{event_type.upper()}] {description}")
    
    def get_logs(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get log entries, optionally filtered by event type"""
        if event_type:
            return [log for log in self.log_entries if log["event_type"] == event_type]
        return self.log_entries
    
    def clear_logs(self):
        """Clear all log entries"""
        self.log_entries.clear()
    
    def export_logs(self, file_path: str):
        """Export logs to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.log_entries, f, indent=2)
