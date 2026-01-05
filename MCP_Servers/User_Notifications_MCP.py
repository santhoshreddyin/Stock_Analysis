import os
import sys
import smtplib
from email.message import EmailMessage
from typing import Optional, List

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


if __name__ == "__main__":
    mcp.run(transport="stdio")
