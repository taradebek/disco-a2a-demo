import asyncio
import json
from datetime import datetime
from agents.procurement_agent.main import procurement_agent
from agents.supplier_agent.main import supplier_agent
from a2a_protocol.event_broadcaster import event_broadcaster

async def run_purchase_scenario():
    """Run the complete office supplies purchase scenario with real-time updates"""
    print("🚀 Starting A2A Agent Purchase Scenario")
    print("=" * 60)
    
    # Start both agents
    print("\n📡 Initializing Agents...")
    await procurement_agent.start()
    await supplier_agent.start()
    
    # Wait a moment for agents to register
    await asyncio.sleep(1)
    
    # Step 1: Create purchase request
    print("\n📝 Step 1: Creating Purchase Request...")
    products = [
        {"product_id": "A4_PAPER", "quantity": 50, "specifications": "White, 80gsm"},
        {"product_id": "BLACK_PENS", "quantity": 20, "specifications": "Box of 12"},
        {"product_id": "STAPLERS", "quantity": 10, "specifications": "Heavy-duty"}
    ]
    
    request_id = await procurement_agent.create_purchase_request(products, budget_limit=1000.0)
    print(f"✅ Purchase request created: {request_id}")
    
    # Step 2: Find suppliers
    print("\n🔍 Step 2: Discovering Suppliers...")
    suppliers = await procurement_agent.find_suppliers()
    print(f"✅ Found {len(suppliers)} suppliers: {suppliers}")
    
    # Step 3: Request quotes
    print("\n💰 Step 3: Requesting Quotes...")
    quote_requests = []
    for supplier in suppliers:
        quote_request_id = await procurement_agent.request_quote(supplier, products)
        quote_requests.append(quote_request_id)
        print(f"✅ Quote request sent to {supplier}: {quote_request_id}")
    
    # Step 4: Start message processing for both agents
    print("\n📨 Step 4: Starting Agent Communication...")
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    # Let the agents communicate and process the scenario
    print("⏳ Processing agent interactions...")
    await asyncio.sleep(8)  # Give agents time to complete the workflow
    
    # Step 5: Check final status
    print("\n📊 Step 5: Final Status Check...")
    event_history = event_broadcaster.get_event_history()
    agent_status = event_broadcaster.get_agent_status()
    
    print(f"✅ Total events recorded: {len(event_history)}")
    print(f"✅ Agent status: {agent_status}")
    
    # Cancel the message processing tasks
    procurement_task.cancel()
    supplier_task.cancel()
    
    print("\n🎉 Purchase scenario completed!")
    print("=" * 60)
    print("📱 Check the dashboard at http://localhost:8000 to see real-time interactions")
    print("🔗 Open the dashboard in your browser to watch the live timeline!")
    
    return {
        "status": "completed",
        "total_events": len(event_history),
        "agents": list(agent_status.keys()),
        "request_id": request_id
    }

async def run_detailed_scenario():
    """Run a more detailed scenario with step-by-step logging"""
    print("🎬 Starting Detailed A2A Purchase Scenario")
    print("=" * 60)
    
    # Initialize agents
    await procurement_agent.start()
    await supplier_agent.start()
    await asyncio.sleep(1)
    
    # Scenario steps with delays for better visualization
    steps = [
        ("Creating Purchase Request", lambda: procurement_agent.create_purchase_request([
            {"product_id": "A4_PAPER", "quantity": 100, "specifications": "White, 80gsm"},
            {"product_id": "BLACK_PENS", "quantity": 50, "specifications": "Box of 12"},
            {"product_id": "STAPLERS", "quantity": 25, "specifications": "Heavy-duty"},
            {"product_id": "BINDERS", "quantity": 15, "specifications": "3-ring binders"}
        ], budget_limit=2000.0)),
        
        ("Discovering Suppliers", lambda: procurement_agent.find_suppliers()),
        
        ("Requesting Quote from Supplier", lambda: procurement_agent.request_quote("supplier_agent", [
            {"product_id": "A4_PAPER", "quantity": 100},
            {"product_id": "BLACK_PENS", "quantity": 50},
            {"product_id": "STAPLERS", "quantity": 25},
            {"product_id": "BINDERS", "quantity": 15}
        ]))
    ]
    
    # Execute steps
    for i, (step_name, step_func) in enumerate(steps, 1):
        print(f"\n🔄 Step {i}: {step_name}...")
        try:
            result = await step_func()
            print(f"✅ {step_name} completed: {result}")
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
        
        # Add delay for better visualization
        await asyncio.sleep(2)
    
    # Start message processing
    print("\n📨 Starting Real-time Message Processing...")
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    # Let it run for a while
    print("⏳ Watching agents interact in real-time...")
    await asyncio.sleep(10)
    
    # Cleanup
    procurement_task.cancel()
    supplier_task.cancel()
    
    print("\n🎬 Detailed scenario completed!")
    return {"status": "completed", "steps_executed": len(steps)}

if __name__ == "__main__":
    # Run the main scenario
    result = asyncio.run(run_purchase_scenario())
    print(f"\n📋 Scenario Result: {result}")
