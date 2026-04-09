import base64


def _extract_header(headers: list[dict], name: str) -> str:
    """
    Returns a header value by name, or an empty string if not found.
    """
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _extract_plain_text(payload: dict) -> str:
    """
    Extracts plain text body from a Gmail message payload.
    Handles both simple and multipart emails.
    """
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part["body"].get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        # fallback: search nested parts
        for part in payload["parts"]:
            text = _extract_plain_text(part)
            if text:
                return text
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""


def get_recent_message(gmail_service) -> dict | None:
    """
    Fetches the most recent inbox message and returns basic details + body.
    """
    results = gmail_service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=1
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return None

    message_id = messages[0]["id"]

    message = gmail_service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = _extract_header(headers, "Subject")
    sender = _extract_header(headers, "From")
    body = _extract_plain_text(payload)

    return {
        "id": message_id,
        "thread_id": message.get("threadId"),
        "subject": subject,
        "sender": sender,
        "body": body.strip(),
    }