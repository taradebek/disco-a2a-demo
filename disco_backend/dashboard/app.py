"""
Disco Developer Dashboard
FastAPI application for the developer web interface
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from disco_backend.core.config import settings
from disco_backend.core.security import verify_api_key
from disco_backend.services.health_monitor import health_monitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Disco Developer Dashboard",
    description="Web interface for managing Disco agents and payments",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="disco_backend/dashboard/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="disco_backend/dashboard/templates")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await health_monitor.initialize()
    logger.info("Disco Developer Dashboard started")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Disco Dashboard"
    })

@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, api_key: str = Depends(verify_api_key)):
    """Agents management page"""
    return templates.TemplateResponse("agents.html", {
        "request": request,
        "title": "Manage Agents",
        "api_key": api_key
    })

@app.get("/payments", response_class=HTMLResponse)
async def payments_page(request: Request, api_key: str = Depends(verify_api_key)):
    """Payments management page"""
    return templates.TemplateResponse("payments.html", {
        "request": request,
        "title": "Payment History",
        "api_key": api_key
    })

@app.get("/services", response_class=HTMLResponse)
async def services_page(request: Request, api_key: str = Depends(verify_api_key)):
    """Services management page"""
    return templates.TemplateResponse("services.html", {
        "request": request,
        "title": "Manage Services",
        "api_key": api_key
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, api_key: str = Depends(verify_api_key)):
    """Analytics dashboard page"""
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "title": "Analytics",
        "api_key": api_key
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, api_key: str = Depends(verify_api_key)):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "Settings",
        "api_key": api_key
    })

@app.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    """System health page"""
    health_status = await health_monitor.check_health()
    return templates.TemplateResponse("health.html", {
        "request": request,
        "title": "System Health",
        "health": health_status
    })

@app.get("/api/health")
async def api_health():
    """API health endpoint"""
    health_status = await health_monitor.check_health()
    return health_status

@app.get("/api/stats")
async def api_stats(api_key: str = Depends(verify_api_key)):
    """Get developer statistics"""
    # This would integrate with the main API to get stats
    return {
        "total_agents": 0,
        "total_payments": 0,
        "total_volume": 0,
        "active_services": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
