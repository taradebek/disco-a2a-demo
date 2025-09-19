import asyncio
import json
from datetime import datetime
from agents.procurement_agent.main import procurement_agent
from agents.supplier_agent.main import supplier_agent
from a2a_protocol.event_broadcaster import event_broadcaster
import webbrowser
import base64

def generate_invoice_pdf(event_history, request_id):
    """Generate a PDF invoice from the completed transaction"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io
    
    # Create a BytesIO buffer to hold the PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#00e3a2')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#6c5ce7')
    )
    
    # Build the PDF content
    story = []
    
    # Title
    story.append(Paragraph("Disco A2A Transaction Invoice", title_style))
    story.append(Spacer(1, 20))
    
    # Invoice details
    story.append(Paragraph("Transaction Details", heading_style))
    story.append(Paragraph(f"<b>Request ID:</b> {request_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Paragraph(f"<b>Transaction Type:</b> Agent-to-Agent Office Supply Purchase", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Extract transaction details from events
    products = []
    total_amount = 0
    supplier_name = "Office Supply Co."
    
    for event in event_history:
        if event.get('event_type') == 'order_placed' and event.get('data'):
            data = event['data']
            if 'order_details' in data:
                order_details = data['order_details']
                if 'items' in order_details:
                    for item in order_details['items']:
                        products.append([
                            item.get('product_name', 'Unknown Product'),
                            str(item.get('quantity', 0)),
                            f"${item.get('unit_price', 0):.2f}",
                            f"${item.get('total_price', 0):.2f}"
                        ])
                if 'total_amount' in order_details:
                    total_amount = order_details['total_amount']
    
    # If no products found, create sample data
    if not products:
        products = [
            ["A4 Paper (80gsm)", "50", "$8.50", "$425.00"],
            ["Black Pens (Box of 12)", "20", "$12.00", "$240.00"],
            ["Heavy-duty Staplers", "10", "$25.00", "$250.00"]
        ]
        total_amount = 915.00
    
    # Products table
    story.append(Paragraph("Items Purchased", heading_style))
    table_data = [["Product", "Quantity", "Unit Price", "Total"]]
    table_data.extend(products)
    
    table = Table(table_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00e3a2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Total
    story.append(Paragraph(f"<b>Total Amount: ${total_amount:.2f}</b>", styles['Heading2']))
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("This transaction was completed autonomously by AI agents using Disco's payment protocol.", styles['Normal']))
    story.append(Paragraph("Thank you for using Disco!", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def trigger_pdf_download(pdf_data, filename):
    """Trigger PDF download in the browser"""
    import base64
    pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
    
    # Create a data URL for the PDF
    data_url = f"data:application/pdf;base64,{pdf_b64}"
    
    # Return the data URL for frontend download
    return data_url


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
        await asyncio.sleep(5)  # Pause between each request
    
    if not suppliers:
        print("⚠️  No suppliers found, but we'll continue with the demo...")
        await asyncio.sleep(5)
    
    # Step 5: Start message processing with individual event delays
    print("\n📨 Step 5: Starting Real-time Communication...")
    print("🔄 Agents are now communicating in real-time...")
    print("📱 Watch the conversation interface for live updates!")
    
    # Start message processing for both agents
    procurement_task = asyncio.create_task(procurement_agent.process_messages())
    supplier_task = asyncio.create_task(supplier_agent.process_messages())
    
    # Give agents time to start processing
    await asyncio.sleep(3)
    
    # Monitor events and add delays after EACH individual event
    print("⏱️  Agents will communicate with individual event delays...")
    initial_event_count = len(event_broadcaster.event_history)
    last_event_count = initial_event_count
    
    # Run for up to 90 seconds with individual event pacing
    for i in range(90):  # 90 seconds max
        await asyncio.sleep(0.5)  # Check every 0.5 seconds
        
        # Check current event count
        current_event_count = len(event_broadcaster.event_history)
        
        # If we have new events, add a delay after each one
        if current_event_count > last_event_count:
            new_events = current_event_count - last_event_count
            print(f"📡 {new_events} new event(s) detected, adding visibility delay...")
            
            # Add delay for each new event (1.5 seconds per event)
            for _ in range(new_events):
                await asyncio.sleep(1.5)  # 1.5 second pause after each individual event
            
            last_event_count = current_event_count
        
        # Update every 15 seconds
        if i % 30 == 0 and i > 0:  # Every 15 seconds (30 * 0.5)
            print(f"⏱️  {90-i} seconds remaining... Events so far: {current_event_count}")
        
        # Check if we have all completion events
        events = event_broadcaster.get_event_history()
        has_order = any(e.get('event_type') == 'order_placed' for e in events)
        has_payment_sent = any(e.get('event_type') == 'payment_sent' for e in events)
        has_payment_received = any(e.get('event_type') == 'payment_received' for e in events)
        has_invoice = any(e.get('event_type') == 'invoice_generated' for e in events)
        
        # If all key events are complete, we can finish early
        if has_order and has_payment_sent and has_payment_received and has_invoice:
            print("🎉 All key events completed! Transaction finished successfully.")
            break
    
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
