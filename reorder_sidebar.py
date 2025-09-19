#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Find the current sidebar structure and swap the order
# Current order: Agent Status -> Current Step -> Controls
# New order: Controls -> Agent Status -> Current Step

# Extract the three main sections
agent_status_section = '''                <!-- Agent Status Panel -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="card-title mb-0">
                            <i class="fas fa-users me-2"></i>Agent Status
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="agent-status">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span>Procurement Agent</span>
                                <span class="agent-status status-active" id="proc-status">Active</span>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span>Supplier Agent</span>
                                <span class="agent-status status-active" id="supp-status">Active</span>
                            </div>
                        </div>
                    </div>
                </div>'''

current_step_section = '''                <!-- Current Step -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="card-title mb-0">
                            <i class="fas fa-play-circle me-2"></i>Current Step
                        </h5>
                    </div>
                    <div class="card-body text-center">
                        <div class="step-counter" id="current-step">0</div>
                        <div class="progress mt-2">
                            <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
                        </div>
                        <small class="text-muted" id="step-description">Waiting for agents to start...</small>
                    </div>
                </div>'''

# Find the controls section (it's the last one, so we need to be more specific)
import re

# Use regex to find the controls section
controls_pattern = r'(<!-- Controls -->.*?</div>\s*</div>\s*</div>\s*</div>\s*</div>\s*</div>)'
controls_match = re.search(controls_pattern, content, re.DOTALL)

if controls_match:
    controls_section = controls_match.group(1)
    
    # Create the new sidebar with reordered sections
    new_sidebar = f'''            <!-- Controls -->
{controls_section}

{agent_status_section}

{current_step_section}'''
    
    # Find the old sidebar section and replace it
    old_sidebar_pattern = r'(<!-- Agent Status Panel -->.*?</div>\s*</div>\s*</div>\s*</div>\s*</div>\s*</div>)'
    old_sidebar_match = re.search(old_sidebar_pattern, content, re.DOTALL)
    
    if old_sidebar_match:
        old_sidebar = old_sidebar_match.group(1)
        content = content.replace(old_sidebar, new_sidebar)
        
        # Write the updated content
        with open('dashboard/templates/index.html', 'w') as f:
            f.write(content)
        
        print("Reordered sidebar: Controls -> Agent Status -> Current Step")
    else:
        print("Could not find the old sidebar structure")
else:
    print("Could not find the controls section")

