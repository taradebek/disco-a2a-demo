#!/usr/bin/env python3

# Read the current index.html
with open('dashboard/templates/index.html', 'r') as f:
    content = f.read()

# Update the title
content = content.replace('<title>A2A Agent Interaction Dashboard</title>', '<title>Disco Agent Dashboard</title>')

# Add the Disco branding CSS variables and styling
disco_css = '''
        :root{
            --brand-bg:#0b1020;           /* deep navy background */
            --brand-surface:#11162a;      /* dark surface */
            --brand-card:#151b31;         /* card base */
            --brand-text:#e6e8f0;         /* primary text */
            --brand-muted:#9aa3b2;        /* muted text */
            --brand-primary:#00e3a2;      /* Disco emerald */
            --brand-primary-700:#00c58d;
            --brand-accent:#6c5ce7;       /* purple accent */
            --brand-warning:#ffc107;
            --brand-danger:#ff5c69;
            --border:#1f2745;
            --shadow:0 10px 30px rgba(0,0,0,0.2625);
        }
        body{background:linear-gradient(180deg,var(--brand-bg),#0e1430);color:var(--brand-text);font-family:'Inter',system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial,'Noto Sans',sans-serif;}
        .navbar-branding{position:sticky;top:0;z-index:1040;background:rgba(11,16,32,0.85);backdrop-filter:saturate(180%) blur(10px);border-bottom:1px solid var(--border);} 
        .navbar-branding .brand-badge{display:inline-flex;align-items:center;gap:10px;padding:10px 14px;border-radius:999px;background:linear-gradient(135deg,rgba(0,227,162,0.15),rgba(108,92,231,0.15));border:1px solid rgba(255,255,255,0.08);} 
        .navbar-branding .brand-dot{width:10px;height:10px;border-radius:50%;background:var(--brand-primary);box-shadow:0 0 9px var(--brand-primary);} 
        .navbar-branding .brand-name{font-weight:700;letter-spacing:0.3px;color:var(--brand-text);} 
        .navbar-branding .brand-tag{color:var(--brand-muted);font-weight:500;}
        .card{background:var(--brand-card);border:1px solid var(--border);color:var(--brand-text);}
        .card-header{background:var(--brand-surface);border-bottom:1px solid var(--border);}
        .bg-primary{background:linear-gradient(135deg,var(--brand-primary),var(--brand-accent)) !important;}
        .btn-primary{background:linear-gradient(135deg,var(--brand-primary),var(--brand-primary-700));border:none;color:#08111f;font-weight:600;}
        .btn-primary:hover{background:linear-gradient(135deg,var(--brand-primary-700),var(--brand-primary));transform:translateY(-1px);}
        .stats-card{background:linear-gradient(135deg,var(--brand-primary),var(--brand-accent)) !important;}
'''

# Add Google Fonts link
fonts_link = '<link rel="preconnect" href="https://fonts.googleapis.com">\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'

# Insert the fonts link after the existing font-awesome link
content = content.replace(
    '<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">',
    '<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">\n    ' + fonts_link
)

# Insert the Disco CSS after the existing style tag
content = content.replace(
    '<style>',
    '<style>\n' + disco_css
)

# Add the Disco navbar before the container-fluid
disco_navbar = '''    <!-- Branded Navbar/Header -->
    <div class="navbar-branding">
        <div class="container-fluid py-3">
            <div class="d-flex align-items-center justify-content-between">
                <div class="d-flex align-items-center gap-2 brand-badge">
                    <span class="brand-dot"></span>
                    <span class="brand-name">Disco</span>
                </div>
                <div class="d-flex align-items-center gap-3">
                    <a href="https://calendly.com/tara-paywithdisco/30min" target="_blank" rel="noopener" class="small text-decoration-none" style="color:var(--brand-primary)">Book a call</a>
                    <div class="brand-tag small">Enterprise-grade agent-to-agent payments</div>
                </div>
            </div>
        </div>
    </div>

'''

content = content.replace(
    '<div class="container-fluid">',
    disco_navbar + '<div class="container-fluid">'
)

# Update the main header
content = content.replace(
    '<h1 class="h3 mb-0">\n                        <i class="fas fa-robot me-2"></i>\n                        A2A Agent Interaction Dashboard\n                    </h1>\n                    <p class="mb-0">Real-time monitoring of Agent-to-Agent communication</p>',
    '<h1 class="h3 mb-0">\n                        <i class="fas fa-robot me-2"></i>\n                        Disco Agent Dashboard\n                    </h1>\n                    <p class="mb-0">Real-time monitoring of Agent-to-Agent payments and communication</p>'
)

# Write the updated content
with open('dashboard/templates/index.html', 'w') as f:
    f.write(content)

print("Updated index.html with Disco branding!")
