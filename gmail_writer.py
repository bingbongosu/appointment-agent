import base64
from email.mime.text import MIMEText


def send_reply(
    gmail_service,
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    original_message_id_header: str,
) -> dict:
    """
    Sends a reply in the same Gmail thread.
    """
    message = MIMEText(body)
    message["to"] = to

    if subject.lower().startswith("re:"):
        message["subject"] = subject
    else:
        message["subject"] = f"Re: {subject}"

    if original_message_id_header:
        message["In-Reply-To"] = original_message_id_header
        message["References"] = original_message_id_header

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return gmail_service.users().messages().send(
        userId="me",
        body={
            "raw": raw_message,
            "threadId": thread_id,
        }
    ).execute()