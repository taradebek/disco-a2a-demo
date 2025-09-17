import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from shared.models import AgentCard, Product, Quote, Order
from shared.agent_base import BaseAgent
from a2a_protocol.protocol import a2a_protocol
from a2a_protocol.event_broadcaster import event_broadcaster

class SupplierAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="supplier_agent",
            name="Office Supplies Supplier Agent",
            description="Provides office supplies inventory, pricing, and order fulfillment",
            agent_card_path="agents/supplier_agent/agent_card.json"
        )
        self.inventory = self._initialize_inventory()
        self.orders = {}
    
    def _initialize_inventory(self) -> Dict[str, Product]:
        """Initialize sample inventory"""
        products = {
            "A4_PAPER": Product(
                product_id="A4_PAPER",
                name="A4 Paper (500 sheets)",
                description="High-quality white A4 paper, 80gsm",
                unit_price=12.50,
                available_quantity=1000,
                category="Paper"
            ),
            "BLACK_PENS": Product(
                product_id="BLACK_PENS",
                name="Black Ballpoint Pens (Box of 12)",
                description="Smooth-writing black ballpoint pens",
                unit_price=8.99,
                available_quantity=500,
                category="Writing"
            ),
            "STAPLERS": Product(
                product_id="STAPLERS",
                name="Heavy-Duty Stapler",
                description="Professional stapler with 1000 staples",
                unit_price=24.99,
                available_quantity=200,
                category="Office Equipment"
            ),
            "BINDERS": Product(
                product_id="BINDERS",
                name="3-Ring Binders (Pack of 5)",
                description="Durable 3-ring binders, various colors",
                unit_price=15.99,
                available_quantity=300,
                category="Organization"
            )
        }
        return products
    
    async def initialize_capabilities(self):
        """Initialize supplier-specific capabilities"""
        # Register message handlers
        self.register_message_handler("application/json", self._handle_json_message)
        
        # Register task handlers
        self.register_task_handler("inventory_check", self._handle_inventory_check)
        self.register_task_handler("quote_generation", self._handle_quote_generation)
        self.register_task_handler("order_processing", self._handle_order_processing)
        
        await self._log_event("status_update", {
            "inventory_count": len(self.inventory),
            "capabilities_initialized": True
        }, f"Supplier capabilities initialized with {len(self.inventory)} products")
    
    async def check_inventory(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check product availability"""
        available = []
        unavailable = []
        
        for product_req in products:
            product_id = product_req.get('product_id')
            requested_qty = product_req.get('quantity', 0)
            
            if product_id in self.inventory:
                product = self.inventory[product_id]
                if product.available_quantity >= requested_qty:
                    available.append({
                        "product_id": product_id,
                        "name": product.name,
                        "available_quantity": product.available_quantity,
                        "requested_quantity": requested_qty
                    })
                else:
                    unavailable.append({
                        "product_id": product_id,
                        "name": product.name,
                        "available_quantity": product.available_quantity,
                        "requested_quantity": requested_qty,
                        "shortage": requested_qty - product.available_quantity
                    })
            else:
                unavailable.append({
                    "product_id": product_id,
                    "name": "Unknown Product",
                    "available_quantity": 0,
                    "requested_quantity": requested_qty,
                    "reason": "Product not found"
                })
        
        await self._log_event("status_update", {
            "available": len(available),
            "unavailable": len(unavailable)
        }, f"Inventory check: {len(available)} available, {len(unavailable)} unavailable")
        
        return {"available_products": available, "unavailable_products": unavailable}
    
    async def generate_quote(self, products: List[Dict[str, Any]], delivery_date: str = None, special_requirements: str = None) -> Dict[str, Any]:
        """Generate a pricing quote"""
        quote_id = str(uuid.uuid4())
        quote_products = []
        total_amount = 0.0
        
        # Check inventory first
        inventory_check = await self.check_inventory(products)
        
        if inventory_check["unavailable_products"]:
            await self._log_event("error", {
                "unavailable_products": inventory_check["unavailable_products"]
            }, "Cannot generate quote - some products unavailable", success=False)
            return None
        
        # Calculate pricing
        for product_req in products:
            product_id = product_req.get('product_id')
            quantity = product_req.get('quantity', 0)
            
            if product_id in self.inventory:
                product = self.inventory[product_id]
                unit_price = product.unit_price
                line_total = unit_price * quantity
                total_amount += line_total
                
                quote_products.append({
                    "product_id": product_id,
                    "name": product.name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total
                })
        
        # Add shipping cost (simplified)
        shipping_cost = 0 if total_amount >= 100 else 15.99
        total_amount += shipping_cost
        
        quote = {
            "request_type": "quote_response",
            "quote_id": quote_id,
            "supplier_agent": self.agent_id,
            "products": quote_products,
            "total_amount": round(total_amount, 2),
            "delivery_time": "3-5 business days",
            "valid_until": (datetime.now() + timedelta(days=7)).isoformat(),
            "shipping_cost": shipping_cost,
            "special_requirements": special_requirements
        }
        
        await self._log_event("quote_generated", {
            "quote_id": quote_id,
            "total_amount": total_amount
        }, f"Quote {quote_id} generated: ${total_amount:.2f}")
        
        return quote
    
    async def process_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a customer order"""
        order_id = order_data.get('order_id')
        products = order_data.get('products', [])
        shipping_address = order_data.get('shipping_address', {})
        
        # Update inventory
        for product in products:
            product_id = product.get('product_id')
            quantity = product.get('quantity', 0)
            if product_id in self.inventory:
                self.inventory[product_id].available_quantity -= quantity
        
        # Generate tracking number
        tracking_number = f"TRK{order_id[:8].upper()}"
        
        # Estimate delivery
        estimated_delivery = datetime.now() + timedelta(days=3)
        
        order_result = {
            "request_type": "order_confirmation",
            "order_id": order_id,
            "status": "confirmed",
            "tracking_number": tracking_number,
            "estimated_delivery": estimated_delivery.isoformat(),
            "shipping_address": shipping_address,
            "products": products,
            "total_amount": order_data.get('total_amount', 0)
        }
        
        self.orders[order_id] = order_result
        
        await self._log_event("order_placed", {
            "order_id": order_id,
            "tracking_number": tracking_number
        }, f"Order {order_id} processed, tracking: {tracking_number}")
        
        return order_result
    
 
    async def _generate_invoice(self, order_result: Dict[str, Any], total_amount: float):
        """Generate an invoice for the completed order"""
        invoice_id = f"INV-{order_result['order_id'][:8].upper()}"
        
        invoice_data = {
            "invoice_id": invoice_id,
            "order_id": order_result['order_id'],
            "total_amount": total_amount,
            "status": "generated",
            "generated_at": datetime.now().isoformat()
        }
        
        await self._log_event("invoice_generated", {
            "invoice_id": invoice_id,
            "order_id": order_result['order_id'],
            "total_amount": total_amount
        }, f"Invoice {invoice_id} generated for order {order_result['order_id']}")
        
        return invoice_data
 
    async def _handle_json_message(self, message):
        """Handle incoming JSON messages"""
        content = message.parts[0].content
        
        if content.get('request_type') == 'quote_request':
            # This is a quote request
            quote = await self.generate_quote(
                content['products'],
                content.get('delivery_date'),
                content.get('special_requirements')
            )
            if quote:
                await self.send_response(message, quote)
        elif content.get('request_type') == 'order':
            # This is an order
            order_result = await self.process_order(content)
            await self.send_response(message, order_result)
        elif content.get('request_type') == 'payment':
            # Payment received
            order_id = content.get('order_id')
            amount = content.get('amount', 0)
            await self._log_event("payment_received", {
                "order_id": order_id,
                "amount": amount
            }, f"Payment received for order {order_id}: ${amount:.2f}")
            # Generate invoice after payment
            order_result = self.orders.get(order_id, {"order_id": order_id})
            invoice = await self._generate_invoice(order_result, amount)
            await self.send_response(message, invoice)
 
    async def _handle_inventory_check(self, task_data):
        """Handle inventory check tasks"""
        products = task_data.get('products', [])
        return await self.check_inventory(products)
    
    async def _handle_quote_generation(self, task_data):
        """Handle quote generation tasks"""
        products = task_data.get('products', [])
        delivery_date = task_data.get('delivery_date')
        special_requirements = task_data.get('special_requirements')
        return await self.generate_quote(products, delivery_date, special_requirements)
    
    async def _handle_order_processing(self, task_data):
        """Handle order processing tasks"""
        return await self.process_order(task_data)
    
    async def process_messages(self):
        """Override to add capability initialization"""
        await self.initialize_capabilities()
        await super().process_messages()

# Global instance
supplier_agent = SupplierAgent()
