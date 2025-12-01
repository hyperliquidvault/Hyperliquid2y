import os
import json
import requests
import smtplib
import ssl
from email.message import EmailMessage

API_URL = "https://api.hyperliquid.xyz/info"
VAULT_ADDRESS = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"
RECIPIENT_EMAIL = "latuihf@gmail.com"
EMAIL_SUBJECT = "Top 5 Positions by Highest Margin"


def api_call():
    """Safe HL API wrapper with full debug logging."""
    payload = {
        "method": "vaultSnapshot",
        "params": {"vaultAddress": VAULT_ADDRESS}
    }

    try:
        r = requests.post(API_URL, json=payload, timeout=20)
        if r.status_code != 200:
            print("DEBUG: API returned non-200:", r.status_code, r.text)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("\n⚠️ API ERROR")
        print("Exception:", e)
        print("Raw response:", getattr(e, "response", None))
        raise


def extract_positions(data):
    """Extract vault positions safely no matter the API structure."""
    # Multiple possible API formats:
    # Format A: {"result": {"vault": {...}}}
    # Format B: {"vault": {...}}
    # Format C: {"data": {"vault": {...}}}
    
    vault = None

    if isinstance(data, dict):
        if "result" in data and isinstance(data["result"], dict):
            vault = data["result"].get("vault")

        if vault is None and "data" in data:
            vault = data["data"].get("vault")

        if vault is None and "vault" in data:
            vault = data["vault"]

    if not vault:
        print("DEBUG: Could not find vault in data:", json.dumps(data, indent=2))
        raise ValueError("Vault structure not found in API response.")

    pos = vault.get("positions", [])
    if not isinstance(pos, list):
        print("DEBUG: positions is not a list:", pos)
        raise TypeError("Invalid positions array.")

    return pos


def safe_float(x):
    try:
        return float(str(x).replace(",", "").strip())
    except:
        return 0.0


def get_margin(position):
    """Auto-detect the correct margin field."""
    for key in ["positionMargin", "marginUsed", "margin", "maintMargin"]:
        if key in position:
            return safe_float(position[key])
    return 0.0


def top5_by_margin(pos_list):
    processed = []

    for p in pos_list:
        processed.append({
            "coin": p.get("coin", "UNKNOWN"),
            "margin": get_margin(p),
            "value": safe_float(p.get("positionValue", 0)),
            "size": safe_float(p.get("size", 0)),
            "side": str(p.get("side", "unknown")).lower()
        })

    processed.sort(key=lambda x: x["margin"], reverse=True)
    return processed[:5]


def build_email(toplist):
    if not toplist:
        return "No positions found in vault."

    lines = ["Top 5 Positions by Highest Margin:\n"]
    for i, p in enumerate(toplist, 1):
        lines.append(
            f"{i}. {p['coin']} — "
            f"Margin: {p['margin']:,.2f} USDC — "
            f"Value: {p['value']:,.2f} — "
            f"Size: {p['size']:,.4f} — "
            f"Side: {p['side']}"
        )
    return "\n".join(lines)


def send_email(body):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd = os.getenv("SMTP_PASS")

    if not all([host, port, user, pwd]):
        raise RuntimeError("Missing SMTP secrets")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = EMAIL_SUBJECT
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as s:
        s.starttls(context=ctx)
        s.login(user, pwd)
        s.send_message(msg)


def main():
    print("Fetching vault data…")
    raw = api_call()

    print("Extracting positions…")
    positions = extract_positions(raw)

    print("Sorting top 5 by margin…")
    top5 = top5_by_margin(positions)

    print("Sending email…")
    send_email(build_email(top5))

    print("✅ Email sent successfully.")


if __name__ == "__main__":
    main()
    
