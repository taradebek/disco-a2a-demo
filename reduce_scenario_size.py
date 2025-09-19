#!/usr/bin/env python3

# Read the current index.html file
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Updated CSS with 30% smaller dimensions
updated_scenario_css = '''
        .scenario-header {
            background: linear-gradient(135deg, var(--brand-surface) 0%, var(--brand-card) 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 17px;
            box-shadow: var(--shadow);
        }
        .scenario-content {
            text-align: center;
        }
        .scenario-title {
            font-size: 1.5em;
            font-weight: 700;
            color: var(--brand-text);
            margin-bottom: 11px;
            letter-spacing: -0.3px;
        }
        .scenario-title i {
            color: var(--brand-primary);
        }
        .scenario-description {
            font-size: 0.9em;
            color: var(--brand-muted);
            line-height: 1.4;
            margin-bottom: 17px;
            max-width: 560px;
            margin-left: auto;
            margin-right: auto;
        }
        .scenario-details {
            display: flex;
            justify-content: center;
            gap: 22px;
            flex-wrap: wrap;
            margin-top: 17px;
        }
        .detail-item {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--brand-text);
            font-weight: 500;
            background: rgba(0,227,162,0.08);
            padding: 8px 11px;
            border-radius: 6px;
            border: 1px solid rgba(0,227,162,0.2);
            font-size: 0.85em;
        }
        .detail-item i {
            color: var(--brand-primary);
            font-size: 0.8em;
        }
        @media (max-width: 768px) {
            .scenario-details {
                flex-direction: column;
                gap: 8px;
            }
            .scenario-title {
                font-size: 1.3em;
            }
        }
'''

# Replace the old scenario CSS
old_scenario_css = '''        .scenario-header {
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
        }'''

content = content.replace(old_scenario_css, updated_scenario_css)

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Reduced scenario section size by 30%!")
