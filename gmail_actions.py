def get_or_create_label(service, label_name: str) -> str:
    """
    Returns the Gmail label ID for the given label name.
    Creates the label if it does not already exist.
    """
    labels = service.users().labels().list(userId="me").execute().get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    new_label = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
    ).execute()

    return new_label["id"]


def mark_as_processed(service, message_id: str, processed_label_id: str):
    """
    Marks an email as processed and removes the UNREAD label.
    """
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "removeLabelIds": ["UNREAD"],
            "addLabelIds": [processed_label_id],
        }
    ).execute()
    
def get_unread_count(service, exclude_processed: bool = True) -> int:
    """
    Returns the number of unread emails.
    Optionally excludes emails labeled as PROCESSED.
    """
    query = "is:unread"

    if exclude_processed:
        query += " -label:PROCESSED"

    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        q=query
    ).execute()

    return results.get("resultSizeEstimate", 0)