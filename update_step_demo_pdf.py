#!/usr/bin/env python3

# Read the current conversation_demo.py file
with open('examples/conversation_demo.py', 'r') as f:
    content = f.read()

# Update the step-by-step demo completion
old_step_completion = '''    events = event_broadcaster.get_event_history()
    print(f"\n📊 Final Results:")
    print(f"   Total events: {len(events)}")
    print(f"   Request ID: {request_id}")
    
    print("✅ Step-by-step demo completed!")'''

new_step_completion = '''    events = event_broadcaster.get_event_history()
    print(f"\n📊 Final Results:")
    print(f"   Total events: {len(events)}")
    print(f"   Request ID: {request_id}")
    
    # Generate PDF invoice for step-by-step demo too
    try:
        pdf_data = generate_invoice_pdf(events, request_id)
        pdf_url = trigger_pdf_download(pdf_data, f"disco_invoice_{request_id}.pdf")
        
        # Broadcast PDF ready event
        event_broadcaster.broadcast_event({
            "type": "pdf_ready",
            "pdf_url": pdf_url,
            "filename": f"disco_invoice_{request_id}.pdf",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        print("📄 PDF invoice generated and ready for download!")
    except Exception as e:
        print(f"⚠️  Error generating PDF: {e}")
    
    print("✅ Step-by-step demo completed!")'''

content = content.replace(old_step_completion, new_step_completion)

# Write the updated content
with open('examples/conversation_demo.py', 'w') as f:
    f.write(content)

print("Added PDF generation to step-by-step demo!")
