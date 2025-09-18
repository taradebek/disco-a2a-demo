# A2A Agent Interaction Prototype

A real-time demonstration of the Agent2Agent (A2A) protocol for retail supply chain automation.

## 🎯 Overview

This prototype demonstrates two AI agents collaborating to purchase office supplies using the A2A protocol:

- **Procurement Agent**: Creates purchase requests, evaluates quotes, and places orders
- **Supplier Agent**: Manages inventory, generates quotes, and processes orders

## ✨ Features

- **Real-time WebSocket Dashboard** - Live visualization of agent interactions
- **Step-by-step Timeline** - Interactive timeline showing each A2A protocol step
- **Live Message Logging** - Real-time message exchange between agents
- **Agent Status Monitoring** - Live status indicators for both agents
- **Complete A2A Protocol Implementation** - Full implementation of the A2A specification
- **Interactive Controls** - Start, stop, and reset scenarios from the dashboard

## 🚀 Quick Start

### Option 1: Full Demo (Recommended)
```bash
python3 run_demo.py
```
This will start the dashboard and run the complete scenario automatically.

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start dashboard (in one terminal)
python3 dashboard/app.py

# Run scenario (in another terminal)
PYTHONPATH=. python3 examples/purchase_scenario.py
```

### Option 3: Dashboard Only
```bash
python3 run_demo.py --dashboard-only
```

### Option 4: Scenario Only
```bash
python3 run_demo.py --scenario-only
```

## 📱 Dashboard

Once running, open your browser to:
- **Main Dashboard**: http://localhost:8000
- **API Endpoints**: http://localhost:8000/api/

### Dashboard Features:
- **Real-time Timeline**: See each step of agent interaction
- **Agent Status**: Monitor agent health and activity  
- **Message Log**: Live feed of agent communications
- **Statistics**: Event counts and performance metrics
- **Interactive Controls**: Start, stop, and reset scenarios

## 🏗️ Project Structure

```
DISCO/
├── agents/                    # Agent implementations
│   ├── procurement_agent/     # Procurement agent
│   │   ├── agent_card.json    # Agent capabilities definition
│   │   └── main.py           # Agent implementation
│   └── supplier_agent/        # Supplier agent
│       ├── agent_card.json    # Agent capabilities definition
│       └── main.py           # Agent implementation
├── a2a_protocol/             # A2A protocol implementation
│   ├── protocol.py           # Main A2A protocol
│   ├── event_broadcaster.py  # Real-time event broadcasting
│   ├── task_manager.py       # Task lifecycle management
│   └── message_handler.py    # Message exchange handling
├── dashboard/                 # Web dashboard
│   ├── app.py               # FastAPI server with WebSocket
│   └── templates/
│       └── index.html       # Real-time dashboard UI
├── shared/                    # Shared models and utilities
│   ├── models.py            # Pydantic data models
│   ├── agent_base.py        # Base agent class
│   └── utils.py             # Utility classes and helpers
├── examples/                  # Demo scenarios
│   └── purchase_scenario.py  # Office supplies purchase demo
├── run_demo.py              # Complete demo launcher
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 A2A Protocol Features

### Core Components:
- **Agent Discovery**: Agents can find and connect to each other
- **Task Management**: Structured task creation and lifecycle management
- **Message Exchange**: Secure communication between agents
- **Real-time Updates**: Live status updates and event broadcasting
- **Capability Discovery**: Agents advertise their capabilities

### Protocol Implementation:
- **Agent Cards**: JSON format describing agent capabilities
- **Task Lifecycle**: Pending → In Progress → Completed/Failed
- **Message Parts**: Support for multiple content types
- **Event Broadcasting**: Real-time event distribution
- **Correlation Tracking**: Message response tracking

## 🎬 Demo Scenario

The office supplies purchase scenario demonstrates:

1. **Agent Registration** - Both agents register with A2A protocol
2. **Capability Discovery** - Agents discover each other's capabilities
3. **Purchase Request** - Procurement agent creates purchase request
4. **Quote Request** - Request sent to supplier agent
5. **Inventory Check** - Supplier checks product availability
6. **Quote Generation** - Supplier generates pricing quote
7. **Quote Evaluation** - Procurement agent evaluates quote
8. **Order Placement** - Order placed if quote is approved
9. **Order Processing** - Supplier processes and confirms order
10. **Status Updates** - Real-time updates throughout process

## 🛠️ Technology Stack

- **Backend**: FastAPI, WebSockets, asyncio
- **Frontend**: HTML5, Bootstrap, JavaScript
- **Protocol**: Custom A2A implementation
- **Real-time**: WebSocket communication
- **Data Models**: Pydantic for validation
- **Visualization**: Interactive timeline and status panels

## �� API Endpoints

- `GET /` - Main dashboard
- `GET /api/events` - Get all events
- `GET /api/agents` - Get agent information
- `GET /api/health` - Health check
- `GET /api/statistics` - Comprehensive statistics
- `POST /api/start-demo` - Start demo scenario
- `WebSocket /ws` - Real-time updates

## 🔍 Monitoring & Debugging

### Real-time Monitoring:
- Live event timeline
- Agent status indicators
- Message exchange logs
- Performance statistics

### Debugging:
- Console logging for all events
- WebSocket connection status
- Error handling and reporting
- Step-by-step execution tracking

## 🚀 Advanced Usage

### Custom Agents:
```python
from shared.agent_base import BaseAgent

class MyAgent(BaseAgent):
    async def initialize_capabilities(self):
        # Define your agent's capabilities
        pass
```

### Custom Scenarios:
```python
from examples.purchase_scenario import run_purchase_scenario

# Run custom scenario
result = await run_purchase_scenario()
```

### API Integration:
```python
import requests

# Get events
response = requests.get("http://localhost:8000/api/events")
events = response.json()
```

## 🤝 Contributing

This is a prototype implementation of the A2A protocol. Feel free to extend and improve the codebase.

### Development Setup:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Based on the A2A protocol specification from Google Cloud
- Inspired by the Agent2Agent interoperability initiative
- Built with modern Python async/await patterns

---

**Ready to see agents in action? Run `python3 run_demo.py` and watch the magic happen! 🎉**
# Updated Thu Sep 18 11:54:02 PDT 2025
