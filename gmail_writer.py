import base64
from email.mime.text import MIMEText


def send_email(gmail_service, to: str, subject: str, body: str) -> dict:
    """
    Sends a brand-new email.
    """
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return gmail_service.users().messages().send(
        userId="me",
        body={"raw": raw_message}
    ).execute()