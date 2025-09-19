import asyncio
import json
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn

# Add the parent directory to the Python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from a2a_protocol.event_broadcaster import event_broadcaster
    print("✅ Successfully imported event_broadcaster")
except Exception as e:
    print(f"❌ Failed to import event_broadcaster: {e}")
    # Create a mock event broadcaster for testing
    class MockEventBroadcaster:
        def __init__(self):
            self.event_history = []
            self.step_counter = 0
            self.connected_clients = []
        
        def add_client(self, client):
            self.connected_clients.append(client)
            print(f"Client connected. Total clients: {len(self.connected_clients)}")
        
        def remove_client(self, client):
            if client in self.connected_clients:
                self.connected_clients.remove(client)
                print(f"Client disconnected. Total clients: {len(self.connected_clients)}")
        
        def reset(self):
            self.event_history.clear()
            self.step_counter = 0
            print("🔄 Event broadcaster reset")
        
        def get_event_history(self):
            return []
        
        def get_agent_status(self):
            return {}
    
    event_broadcaster = MockEventBroadcaster()

app = FastAPI(title="Disco A2A Dashboard", version="1.0.0")

# Mount static files only if the directory exists
static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates - use absolute path to ensure it works in Railway
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
print(f"Templates directory: {templates_dir}")
print(f"Templates directory exists: {os.path.exists(templates_dir)}")
if os.path.exists(templates_dir):
    print(f"Files in templates directory: {os.listdir(templates_dir)}")
templates = Jinja2Templates(directory=templates_dir)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        event_broadcaster.add_client(websocket)
        
        # Send initial data
        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "event_history": event_broadcaster.get_event_history(),
            "agent_status": event_broadcaster.get_agent_status()
        }))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        event_broadcaster.remove_client(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/")
async def get_dashboard(request: Request):
    """Serve the main dashboard"""
    try:
        print(f"Attempting to render index.html from: {templates_dir}")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        print(f"Error serving dashboard: {e}")
        # Return a simple HTML response instead of 500
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Disco A2A Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a2e; color: white; }
                .error { background: #e17055; padding: 20px; border-radius: 10px; margin: 20px 0; }
                .info { background: #00b894; padding: 20px; border-radius: 10px; margin: 20px 0; }
                .debug { background: #6c5ce7; padding: 20px; border-radius: 10px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>🚀 Disco A2A Dashboard</h1>
            <div class="error">
                <h2>⚠️ Template Loading Error</h2>
                <p>Could not load the dashboard template. This is likely a deployment issue.</p>
                <p><strong>Error:</strong> {}</p>
            </div>
            <div class="info">
                <h2>📊 Dashboard Status</h2>
                <p>The backend is running correctly, but there's an issue with the frontend template.</p>
                <p><a href="/test">Test Backend</a> | <a href="/api/health">Health Check</a></p>
            </div>
            <div class="debug">
                <h2>🔧 Debug Information</h2>
                <p><strong>Current Directory:</strong> {}</p>
                <p><strong>Templates Directory:</strong> {}</p>
                <p><strong>Templates Exist:</strong> {}</p>
            </div>
        </body>
        </html>
        """.format(str(e), os.getcwd(), templates_dir, os.path.exists(templates_dir)), status_code=200)

@app.get("/test")
async def test_endpoint():
    """Test endpoint to check if the app is working"""
    return {
        "status": "ok",
        "message": "App is running",
        "event_broadcaster_working": hasattr(event_broadcaster, 'get_event_history'),
        "python_path": sys.path[:3],  # Show first 3 paths
        "current_directory": os.getcwd(),
        "templates_directory": templates_dir,
        "templates_exist": os.path.exists(templates_dir),
        "templates_files": os.listdir(templates_dir) if os.path.exists(templates_dir) else "Directory not found"
    }

@app.get("/conversation")
async def get_conversation(request: Request):
    """Serve the conversation interface"""
    try:
        return templates.TemplateResponse("conversation.html", {"request": request})
    except Exception as e:
        print(f"Error serving conversation: {e}")
        return HTMLResponse(f"<h1>Error loading conversation</h1><p>{str(e)}</p>", status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "get_status":
                await websocket.send_text(json.dumps({
                    "type": "status_update",
                    "agent_status": event_broadcaster.get_agent_status(),
                    "event_history": event_broadcaster.get_event_history()
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/api/agents")
async def get_agents():
    """Get list of available agents"""
    return {
        "agents": [
            {
                "id": "procurement_agent",
                "name": "Procurement Agent",
                "status": "active",
                "capabilities": ["create_purchase_request", "find_suppliers", "request_quote", "place_order"]
            },
            {
                "id": "supplier_agent", 
                "name": "Supplier Agent",
                "status": "active",
                "capabilities": ["check_inventory", "generate_quote", "process_order"]
            }
        ]
    }

@app.post("/api/start-demo")
async def start_demo():
    """Start the slow conversation demo"""
    try:
        from examples.conversation_demo import run_conversation_demo
        
        # Run the demo in the background
        asyncio.create_task(run_conversation_demo())
        
        return {"status": "success", "message": "Slow conversation demo started"}
    except Exception as e:
        print(f"Error starting demo: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/start-step-demo")
async def start_step_demo():
    """Start the step-by-step demo"""
    try:
        from examples.conversation_demo import run_step_by_step_demo
        
        asyncio.create_task(run_step_by_step_demo())
        
        return {"status": "success", "message": "Step-by-step demo started"}
    except Exception as e:
        print(f"Error starting step demo: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/reset-demo")
async def reset_demo():
    """Reset the demo and clear all events"""
    try:
        # Reset the event broadcaster
        event_broadcaster.reset()
        
        # Broadcast reset event to all connected clients
        await manager.broadcast(json.dumps({
            "type": "demo_reset",
            "message": "Demo has been reset"
        }))
        
        return {"status": "success", "message": "Demo reset successfully"}
    except Exception as e:
        print(f"Error resetting demo: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "active_connections": len(manager.active_connections),
            "total_events": len(event_broadcaster.get_event_history()),
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        print(f"Health check error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/statistics")
async def get_statistics():
    """Get comprehensive statistics"""
    try:
        from a2a_protocol.protocol import a2a_protocol
        
        protocol_stats = await a2a_protocol.get_protocol_statistics()
        return {
            "protocol": protocol_stats,
            "dashboard": {
                "active_connections": len(manager.active_connections),
                "total_events": len(event_broadcaster.get_event_history()),
                "step_counter": event_broadcaster.step_counter
            }
        }
    except Exception as e:
        print(f"Statistics error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
