import os
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

app = FastAPI(title="DaTraders Terminal")

# ─── Configuration ────────────────────────────────────────────────
DERIV_APP_ID = os.environ.get("DERIV_APP_ID", "119695")
DERIV_OAUTH_URL = f"https://oauth.deriv.com/oauth2/authorize?app_id={DERIV_APP_ID}"

# Persistent token storage (Render disk or env-based)
TOKEN_STORE_PATH = Path(__file__).parent / "deriv_tokens.json"

def _load_tokens():
    if TOKEN_STORE_PATH.exists():
        try:
            with open(TOKEN_STORE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_tokens(data):
    try:
        with open(TOKEN_STORE_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[OAuth] Token save error: {e}")

# ─── Landing Page ─────────────────────────────────────────────────
html_file_path = Path(__file__).parent / "index.html"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(html_file_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ─── Deriv OAuth Endpoints ────────────────────────────────────────

@app.get("/deriv/auth")
async def deriv_auth():
    """Redirect user to Deriv OAuth login page."""
    return RedirectResponse(url=DERIV_OAUTH_URL)

@app.get("/deriv/callback", response_class=HTMLResponse)
async def deriv_callback(request: Request):
    """
    Deriv OAuth Callback Handler.
    
    Deriv redirects here after user authorizes the app.
    Tokens are passed as URL query parameters:
        ?acct1=CR123456&token1=a1-xxxxx&cur1=USD&acct2=...
    
    We capture all accounts/tokens, persist them, and display
    a confirmation page with the API token the user needs.
    """
    params = dict(request.query_params)
    
    # Parse all account/token pairs from query params
    accounts = []
    i = 1
    while f"acct{i}" in params:
        acc = {
            "account": params.get(f"acct{i}", ""),
            "token": params.get(f"token{i}", ""),
            "currency": params.get(f"cur{i}", ""),
        }
        accounts.append(acc)
        i += 1
    
    # Persist tokens
    token_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "app_id": DERIV_APP_ID,
        "accounts": accounts,
    }
    _save_tokens(token_data)
    
    # Build account rows for the UI
    account_rows = ""
    primary_token = ""
    primary_account = ""
    for idx, acc in enumerate(accounts):
        is_primary = idx == 0
        if is_primary:
            primary_token = acc["token"]
            primary_account = acc["account"]
        badge = '<span style="background:#00E676;color:#000;padding:2px 8px;border-radius:8px;font-size:0.7rem;font-weight:700;margin-left:8px;">PRIMARY</span>' if is_primary else ""
        masked = acc["token"][:8] + "••••••••" + acc["token"][-4:] if len(acc["token"]) > 14 else acc["token"]
        account_rows += f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px;margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-weight:700;font-size:1.1rem;">{acc['account']}{badge}</span>
                <span style="background:rgba(75,145,247,0.15);color:#4B91F7;padding:4px 12px;border-radius:8px;font-size:0.85rem;font-weight:600;">{acc['currency']}</span>
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:rgba(255,255,255,0.6);word-break:break-all;">
                {masked}
            </div>
        </div>
        """
    
    no_accounts_msg = ""
    if not accounts:
        no_accounts_msg = """
        <div style="background:rgba(255,80,80,0.1);border:1px solid rgba(255,80,80,0.3);border-radius:12px;padding:20px;text-align:center;">
            <p style="color:#FF5050;font-weight:700;margin:0;">No accounts returned from Deriv.</p>
            <p style="color:rgba(255,255,255,0.5);margin:8px 0 0 0;font-size:0.9rem;">Please try authenticating again.</p>
        </div>
        """
    
    # Build the callback confirmation page
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deriv Auth | DaTraders Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0a0a0f;
            --accent: #4B91F7;
            --green: #00E676;
        }}
        @keyframes gradient-bg {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes pulse-green {{
            0% {{ box-shadow: 0 0 0 0 rgba(0,230,118,0.6); }}
            70% {{ box-shadow: 0 0 0 15px rgba(0,230,118,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(0,230,118,0); }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(-45deg, #020617, #0f172a, #1e1b4b, #000000);
            background-size: 400% 400%;
            animation: gradient-bg 15s ease infinite;
            color: #FAFAFA;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 24px;
        }}
        .card {{
            background: rgba(255,255,255,0.025);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            box-shadow: 0 8px 40px rgba(0,0,0,0.4);
            max-width: 520px;
            width: 100%;
            padding: 40px;
            animation: fadeInUp 0.6s ease-out;
        }}
        .status-dot {{
            width: 12px; height: 12px;
            background: var(--green);
            border-radius: 50%;
            display: inline-block;
            animation: pulse-green 2s infinite;
            margin-right: 10px;
        }}
        .status-dot.error {{
            background: #FF5050;
            animation: none;
        }}
        h1 {{
            font-size: 1.6rem;
            font-weight: 900;
            margin-bottom: 8px;
            text-shadow: 0 0 20px rgba(75,145,247,0.5);
        }}
        .subtitle {{
            color: rgba(255,255,255,0.5);
            font-size: 0.9rem;
            margin-bottom: 28px;
        }}
        .section-title {{
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: rgba(255,255,255,0.35);
            margin-bottom: 12px;
        }}
        .token-box {{
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(75,145,247,0.3);
            border-radius: 12px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--accent);
            word-break: break-all;
            position: relative;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 24px;
        }}
        .token-box:hover {{
            border-color: var(--accent);
            box-shadow: 0 0 20px rgba(75,145,247,0.15);
        }}
        .copy-hint {{
            position: absolute;
            top: 8px; right: 12px;
            font-size: 0.7rem;
            color: rgba(255,255,255,0.3);
            font-family: 'Inter', sans-serif;
        }}
        .btn {{
            display: inline-block;
            padding: 12px 28px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.95rem;
            text-decoration: none;
            transition: all 0.3s;
            cursor: pointer;
            border: none;
            text-align: center;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #4B91F7, #3b6fd4);
            color: white;
            box-shadow: 0 4px 15px rgba(75,145,247,0.3);
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(75,145,247,0.5);
        }}
        .btn-ghost {{
            background: rgba(255,255,255,0.05);
            color: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .btn-ghost:hover {{
            background: rgba(255,255,255,0.08);
            color: white;
        }}
        .btn-row {{
            display: flex;
            gap: 12px;
            margin-top: 24px;
        }}
        .btn-row .btn {{ flex: 1; }}
        .copied-toast {{
            position: fixed;
            bottom: 30px;
            left: 50%; transform: translateX(-50%);
            background: var(--green);
            color: #000;
            padding: 10px 24px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.9rem;
            display: none;
            z-index: 999;
            box-shadow: 0 4px 20px rgba(0,230,118,0.4);
        }}
    </style>
</head>
<body>
    <div class="card">
        <div style="display:flex;align-items:center;margin-bottom:6px;">
            <span class="status-dot {'error' if not accounts else ''}"></span>
            <h1>{'Authorization Complete' if accounts else 'Authorization Failed'}</h1>
        </div>
        <p class="subtitle">{'Your Deriv API tokens have been captured and stored.' if accounts else 'No tokens were returned. Please try again.'}</p>
        
        {f'''
        <div class="section-title">API Token (Click to Copy)</div>
        <div class="token-box" id="tokenBox" onclick="copyToken()">
            {primary_token}
            <span class="copy-hint">CLICK TO COPY</span>
        </div>
        
        <div class="section-title">Linked Accounts</div>
        {account_rows}
        ''' if accounts else no_accounts_msg}
        
        <div class="section-title" style="margin-top:28px;">Next Steps</div>
        <p style="color:rgba(255,255,255,0.5);font-size:0.85rem;line-height:1.6;margin-bottom:4px;">
            {'Copy the API token above and paste it into your <strong style="color:#fff;">deriv_config.json</strong> under the <code style="color:#4B91F7;">"api_token"</code> field. The terminal will use this to authenticate the WebSocket data feed.' if accounts else 'Click the button below to try authenticating again.'}
        </p>
        
        <div class="btn-row">
            <a href="/deriv/auth" class="btn btn-primary">{'Re-Authorize' if accounts else 'Try Again'}</a>
            <a href="/" class="btn btn-ghost">Home</a>
        </div>
    </div>
    
    <div class="copied-toast" id="toast">✓ Token Copied to Clipboard</div>
    
    <script>
        // Cache the primary token and account in browser localStorage
        const primaryToken = '{primary_token}';
        const primaryAccount = '{primary_account}';
        if (primaryToken) {{
            localStorage.setItem('deriv_api_token', primaryToken);
            localStorage.setItem('deriv_api_account', primaryAccount);
            console.log("Token cached in browser localStorage:", primaryAccount);
        }}

        function copyToken() {{
            const token = document.getElementById('tokenBox').innerText.replace('CLICK TO COPY', '').trim();
            navigator.clipboard.writeText(token).then(() => {{
                const toast = document.getElementById('toast');
                toast.style.display = 'block';
                setTimeout(() => {{ toast.style.display = 'none'; }}, 2000);
            }});
        }}
    </script>
</body>
</html>"""
    return html

# ─── API: Get stored tokens (for terminal to fetch remotely) ──────

@app.get("/deriv/tokens")
async def get_tokens():
    """
    Returns the stored OAuth tokens as JSON.
    The desktop terminal can poll this endpoint to auto-configure
    its Deriv API token without manual copy-paste.
    """
    data = _load_tokens()
    if not data or not data.get("accounts"):
        return {"success": False, "message": "No tokens stored. Visit /deriv/auth to authorize."}
    return {
        "success": True,
        "app_id": data.get("app_id"),
        "timestamp": data.get("timestamp"),
        "accounts": [
            {"account": a["account"], "token": a["token"], "currency": a["currency"]}
            for a in data["accounts"]
        ]
    }
