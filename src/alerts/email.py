import os
import smtplib
from email.message import EmailMessage
from typing import Optional


def send_email(subject: str, body: str) -> Optional[str]:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    from_addr = os.environ.get("ALERT_FROM")
    to_addrs = os.environ.get("ALERT_TO")

    if not all([host, from_addr, to_addrs]):
        return "Email not sent: SMTP_HOST, ALERT_FROM, and ALERT_TO must be set."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addrs
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return None
    except Exception as e:
        return f"Email send failed: {e}"

