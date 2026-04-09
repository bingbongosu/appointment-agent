from typing import List, Optional
from pydantic import BaseModel, Field


# models.py imported by multiple modules to define structured data formats for the appointment scheduling agent.
class AppointmentRequest(BaseModel):
    # Define the structure for an appointment request extracted from an email. Sets boolean if it's a scheduling request.
    is_scheduling_request: bool = Field(
        description="True if the email is asking to schedule, book, move, or confirm a meeting."
    )
    # Optional sender name if it can be reasonably inferred from the email.
    sender_name: Optional[str] = Field(
        default=None,
        description="Name of the sender if it can be inferred."
    )
    # Optional short topic of the meeting, if mentioned in the email.
    topic: Optional[str] = Field(
        default=None,
        description="Short topic of the meeting."
    )
    # Natural language description of the requested timeframe for the meeting.
    requested_timeframe: Optional[str] = Field(
        default=None,
        description="Natural-language time preference, e.g. 'next Tuesday afternoon'."
    )
    # Expected duration of the meeting in minutes, defaulting to 30 unless the email strongly suggests otherwise.
    duration_minutes: int = Field(
        default=30,
        description="Expected duration in minutes."
    )
    # Overall tone of the sender's email, categorized as one word like 'professional'
    tone: str = Field(
        default="professional",
        description="Overall tone of the sender's email."
    )
    # Any extra notes or interpretations that might be useful for scheduling or drafting a reply.
    notes: Optional[str] = Field(
        default=None,
        description="Any extra useful interpretation."
    )


# Define a structured output model for the agent's processing results
class AgentOutput(BaseModel):
    # Combines the parsed appointment request, proposed meeting slots, and the drafted reply into a single structured output.
    parsed_request: AppointmentRequest
    # List of proposed meeting slots in plain English, e.g. "Tuesday 2:00 PM".
    proposed_slots: List[str]
    # The drafted reply to the sender, based on the parsed request and proposed slots.
    reply_draft: str