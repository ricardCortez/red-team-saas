#!/usr/bin/env python3
"""
GoPhish base templates setup script.
Idempotent — safe to run multiple times.
Usage: python setup_gophish.py --api-key <API_KEY> [--url https://localhost:3333]
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
import ssl

def make_request(url, api_key, method="GET", data=None):
    """Make a request to the GoPhish API."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} for {method} {url}: {body}", file=sys.stderr)
        return None

def get_existing_names(base_url, api_key, endpoint):
    """Return set of existing object names at endpoint."""
    result = make_request(f"{base_url}{endpoint}", api_key)
    if not result:
        return set()
    return {item.get("name", "") for item in result}

def setup_sending_profile(base_url, api_key):
    name = "Test SMTP"
    existing = get_existing_names(base_url, api_key, "/api/smtp/")
    if name in existing:
        print(f"[SKIP] Sending profile '{name}' already exists")
        return
    data = {
        "name": name,
        "interface_type": "SMTP",
        "host": "mail.example.com:25",
        "from_address": "security@example.com",
        "ignore_cert_errors": True,
    }
    result = make_request(f"{base_url}/api/smtp/", api_key, "POST", data)
    if result:
        print(f"[OK] Created sending profile: {name}")
    else:
        print(f"[ERROR] Failed to create sending profile: {name}", file=sys.stderr)

def setup_email_template(base_url, api_key):
    name = "Microsoft 365 - Account Verification"
    existing = get_existing_names(base_url, api_key, "/api/templates/")
    if name in existing:
        print(f"[SKIP] Email template '{name}' already exists")
        return
    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Microsoft Account</title></head>
<body style="font-family:Segoe UI,Arial,sans-serif;background:#f3f2f1;margin:0;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:#fff;padding:40px;border-radius:4px;">
  <img src="https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg" width="108" alt="Microsoft" style="margin-bottom:24px;">
  <h1 style="font-size:24px;color:#0078d4;margin:0 0 16px;">Verify your Microsoft account</h1>
  <p style="color:#323130;font-size:14px;">We need to verify your account to ensure continued access to Microsoft 365 services.</p>
  <p style="color:#323130;font-size:14px;">Please click the button below to verify your identity:</p>
  <a href="{{.URL}}" style="display:inline-block;background:#0078d4;color:#fff;padding:12px 24px;text-decoration:none;border-radius:2px;font-size:14px;margin:16px 0;">Verify My Account</a>
  <p style="color:#605e5c;font-size:12px;margin-top:24px;">If you did not request this, please ignore this email.</p>
  <hr style="border:none;border-top:1px solid #edebe9;margin:24px 0;">
  <p style="color:#605e5c;font-size:11px;">Microsoft Corporation, One Microsoft Way, Redmond, WA 98052</p>
</div>
</body>
</html>"""
    data = {
        "name": name,
        "subject": "[Action Required] Verify your Microsoft account",
        "html": html,
        "text": "Please verify your Microsoft account by visiting: {{.URL}}",
    }
    result = make_request(f"{base_url}/api/templates/", api_key, "POST", data)
    if result:
        print(f"[OK] Created email template: {name}")
    else:
        print(f"[ERROR] Failed to create email template: {name}", file=sys.stderr)

def setup_landing_page(base_url, api_key):
    name = "Microsoft Login Page"
    existing = get_existing_names(base_url, api_key, "/api/pages/")
    if name in existing:
        print(f"[SKIP] Landing page '{name}' already exists")
        return
    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Sign in to your account</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;background:#f3f2f1;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
.box{background:#fff;padding:44px;border-radius:4px;width:360px;box-shadow:0 2px 6px rgba(0,0,0,.1);}
img{display:block;margin:0 auto 24px;}
h1{font-size:24px;color:#1b1b1b;margin:0 0 16px;font-weight:600;}
input{width:100%;padding:8px 0;border:none;border-bottom:1px solid #666;margin:8px 0 20px;font-size:14px;outline:none;box-sizing:border-box;}
input:focus{border-bottom-color:#0078d4;}
button{width:100%;background:#0078d4;color:#fff;border:none;padding:10px;font-size:14px;cursor:pointer;border-radius:2px;}
button:hover{background:#106ebe;}
</style></head>
<body>
<div class="box">
  <img src="https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg" width="108" alt="Microsoft">
  <h1>Sign in</h1>
  <form method="POST" action="">
    <input type="hidden" name="rid" value="{{.RId}}">
    <input type="email" name="email" placeholder="Email, phone, or Skype" required>
    <input type="password" name="password" placeholder="Password" required>
    <button type="submit">Sign in</button>
  </form>
</div>
</body>
</html>"""
    data = {
        "name": name,
        "html": html,
        "capture_credentials": True,
        "capture_passwords": True,
        "redirect_url": "https://microsoft.com",
    }
    result = make_request(f"{base_url}/api/pages/", api_key, "POST", data)
    if result:
        print(f"[OK] Created landing page: {name}")
    else:
        print(f"[ERROR] Failed to create landing page: {name}", file=sys.stderr)

def setup_target_group(base_url, api_key):
    name = "Test Group"
    existing = get_existing_names(base_url, api_key, "/api/groups/")
    if name in existing:
        print(f"[SKIP] Target group '{name}' already exists")
        return
    data = {
        "name": name,
        "targets": [
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "testuser@example.com",
                "position": "Employee",
            }
        ],
    }
    result = make_request(f"{base_url}/api/groups/", api_key, "POST", data)
    if result:
        print(f"[OK] Created target group: {name}")
    else:
        print(f"[ERROR] Failed to create target group: {name}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Set up GoPhish base templates")
    parser.add_argument("--api-key", required=True, help="GoPhish API key")
    parser.add_argument("--url", default="https://localhost:3333", help="GoPhish base URL")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    api_key = args.api_key

    print(f"Connecting to GoPhish at {base_url} ...")
    setup_sending_profile(base_url, api_key)
    setup_email_template(base_url, api_key)
    setup_landing_page(base_url, api_key)
    setup_target_group(base_url, api_key)
    print("Setup complete.")

if __name__ == "__main__":
    main()
