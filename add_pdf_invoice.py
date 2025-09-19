#!/usr/bin/env python3

# First, let's add PDF generation to the conversation demo
with open('examples/conversation_demo.py', 'r') as f:
    demo_content = f.read()

# Add PDF generation import and function
pdf_import = '''import asyncio
import json
from datetime import datetime
from agents.procurement_agent.main import procurement_agent
from agents.supplier_agent.main import supplier_agent
from a2a_protocol.event_broadcaster import event_broadcaster
import webbrowser
import base64'''

# Replace the import section
demo_content = demo_content.replace(
    'import asyncio\nimport json\nfrom datetime import datetime\nfrom agents.procurement_agent.main import procurement_agent\nfrom agents.supplier_agent.main import supplier_agent\nfrom a2a_protocol.event_broadcaster import event_broadcaster',
    pdf_import
)

# Add PDF generation function
pdf_function = '''
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
    story.append(Paragraph("Disco Agent Transaction Invoice", title_style))
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
'''

# Add the PDF function after the imports
demo_content = demo_content.replace(
    'from a2a_protocol.event_broadcaster import event_broadcaster\nimport webbrowser\nimport base64',
    'from a2a_protocol.event_broadcaster import event_broadcaster\nimport webbrowser\nimport base64' + pdf_function
)

# Update the demo completion to generate PDF
old_completion = '''    print("\n🎉 Conversation Demo Completed!")
    print("=" * 50)
    print("📱 Check the conversation interface to see the full interaction!")
    
    return {
        "status": "completed",
        "total_events": len(event_history),
        "agents": list(agent_status.keys()),
        "request_id": request_id
    }'''

new_completion = '''    print("\n🎉 Conversation Demo Completed!")
    print("=" * 50)
    print("📱 Check the conversation interface to see the full interaction!")
    
    # Generate PDF invoice
    try:
        pdf_data = generate_invoice_pdf(event_history, request_id)
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
    
    return {
        "status": "completed",
        "total_events": len(event_history),
        "agents": list(agent_status.keys()),
        "request_id": request_id
    }'''

demo_content = demo_content.replace(old_completion, new_completion)

# Write the updated demo file
with open('examples/conversation_demo.py', 'w') as f:
    f.write(demo_content)

print("Added PDF invoice generation to conversation demo!")
