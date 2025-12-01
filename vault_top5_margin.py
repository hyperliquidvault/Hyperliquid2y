import os
import smtplib
import ssl
from typing import Any, Dict, List

import requests

API_URL = "https://api.hyperliquid.xyz/info"
PAYLOAD = {
    "type": "vaultSnapshot",
    "vaultAddress": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",
}
RECIPIENT_EMAIL = "latuihf@gmail.com"
EMAIL_SUBJECT = "Top 5 Positions by Highest Margin"


def fetch_positions() -> List[Dict[str, Any]]:
    response = requests.post(API_URL, json=PAYLOAD, timeout=15)
    response.raise_for_status()
    payload = response.json()

    vault = None
    if isinstance(payload.get("data"), dict):
        vault = payload["data"].get("vault")
    if vault is None:
        vault = payload.get("vault")
    if not vault or "positions" not in vault:
        raise ValueError("Vault positions not found in API response.")

    positions = vault["positions"]
    if not isinstance(positions, list):
        raise TypeError("Expected positions to be a list.")

    return positions


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0
    return 0.0


def extract_top_positions(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for pos in positions:
        margin_source = (
            pos.get("positionMargin")
            if "positionMargin" in pos
            else pos.get("marginUsed")
        )
        margin = to_float(margin_source)
        normalized.append(
            {
                "coin": pos.get("coin", "UNKNOWN"),
                "margin": margin,
                "positionValue": to_float(pos.get("positionValue")),
                "size": to_float(pos.get("size")),
                "side": str(pos.get("side", "n/a")).lower(),
                "entryPx": to_float(pos.get("entryPx")),
            }
        )

    normalized.sort(key=lambda item: item["margin"], reverse=True)
    return normalized[:5]


def build_email_body(top_positions: List[Dict[str, Any]]) -> str:
    if not top_positions:
        return "Top 5 Positions by Margin:\n(No positions available.)"

    lines = ["Top 5 Positions by Margin:"]
    for idx, pos in enumerate(top_positions, start=1):
        lines.append(
            f"{idx}. {pos['coin']} — Margin: {pos['margin']:,.2f} USDC — "
            f"Value: {pos['positionValue']:,.2f} — Size: {pos['size']:,.4f} — "
            f"Side: {pos['side']}"
        )
    return "\n".join(lines)


def send_email(body: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass]):
        raise EnvironmentError("Missing SMTP environment variables.")

    message = (
        f"Subject: {EMAIL_SUBJECT}\n"
        f"To: {RECIPIENT_EMAIL}\n"
        f"From: {smtp_user}\n\n"
        f"{body}"
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, RECIPIENT_EMAIL, message)


def main() -> None:
    positions = fetch_positions()
    top_positions = extract_top_positions(positions)
    email_body = build_email_body(top_positions)
    send_email(email_body)
    print("Top 5 margin report emailed successfully.")


if __name__ == "__main__":
    main()
