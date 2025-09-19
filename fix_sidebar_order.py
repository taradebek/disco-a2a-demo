#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Find the three sidebar sections and reorder them
# Current order: Agent Status -> Current Step -> Controls  
# New order: Controls -> Agent Status -> Current Step

# Extract the three sections
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

controls_section = '''                <!-- Controls -->
                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">
                            <i class="fas fa-cogs me-2"></i>Controls
                        </h5>
                    </div>
                    <div class="card-body">
                        <button class="btn btn-primary btn-sm w-100 mb-2" onclick="startDemo()">
                            <i class="fas fa-play me-2"></i>Start Demo
                        </button>
                        <button class="btn btn-secondary btn-sm w-100 mb-2" onclick="resetDemo()">
                            <i class="fas fa-refresh me-2"></i>Reset
                        </button>
                        <button class="btn btn-info btn-sm w-100 mb-2" onclick="refreshStatus()">
                            <i class="fas fa-sync me-2"></i>Refresh Status
                        </button>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="auto-scroll" checked>
                            <label class="form-check-label" for="auto-scroll">
                                Auto-scroll timeline
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="sound-alerts" checked>
                            <label class="form-check-label" for="sound-alerts">
                                Sound alerts
                            </label>
                        </div>
                    </div>
                </div>'''

# Create the new sidebar with proper order
new_sidebar = f'''            <!-- Controls -->
{controls_section}

{agent_status_section}

{current_step_section}'''

# Find and replace the old sidebar
old_sidebar = f'''{agent_status_section}

{current_step_section}

{controls_section}'''

content = content.replace(old_sidebar, new_sidebar)

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Fixed sidebar order: Controls -> Agent Status -> Current Step")
