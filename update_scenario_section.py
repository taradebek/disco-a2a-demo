#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# New professional scenario section
new_scenario_section = '''        <div class="row">
            <!-- Scenario Description -->
            <div class="col-12">
                <div class="scenario-header">
                    <div class="scenario-content">
                        <h1 class="scenario-title">
                            <i class="fas fa-building me-3"></i>
                            Office Supply Procurement Scenario
                        </h1>
                        <p class="scenario-description">
                            A procurement agent needs to purchase office supplies within a $1,200 budget. 
                            Watch as it discovers suppliers, negotiates pricing, and completes the transaction 
                            through autonomous agent-to-agent communication powered by Disco's payment protocol.
                        </p>
                        <div class="scenario-details">
                            <div class="detail-item">
                                <i class="fas fa-shopping-cart"></i>
                                <span>50x A4 Paper, 20x Black Pens, 10x Staplers</span>
                            </div>
                            <div class="detail-item">
                                <i class="fas fa-dollar-sign"></i>
                                <span>Budget: $1,200 maximum</span>
                            </div>
                            <div class="detail-item">
                                <i class="fas fa-robot"></i>
                                <span>Fully autonomous agent negotiation</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>'''

# Add CSS for the new scenario section
scenario_css = '''
        .scenario-header {
            background: linear-gradient(135deg, var(--brand-surface) 0%, var(--brand-card) 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: var(--shadow);
        }
        .scenario-content {
            text-align: center;
        }
        .scenario-title {
            font-size: 2.2em;
            font-weight: 700;
            color: var(--brand-text);
            margin-bottom: 16px;
            letter-spacing: -0.5px;
        }
        .scenario-title i {
            color: var(--brand-primary);
        }
        .scenario-description {
            font-size: 1.1em;
            color: var(--brand-muted);
            line-height: 1.6;
            margin-bottom: 24px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        .scenario-details {
            display: flex;
            justify-content: center;
            gap: 32px;
            flex-wrap: wrap;
            margin-top: 24px;
        }
        .detail-item {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--brand-text);
            font-weight: 500;
            background: rgba(0,227,162,0.08);
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid rgba(0,227,162,0.2);
        }
        .detail-item i {
            color: var(--brand-primary);
            font-size: 0.9em;
        }
        @media (max-width: 768px) {
            .scenario-details {
                flex-direction: column;
                gap: 12px;
            }
            .scenario-title {
                font-size: 1.8em;
            }
        }
'''

# Add the CSS to the existing styles
content = content.replace(
    '        .book-call-btn i {\n            font-size: 0.8em;\n        }',
    '        .book-call-btn i {\n            font-size: 0.8em;\n        }\n' + scenario_css
)

# Replace the old header section
old_header = '''        <div class="row">
            <!-- Header -->
            <div class="col-12">
                <div class="bg-primary text-white p-3 mb-4">
                    <h1 class="h3 mb-0">
                        <i class="fas fa-robot me-2"></i>
                        Disco Agent Dashboard
                    </h1>
                    <p class="mb-0">Real-time monitoring of Agent-to-Agent payments and communication</p>
                </div>
            </div>
        </div>'''

content = content.replace(old_header, new_scenario_section)

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Updated scenario section with professional dark styling!")
