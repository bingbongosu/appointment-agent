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
- requested_timeframe should summarize the sender's timing preference in plain English.
- preferred_days should contain full lowercase weekday names only when clearly stated.
- excluded_days should contain full lowercase weekday names the sender says do not work.
- preferred_time_of_day should be one of: morning, afternoon, evening, noon, or null.
- specific_time should be included only if the sender clearly requests a specific time, formatted as HH:MM in 24-hour time.
- not_before_time should be included for phrases like 'after 2 PM', formatted as HH:MM in 24-hour time.
- not_after_time should be included for phrases like 'before 4 PM', formatted as HH:MM in 24-hour time.
- duration_minutes defaults to 30 unless the email strongly suggests otherwise.
- tone should be a single word like professional, casual, urgent, warm, or direct.
- notes may include useful interpretation that does not fit elsewhere.
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