import os
from openai import OpenAI
from models import AppointmentRequest


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You extract scheduling intent from emails.

Return structured data only.

Rules:
- is_scheduling_request should be true if the sender wants to meet, book time, reschedule, confirm a meeting, or discuss availability.
- sender_name should only be included if reasonably inferable.
- topic should be short and clear.
- requested_timeframe should capture phrases like 'next week', 'Tuesday afternoon', 'tomorrow morning'.
- duration_minutes defaults to 30 unless the email strongly suggests otherwise.
- tone should be one word like 'professional', 'casual', 'urgent'.
"""


def parse_email(email_text: str) -> AppointmentRequest:
    
    #Sends the email text to the model and parses it into an AppointmentRequest object.
    
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Email:\n{email_text}"
            }
        ],
        text_format=AppointmentRequest,
    )

    return response.output_parsed