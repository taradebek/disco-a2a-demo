#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Remove the statistics HTML block
statistics_block = '''                <!-- Statistics -->
                <div class="card mb-4 stats-card">
                    <div class="card-header">
                        <h5 class="card-title mb-0 text-white">
                            <i class="fas fa-chart-bar me-2"></i>Statistics
                        </h5>
                    </div>
                    <div class="card-body text-white">
                        <div class="row text-center">
                            <div class="col-6">
                                <div class="h4 mb-0" id="total-events">0</div>
                                <small>Events</small>
                            </div>
                            <div class="col-6">
                                <div class="h4 mb-0" id="total-messages">0</div>
                                <small>Messages</small>
                            </div>
                        </div>
                    </div>
                </div>'''

content = content.replace(statistics_block, '')

# Remove the updateStatistics function
old_update_stats = '''        function updateStatistics(data = null) {
            if (data) {
                if (data.event_history) {
                    document.getElementById('total-events').textContent = data.event_history.length;
                }
                if (data.agent_status) {
                    // Update message count based on agent activity
                    const totalMessages = Object.keys(data.agent_status).length;
                    document.getElementById('total-messages').textContent = totalMessages;
                }
            }
        }'''

content = content.replace(old_update_stats, '')

# Remove calls to updateStatistics
content = content.replace('                updateStatistics(data);', '')
content = content.replace('                updateStatistics();', '')

# Remove the stats-card CSS class since it's no longer needed
content = content.replace('        .stats-card{background:linear-gradient(135deg,var(--brand-primary),var(--brand-accent)) !important;}', '')

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Removed statistics block and related code!")
