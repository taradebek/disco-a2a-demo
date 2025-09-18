import asyncio
import json
from datetime import datetime
from agents.procurement_agent.main import procurement_agent
from agents.supplier_agent.main import supplier_agent
from a2a_protocol.event_broadcaster import event_broadcaster

async def run_conversation_demo():
    """Run a slow, step-by-step conversation demo for the web interface"""
    print("🎬 Starting Conversation Demo...")
    print("=" * 50)
    
    # Step 1: Initialize agents with delays
    print("\n🤖 Step 1: Initializing Agents...")
    await procurement_agent.start()
    await asyncio.sleep(3)  # Pause to see the event in dashboard
    
    await supplier_agent.start()
    await asyncio.sleep(3)  # Pause to see the event in dashboard
    
    print("✅ Both agents are now registered and ready!")
    await asyncio.sleep(5)  # Give more time for registration
    
    # Step 2: Create purchase request
    print("\n📝 Step 2: Creating Purchase Request...")
    products = [
        {"product_id": "A4_PAPER", "quantity": 50, "specifications": "White, 80gsm"},
        {"product_id": "BLACK_PENS", "quantity": 20, "specifications": "Box of 12"},
        {"product_id": "STAPLERS", "quantity": 10, "specifications": "Heavy-duty"}
    ]
    
    request_id = await procurement_agent.create_purchase_request(products, budget_limit=1200.0)
    print(f"✅ Purchase request created: {request_id}")
    await asyncio.sleep(3)  # Pause to see the event
    
    # Step 3: Find suppliers
    print("\n🔍 Step 3: Discovering Suppliers...")
    suppliers = await procurement_agent.find_suppliers()
    print(f"✅ Found {len(suppliers)} suppliers: {suppliers}")
    await asyncio.sleep(3)  # Pause to see the event
    
    # Step 4: Request quotes
    print("\n💰 Step 4: Requesting Quotes...")
    for supplier in suppliers:
        quote_request_id = await procurement_agent.request_quote(supplier, products)
        print(f"✅ Quote request sent to {supplier}: {quote_request_id}")
        await asyncio.sleep(5)  # Give more time for registration  # Pause between each request
    
    if not suppliers:
        print("⚠️  No suppliers found, but we'll continue with the demo...")
        await asyncio.sleep(5)  # Give more time for registration
    
    # Step 5: Start message processing
    print("\n📨 Step 5: Starting Real-time Communication...")
    print("🔄 Agents are now communicating in real-time...")
    print("📱 Watch the conversation interface for live updates!")
    
    # Start message processing for both agents
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    # Give agents time to start processing
    await asyncio.sleep(3)
    
    # Let the agents communicate for a while with periodic updates
    print("⏱️  Agents will communicate for 30 seconds...")
    for i in range(30):  # 30 seconds total (doubled the time)
        await asyncio.sleep(1)
        if i % 5 == 0:  # Update every 5 seconds
            print(f"⏱️  {30-i} seconds remaining...")
    
    # Step 6: Final status
    print("\n📊 Step 6: Final Status Check...")
    event_history = event_broadcaster.get_event_history()
    agent_status = event_broadcaster.get_agent_status()
    
    print(f"✅ Total events recorded: {len(event_history)}")
    print(f"✅ Agent status: {list(agent_status.keys())}")
    
    # Cancel the message processing tasks
    procurement_task.cancel()
    supplier_task.cancel()
    
    print("\n🎉 Conversation Demo Completed!")
    print("=" * 50)
    print("📱 Check the conversation interface to see the full interaction!")
    
    return {
        "status": "completed",
        "total_events": len(event_history),
        "agents": list(agent_status.keys()),
        "request_id": request_id
    }

async def run_step_by_step_demo():
    """Run an even slower demo with manual step progression"""
    print("🎮 STEP-BY-STEP DEMO")
    print("=" * 40)
    print("This demo will pause between each major step.")
    print("Watch the conversation interface for real-time updates!")
    print("=" * 40)
    
    # Initialize agents
    print("\n🤖 Initializing Agents...")
    await procurement_agent.start()
    await asyncio.sleep(5)  # Give more time for registration
    await supplier_agent.start()
    await asyncio.sleep(5)  # Give more time for registration
    print("✅ Agents ready!")
    
    # Create purchase request
    print("\n📝 Creating Purchase Request...")
    products = [
        {"product_id": "A4_PAPER", "quantity": 100, "specifications": "White, 80gsm"},
        {"product_id": "BLACK_PENS", "quantity": 50, "specifications": "Box of 12"},
        {"product_id": "STAPLERS", "quantity": 25, "specifications": "Heavy-duty"},
        {"product_id": "BINDERS", "quantity": 15, "specifications": "3-ring binders"}
    ]
    
    request_id = await procurement_agent.create_purchase_request(products, budget_limit=2000.0)
    print(f"✅ Request created: {request_id}")
    await asyncio.sleep(3)
    
    # Find suppliers
    print("\n🔍 Discovering Suppliers...")
    suppliers = await procurement_agent.find_suppliers()
    print(f"✅ Found suppliers: {suppliers}")
    await asyncio.sleep(3)
    
    # Request quotes
    print("\n💰 Requesting Quotes...")
    for supplier in suppliers:
        quote_id = await procurement_agent.request_quote(supplier, products)
        print(f"✅ Quote requested from {supplier}")
        await asyncio.sleep(5)  # Give more time for registration
    
    # Start real-time communication
    print("\n📨 Starting Real-time Communication...")
    print("Watch the conversation interface for live updates!")
    
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    # Let it run for a while
    print("⏱️  Agents will communicate for 45 seconds...")
    for i in range(45):  # 45 seconds (more time for step-by-step)
        await asyncio.sleep(1)
        if i % 5 == 0:
            print(f"⏱️  {45-i} seconds remaining...")
    
    # Stop and show results
    procurement_task.cancel()
    supplier_task.cancel()
    
    events = event_broadcaster.get_event_history()
    print(f"\n📊 Final Results:")
    print(f"   Total events: {len(events)}")
    print(f"   Request ID: {request_id}")
    print("✅ Step-by-step demo completed!")

if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Conversation demo (automatic with delays)")
    print("2. Step-by-step demo (slower with more pauses)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(run_step_by_step_demo())
    else:
        asyncio.run(run_conversation_demo())
