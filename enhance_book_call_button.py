#!/usr/bin/env python3

# Read the current conversation.html file
with open('dashboard/templates/conversation.html', 'r') as f:
    conversation_content = f.read()

# Read the current index.html file  
with open('dashboard/templates/index.html', 'r') as f:
    index_content = f.read()

# Enhanced button styling
enhanced_button_css = '''
        .book-call-btn {
            background: linear-gradient(135deg, var(--brand-primary) 0%, var(--brand-primary-700) 100%);
            color: #08111f !important;
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none !important;
            font-size: 0.9em;
            border: 1px solid rgba(0,227,162,0.3);
            box-shadow: 0 4px 12px rgba(0,227,162,0.2);
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .book-call-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,227,162,0.3);
            color: #06101d !important;
        }
        .book-call-btn:active {
            transform: translateY(0);
        }
        .book-call-btn i {
            font-size: 0.8em;
        }
'''

# Enhanced button HTML
enhanced_button_html = '''<a href="https://calendly.com/tara-paywithdisco/30min" target="_blank" rel="noopener" class="book-call-btn">
                        <i class="fas fa-calendar-alt"></i>
                        Book a call
                    </a>'''

# Update conversation.html
# Add the CSS
conversation_content = conversation_content.replace(
    '        .low-stock-alert {background: linear-gradient(135deg, rgba(255,92,105,0.2) 0%, rgba(255,92,105,0.12) 100%);color: white;padding: 15px;border-radius: 10px;margin: 15px 0;text-align: center;animation: pulse 2s infinite;box-shadow: 0 4px 15px rgba(220, 53, 69, 0.1875);}',
    '        .low-stock-alert {background: linear-gradient(135deg, rgba(255,92,105,0.2) 0%, rgba(255,92,105,0.12) 100%);color: white;padding: 15px;border-radius: 10px;margin: 15px 0;text-align: center;animation: pulse 2s infinite;box-shadow: 0 4px 15px rgba(220, 53, 69, 0.1875);}\n' + enhanced_button_css
)

# Replace the button
conversation_content = conversation_content.replace(
    '<a href="https://calendly.com/tara-paywithdisco/30min" target="_blank" rel="noopener" class="small text-decoration-none" style="color:var(--brand-primary)">Book a call</a>',
    enhanced_button_html
)

# Update index.html
# Add the CSS
index_content = index_content.replace(
    '        .btn-primary:hover{background:linear-gradient(135deg,var(--brand-primary-700),var(--brand-primary));transform:translateY(-1px);}',
    '        .btn-primary:hover{background:linear-gradient(135deg,var(--brand-primary-700),var(--brand-primary));transform:translateY(-1px);}\n' + enhanced_button_css
)

# Replace the button
index_content = index_content.replace(
    '<a href="https://calendly.com/tara-paywithdisco/30min" target="_blank" rel="noopener" class="small text-decoration-none" style="color:var(--brand-primary)">Book a call</a>',
    enhanced_button_html
)

# Write the updated files
with open('dashboard/templates/conversation.html', 'w') as f:
    f.write(conversation_content)

with open('dashboard/templates/index.html', 'w') as f:
    f.write(index_content)

print("Enhanced 'Book a call' button styling in both templates!")
