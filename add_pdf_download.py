#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Add PDF download functionality to the JavaScript
pdf_download_js = '''
        function downloadPDF(pdfUrl, filename) {
            // Create a temporary link element and trigger download
            const link = document.createElement('a');
            link.href = pdfUrl;
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        function showPDFNotification(filename) {
            // Create a notification for PDF download
            const notification = document.createElement('div');
            notification.className = 'alert alert-success alert-dismissible fade show';
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.zIndex = '9999';
            notification.innerHTML = `
                <i class="fas fa-file-pdf me-2"></i>
                <strong>Invoice Ready!</strong> ${filename} is downloading...
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }'''

# Add the PDF functions before the existing functions
content = content.replace(
    '        function connectWebSocket() {',
    pdf_download_js + '\n\n        function connectWebSocket() {'
)

# Update the WebSocket message handler to handle PDF events
old_websocket_handler = '''        function handleWebSocketMessage(data) {
            if (data.type === 'initial_data') {
                // Load initial data
                loadEventHistory(data.event_history);
                updateAgentStatus(data.agent_status);
                updateStatistics(data);
            } else if (data.step_number) {
                // New event
                addTimelineEvent(data);
                updateCurrentStep(data.step_number);
                addMessageLog(data);
                updateStatistics();
                
                // Play sound alert if enabled
                if (document.getElementById('sound-alerts').checked) {
                    playNotificationSound();
                }
            } else if (data.type === 'status_update') {
                updateAgentStatus(data.agent_status);
                updateStatistics(data);
            }
        }'''

new_websocket_handler = '''        function handleWebSocketMessage(data) {
            if (data.type === 'initial_data') {
                // Load initial data
                loadEventHistory(data.event_history);
                updateAgentStatus(data.agent_status);
            } else if (data.step_number) {
                // New event
                addTimelineEvent(data);
                updateCurrentStep(data.step_number);
                addMessageLog(data);
                
                // Play sound alert if enabled
                if (document.getElementById('sound-alerts').checked) {
                    playNotificationSound();
                }
            } else if (data.type === 'status_update') {
                updateAgentStatus(data.agent_status);
            } else if (data.type === 'pdf_ready') {
                // Handle PDF download
                downloadPDF(data.pdf_url, data.filename);
                showPDFNotification(data.filename);
            }
        }'''

content = content.replace(old_websocket_handler, new_websocket_handler)

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Added PDF download functionality to frontend!")
