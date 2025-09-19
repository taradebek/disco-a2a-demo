import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime
from shared.models import AgentEvent, EventType

class EventBroadcaster:
    def __init__(self):
        self.connected_clients: List[Any] = []
        self.event_history: List[AgentEvent] = []
        self.step_counter = 0
    
    def add_client(self, client):
        """Add a WebSocket client to receive events"""
        self.connected_clients.append(client)
        print(f"Client connected. Total clients: {len(self.connected_clients)}")
    
    def remove_client(self, client):
        """Remove a WebSocket client"""
        if client in self.connected_clients:
            self.connected_clients.remove(client)
            print(f"Client disconnected. Total clients: {len(self.connected_clients)}")
    
    def reset(self):
        """Reset the event broadcaster to initial state"""
        self.event_history.clear()
        self.step_counter = 0
        print("🔄 Event broadcaster reset - step counter and history cleared")
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast an event to all connected clients"""
        self.step_counter += 1
        
        # Create AgentEvent object
        event = AgentEvent(
            agent_id=event_data.get("agent_id", "system"),
            event_type=EventType(event_data.get("event_type", "status_update")),
            timestamp=event_data.get("timestamp", datetime.now()),
            data=event_data.get("data", {}),
            step_number=self.step_counter,
            description=event_data.get("description", "Event"),
            success=event_data.get("success", True)
        )
        
        # Add to history
        self.event_history.append(event)
        
        # Prepare event data for WebSocket
        ws_event_data = {
            "step_number": event.step_number,
            "agent_id": event.agent_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "description": event.description,
            "success": event.success
        }
        
        # Broadcast to all connected clients
        if self.connected_clients:
            message = json.dumps(ws_event_data)
            disconnected_clients = []
            
            for client in self.connected_clients:
                try:
                    await client.send_text(message)
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    disconnected_clients.append(client)
            
            # Remove disconnected clients
            for client in disconnected_clients:
                self.remove_client(client)
        
        print(f"📡 Event broadcasted: {event.description}")
    
    def get_event_history(self) -> List[Dict[str, Any]]:
        """Get formatted event history for dashboard"""
        return [
            {
                "step_number": event.step_number,
                "agent_id": event.agent_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data,
                "description": event.description,
                "success": event.success
            }
            for event in self.event_history
        ]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all agents"""
        agents = {}
        for event in reversed(self.event_history):
            if event.agent_id not in agents:
                agents[event.agent_id] = {
                    "last_activity": event.timestamp.isoformat(),
                    "status": "active" if event.success else "error",
                    "last_event": event.event_type
                }
        return agents

# Global event broadcaster instance
event_broadcaster = EventBroadcaster()
