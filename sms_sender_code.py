import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()


def send_sms(to_number: str, body: str) -> dict:
    """
    Sends an SMS message using Twilio.
    """

    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )

    message = client.messages.create(
        body=body,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        to=to_number
    )

    return {
        "status": message.status,
        "sid": message.sid,
        "to": message.to,
        "body": message.body
    }