import os
import sys
import smtplib
from email.message import EmailMessage
from typing import Optional

import requests

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("user-notifications-mcp")


# Reuse shared helper (file lives one directory up from MCP_Servers)
try:
    from HelperFunctions import _require_env
except ModuleNotFoundError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from HelperFunctions import _require_env



@mcp.tool()
def send_gmail_email(
    subject: str,
    body: str,
) -> str:
    """
    Send an email via Gmail SMTP (synchronous).

    Env vars:
      - GMAIL_SMTP_USER: your Gmail address (or Google Workspace user)
      - GMAIL_APP_PASSWORD: 16-char Gmail App Password (recommended)
    """
    smtp_user = _require_env("GMAIL_SMTP_USER")
    app_password = _require_env("GMAIL_APP_PASSWORD")

    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = "santhoshreddyin@gmail.com"  # For simplicity, sending to self only
    msg["Subject"] = subject
    msg.set_content(body)

    # Gmail SMTP over SSL (sync)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(smtp_user, app_password)
        smtp.send_message(msg, from_addr=smtp_user, to_addrs="santhoshreddyin@gmail.com")

    return f"email sent"


@mcp.tool()
def send_telegram_message(
    message: str,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
) -> str:
    """
    Send a Telegram message via the Telegram Bot API.

    Env vars:
      - TELEGRAM_CHAT_ID: destination chat_id (user, group, or channel)

    Args:
      - message: the text to send
      - chat_id: optional override (defaults to TELEGRAM_CHAT_ID)
      - parse_mode: optional (e.g., "MarkdownV2" or "HTML")
      - disable_web_page_preview: defaults to True
    """
    token = _require_env("TELEGRAM_BOT_TOKEN")
    target_chat_id = _require_env("TELEGRAM_CHAT_ID")
    chat_ids = [6792474125,target_chat_id]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat in chat_ids:
        payload = {
            "chat_id": chat,
            "text": message,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            resp = requests.post(url, json=payload, timeout=30)
        except requests.RequestException as e:
            raise RuntimeError(f"Telegram request failed: {e}")
        if not resp.ok:
            if resp.status_code == 400 and "chat not found" in (resp.text or "").lower():
                raise RuntimeError(
                    "Telegram API error 400: chat not found. "
                    "TELEGRAM_CHAT_ID is likely wrong, or the bot has not interacted with that chat yet. "
                    "Fix: message the bot (or add it to the group/channel), then run MCP_Servers/mcptest.py --discover to find the correct chat_id."
                )
            raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text}")

        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API returned ok=false: {data}")

    return "telegram message sent"


if __name__ == "__main__":
    mcp.run(transport="stdio")
