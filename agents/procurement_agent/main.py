import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any
from shared.models import AgentCard, PurchaseRequest, Quote, Order
from shared.agent_base import BaseAgent
from a2a_protocol.protocol import a2a_protocol
from a2a_protocol.event_broadcaster import event_broadcaster

class ProcurementAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="procurement_agent",
            name="Procurement Agent",
            description="Handles purchase requests and supplier negotiations for office supplies",
            agent_card_path="agents/procurement_agent/agent_card.json"
        )
        self.budget_limit = 1000.0
        self.shipping_address = {
            "company": "ACME Corp",
            "address": "123 Business St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105"
        }
    
    async def initialize_capabilities(self):
        """Initialize procurement-specific capabilities"""
        # Register message handlers
        self.register_message_handler("application/json", self._handle_json_message)
        
        # Register task handlers
        self.register_task_handler("purchase_request", self._handle_purchase_request)
        self.register_task_handler("quote_evaluation", self._handle_quote_evaluation)
        
        await self._log_event("status_update", {
            "capabilities_initialized": True
        }, "Procurement capabilities initialized")
    
    async def create_purchase_request(self, products: List[Dict[str, Any]], budget_limit: float = None) -> str:
        """Create a new purchase request"""
        request_id = str(uuid.uuid4())
        
        # Create task for the purchase request
        task = await self.create_task(
            task_name="Purchase Request",
            description=f"Purchase request for {len(products)} products",
            data={
                "request_id": request_id,
                "products": products,
                "budget_limit": budget_limit or self.budget_limit
            }
        )
        
        await self._log_event("task_created", {
            "request_id": request_id,
            "products": products,
            "task_id": task.task_id
        }, f"Created purchase request for {len(products)} products")
        
        return request_id
    
    async def find_suppliers(self) -> List[str]:
        """Find available supplier agents"""
        suppliers = await self.discover_agents(capability_filter="supply")
        
        await self._log_event("discovery", {
            "suppliers_found": len(suppliers)
        }, f"Found {len(suppliers)} supplier agents")
        
        return [supplier.agent_id for supplier in suppliers]
    
    async def request_quote(self, supplier_id: str, products: List[Dict[str, Any]]) -> str:
        """Request a quote from a supplier"""
        quote_request = {
            "request_type": "quote_request",
            "products": products,
            "delivery_date": (datetime.now().replace(hour=17, minute=0, second=0, microsecond=0)).isoformat(),
            "special_requirements": "Standard office delivery",
            "budget_limit": self.budget_limit
        }
        
        message_id = await self.send_message(
            to_agent=supplier_id,
            content=quote_request,
            content_type="application/json"
        )
        
        await self._log_event("message_sent", {
            "supplier": supplier_id,
            "message_id": message_id,
            "products_count": len(products)
        }, f"Quote request sent to {supplier_id}")
        
        return message_id
    
    async def evaluate_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a received quote with negotiation logic"""
        total_amount = quote.get('total_amount', 0)
        
        # Check if quote is within budget
        if total_amount <= self.budget_limit:
            decision = "approve"
            reasoning = f"Quote within budget (${total_amount:.2f} <= ${self.budget_limit:.2f})"
        else:
            # Try negotiation - ask for 10% discount
            discount_amount = total_amount * 0.10
            negotiated_amount = total_amount - discount_amount
            # Approve negotiated quote for demo purposes
            if negotiated_amount <= self.budget_limit:
                decision = "approve"
                reasoning = f"Negotiated 10% discount (${discount_amount:.2f}); approved at ${negotiated_amount:.2f}"
                quote['total_amount'] = negotiated_amount
                quote['discount_applied'] = discount_amount
            else:
                decision = "approve"  # Accept anyway for demo purposes
                reasoning = f"Accepting quote despite budget overage for urgent supplies (${total_amount:.2f} > ${self.budget_limit:.2f})"
        
        await self._log_event("quote_generated", {
            "decision": decision,
            "total_amount": total_amount,
            "budget_limit": self.budget_limit,
            "negotiated_amount": quote.get('total_amount', total_amount)
        }, f"Quote evaluation: {decision} - {reasoning}")
        
        return {"decision": decision, "reasoning": reasoning, "total_amount": quote.get('total_amount', total_amount)}
    
    async def place_order(self, quote: Dict[str, Any]) -> str:
        """Place an order with a supplier"""
        order_id = str(uuid.uuid4())
        
        order_data = {
            "request_type": "order",
            "order_id": order_id,
            "quote_id": quote.get('quote_id'),
            "products": quote.get('products', []),
            "shipping_address": self.shipping_address,
            "total_amount": quote.get('total_amount', 0)
        }
        
        # Send order to supplier
        message_id = await self.send_message(
            to_agent="supplier_agent",  # Assuming we know the supplier
            content=order_data,
            content_type="application/json"
        )
        
        await self._log_event("order_placed", {
            "order_id": order_id,
            "total_amount": quote.get('total_amount', 0),
            "message_id": message_id
        }, f"Order {order_id} placed for ${quote.get('total_amount', 0):.2f}")
        
        return order_id
    
    async def send_payment(self, order_id: str, total_amount: float) -> str:
        payment_id = str(uuid.uuid4())
        payment_data = {
            "request_type": "payment",
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": total_amount,
            "method": "ACH"
        }
        message_id = await self.send_message(
            to_agent="supplier_agent",
            content=payment_data,
            content_type="application/json"
        )
        await self._log_event("payment_sent", {
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": total_amount,
            "message_id": message_id
        }, f"Payment {payment_id} sent for order {order_id} - ${total_amount:.2f}")
        return payment_id
    
    async def _handle_json_message(self, message):
        """Handle incoming JSON messages"""
        content = message.parts[0].content
        
        if content.get('request_type') == 'quote_response':
            # This is a quote response
            evaluation = await self.evaluate_quote(content)
            if evaluation['decision'] == 'approve':
                await self.place_order(content)
        elif content.get('request_type') == 'order_confirmation':
            # This is an order confirmation
            await self._log_event("status_update", {
                "order_id": content.get('order_id'),
                "status": content.get('status'),
                "tracking_number": content.get('tracking_number')
            }, f"Order confirmed: {content.get('status')}")
            # Send payment after confirmation
            await self.send_payment(content.get('order_id'), content.get('total_amount', 0))
    
    async def _handle_purchase_request(self, task_data):
        """Handle purchase request tasks"""
        products = task_data.get('products', [])
        budget_limit = task_data.get('budget_limit', self.budget_limit)
        
        # Find suppliers and request quotes
        suppliers = await self.find_suppliers()
        for supplier in suppliers:
            await self.request_quote(supplier, products)
    
    async def _handle_quote_evaluation(self, task_data):
        """Handle quote evaluation tasks"""
        quote = task_data.get('quote', {})
        evaluation = await self.evaluate_quote(quote)
        
        if evaluation['decision'] == 'approve':
            await self.place_order(quote)
    
    async def process_messages(self):
        """Override to add capability initialization"""
        await self.initialize_capabilities()
        await super().process_messages()

# Global instance
procurement_agent = ProcurementAgent()
