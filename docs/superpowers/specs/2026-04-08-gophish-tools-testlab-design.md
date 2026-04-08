# GoPhish + Tools Catalog + Test Lab — Spec

**Date:** 2026-04-08  
**Status:** Approved

---

## Overview

Three independent deliverables:
1. GoPhish running in Docker with pre-configured base phishing templates
2. Rich tools catalog page with execution forms per tool
3. Test Lab page for validating all system features

---

## Block 1: GoPhish in Docker + Base Templates

### Docker
- Add `gophish` service to `docker-compose.yml`
- Image: `gophish/gophish:latest`
- Ports: `3333` (admin UI), `8080` (phishing listener)
- Volume: `gophish_data:/opt/gophish/data` for persistence
- Environment: `GOPHISH_INITIAL_ADMIN_PASSWORD=RedTeam@2024!`

### Base Templates Script
Python script `backend/scripts/setup_gophish.py` that calls GoPhish REST API to create:

1. **Sending Profile** — name: `Test SMTP`, host: `mail.example.com:25`, from: `security@example.com`
2. **Email Template** — name: `Microsoft 365 - Account Verification`
   - Subject: `[Action Required] Verify your Microsoft account`
   - HTML body: branded Microsoft-style phishing email with click tracking
3. **Landing Page** — name: `Microsoft Login Page`
   - HTML: fake Microsoft login form that captures credentials
   - Redirect URL: `https://microsoft.com` after submission
4. **Target Group** — name: `Test Group` (empty, ready to add targets)

### GoPhish Credentials (post-setup)
- Admin URL: `http://localhost:3333`
- Username: `admin`
- Password: `RedTeam@2024!`
- API Key: retrieved programmatically after first login

### Integration with Frontend Campaign Form
The campaign creation form auto-fills:
- GoPhish URL: `http://gophish:3333` (internal Docker network)
- Template Name: `Microsoft 365 - Account Verification`
- Landing Page: `Microsoft Login Page`
- SMTP Profile: `Test SMTP`
- Phishing URL: `http://localhost:8080`

---

## Block 2: Tools Page Redesign

### Layout
- Page header with total count and search/filter bar
- Category tabs: All · Scan · Web · Brute Force · OSINT · Exploitation · Post-Exploitation · Phishing
- Grid of tool cards (2 columns on desktop)

### Tool Card
Each card shows:
- Icon (unique per tool, from lucide-react)
- Tool name (font-mono, neon styled)
- Category badge (neon color per category)
- Status indicator: green pulse = available, gray = not installed
- Short description
- "Details" chevron to expand
- "Execute" button (only if available, or shows "Not installed")

### Execution Panel
Clicking "Execute" opens a modal with:
- Tool name + description
- Dynamic parameter form built from tool schema
- Each parameter: label, input type (text/number/select), required marker, placeholder with example
- "Run" button → calls `POST /api/v1/executions/` with selected project
- Shows execution ID and link to results

### Tool Metadata (hardcoded in frontend — backend parameters are empty)
Rich descriptions and parameters defined per tool in `src/data/toolDefinitions.ts`:

| Tool | Category | Icon | Key Parameters |
|---|---|---|---|
| nmap | Scan | Radar | target, profile (quick/standard/full/stealth) |
| nikto | Web | Globe | target, port, ssl |
| gobuster | Web | Search | target, wordlist, mode (dir/dns/vhost) |
| hydra | Brute Force | Key | target, service, username, wordlist |
| john | Brute Force | Lock | hashfile, format, wordlist |
| medusa | Brute Force | ShieldAlert | target, username, password, module |
| cewl | OSINT | FileSearch | url, depth, min_word_length |
| wpscan | Web | WordPress | url, enumerate (users/plugins/themes) |
| shodan | OSINT | Satellite | query, limit |
| theharvester | OSINT | Binoculars | domain, sources, limit |
| whois | OSINT | Info | domain |
| hunter_io | OSINT | Mail | domain, api_key |
| passive_dns | OSINT | Network | domain |
| sqlmap | Web | Database | url, forms, level, risk |
| metasploit | Exploitation | Zap | module, rhosts, payload |
| burpsuite | Web | Bug | target, proxy_port |
| gophish | Phishing | Mail | campaign_id |
| mimikatz | Post-Exploitation | Key | command |
| empire | Post-Exploitation | Terminal | listener, agent |
| lateral_movement | Post-Exploitation | ArrowRight | target, technique |

### Files
- Modify: `frontend/src/pages/ToolsPage.tsx`
- Create: `frontend/src/data/toolDefinitions.ts`
- Create: `frontend/src/components/Tools/ToolCard.tsx`
- Create: `frontend/src/components/Tools/ToolExecuteModal.tsx`

---

## Block 3: Test Lab Page

### Route
`/test-lab` — added to sidebar between Notifications and Settings with `FlaskConical` icon.

### Sections

**1. System Health**
Grid of service status cards — each card pings its endpoint and shows green/red:
- API (`/api/v1/health` or `/`)
- PostgreSQL (via API health)
- Redis (via API health)
- GoPhish (`http://localhost:3333`)
- Grafana (`http://localhost:3000`)
- Prometheus (`http://localhost:9090`)
- Flower (`http://localhost:5555`)
- Celery Workers (via Flower API)

**2. Quick Actions**
Row of action buttons:
- **Quick Scan** — modal with target input, launches nmap quick scan
- **Quick Phishing** — 1-click creates draft campaign with GoPhish base templates
- **Generate Report** — triggers report generation for first available project

**3. Quick Links**
Button grid opening external tabs:
- Grafana Dashboard
- Prometheus Metrics
- Flower (Celery Monitor)
- Swagger API Docs

**4. Recent Activity Feed**
Live feed of last 10 executions + last 5 phishing campaigns with status badges.

**5. System Stats**
Mini stat cards: total findings, total scans, total projects, total targets.

### Files
- Create: `frontend/src/pages/TestLabPage.tsx`
- Create: `frontend/src/components/TestLab/ServiceHealthCard.tsx`
- Modify: `frontend/src/App.tsx` (add route)
- Modify: `frontend/src/components/Common/Sidebar.tsx` (add nav item)
- Modify: `frontend/src/layouts/MainLayout.tsx` (add page title)

---

## Constraints
- GoPhish setup script is idempotent (safe to run multiple times)
- Tool execution requires a project to be selected
- Test Lab health checks are client-side fetch calls (no proxy needed for localhost services)
- GoPhish internal Docker hostname is `gophish`, external is `localhost:3333`
