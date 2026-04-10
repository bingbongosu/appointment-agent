import os
from email.utils import parseaddr

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Your modules
from gmail_reader import get_recent_message
from gmail_writer import send_reply 
from gmail_actions import get_or_create_label, mark_as_processed, get_unread_count

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

processed_label_id = "PROCESSED"

def get_gmail_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def main():
    print("Connecting to Gmail...")
    service = get_gmail_service()

    count = get_unread_count(service)
    print(f"Unread emails: {count}")
    
    print("Fetching latest message...\n")
    message = get_recent_message(service)

    if not message:
        print("No messages found.")
        return

    print("=== EMAIL OUTPUT ===")
    print(f"ID: {message['id']}")
    print(f"Thread: {message['thread_id']}")
    print(f"From: {message['sender']}")
    print(f"Subject: {message['subject']}")
    print("\n--- BODY ---\n")
    print(message["body"])

    # 👇 Extract clean email address
    sender_email = parseaddr(message["sender"])[1]

    print("\nSending reply...\n")

    sent = send_reply(
        gmail_service=service,
        to=sender_email,
        subject=message["subject"],
        body="Thanks for your email! I'll get back to you soon.",
        thread_id=message["thread_id"],
        original_message_id_header=message["message_id_header"],
    )

    if sent:
        print("Reply sent successfully.")

        processed_label_id = get_or_create_label(service, "PROCESSED")
        
        mark_as_processed(service, message["id"], processed_label_id)

    else:
        print("Reply failed.")


if __name__ == "__main__":
    main()