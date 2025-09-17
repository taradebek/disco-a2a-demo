from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

class EventType(str, Enum):
    DISCOVERY = "discovery"
    TASK_CREATED = "task_created"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    QUOTE_GENERATED = "quote_generated"
    ORDER_PLACED = "order_placed"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    # Added for payment and invoice flow
    PAYMENT_SENT = "payment_sent"
    PAYMENT_RECEIVED = "payment_received"
    INVOICE_GENERATED = "invoice_generated"

class AgentEvent(BaseModel):
    agent_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    step_number: int
    description: str
    success: bool = True

class AgentCapability(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class AgentCard(BaseModel):
    agent_id: str
    name: str
    description: str
    capabilities: List[AgentCapability]
    version: str = "1.0.0"
    status: str = "active"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task(BaseModel):
    task_id: str
    name: str
    description: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    assigned_agent: Optional[str] = None
    data: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None

class MessagePart(BaseModel):
    content_type: str
    content: Any
    metadata: Dict[str, Any] = {}

class A2AMessage(BaseModel):
    message_id: str
    from_agent: str
    to_agent: str
    task_id: Optional[str] = None
    parts: List[MessagePart]
    timestamp: datetime
    correlation_id: Optional[str] = None

class Product(BaseModel):
    product_id: str
    name: str
    description: str
    unit_price: float
    available_quantity: int
    category: str

class PurchaseRequest(BaseModel):
    request_id: str
    products: List[Dict[str, Any]]  # product_id, quantity, specifications
    delivery_date: Optional[datetime] = None
    budget_limit: Optional[float] = None
    special_requirements: Optional[str] = None

class Quote(BaseModel):
    quote_id: str
    supplier_agent: str
    products: List[Dict[str, Any]]  # product details with pricing
    total_amount: float
    valid_until: datetime
    delivery_time: str
    terms: Dict[str, Any] = {}

class Order(BaseModel):
    order_id: str
    quote_id: str
    status: str
    total_amount: float
    products: List[Dict[str, Any]]
    shipping_address: Dict[str, str]
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
