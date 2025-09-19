#!/usr/bin/env python3

# Read the current files
with open('dashboard/templates/index.html', 'r') as f:
    index_content = f.read()

with open('dashboard/templates/conversation.html', 'r') as f:
    conversation_content = f.read()

# Remove the enterprise text from both files
enterprise_text = '                    <div class="brand-tag small">Enterprise-grade agent-to-agent payments</div>'

# Remove from index.html
index_content = index_content.replace(enterprise_text, '')

# Remove from conversation.html  
conversation_content = conversation_content.replace(enterprise_text, '')

# Write the updated files
with open('dashboard/templates/index.html', 'w') as f:
    f.write(index_content)

with open('dashboard/templates/conversation.html', 'w') as f:
    f.write(conversation_content)

print("Removed 'Enterprise-grade agent-to-agent payments' text from both templates!")
