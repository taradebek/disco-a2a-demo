from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import asyncio
import uvicorn
from a2a_protocol.event_broadcaster import event_broadcaster

app = FastAPI(title="A2A Agent Interaction Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# Templates
templates = Jinja2Templates(directory="dashboard/templates")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.event_broadcaster = event_broadcaster
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.event_broadcaster.add_client(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.event_broadcaster.remove_client(websocket)
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all active connections"""
        if self.active_connections:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"Error broadcasting to connection: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/conversation", response_class=HTMLResponse)
async def conversation_demo(request: Request):
    """Conversation-style demo page"""
    return templates.TemplateResponse("conversation.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial data
        initial_data = {
            "type": "initial_data",
            "event_history": event_broadcaster.get_event_history(),
            "agent_status": event_broadcaster.get_agent_status(),
            "timestamp": asyncio.get_event_loop().time()
        }
        await manager.send_personal_message(json.dumps(initial_data), websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (like ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": asyncio.get_event_loop().time()}),
                        websocket
                    )
                elif message.get("type") == "get_status":
                    status_data = {
                        "type": "status_update",
                        "event_history": event_broadcaster.get_event_history(),
                        "agent_status": event_broadcaster.get_agent_status(),
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    await manager.send_personal_message(json.dumps(status_data), websocket)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

@app.get("/api/events")
async def get_events():
    """Get all events"""
    return {
        "events": event_broadcaster.get_event_history(),
        "agent_status": event_broadcaster.get_agent_status(),
        "total_events": len(event_broadcaster.get_event_history())
    }

@app.get("/api/agents")
async def get_agents():
    """Get agent information"""
    return {
        "agents": [
            {
                "id": "procurement_agent",
                "name": "Procurement Agent",
                "status": "active",
                "capabilities": ["create_purchase_request", "evaluate_quote", "place_order"]
            },
            {
                "id": "supplier_agent", 
                "name": "Office Supplies Supplier Agent",
                "status": "active",
                "capabilities": ["check_inventory", "generate_quote", "process_order"]
            }
        ]
    }

@app.post("/api/start-demo")
async def start_demo():
    """Start the slow conversation demo"""
    try:
        # Import and run the conversation demo
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from examples.conversation_demo import run_conversation_demo
        
        # Run the demo in the background
        asyncio.create_task(run_conversation_demo())
        
        return {"status": "success", "message": "Slow conversation demo started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/start-step-demo")
async def start_step_demo():
    """Start the step-by-step demo"""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from examples.conversation_demo import run_step_by_step_demo
        
        asyncio.create_task(run_step_by_step_demo())
        
        return {"status": "success", "message": "Step-by-step demo started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "total_events": len(event_broadcaster.get_event_history()),
        "timestamp": asyncio.get_event_loop().time()
    }

@app.get("/api/statistics")
async def get_statistics():
    """Get comprehensive statistics"""
    from a2a_protocol.protocol import a2a_protocol
    
    try:
        protocol_stats = await a2a_protocol.get_protocol_statistics()
        return {
            "protocol": protocol_stats,
            "dashboard": {
                "active_connections": len(manager.active_connections),
                "total_events": len(event_broadcaster.get_event_history())
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
