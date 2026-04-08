# GoPhish + Tools Catalog + Test Lab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GoPhish to Docker with base phishing templates, redesign the tools page as a rich catalog with execution forms, and build a Test Lab page for validating all system features.

**Architecture:** GoPhish runs as a Docker service alongside existing containers. Frontend gets a `toolDefinitions.ts` data file with rich metadata for all 20 tools, powering a redesigned ToolsPage with cards and execution modals. A new TestLabPage at `/test-lab` aggregates health checks, quick actions, and links to all system services.

**Tech Stack:** Docker Compose, GoPhish REST API, Python (setup script), React 19, TypeScript, Tailwind v4, lucide-react, Zustand, CSS custom properties (cyberpunk theme)

---

## Task 1: Add GoPhish to Docker Compose

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Read current docker-compose.yml**

Read `D:/Archivos/Desarrollo/red-team-saas/docker-compose.yml` to see current structure.

- [ ] **Step 2: Add GoPhish service**

In `docker-compose.yml`, add the `gophish` service block BEFORE the `volumes:` section (after the `grafana` service block), and add `gophish_data:` to the `volumes:` section.

Add this service:
```yaml
  gophish:
    image: gophish/gophish:latest
    container_name: redteam-gophish
    ports:
      - "3333:3333"
      - "8080:8080"
    volumes:
      - gophish_data:/opt/gophish
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3333"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 20s
```

Add to `volumes:` section:
```yaml
  gophish_data:
```

- [ ] **Step 3: Start GoPhish**

```bash
docker compose -f D:/Archivos/Desarrollo/red-team-saas/docker-compose.yml up -d gophish
```

Wait ~20 seconds then check:
```bash
docker logs redteam-gophish 2>&1 | tail -20
```

Expected: logs showing GoPhish started, a line like `Please login with the username admin and the password <GENERATED>`.

Copy the generated password from the logs — you'll need it in Task 2.

- [ ] **Step 4: Verify GoPhish admin accessible**

```bash
curl -sk https://localhost:3333/api/campaigns/?api_key=test 2>&1 | head -5
```

Note: GoPhish uses HTTPS on 3333 by default (self-signed cert).

- [ ] **Step 5: Commit**

```bash
cd D:/Archivos/Desarrollo/red-team-saas
git add docker-compose.yml
git commit -m "feat(docker): add GoPhish service on ports 3333/8080"
```

---

## Task 2: GoPhish base templates setup script

**Files:**
- Create: `backend/scripts/setup_gophish.py`

- [ ] **Step 1: Get GoPhish initial password from logs**

```bash
docker logs redteam-gophish 2>&1 | grep -i "password"
```

Note the generated password (it looks like a random string, e.g. `847392abc`).

- [ ] **Step 2: Login to GoPhish and get API key**

```bash
curl -sk -X POST https://localhost:3333/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<PASSWORD_FROM_LOGS>"}' | python -m json.tool
```

Note the `api_key` from the response.

- [ ] **Step 3: Create the setup script**

Create `backend/scripts/setup_gophish.py`:

```python
#!/usr/bin/env python3
"""
GoPhish base templates setup script.
Run once after GoPhish starts to create base phishing resources.

Usage:
    python setup_gophish.py --api-key <YOUR_API_KEY> [--host https://localhost:3333]
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
import ssl

# Ignore self-signed cert
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api_call(host: str, api_key: str, method: str, path: str, body=None):
    url = f"{host}/api/{path}/?api_key={api_key}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:200]}")
        return None


def resource_exists(host: str, api_key: str, path: str, name: str) -> bool:
    items = api_call(host, api_key, "GET", path)
    if not items:
        return False
    return any(i.get("name") == name for i in (items if isinstance(items, list) else []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--host", default="https://localhost:3333")
    args = parser.parse_args()

    host, key = args.host.rstrip("/"), args.api_key
    print(f"Connecting to GoPhish at {host}...")

    # ── 1. Sending Profile ────────────────────────────────────────────────────
    smtp_name = "Test SMTP"
    if resource_exists(host, key, "smtp", smtp_name):
        print(f"  [SKIP] Sending profile '{smtp_name}' already exists")
    else:
        result = api_call(host, key, "POST", "smtp", {
            "name": smtp_name,
            "host": "mail.example.com:25",
            "from_address": "IT Security <security@example.com>",
            "ignore_cert_errors": True,
            "headers": [],
        })
        print(f"  [OK]   Sending profile created: {smtp_name}" if result else f"  [FAIL] Sending profile")

    # ── 2. Email Template ─────────────────────────────────────────────────────
    template_name = "Microsoft 365 - Account Verification"
    if resource_exists(host, key, "templates", template_name):
        print(f"  [SKIP] Email template '{template_name}' already exists")
    else:
        html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Microsoft Account</title></head>
<body style="margin:0;padding:0;background:#f3f3f3;font-family:Segoe UI,Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:40px 0">
<table width="480" style="background:#fff;border:1px solid #ddd;border-radius:4px">
<tr><td style="padding:24px;background:#0078d4;text-align:center">
  <img src="https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RE1Mu3b?ver=5c31" width="108" alt="Microsoft" style="display:block;margin:auto">
</td></tr>
<tr><td style="padding:32px 24px">
  <h2 style="margin:0 0 16px;color:#323130;font-size:20px">Verify your Microsoft account</h2>
  <p style="color:#605e5c;font-size:14px;line-height:1.5">We noticed unusual activity on your account. To protect your account, please verify your identity by clicking the button below.</p>
  <p style="text-align:center;margin:28px 0">
    <a href="{{.URL}}" style="background:#0078d4;color:#fff;text-decoration:none;padding:12px 28px;border-radius:2px;font-size:14px;display:inline-block">Verify My Account</a>
  </p>
  <p style="color:#a19f9d;font-size:12px">If you didn't request this, you can ignore this email. Your account will remain secure.</p>
</td></tr>
<tr><td style="padding:16px 24px;border-top:1px solid #eee;text-align:center">
  <p style="color:#a19f9d;font-size:11px;margin:0">Microsoft Corporation, One Microsoft Way, Redmond, WA 98052</p>
</td></tr>
</table></td></tr></table>
</body></html>"""

        result = api_call(host, key, "POST", "templates", {
            "name": template_name,
            "subject": "[Action Required] Verify your Microsoft account activity",
            "html": html,
            "text": "Unusual activity detected on your Microsoft account. Visit {{.URL}} to verify your identity.",
            "attachments": [],
        })
        print(f"  [OK]   Email template created: {template_name}" if result else f"  [FAIL] Email template")

    # ── 3. Landing Page ───────────────────────────────────────────────────────
    page_name = "Microsoft Login Page"
    if resource_exists(host, key, "pages", page_name):
        print(f"  [SKIP] Landing page '{page_name}' already exists")
    else:
        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Sign in to your Microsoft account</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f2f2f2;display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:#fff;padding:44px;width:440px;box-shadow:0 2px 6px rgba(0,0,0,.2)}
.logo{margin-bottom:16px}
h1{font-size:24px;font-weight:600;color:#1b1b1b;margin-bottom:16px}
.subtitle{font-size:13px;color:#1b1b1b;margin-bottom:24px}
input{width:100%;border:1px solid #605e5c;padding:6px 10px;font-size:15px;height:36px;margin-bottom:16px;outline:none}
input:focus{border-color:#0067b8}
.btn{width:100%;background:#0067b8;color:#fff;border:none;padding:0 12px;height:36px;font-size:15px;cursor:pointer}
.btn:hover{background:#005fa3}
.links{margin-top:12px;font-size:13px}
.links a{color:#0067b8;text-decoration:none}
</style>
</head>
<body>
<div class="box">
  <div class="logo">
    <svg width="108" height="24" viewBox="0 0 108 24"><path fill="#f25022" d="M0 0h11v11H0z"/><path fill="#7fba00" d="M13 0h11v11H13z"/><path fill="#00a4ef" d="M0 13h11v11H0z"/><path fill="#ffb900" d="M13 13h11v11H13z"/><text x="28" y="18" font-family="Segoe UI,Arial" font-size="15" fill="#737373">Microsoft</text></svg>
  </div>
  <h1>Sign in</h1>
  <form action="" method="post">
    <input type="hidden" name="rid" value="{{.RId}}">
    <input type="email" name="email" placeholder="Email, phone, or Skype" required>
    <input type="password" name="password" placeholder="Password" required>
    <button class="btn" type="submit">Sign in</button>
  </form>
  <div class="links">
    <a href="#">No account? Create one!</a> &nbsp;|&nbsp; <a href="#">Forgot password?</a>
  </div>
</div>
</body>
</html>"""

        result = api_call(host, key, "POST", "pages", {
            "name": page_name,
            "html": html,
            "capture_credentials": True,
            "capture_passwords": True,
            "redirect_url": "https://microsoft.com",
        })
        print(f"  [OK]   Landing page created: {page_name}" if result else f"  [FAIL] Landing page")

    # ── 4. Target Group ───────────────────────────────────────────────────────
    group_name = "Test Group"
    if resource_exists(host, key, "groups", group_name):
        print(f"  [SKIP] Target group '{group_name}' already exists")
    else:
        result = api_call(host, key, "POST", "groups", {
            "name": group_name,
            "targets": [
                {"first_name": "Test", "last_name": "User", "email": "test@example.com", "position": "Employee"},
            ],
        })
        print(f"  [OK]   Target group created: {group_name}" if result else f"  [FAIL] Target group")

    print("\nSetup complete. Resources ready in GoPhish.")
    print(f"  Email Template : {template_name}")
    print(f"  Landing Page   : {page_name}")
    print(f"  SMTP Profile   : {smtp_name}")
    print(f"  Target Group   : {group_name}")
    print(f"  Phishing URL   : http://localhost:8080")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the setup script**

Replace `<YOUR_API_KEY>` with the key from Task 2 Step 2:

```bash
docker exec redteam-api python /app/scripts/setup_gophish.py \
  --api-key <YOUR_API_KEY> \
  --host https://gophish:3333
```

If the container can't reach GoPhish, run from host:
```bash
cd D:/Archivos/Desarrollo/red-team-saas/backend
python scripts/setup_gophish.py --api-key <YOUR_API_KEY> --host https://localhost:3333
```

Expected output:
```
Connecting to GoPhish at https://localhost:3333...
  [OK]   Sending profile created: Test SMTP
  [OK]   Email template created: Microsoft 365 - Account Verification
  [OK]   Landing page created: Microsoft Login Page
  [OK]   Target group created: Test Group
Setup complete.
```

- [ ] **Step 5: Commit**

```bash
cd D:/Archivos/Desarrollo/red-team-saas
git add backend/scripts/setup_gophish.py
git commit -m "feat(phishing): add GoPhish base templates setup script"
```

---

## Task 3: Tool definitions data file

**Files:**
- Create: `frontend/src/data/toolDefinitions.ts`

- [ ] **Step 1: Create tool definitions data**

Create `frontend/src/data/toolDefinitions.ts`:

```ts
// Rich metadata for all security tools — supplements the minimal API response

export interface ToolDef {
  name: string
  category: string
  categoryLabel: string
  icon: string            // lucide-react icon name
  description: string
  longDescription: string
  useCases: string[]
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  params: ToolParamDef[]
}

export interface ToolParamDef {
  key: string
  label: string
  type: 'text' | 'number' | 'select' | 'boolean'
  required: boolean
  placeholder?: string
  default?: string | number | boolean
  options?: { label: string; value: string }[]
  description: string
}

export const CATEGORY_COLORS: Record<string, string> = {
  scan:               'var(--neon-blue)',
  web:                'var(--neon-green)',
  brute_force:        'var(--neon-red)',
  osint:              '#ffd000',
  exploitation:       '#ff6b00',
  post_exploitation:  'var(--neon-purple)',
  phishing:           'var(--neon-red)',
}

export const CATEGORY_LABELS: Record<string, string> = {
  scan:               'Scan',
  web:                'Web',
  brute_force:        'Brute Force',
  osint:              'OSINT',
  exploitation:       'Exploitation',
  post_exploitation:  'Post-Exploitation',
  phishing:           'Phishing',
}

export const TOOL_DEFINITIONS: ToolDef[] = [
  {
    name: 'nmap',
    category: 'scan',
    categoryLabel: 'Scan',
    icon: 'Radar',
    description: 'Network exploration and security auditing tool',
    longDescription: 'Nmap discovers hosts and services on a network by sending packets and analyzing responses. Detects open ports, running services, OS versions, and vulnerabilities.',
    useCases: ['Port scanning', 'Service detection', 'OS fingerprinting', 'Network inventory'],
    riskLevel: 'medium',
    params: [
      { key: 'target', label: 'Target', type: 'text', required: true, placeholder: '192.168.1.0/24 or example.com', description: 'IP, range, CIDR or hostname' },
      { key: 'profile', label: 'Scan Profile', type: 'select', required: false, default: 'standard', description: 'Scan intensity and technique',
        options: [
          { label: 'Quick (-T4 -F)', value: 'quick' },
          { label: 'Standard (-T4 -sV -sC -O)', value: 'standard' },
          { label: 'Full (all ports)', value: 'full' },
          { label: 'Stealth (-T2 -sS)', value: 'stealth' },
          { label: 'UDP (top 100)', value: 'udp' },
        ]},
      { key: 'ports', label: 'Custom Ports', type: 'text', required: false, placeholder: '80,443,8080 or 1-1024', description: 'Override profile port selection' },
    ],
  },
  {
    name: 'nikto',
    category: 'web',
    categoryLabel: 'Web',
    icon: 'Globe',
    description: 'Web server vulnerability scanner',
    longDescription: 'Nikto scans web servers for dangerous files, outdated software, and misconfigurations. Checks for 6700+ known vulnerabilities.',
    useCases: ['Web server auditing', 'Misconfiguration detection', 'Outdated software detection'],
    riskLevel: 'medium',
    params: [
      { key: 'target', label: 'Target URL', type: 'text', required: true, placeholder: 'http://example.com', description: 'Full URL including protocol' },
      { key: 'port', label: 'Port', type: 'number', required: false, placeholder: '80', description: 'Override default port' },
      { key: 'ssl', label: 'Force SSL', type: 'boolean', required: false, default: false, description: 'Force SSL mode' },
    ],
  },
  {
    name: 'gobuster',
    category: 'web',
    categoryLabel: 'Web',
    icon: 'Search',
    description: 'Directory and DNS busting tool',
    longDescription: 'Gobuster brute-forces URIs, DNS subdomains, virtual hostnames, and S3 buckets using wordlists. Fast, concurrent, and configurable.',
    useCases: ['Directory enumeration', 'DNS subdomain discovery', 'Virtual host discovery'],
    riskLevel: 'medium',
    params: [
      { key: 'target', label: 'Target URL', type: 'text', required: true, placeholder: 'http://example.com', description: 'Target URL or domain' },
      { key: 'mode', label: 'Mode', type: 'select', required: true, default: 'dir', description: 'Scan mode',
        options: [{ label: 'Directory (dir)', value: 'dir' }, { label: 'DNS (dns)', value: 'dns' }, { label: 'Virtual Host (vhost)', value: 'vhost' }]},
      { key: 'wordlist', label: 'Wordlist', type: 'text', required: false, placeholder: '/usr/share/wordlists/dirb/common.txt', description: 'Path to wordlist file' },
      { key: 'extensions', label: 'Extensions', type: 'text', required: false, placeholder: 'php,html,js', description: 'File extensions to check (dir mode)' },
    ],
  },
  {
    name: 'hydra',
    category: 'brute_force',
    categoryLabel: 'Brute Force',
    icon: 'KeyRound',
    description: 'Network login cracker supporting many protocols',
    longDescription: 'Hydra performs fast, parallelized login attacks against many protocols: SSH, FTP, HTTP, SMB, databases, LDAP, and more.',
    useCases: ['Credential testing', 'Password spraying', 'Service authentication testing'],
    riskLevel: 'high',
    params: [
      { key: 'target', label: 'Target', type: 'text', required: true, placeholder: '192.168.1.10', description: 'Target IP or hostname' },
      { key: 'service', label: 'Service', type: 'select', required: true, default: 'ssh', description: 'Protocol to attack',
        options: [
          { label: 'SSH', value: 'ssh' }, { label: 'FTP', value: 'ftp' }, { label: 'HTTP-POST', value: 'http-post-form' },
          { label: 'SMB', value: 'smb' }, { label: 'RDP', value: 'rdp' }, { label: 'MySQL', value: 'mysql' }, { label: 'MSSQL', value: 'mssql' },
        ]},
      { key: 'username', label: 'Username', type: 'text', required: false, placeholder: 'admin', description: 'Single username or -L for list' },
      { key: 'password_list', label: 'Password List', type: 'text', required: false, placeholder: '/usr/share/wordlists/rockyou.txt', description: 'Path to password wordlist' },
    ],
  },
  {
    name: 'john',
    category: 'brute_force',
    categoryLabel: 'Brute Force',
    icon: 'Lock',
    description: 'Password hash cracker',
    longDescription: 'John the Ripper is a fast password security auditing and password recovery tool available for many operating systems. Supports hundreds of hash types.',
    useCases: ['Hash cracking', 'Password recovery', 'Security auditing'],
    riskLevel: 'high',
    params: [
      { key: 'hashfile', label: 'Hash File Path', type: 'text', required: true, placeholder: '/tmp/hashes.txt', description: 'File containing hashes to crack' },
      { key: 'format', label: 'Hash Format', type: 'select', required: false, default: 'auto', description: 'Hash format',
        options: [
          { label: 'Auto-detect', value: 'auto' }, { label: 'MD5', value: 'md5' }, { label: 'SHA-256', value: 'sha256' },
          { label: 'bcrypt', value: 'bcrypt' }, { label: 'NTLM', value: 'nt' }, { label: 'LM', value: 'lm' },
        ]},
      { key: 'wordlist', label: 'Wordlist', type: 'text', required: false, placeholder: '/usr/share/wordlists/rockyou.txt', description: 'Wordlist for dictionary attack' },
    ],
  },
  {
    name: 'medusa',
    category: 'brute_force',
    categoryLabel: 'Brute Force',
    icon: 'ShieldAlert',
    description: 'Parallel network login auditor',
    longDescription: 'Medusa is a speedy, massively parallel, modular login brute-forcer. Designed for reliability and flexibility in authentication testing.',
    useCases: ['Parallel brute force', 'Multi-target testing', 'Protocol auditing'],
    riskLevel: 'high',
    params: [
      { key: 'target', label: 'Target', type: 'text', required: true, placeholder: '192.168.1.10', description: 'Target host' },
      { key: 'username', label: 'Username', type: 'text', required: true, placeholder: 'admin', description: 'Username to test' },
      { key: 'module', label: 'Module', type: 'select', required: true, default: 'ssh', description: 'Service module',
        options: [{ label: 'SSH', value: 'ssh' }, { label: 'FTP', value: 'ftp' }, { label: 'HTTP', value: 'http' }, { label: 'SMB', value: 'smbnt' }]},
      { key: 'password_file', label: 'Password File', type: 'text', required: false, placeholder: '/usr/share/wordlists/rockyou.txt', description: 'Password list file' },
    ],
  },
  {
    name: 'cewl',
    category: 'osint',
    categoryLabel: 'OSINT',
    icon: 'FileSearch',
    description: 'Custom wordlist generator from website content',
    longDescription: 'CeWL spiders a URL and returns a list of words found on the site, useful for targeted password attacks against company-specific services.',
    useCases: ['Custom wordlist creation', 'Target reconnaissance', 'Password list generation'],
    riskLevel: 'low',
    params: [
      { key: 'url', label: 'Target URL', type: 'text', required: true, placeholder: 'https://example.com', description: 'Website to scrape' },
      { key: 'depth', label: 'Spider Depth', type: 'number', required: false, default: 2, description: 'How deep to spider the site' },
      { key: 'min_word_length', label: 'Min Word Length', type: 'number', required: false, default: 6, description: 'Minimum characters per word' },
    ],
  },
  {
    name: 'wpscan',
    category: 'web',
    categoryLabel: 'Web',
    icon: 'FileCode',
    description: 'WordPress vulnerability scanner',
    longDescription: 'WPScan is a black box WordPress security scanner that detects vulnerabilities in WordPress core, themes, and plugins using a vulnerability database.',
    useCases: ['WordPress auditing', 'Plugin vulnerability detection', 'User enumeration'],
    riskLevel: 'medium',
    params: [
      { key: 'url', label: 'WordPress URL', type: 'text', required: true, placeholder: 'https://example.com', description: 'URL of the WordPress site' },
      { key: 'enumerate', label: 'Enumerate', type: 'select', required: false, default: 'vp', description: 'What to enumerate',
        options: [
          { label: 'Vulnerable Plugins (vp)', value: 'vp' }, { label: 'All Plugins (ap)', value: 'ap' },
          { label: 'Users (u)', value: 'u' }, { label: 'Themes (t)', value: 't' }, { label: 'All (vp,vt,u)', value: 'vp,vt,u' },
        ]},
    ],
  },
  {
    name: 'shodan',
    category: 'osint',
    categoryLabel: 'OSINT',
    icon: 'Satellite',
    description: 'Internet-wide device search engine',
    longDescription: 'Shodan searches for internet-connected devices and services. Reveals open ports, software versions, vulnerabilities, and device metadata globally.',
    useCases: ['Asset discovery', 'Exposure analysis', 'Vulnerability intelligence'],
    riskLevel: 'low',
    params: [
      { key: 'query', label: 'Search Query', type: 'text', required: true, placeholder: 'org:"Example Corp" port:22', description: 'Shodan search query' },
      { key: 'limit', label: 'Result Limit', type: 'number', required: false, default: 10, description: 'Max results to return' },
    ],
  },
  {
    name: 'theharvester',
    category: 'osint',
    categoryLabel: 'OSINT',
    icon: 'Binoculars',
    description: 'Email, subdomain and name harvester',
    longDescription: 'theHarvester gathers emails, names, subdomains, IPs, and URLs from multiple public sources: search engines, PGP key servers, LinkedIn, and more.',
    useCases: ['Email enumeration', 'Subdomain discovery', 'Passive reconnaissance'],
    riskLevel: 'low',
    params: [
      { key: 'domain', label: 'Target Domain', type: 'text', required: true, placeholder: 'example.com', description: 'Domain to investigate' },
      { key: 'sources', label: 'Sources', type: 'text', required: false, default: 'google,bing,linkedin', placeholder: 'google,bing,linkedin', description: 'Comma-separated list of sources' },
      { key: 'limit', label: 'Result Limit', type: 'number', required: false, default: 100, description: 'Max results per source' },
    ],
  },
  {
    name: 'whois',
    category: 'osint',
    categoryLabel: 'OSINT',
    icon: 'Info',
    description: 'Domain registration information lookup',
    longDescription: 'WHOIS queries domain registrar databases to find registration data: registrant, creation/expiry dates, name servers, and contact info.',
    useCases: ['Domain intelligence', 'Registrant lookup', 'Infrastructure mapping'],
    riskLevel: 'low',
    params: [
      { key: 'domain', label: 'Domain', type: 'text', required: true, placeholder: 'example.com', description: 'Domain or IP to look up' },
    ],
  },
  {
    name: 'hunter_io',
    category: 'osint',
    categoryLabel: 'OSINT',
    icon: 'Mail',
    description: 'Email address finder for domains',
    longDescription: 'Hunter.io finds email addresses associated with a domain, reveals email patterns, and provides confidence scores for discovered addresses.',
    useCases: ['Email harvesting', 'Contact discovery', 'Phishing target research'],
    riskLevel: 'low',
    params: [
      { key: 'domain', label: 'Target Domain', type: 'text', required: true, placeholder: 'example.com', description: 'Domain to search for emails' },
    ],
  },
  {
    name: 'passive_dns',
    category: 'osint',
    categoryLabel: 'OSINT',
    icon: 'Network',
    description: 'Passive DNS history lookup',
    longDescription: 'Passive DNS queries historical DNS resolution data to map IP-to-domain associations over time — useful for tracking infrastructure changes.',
    useCases: ['Historical DNS analysis', 'IP attribution', 'Infrastructure tracking'],
    riskLevel: 'low',
    params: [
      { key: 'domain', label: 'Domain or IP', type: 'text', required: true, placeholder: 'example.com or 1.2.3.4', description: 'Domain or IP to look up' },
    ],
  },
  {
    name: 'sqlmap',
    category: 'web',
    categoryLabel: 'Web',
    icon: 'Database',
    description: 'Automatic SQL injection detection and exploitation',
    longDescription: 'SQLMap automates detecting and exploiting SQL injection vulnerabilities in web applications. Supports MySQL, PostgreSQL, MSSQL, Oracle, and more.',
    useCases: ['SQL injection testing', 'Database fingerprinting', 'Data extraction'],
    riskLevel: 'critical',
    params: [
      { key: 'url', label: 'Target URL', type: 'text', required: true, placeholder: 'http://example.com/page?id=1', description: 'URL with parameter to test' },
      { key: 'forms', label: 'Test Forms', type: 'boolean', required: false, default: false, description: 'Automatically test HTML forms' },
      { key: 'level', label: 'Test Level', type: 'select', required: false, default: '1', description: 'Depth of tests (1-5)',
        options: [{ label: '1 - Basic', value: '1' }, { label: '2', value: '2' }, { label: '3', value: '3' }, { label: '5 - Maximum', value: '5' }]},
      { key: 'risk', label: 'Risk Level', type: 'select', required: false, default: '1', description: 'Risk of tests (1-3)',
        options: [{ label: '1 - Safe', value: '1' }, { label: '2 - Medium', value: '2' }, { label: '3 - Aggressive', value: '3' }]},
    ],
  },
  {
    name: 'metasploit',
    category: 'exploitation',
    categoryLabel: 'Exploitation',
    icon: 'Zap',
    description: 'Penetration testing framework',
    longDescription: 'Metasploit is the world\'s most used penetration testing framework. Provides exploits, payloads, encoders, and post-exploitation modules.',
    useCases: ['Exploit development', 'Vulnerability validation', 'Post-exploitation'],
    riskLevel: 'critical',
    params: [
      { key: 'module', label: 'Module', type: 'text', required: true, placeholder: 'exploit/multi/handler', description: 'Metasploit module path' },
      { key: 'rhosts', label: 'Target (RHOSTS)', type: 'text', required: true, placeholder: '192.168.1.10', description: 'Target host(s)' },
      { key: 'payload', label: 'Payload', type: 'text', required: false, placeholder: 'windows/x64/meterpreter/reverse_tcp', description: 'Payload to use' },
      { key: 'lhost', label: 'LHOST', type: 'text', required: false, placeholder: '192.168.1.5', description: 'Your IP for reverse shells' },
    ],
  },
  {
    name: 'burpsuite',
    category: 'web',
    categoryLabel: 'Web',
    icon: 'Bug',
    description: 'Web application security testing platform',
    longDescription: 'Burp Suite is an integrated platform for performing web application security testing. Includes proxy, scanner, intruder, repeater, and extensibility.',
    useCases: ['Web app pentesting', 'API testing', 'Session analysis', 'CSRF/XSS testing'],
    riskLevel: 'high',
    params: [
      { key: 'target', label: 'Target URL', type: 'text', required: true, placeholder: 'http://example.com', description: 'Web application URL' },
      { key: 'proxy_port', label: 'Proxy Port', type: 'number', required: false, default: 8081, description: 'Local proxy listener port' },
    ],
  },
  {
    name: 'gophish',
    category: 'phishing',
    categoryLabel: 'Phishing',
    icon: 'MailWarning',
    description: 'Open-source phishing campaign toolkit',
    longDescription: 'GoPhish is an open-source phishing toolkit that makes it easy to test organizational exposure to phishing attacks with tracking, templates, and analytics.',
    useCases: ['Phishing simulations', 'Employee awareness testing', 'Email campaign management'],
    riskLevel: 'high',
    params: [
      { key: 'campaign_id', label: 'Campaign ID', type: 'number', required: true, placeholder: '1', description: 'GoPhish campaign ID to manage' },
    ],
  },
  {
    name: 'mimikatz',
    category: 'post_exploitation',
    categoryLabel: 'Post-Exploitation',
    icon: 'KeySquare',
    description: 'Windows credential extraction tool',
    longDescription: 'Mimikatz extracts plaintext passwords, hashes, PIN codes, and Kerberos tickets from Windows memory. Essential for post-exploitation credential harvesting.',
    useCases: ['Credential dumping', 'Pass-the-hash', 'Kerberoasting', 'Golden ticket attacks'],
    riskLevel: 'critical',
    params: [
      { key: 'command', label: 'Command', type: 'select', required: true, default: 'sekurlsa::logonpasswords', description: 'Mimikatz command to run',
        options: [
          { label: 'Dump Logon Passwords', value: 'sekurlsa::logonpasswords' },
          { label: 'Dump NTLM Hashes', value: 'lsadump::sam' },
          { label: 'Kerberos Tickets', value: 'kerberos::list' },
          { label: 'DCSync', value: 'lsadump::dcsync' },
        ]},
    ],
  },
  {
    name: 'empire',
    category: 'post_exploitation',
    categoryLabel: 'Post-Exploitation',
    icon: 'Terminal',
    description: 'PowerShell and Python post-exploitation agent',
    longDescription: 'Empire is a post-exploitation framework that includes a pure-PowerShell Windows agent and Python agent. Provides C2 capabilities without needing meterpreter.',
    useCases: ['C2 operations', 'Lateral movement', 'Persistence', 'Data exfiltration'],
    riskLevel: 'critical',
    params: [
      { key: 'listener', label: 'Listener Name', type: 'text', required: true, placeholder: 'http_listener', description: 'Name of the Empire listener' },
      { key: 'agent', label: 'Agent Name', type: 'text', required: false, placeholder: 'WIN10_AGENT1', description: 'Agent to interact with' },
    ],
  },
  {
    name: 'lateral_movement',
    category: 'post_exploitation',
    categoryLabel: 'Post-Exploitation',
    icon: 'ArrowRightLeft',
    description: 'Lateral movement techniques toolkit',
    longDescription: 'Collection of lateral movement techniques: Pass-the-Hash, Pass-the-Ticket, WMI execution, PsExec, and SMB-based movement across network segments.',
    useCases: ['Network pivoting', 'Privilege escalation', 'Domain compromise', 'Pass-the-Hash'],
    riskLevel: 'critical',
    params: [
      { key: 'target', label: 'Target Host', type: 'text', required: true, placeholder: '192.168.1.20', description: 'Target host to move to' },
      { key: 'technique', label: 'Technique', type: 'select', required: true, default: 'pth', description: 'Lateral movement technique',
        options: [
          { label: 'Pass-the-Hash', value: 'pth' }, { label: 'WMI Execution', value: 'wmi' },
          { label: 'PsExec', value: 'psexec' }, { label: 'SMB', value: 'smb' },
        ]},
      { key: 'username', label: 'Username', type: 'text', required: false, placeholder: 'DOMAIN\\Administrator', description: 'Credentials to use' },
    ],
  },
]

export function getToolDef(name: string): ToolDef | undefined {
  return TOOL_DEFINITIONS.find((t) => t.name === name)
}

export function getRiskColor(risk: ToolDef['riskLevel']): string {
  const colors = {
    low:      'var(--neon-green)',
    medium:   '#ffd000',
    high:     '#ff6b00',
    critical: 'var(--neon-red)',
  }
  return colors[risk]
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd D:/Archivos/Desarrollo/red-team-saas/frontend && npx tsc --noEmit 2>&1 | head -10
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd D:/Archivos/Desarrollo/red-team-saas
git add frontend/src/data/toolDefinitions.ts
git commit -m "feat(tools): add rich tool definitions data for all 20 tools"
```

---

## Task 4: Tools page redesign — ToolCard + ToolExecuteModal + ToolsPage

**Files:**
- Create: `frontend/src/components/Tools/ToolCard.tsx`
- Create: `frontend/src/components/Tools/ToolExecuteModal.tsx`
- Modify: `frontend/src/pages/ToolsPage.tsx`

- [ ] **Step 1: Create ToolCard component**

Create `frontend/src/components/Tools/ToolCard.tsx`:

```tsx
import { useState } from 'react'
import { ChevronDown, ChevronUp, Play, AlertTriangle } from 'lucide-react'
import * as Icons from 'lucide-react'
import type { Tool } from '../../types'
import { getToolDef, getRiskColor, CATEGORY_COLORS, CATEGORY_LABELS } from '../../data/toolDefinitions'

interface ToolCardProps {
  tool: Tool
  onExecute: (toolName: string) => void
}

export default function ToolCard({ tool, onExecute }: ToolCardProps) {
  const [expanded, setExpanded] = useState(false)
  const def = getToolDef(tool.name)

  // Dynamically get icon from lucide-react
  const iconName = def?.icon || 'Wrench'
  const IconComponent = (Icons as Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>>)[iconName] || Icons.Wrench

  const catColor = CATEGORY_COLORS[tool.category] || 'var(--color-text-secondary)'
  const catLabel = CATEGORY_LABELS[tool.category] || tool.category
  const riskColor = def ? getRiskColor(def.riskLevel) : 'var(--color-text-secondary)'

  return (
    <div className="rounded-sm overflow-hidden transition-all duration-200"
      style={{ border: `1px solid ${expanded ? catColor : 'var(--color-border)'}`, background: 'var(--color-bg-secondary)' }}>

      {/* Header */}
      <div className="flex items-start gap-4 p-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        {/* Icon */}
        <div className="w-10 h-10 rounded-sm flex items-center justify-center flex-shrink-0"
          style={{ background: `${catColor}15`, border: `1px solid ${catColor}40` }}>
          <IconComponent className="w-5 h-5" style={{ color: catColor }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-white font-mono font-semibold text-sm">{tool.name}</span>
            <span className="text-xs font-mono px-1.5 py-0.5 rounded-sm"
              style={{ color: catColor, background: `${catColor}15`, border: `1px solid ${catColor}30` }}>
              {catLabel}
            </span>
            {def && (
              <span className="text-xs font-mono px-1.5 py-0.5 rounded-sm"
                style={{ color: riskColor, background: `${riskColor}15`, border: `1px solid ${riskColor}30` }}>
                {def.riskLevel}
              </span>
            )}
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1 font-mono">
            {def?.description || tool.description}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Status dot */}
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${tool.available ? 'neon-pulse' : ''}`}
              style={{ background: tool.available ? 'var(--neon-green)' : 'var(--color-text-secondary)' }} />
            <span className="text-xs font-mono" style={{ color: tool.available ? 'var(--neon-green)' : 'var(--color-text-secondary)' }}>
              {tool.available ? 'ready' : 'n/a'}
            </span>
          </div>
          {expanded ? <ChevronUp className="w-4 h-4 text-[var(--color-text-secondary)]" /> : <ChevronDown className="w-4 h-4 text-[var(--color-text-secondary)]" />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && def && (
        <div className="px-4 pb-4 border-t border-[var(--color-border)] pt-3 space-y-3">
          <p className="text-xs font-mono text-[var(--color-text-secondary)] leading-relaxed">
            {def.longDescription}
          </p>

          {/* Use cases */}
          <div>
            <p className="text-xs font-mono mb-1.5" style={{ color: catColor }}>// Use Cases</p>
            <div className="flex flex-wrap gap-1.5">
              {def.useCases.map((uc) => (
                <span key={uc} className="text-xs font-mono px-2 py-0.5 rounded-sm"
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
                  {uc}
                </span>
              ))}
            </div>
          </div>

          {/* Parameters preview */}
          {def.params.length > 0 && (
            <div>
              <p className="text-xs font-mono mb-1.5" style={{ color: 'var(--neon-blue)' }}>// Parameters</p>
              <div className="space-y-1">
                {def.params.map((p) => (
                  <div key={p.key} className="flex items-center gap-2 text-xs font-mono">
                    <span style={{ color: catColor }}>{p.key}</span>
                    <span className="text-[var(--color-text-secondary)]">({p.type})</span>
                    {p.required && <span style={{ color: 'var(--neon-red)' }}>*</span>}
                    <span className="text-[var(--color-text-secondary)]">— {p.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk warning */}
          {(def.riskLevel === 'high' || def.riskLevel === 'critical') && (
            <div className="flex items-center gap-2 p-2 rounded-sm text-xs font-mono"
              style={{ background: `${riskColor}08`, border: `1px solid ${riskColor}30`, color: riskColor }}>
              <AlertTriangle className="w-3 h-3 flex-shrink-0" />
              {def.riskLevel === 'critical' ? 'Critical risk — only use in authorized engagements' : 'High risk — ensure proper authorization before use'}
            </div>
          )}

          {/* Execute button */}
          <button
            onClick={(e) => { e.stopPropagation(); onExecute(tool.name) }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-mono transition-all"
            style={tool.available
              ? { border: `1px solid ${catColor}`, color: catColor, background: `${catColor}10`, cursor: 'pointer' }
              : { border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)', background: 'transparent', cursor: 'not-allowed', opacity: 0.5 }}>
            <Play className="w-3 h-3" />
            {tool.available ? 'execute' : 'not installed'}
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create ToolExecuteModal**

Create `frontend/src/components/Tools/ToolExecuteModal.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { X, Play, Loader2, ExternalLink } from 'lucide-react'
import { getToolDef, CATEGORY_COLORS } from '../../data/toolDefinitions'
import { toolService } from '../../services/toolService'
import api from '../../services/api'
import type { Project } from '../../types'

interface ToolExecuteModalProps {
  toolName: string
  onClose: () => void
}

export default function ToolExecuteModal({ toolName, onClose }: ToolExecuteModalProps) {
  const def = getToolDef(toolName)
  const catColor = def ? CATEGORY_COLORS[def.category] || 'var(--neon-green)' : 'var(--neon-green)'

  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number>(0)
  const [params, setParams] = useState<Record<string, string | number | boolean>>({})
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ executionId?: number; error?: string } | null>(null)

  useEffect(() => {
    api.get('/projects/').then((r) => {
      const items: Project[] = Array.isArray(r.data) ? r.data : r.data.items ?? []
      setProjects(items)
      if (items.length > 0) setProjectId(items[0].id)
    }).catch(() => {})

    // Set defaults
    if (def) {
      const defaults: Record<string, string | number | boolean> = {}
      def.params.forEach((p) => {
        if (p.default !== undefined) defaults[p.key] = p.default as string | number | boolean
      })
      setParams(defaults)
    }
  }, [toolName, def])

  const setParam = (key: string, value: string | number | boolean) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }

  const handleRun = async () => {
    setRunning(true)
    setResult(null)
    try {
      const payload = { tool_name: toolName, parameters: params, project_id: projectId }
      const data = await toolService.execute(toolName, { ...params, project_id: projectId })
      const exec = data as { id?: number; execution_id?: number }
      setResult({ executionId: exec?.id || exec?.execution_id })
    } catch (err: any) {
      setResult({ error: err?.response?.data?.detail || 'Execution failed' })
    } finally {
      setRunning(false)
    }
  }

  const inputClass = "w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
  const inputStyle = { background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }

  if (!def) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)' }} onClick={onClose}>
      <div className="w-full max-w-lg rounded-sm overflow-hidden max-h-[90vh] flex flex-col"
        style={{ background: 'var(--color-bg-secondary)', border: `1px solid ${catColor}`, boxShadow: `0 0 20px ${catColor}22` }}
        onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div>
            <span className="text-sm font-mono font-bold" style={{ color: catColor }}>{toolName}</span>
            <span className="text-xs font-mono text-[var(--color-text-secondary)] ml-2">// execute</span>
          </div>
          <button onClick={onClose} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="overflow-y-auto p-5 space-y-4 flex-1">
          {/* Project selector */}
          <div>
            <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Project</label>
            <select value={projectId} onChange={(e) => setProjectId(Number(e.target.value))}
              className={inputClass} style={inputStyle}>
              {projects.length === 0
                ? <option value={0}>No projects — create one first</option>
                : projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          {/* Dynamic params */}
          {def.params.map((p) => (
            <div key={p.key}>
              <label className="block text-xs font-mono mb-1">
                <span style={{ color: catColor }}>{p.key}</span>
                {p.required && <span style={{ color: 'var(--neon-red)' }}> *</span>}
                <span className="text-[var(--color-text-secondary)] ml-2">— {p.description}</span>
              </label>

              {p.type === 'select' ? (
                <select value={String(params[p.key] ?? p.default ?? '')}
                  onChange={(e) => setParam(p.key, e.target.value)}
                  className={inputClass} style={inputStyle}>
                  {p.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              ) : p.type === 'boolean' ? (
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={Boolean(params[p.key] ?? p.default)}
                    onChange={(e) => setParam(p.key, e.target.checked)} className="w-4 h-4" />
                  <span className="text-xs font-mono text-[var(--color-text-secondary)]">Enable</span>
                </label>
              ) : (
                <input
                  type={p.type === 'number' ? 'number' : 'text'}
                  value={String(params[p.key] ?? p.default ?? '')}
                  onChange={(e) => setParam(p.key, p.type === 'number' ? Number(e.target.value) : e.target.value)}
                  placeholder={p.placeholder}
                  className={inputClass} style={inputStyle}
                  onFocus={(e) => e.target.style.borderColor = catColor}
                  onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
                />
              )}
            </div>
          ))}

          {/* Result */}
          {result && (
            <div className="p-3 rounded-sm text-xs font-mono"
              style={result.error
                ? { background: 'rgba(255,0,64,0.05)', border: '1px solid var(--neon-red)', color: 'var(--neon-red)' }
                : { background: 'rgba(0,255,65,0.05)', border: '1px solid var(--neon-green)', color: 'var(--neon-green)' }}>
              {result.error
                ? `✗ ${result.error}`
                : <>✓ Execution started — ID: <strong>{result.executionId}</strong> — check Scans for results</>}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-[var(--color-border)] flex justify-end gap-3">
          <button onClick={onClose}
            className="px-4 py-2 rounded-sm text-xs font-mono text-[var(--color-text-secondary)] hover:text-white transition-colors">
            cancel
          </button>
          <button onClick={handleRun} disabled={running || !projectId}
            className="px-4 py-2 rounded-sm text-xs font-mono flex items-center gap-2 disabled:opacity-40 transition-all"
            style={{ border: `1px solid ${catColor}`, color: catColor, background: `${catColor}10`, cursor: 'pointer' }}>
            {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            {running ? 'running...' : 'execute'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Replace ToolsPage**

Replace `frontend/src/pages/ToolsPage.tsx` entirely:

```tsx
import { useEffect, useState } from 'react'
import { Wrench } from 'lucide-react'
import { toolService } from '../services/toolService'
import type { Tool } from '../types'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import ToolCard from '../components/Tools/ToolCard'
import ToolExecuteModal from '../components/Tools/ToolExecuteModal'
import { CATEGORY_LABELS, CATEGORY_COLORS } from '../data/toolDefinitions'

const ALL_CATEGORIES = ['all', 'scan', 'web', 'brute_force', 'osint', 'exploitation', 'post_exploitation', 'phishing']

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState('all')
  const [search, setSearch] = useState('')
  const [executingTool, setExecutingTool] = useState<string | null>(null)

  useEffect(() => {
    toolService.listAvailable().then(setTools).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading tools..." />

  const filtered = tools.filter((t) => {
    const matchCat = activeCategory === 'all' || t.category === activeCategory
    const matchSearch = !search || t.name.includes(search.toLowerCase()) || t.description?.toLowerCase().includes(search.toLowerCase())
    return matchCat && matchSearch
  })

  const available = tools.filter((t) => t.available).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white font-mono">
            <span style={{ color: 'var(--neon-green)' }}>{'>'}</span> Security Tools
          </h2>
          <p className="text-sm font-mono text-[var(--color-text-secondary)]">
            {tools.length} tools · <span style={{ color: 'var(--neon-green)' }}>{available} ready</span>
            {' · '}<span style={{ color: 'var(--neon-red)' }}>{tools.length - available} not installed</span>
          </p>
        </div>

        {/* Search */}
        <input
          type="text" value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="// search tools..."
          className="px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none w-48"
          style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
          onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
          onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
        />
      </div>

      {/* Category filter */}
      <div className="flex gap-1 flex-wrap">
        {ALL_CATEGORIES.map((cat) => {
          const color = cat === 'all' ? 'var(--neon-green)' : CATEGORY_COLORS[cat] || 'var(--color-text-secondary)'
          const label = cat === 'all' ? 'All' : CATEGORY_LABELS[cat] || cat
          const count = cat === 'all' ? tools.length : tools.filter((t) => t.category === cat).length
          return (
            <button key={cat} onClick={() => setActiveCategory(cat)}
              className="px-3 py-1.5 rounded-sm text-xs font-mono transition-all"
              style={activeCategory === cat
                ? { background: `${color}15`, border: `1px solid ${color}`, color }
                : { background: 'transparent', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
              {label} <span className="opacity-60">({count})</span>
            </button>
          )
        })}
      </div>

      {/* Tools grid */}
      {filtered.length === 0 ? (
        <EmptyState icon={<Wrench className="w-12 h-12" />} title="No tools found"
          description={search ? `No tools match "${search}"` : 'No tools in this category.'} />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
          {filtered.map((tool) => (
            <ToolCard key={tool.name} tool={tool} onExecute={setExecutingTool} />
          ))}
        </div>
      )}

      {/* Execute modal */}
      {executingTool && (
        <ToolExecuteModal toolName={executingTool} onClose={() => setExecutingTool(null)} />
      )}
    </div>
  )
}
```

- [ ] **Step 4: TypeScript check**

```bash
cd D:/Archivos/Desarrollo/red-team-saas/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
cd D:/Archivos/Desarrollo/red-team-saas
git add frontend/src/components/Tools/ frontend/src/pages/ToolsPage.tsx
git commit -m "feat(tools): redesign tools page with rich cards, categories, and execution modal"
```

---

## Task 5: Test Lab page

**Files:**
- Create: `frontend/src/components/TestLab/ServiceHealthCard.tsx`
- Create: `frontend/src/pages/TestLabPage.tsx`
- Modify: `frontend/src/components/Common/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/MainLayout.tsx`

- [ ] **Step 1: Create ServiceHealthCard**

Create `frontend/src/components/TestLab/ServiceHealthCard.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Loader2, CheckCircle, XCircle, ExternalLink } from 'lucide-react'

interface ServiceHealthCardProps {
  name: string
  url: string
  checkUrl: string        // URL to fetch for health check
  externalUrl?: string    // URL to open in browser
  description: string
}

type Status = 'checking' | 'online' | 'offline'

export default function ServiceHealthCard({ name, url, checkUrl, externalUrl, description }: ServiceHealthCardProps) {
  const [status, setStatus] = useState<Status>('checking')
  const [latency, setLatency] = useState<number | null>(null)

  const check = async () => {
    setStatus('checking')
    const start = Date.now()
    try {
      await fetch(checkUrl, { mode: 'no-cors', signal: AbortSignal.timeout(3000) })
      setLatency(Date.now() - start)
      setStatus('online')
    } catch {
      setStatus('offline')
      setLatency(null)
    }
  }

  useEffect(() => {
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [checkUrl])

  const statusColor = status === 'online' ? 'var(--neon-green)' : status === 'offline' ? 'var(--neon-red)' : '#ffd000'

  return (
    <div className="p-4 rounded-sm flex items-center gap-3 transition-all cursor-pointer group"
      style={{ background: 'var(--color-bg-secondary)', border: `1px solid ${status === 'online' ? 'var(--neon-green)' : status === 'offline' ? 'var(--neon-red)' : 'var(--color-border)'}40` }}
      onClick={() => externalUrl && window.open(externalUrl, '_blank')}>

      <div className="flex-shrink-0">
        {status === 'checking'
          ? <Loader2 className="w-5 h-5 animate-spin" style={{ color: '#ffd000' }} />
          : status === 'online'
          ? <CheckCircle className="w-5 h-5" style={{ color: 'var(--neon-green)' }} />
          : <XCircle className="w-5 h-5" style={{ color: 'var(--neon-red)' }} />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono font-semibold text-white">{name}</span>
          {status === 'online' && latency && (
            <span className="text-xs font-mono" style={{ color: 'var(--neon-green)', opacity: 0.7 }}>{latency}ms</span>
          )}
        </div>
        <p className="text-xs font-mono text-[var(--color-text-secondary)] truncate">{description}</p>
      </div>

      {externalUrl && (
        <ExternalLink className="w-3.5 h-3.5 text-[var(--color-text-secondary)] opacity-0 group-hover:opacity-100 transition-opacity" />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create TestLabPage**

Create `frontend/src/pages/TestLabPage.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { FlaskConical, Zap, Mail, BarChart3, RefreshCw, ExternalLink, Play, Loader2 } from 'lucide-react'
import ServiceHealthCard from '../components/TestLab/ServiceHealthCard'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import { scanService } from '../services/scanService'
import { phishingService } from '../services/phishingService'
import { findingsService } from '../services/findingsService'
import { dashboardService } from '../services/dashboardService'
import api from '../services/api'
import type { Scan, Finding, Project } from '../types'
import { formatDate } from '../utils/cn'

const SERVICES = [
  { name: 'API (FastAPI)', description: 'Backend REST API · :8000', checkUrl: 'http://localhost:8000/health', externalUrl: 'http://localhost:8000/docs' },
  { name: 'Frontend (Vite)', description: 'React web app · :5173', checkUrl: 'http://localhost:5173', externalUrl: 'http://localhost:5173' },
  { name: 'GoPhish', description: 'Phishing engine · :3333', checkUrl: 'http://localhost:3333', externalUrl: 'http://localhost:3333' },
  { name: 'Grafana', description: 'Metrics dashboard · :3000', checkUrl: 'http://localhost:3000', externalUrl: 'http://localhost:3000' },
  { name: 'Prometheus', description: 'Metrics collector · :9090', checkUrl: 'http://localhost:9090', externalUrl: 'http://localhost:9090' },
  { name: 'Flower', description: 'Celery monitor · :5555', checkUrl: 'http://localhost:5555', externalUrl: 'http://localhost:5555' },
  { name: 'PostgreSQL', description: 'Database · :5432', checkUrl: 'http://localhost:8000/health' },
  { name: 'Redis', description: 'Cache/Broker · :6379', checkUrl: 'http://localhost:8000/health' },
]

const QUICK_LINKS = [
  { label: 'Grafana Dashboard', url: 'http://localhost:3000', icon: BarChart3, color: 'var(--neon-green)' },
  { label: 'Prometheus', url: 'http://localhost:9090', icon: BarChart3, color: '#ff6b00' },
  { label: 'Flower (Celery)', url: 'http://localhost:5555', icon: Zap, color: '#ffd000' },
  { label: 'Swagger API Docs', url: 'http://localhost:8000/docs', icon: ExternalLink, color: 'var(--neon-blue)' },
  { label: 'GoPhish Admin', url: 'http://localhost:3333', icon: Mail, color: 'var(--neon-red)' },
]

export default function TestLabPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [recentScans, setRecentScans] = useState<Scan[]>([])
  const [recentFindings, setRecentFindings] = useState<Finding[]>([])
  const [stats, setStats] = useState<{ projects: number; scans: number; findings: number } | null>(null)
  const [scanTarget, setScanTarget] = useState('192.168.1.1')
  const [quickScanning, setQuickScanning] = useState(false)
  const [quickScanResult, setQuickScanResult] = useState<string | null>(null)
  const [quickPhishing, setQuickPhishing] = useState(false)
  const [quickPhishResult, setQuickPhishResult] = useState<string | null>(null)

  const load = async () => {
    try {
      const [projRes, scansRes, findingsRes] = await Promise.allSettled([
        api.get('/projects/'),
        scanService.list({ limit: 5 }),
        findingsService.list({ limit: 5 }),
      ])
      if (projRes.status === 'fulfilled') {
        const items: Project[] = Array.isArray(projRes.value.data) ? projRes.value.data : projRes.value.data.items ?? []
        setProjects(items)
      }
      if (scansRes.status === 'fulfilled') setRecentScans(scansRes.value.slice(0, 5))
      if (findingsRes.status === 'fulfilled') setRecentFindings(findingsRes.value.slice(0, 5))
    } catch {}

    try {
      const dash = await dashboardService.getStats()
      setStats({ projects: dash.total_projects, scans: dash.total_scans, findings: dash.total_findings })
    } catch {}
  }

  useEffect(() => { load() }, [])

  const handleQuickScan = async () => {
    if (!projects.length) { setQuickScanResult('✗ Create a project first'); return }
    setQuickScanning(true)
    setQuickScanResult(null)
    try {
      const scan = await scanService.create({
        name: `Quick Scan — ${scanTarget}`,
        scan_type: 'nmap',
        target: scanTarget,
        project_id: projects[0].id,
        tools: ['nmap'],
        options: { profile: 'quick' },
      })
      await scanService.run(scan.id)
      setQuickScanResult(`✓ Scan #${scan.id} launched → check Scans page for results`)
      load()
    } catch (err: any) {
      setQuickScanResult(`✗ ${err?.response?.data?.detail || 'Scan failed'}`)
    } finally {
      setQuickScanning(false)
    }
  }

  const handleQuickPhishing = async () => {
    if (!projects.length) { setQuickPhishResult('✗ Create a project first'); return }
    setQuickPhishing(true)
    setQuickPhishResult(null)
    try {
      const campaign = await phishingService.create({
        project_id: projects[0].id,
        name: `Quick Phishing Test — ${new Date().toLocaleDateString()}`,
        description: 'Auto-created from Test Lab',
        gophish_url: 'http://localhost:3333',
        gophish_api_key: 'change-me',
        template_name: 'Microsoft 365 - Account Verification',
        landing_page_name: 'Microsoft Login Page',
        smtp_profile_name: 'Test SMTP',
        target_group_name: 'Test Group',
        phishing_url: 'http://localhost:8080',
      } as any)
      setQuickPhishResult(`✓ Campaign "${campaign.name}" created (draft) → configure API key in Phishing page`)
      load()
    } catch (err: any) {
      setQuickPhishResult(`✗ ${err?.response?.data?.detail || 'Campaign creation failed'}`)
    } finally {
      setQuickPhishing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white font-mono">
          <span style={{ color: 'var(--neon-green)' }}>{'>'}</span> Test Lab
        </h2>
        <p className="text-sm font-mono text-[var(--color-text-secondary)]">System health, quick actions, and feature testing</p>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Projects', value: stats.projects, color: 'var(--neon-blue)' },
            { label: 'Scans', value: stats.scans, color: 'var(--neon-green)' },
            { label: 'Findings', value: stats.findings, color: 'var(--neon-red)' },
          ].map((s) => (
            <div key={s.label} className="p-4 rounded-sm text-center"
              style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
              <p className="text-3xl font-bold font-mono" style={{ color: s.color }}>{s.value}</p>
              <p className="text-xs font-mono text-[var(--color-text-secondary)] mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Health */}
        <Card title="System Health">
          <div className="space-y-2 -mt-2">
            {SERVICES.map((s) => (
              <ServiceHealthCard key={s.name} name={s.name} url={s.checkUrl}
                checkUrl={s.checkUrl} externalUrl={s.externalUrl} description={s.description} />
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          {/* Quick Scan */}
          <Card title="Quick Scan">
            <div className="space-y-3">
              <p className="text-xs font-mono text-[var(--color-text-secondary)]">Launch a quick nmap scan against a target using the first available project.</p>
              <div className="flex gap-2">
                <input type="text" value={scanTarget} onChange={(e) => setScanTarget(e.target.value)}
                  placeholder="192.168.1.1 or example.com"
                  className="flex-1 px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                  onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
                <button onClick={handleQuickScan} disabled={quickScanning}
                  className="px-3 py-2 rounded-sm text-xs font-mono flex items-center gap-1.5 btn-neon disabled:opacity-40">
                  {quickScanning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                  scan
                </button>
              </div>
              {quickScanResult && (
                <p className="text-xs font-mono" style={{ color: quickScanResult.startsWith('✓') ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                  {quickScanResult}
                </p>
              )}
            </div>
          </Card>

          {/* Quick Phishing */}
          <Card title="Quick Phishing">
            <div className="space-y-3">
              <p className="text-xs font-mono text-[var(--color-text-secondary)]">
                Create a draft phishing campaign with pre-configured GoPhish base templates.
                Requires GoPhish running at <span style={{ color: 'var(--neon-green)' }}>localhost:3333</span>.
              </p>
              <button onClick={handleQuickPhishing} disabled={quickPhishing}
                className="px-3 py-2 rounded-sm text-xs font-mono flex items-center gap-1.5 transition-all disabled:opacity-40"
                style={{ border: '1px solid var(--neon-red)', color: 'var(--neon-red)', background: 'rgba(255,0,64,0.08)', cursor: 'pointer' }}>
                {quickPhishing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Mail className="w-3 h-3" />}
                {quickPhishing ? 'creating...' : 'create test campaign'}
              </button>
              {quickPhishResult && (
                <p className="text-xs font-mono" style={{ color: quickPhishResult.startsWith('✓') ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                  {quickPhishResult}
                </p>
              )}
            </div>
          </Card>

          {/* Quick Links */}
          <Card title="Quick Links">
            <div className="grid grid-cols-1 gap-2 -mt-2">
              {QUICK_LINKS.map((link) => {
                const Icon = link.icon
                return (
                  <button key={link.label} onClick={() => window.open(link.url, '_blank')}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm font-mono transition-all text-left group"
                    style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
                    <Icon className="w-4 h-4 flex-shrink-0" style={{ color: link.color }} />
                    <span className="text-white group-hover:text-[var(--neon-green)] transition-colors">{link.label}</span>
                    <ExternalLink className="w-3 h-3 ml-auto text-[var(--color-text-secondary)]" />
                  </button>
                )
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Recent Scans" action={
          <button onClick={load} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-green)] transition-colors">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        }>
          {recentScans.length === 0 ? (
            <p className="text-xs font-mono text-[var(--color-text-secondary)] text-center py-4">No scans yet — use Quick Scan above</p>
          ) : (
            <div className="space-y-2 -mt-2">
              {recentScans.map((s) => (
                <div key={s.id} className="flex items-center justify-between py-2 border-b border-[var(--color-border)] last:border-0">
                  <div>
                    <p className="text-xs font-mono text-white">{s.name}</p>
                    <p className="text-xs font-mono text-[var(--color-text-secondary)]">{s.target} · {formatDate(s.created_at)}</p>
                  </div>
                  <Badge text={s.status} variant="status" />
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Recent Findings">
          {recentFindings.length === 0 ? (
            <p className="text-xs font-mono text-[var(--color-text-secondary)] text-center py-4">No findings yet — run a scan to generate findings</p>
          ) : (
            <div className="space-y-2 -mt-2">
              {recentFindings.map((f) => (
                <div key={f.id} className="flex items-center justify-between py-2 border-b border-[var(--color-border)] last:border-0">
                  <div className="min-w-0 flex-1 mr-3">
                    <p className="text-xs font-mono text-white truncate">{f.title}</p>
                    <p className="text-xs font-mono text-[var(--color-text-secondary)]">{f.host || 'unknown host'}</p>
                  </div>
                  <Badge text={f.severity} variant="severity" />
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add route to App.tsx**

Read `frontend/src/App.tsx`, then add the import and route:

Add import at the top with other page imports:
```tsx
import TestLabPage from './pages/TestLabPage'
```

Add route inside the `<Route path="/" ...>` group, after the notifications route:
```tsx
<Route path="test-lab" element={<TestLabPage />} />
```

- [ ] **Step 4: Add to Sidebar**

Read `frontend/src/components/Common/Sidebar.tsx`, then:

1. Add `FlaskConical` to the lucide-react import
2. Add to `navItems` array (after notifications, before settings):
```tsx
{ to: '/test-lab', icon: FlaskConical, label: 'Test Lab' },
```

- [ ] **Step 5: Add to MainLayout pageTitles**

Read `frontend/src/layouts/MainLayout.tsx`, then add to `pageTitles`:
```tsx
'/test-lab': 'Test Lab',
```

- [ ] **Step 6: TypeScript check**

```bash
cd D:/Archivos/Desarrollo/red-team-saas/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no new errors.

- [ ] **Step 7: Commit**

```bash
cd D:/Archivos/Desarrollo/red-team-saas
git add frontend/src/components/TestLab/ frontend/src/pages/TestLabPage.tsx frontend/src/App.tsx frontend/src/components/Common/Sidebar.tsx frontend/src/layouts/MainLayout.tsx
git commit -m "feat(testlab): add Test Lab page with health checks, quick actions, and activity feed"
```

---

## Task 6: Final verification

- [ ] **Step 1: Verify all containers**

```bash
docker compose -f D:/Archivos/Desarrollo/red-team-saas/docker-compose.yml ps
```

Expected: all services up including `redteam-gophish`.

- [ ] **Step 2: Verify GoPhish accessible**

```bash
curl -sk https://localhost:3333 -o /dev/null -w "%{http_code}"
```

Expected: `200` or `302`.

- [ ] **Step 3: Verify frontend loads at /test-lab**

Open http://localhost:5173/test-lab — should show health cards, quick scan, quick phishing, quick links.

- [ ] **Step 4: Verify tools page**

Open http://localhost:5173/tools — should show tool cards with icons, categories, descriptions, and execute buttons.

- [ ] **Step 5: Final commit**

```bash
cd D:/Archivos/Desarrollo/red-team-saas && git add -A && git status
```

If nothing uncommitted, all good. Otherwise:
```bash
git commit -m "feat: complete GoPhish + tools catalog + test lab"
```
