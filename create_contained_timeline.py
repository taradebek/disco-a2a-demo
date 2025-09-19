#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Enhanced timeline CSS for contained scrolling
timeline_css = '''
        .timeline-container {
            max-height: 500px;
            overflow-y: auto;
            padding: 20px 0;
            border-radius: 8px;
            background: var(--brand-surface);
            border: 1px solid var(--border);
        }
        .timeline-container::-webkit-scrollbar {
            width: 6px;
        }
        .timeline-container::-webkit-scrollbar-track {
            background: var(--brand-bg);
            border-radius: 3px;
        }
        .timeline-container::-webkit-scrollbar-thumb {
            background: var(--brand-primary);
            border-radius: 3px;
        }
        .timeline-container::-webkit-scrollbar-thumb:hover {
            background: var(--brand-primary-700);
        }
        .timeline {
            position: relative;
            padding: 0;
        }
        .timeline-item {
            position: relative;
            margin-bottom: 20px;
            padding-left: 40px;
            padding-right: 20px;
        }
        .timeline-item::before {
            content: '';
            position: absolute;
            left: 15px;
            top: 0;
            bottom: -20px;
            width: 2px;
            background: var(--border);
        }
        .timeline-item:last-child::before {
            display: none;
        }
        .timeline-marker {
            position: absolute;
            left: 8px;
            top: 8px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--brand-muted);
            border: 3px solid var(--brand-surface);
            box-shadow: 0 0 0 3px var(--border);
        }
        .timeline-marker.success {
            background: var(--brand-primary);
        }
        .timeline-marker.error {
            background: var(--brand-danger);
        }
        .timeline-marker.in-progress {
            background: var(--brand-warning);
            animation: pulse 2s infinite;
        }
        .timeline-card {
            background: var(--brand-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .timeline-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .timeline-card .card-title {
            color: var(--brand-text);
            font-weight: 600;
            margin-bottom: 8px;
        }
        .timeline-card .card-text {
            color: var(--brand-muted);
            font-size: 0.9em;
        }
        .timeline-card .timestamp {
            color: var(--brand-muted);
            font-size: 0.8em;
        }
        .timeline-card .agent-name {
            color: var(--brand-primary);
            font-weight: 500;
        }
        .timeline-card .event-type {
            color: var(--brand-accent);
            font-weight: 500;
        }
        .timeline-empty {
            text-align: center;
            color: var(--brand-muted);
            padding: 40px 20px;
        }
        .timeline-empty i {
            font-size: 2em;
            margin-bottom: 16px;
            color: var(--brand-muted);
        }
'''

# Update the timeline section HTML
new_timeline_section = '''            <!-- Main Timeline -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">
                            <i class="fas fa-history me-2"></i>Interaction Timeline
                        </h5>
                        <span class="badge bg-primary" id="timeline-count">0 events</span>
                    </div>
                    <div class="card-body p-0">
                        <div class="timeline-container" id="timeline-container">
                            <div class="timeline" id="timeline">
                                <div class="timeline-empty">
                                    <i class="fas fa-clock"></i>
                                    <p>Waiting for agent interactions...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>'''

# Add the CSS to the existing styles
content = content.replace(
    '        @media (max-width: 768px) {\n            .scenario-details {\n                flex-direction: column;\n                gap: 12px;\n            }\n            .scenario-title {\n                font-size: 1.8em;\n            }\n        }',
    '        @media (max-width: 768px) {\n            .scenario-details {\n                flex-direction: column;\n                gap: 12px;\n            }\n            .scenario-title {\n                font-size: 1.8em;\n            }\n        }\n' + timeline_css
)

# Replace the old timeline section
old_timeline = '''            <!-- Main Timeline -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">
                            <i class="fas fa-history me-2"></i>Interaction Timeline
                        </h5>
                        <span class="badge bg-primary" id="timeline-count">0 events</span>
                    </div>
                    <div class="card-body">
                        <div class="timeline" id="timeline">
                            <div class="text-center text-muted py-4">
                                <i class="fas fa-clock fa-2x mb-2"></i>
                                <p>Waiting for agent interactions...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>'''

content = content.replace(old_timeline, new_timeline_section)

# Update the JavaScript to work with the new timeline structure
js_updates = '''
        function addTimelineEvent(event) {
            const timeline = document.getElementById('timeline');
            const timelineContainer = document.getElementById('timeline-container');
            
            // Remove "waiting" message if it exists
            const waitingMsg = timeline.querySelector('.timeline-empty');
            if (waitingMsg) {
                waitingMsg.remove();
            }
            
            const eventDiv = document.createElement('div');
            eventDiv.className = 'timeline-item';
            eventDiv.innerHTML = `
                <div class="timeline-marker ${event.success ? 'success' : 'error'}"></div>
                <div class="timeline-card">
                    <div class="d-flex justify-content-between align-items-start">
                        <h6 class="card-title">Step ${event.step_number}: ${event.description}</h6>
                        <small class="timestamp">${new Date(event.timestamp).toLocaleTimeString()}</small>
                    </div>
                    <p class="card-text mb-1">
                        <strong class="agent-name">Agent:</strong> ${event.agent_id.replace('_', ' ').toUpperCase()}
                    </p>
                    <p class="card-text mb-0">
                        <strong class="event-type">Type:</strong> ${event.event_type.replace('_', ' ').toUpperCase()}
                    </p>
                    ${event.data && Object.keys(event.data).length > 0 ? `
                        <details class="mt-2">
                            <summary class="text-primary" style="cursor: pointer;">View Details</summary>
                            <pre class="mt-2 small" style="background: var(--brand-bg); padding: 8px; border-radius: 4px; color: var(--brand-text);">${JSON.stringify(event.data, null, 2)}</pre>
                        </details>
                    ` : ''}
                </div>
            `;
            
            timeline.appendChild(eventDiv);
            
            // Update timeline count
            const timelineCount = document.getElementById('timeline-count');
            timelineCount.textContent = `${timeline.children.length} events`;
            
            // Auto-scroll within the container if enabled
            if (document.getElementById('auto-scroll').checked) {
                timelineContainer.scrollTop = timelineContainer.scrollHeight;
            }
        }'''

# Replace the old addTimelineEvent function
old_js_function = '''        function addTimelineEvent(event) {
            const timeline = document.getElementById('timeline');
            
            // Remove "waiting" message if it exists
            const waitingMsg = timeline.querySelector('.text-center');
            if (waitingMsg) {
                waitingMsg.remove();
            }
            
            const eventDiv = document.createElement('div');
            eventDiv.className = 'timeline-item event-card';
            eventDiv.innerHTML = `
                <div class="timeline-marker ${event.success ? 'success' : 'error'}"></div>
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <h6 class="card-title mb-1">Step ${event.step_number}: ${event.description}</h6>
                            <small class="text-muted">${new Date(event.timestamp).toLocaleTimeString()}</small>
                        </div>
                        <p class="card-text text-muted mb-1">
                            <strong>Agent:</strong> ${event.agent_id.replace('_', ' ').toUpperCase()}
                        </p>
                        <p class="card-text text-muted mb-0">
                            <strong>Type:</strong> ${event.event_type.replace('_', ' ').toUpperCase()}
                        </p>
                        ${event.data && Object.keys(event.data).length > 0 ? `
                            <details class="mt-2">
                                <summary class="text-primary" style="cursor: pointer;">View Details</summary>
                                <pre class="mt-2 small">${JSON.stringify(event.data, null, 2)}</pre>
                            </details>
                        ` : ''}
                    </div>
                </div>
            `;
            
            timeline.appendChild(eventDiv);
            
            // Update timeline count
            const timelineCount = document.getElementById('timeline-count');
            timelineCount.textContent = `${timeline.children.length} events`;
            
            // Auto-scroll if enabled
            if (document.getElementById('auto-scroll').checked) {
                eventDiv.scrollIntoView({ behavior: 'smooth' });
            }
        }'''

content = content.replace(old_js_function, js_updates)

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Created contained timeline with fixed height and internal auto-scrolling!")
