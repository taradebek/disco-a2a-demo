import asyncio
import json
from datetime import datetime
from agents.procurement_agent.main import procurement_agent
from agents.supplier_agent.main import supplier_agent
from a2a_protocol.event_broadcaster import event_broadcaster

async def run_slow_demo():
    """Run a slow, educational version of the A2A demo with pauses"""
    print("🎬 Starting SLOW A2A Agent Demo - Watch Each Step!")
    print("=" * 60)
    print("This demo will pause between each step so you can follow along.")
    print("Watch the dashboard at http://localhost:8000 for real-time updates!")
    print("=" * 60)
    
    # Step 1: Initialize agents
    print("\n🤖 STEP 1: Initializing Agents...")
    print("   Starting Procurement Agent...")
    await procurement_agent.start()
    await asyncio.sleep(2)  # Pause to see the event
    
    print("   Starting Supplier Agent...")
    await supplier_agent.start()
    await asyncio.sleep(2)  # Pause to see the event
    
    print("✅ Both agents are now registered and ready!")
    input("   Press Enter to continue to the next step...")
    
    # Step 2: Create purchase request
    print("\n📝 STEP 2: Creating Purchase Request...")
    print("   Procurement Agent is creating a request for office supplies...")
    
    products = [
        {"product_id": "A4_PAPER", "quantity": 50, "specifications": "White, 80gsm"},
        {"product_id": "BLACK_PENS", "quantity": 20, "specifications": "Box of 12"},
        {"product_id": "STAPLERS", "quantity": 10, "specifications": "Heavy-duty"}
    ]
    
    request_id = await procurement_agent.create_purchase_request(products, budget_limit=1000.0)
    print(f"   ✅ Purchase request created: {request_id}")
    await asyncio.sleep(2)  # Pause to see the event
    input("   Press Enter to continue to the next step...")
    
    # Step 3: Find suppliers
    print("\n🔍 STEP 3: Discovering Suppliers...")
    print("   Procurement Agent is looking for supplier agents...")
    
    suppliers = await procurement_agent.find_suppliers()
    print(f"   ✅ Found {len(suppliers)} suppliers: {suppliers}")
    await asyncio.sleep(2)  # Pause to see the event
    input("   Press Enter to continue to the next step...")
    
    # Step 4: Request quotes
    print("\n💰 STEP 4: Requesting Quotes...")
    print("   Procurement Agent is sending quote requests to suppliers...")
    
    for supplier in suppliers:
        quote_request_id = await procurement_agent.request_quote(supplier, products)
        print(f"   ✅ Quote request sent to {supplier}: {quote_request_id}")
        await asyncio.sleep(1)  # Pause between each request
    
    if not suppliers:
        print("   ⚠️  No suppliers found, but we'll continue with the demo...")
    
    input("   Press Enter to continue to the next step...")
    
    # Step 5: Start message processing
    print("\n📨 STEP 5: Starting Real-time Communication...")
    print("   Both agents are now listening for messages...")
    print("   Watch the dashboard for live message exchanges!")
    
    # Start message processing for both agents
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    print("   🔄 Agents are now communicating in real-time...")
    print("   📱 Check the dashboard at http://localhost:8000")
    print("   ⏳ Letting agents interact for 10 seconds...")
    
    # Let the agents communicate for a while
    for i in range(10):
        await asyncio.sleep(1)
        print(f"   ⏱️  {10-i} seconds remaining...")
    
    # Step 6: Final status
    print("\n📊 STEP 6: Final Status Check...")
    event_history = event_broadcaster.get_event_history()
    agent_status = event_broadcaster.get_agent_status()
    
    print(f"   ✅ Total events recorded: {len(event_history)}")
    print(f"   ✅ Agent status: {list(agent_status.keys())}")
    
    # Cancel the message processing tasks
    procurement_task.cancel()
    supplier_task.cancel()
    
    print("\n🎉 SLOW DEMO COMPLETED!")
    print("=" * 60)
    print("📱 The dashboard is still running at http://localhost:8000")
    print("🔄 You can run the scenario again from the dashboard")
    print("📊 Check the timeline to see all the agent interactions!")
    
    return {
        "status": "completed",
        "total_events": len(event_history),
        "agents": list(agent_status.keys()),
        "request_id": request_id
    }

async def run_interactive_demo():
    """Run an interactive demo where user controls the pace"""
    print("�� INTERACTIVE A2A Agent Demo")
    print("=" * 50)
    print("You control the pace! Press Enter after each step.")
    print("Watch the dashboard at http://localhost:8000")
    print("=" * 50)
    
    # Initialize agents
    print("\n🤖 Initializing Agents...")
    await procurement_agent.start()
    await supplier_agent.start()
    print("✅ Agents ready!")
    input("Press Enter to create a purchase request...")
    
    # Create purchase request
    print("\n📝 Creating Purchase Request...")
    products = [
        {"product_id": "A4_PAPER", "quantity": 100, "specifications": "White, 80gsm"},
        {"product_id": "BLACK_PENS", "quantity": 50, "specifications": "Box of 12"},
        {"product_id": "STAPLERS", "quantity": 25, "specifications": "Heavy-duty"}
    ]
    
    request_id = await procurement_agent.create_purchase_request(products, budget_limit=2000.0)
    print(f"✅ Request created: {request_id}")
    input("Press Enter to discover suppliers...")
    
    # Find suppliers
    print("\n🔍 Discovering Suppliers...")
    suppliers = await procurement_agent.find_suppliers()
    print(f"✅ Found suppliers: {suppliers}")
    input("Press Enter to request quotes...")
    
    # Request quotes
    print("\n💰 Requesting Quotes...")
    for supplier in suppliers:
        quote_id = await procurement_agent.request_quote(supplier, products)
        print(f"✅ Quote requested from {supplier}")
    input("Press Enter to start real-time communication...")
    
    # Start real-time communication
    print("\n📨 Starting Real-time Communication...")
    print("Watch the dashboard for live updates!")
    
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    print("Agents are now communicating...")
    input("Press Enter to stop and see final results...")
    
    # Stop and show results
    procurement_task.cancel()
    supplier_task.cancel()
    
    events = event_broadcaster.get_event_history()
    print(f"\n📊 Final Results:")
    print(f"   Total events: {len(events)}")
    print(f"   Request ID: {request_id}")
    print("✅ Interactive demo completed!")

if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Slow demo (automatic with pauses)")
    print("2. Interactive demo (you control the pace)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(run_interactive_demo())
    else:
        asyncio.run(run_slow_demo())
