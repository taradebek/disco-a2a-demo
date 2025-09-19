#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Fix the duplicate comment
content = content.replace('                        <!-- Controls -->\n<!-- Controls -->', '            <!-- Controls -->')

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Fixed duplicate comment!")
