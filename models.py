from typing import List, Optional
from pydantic import BaseModel, Field


class AppointmentRequest(BaseModel):
    is_scheduling_request: bool = Field(
        description="True if the email is asking to schedule, book, move, or confirm a meeting."
    )

    sender_name: Optional[str] = Field(
        default=None,
        description="Name of the sender if it can be inferred."
    )

    topic: Optional[str] = Field(
        default=None,
        description="Short topic of the meeting."
    )

    requested_timeframe: Optional[str] = Field(
        default=None,
        description="Original natural-language time preference exactly as understood from the email, e.g. 'next Tuesday afternoon' or 'around noon on Wednesday'."
    )

    preferred_days: Optional[List[str]] = Field(
        default=None,
        description="Preferred weekdays mentioned in the email, using full lowercase day names like ['monday', 'wednesday']. Leave null if none are clearly stated."
    )

    excluded_days: Optional[List[str]] = Field(
        default=None,
        description="Days the sender says will not work, using full lowercase day names like ['friday']. Leave null if none are stated."
    )

    preferred_time_of_day: Optional[str] = Field(
        default=None,
        description="Broad preferred time of day if stated. Use one of: morning, afternoon, evening, noon. Leave null if not clearly stated."
    )

    specific_time: Optional[str] = Field(
        default=None,
        description="Specific requested time if clearly stated, formatted as HH:MM in 24-hour time, for example '12:00' or '14:30'. Leave null if no exact time is requested."
    )

    not_before_time: Optional[str] = Field(
        default=None,
        description="Earliest acceptable time if the sender says things like 'after 2 PM'. Format as HH:MM in 24-hour time, for example '14:00'. Leave null if not stated."
    )

    not_after_time: Optional[str] = Field(
        default=None,
        description="Latest acceptable start time if the sender says things like 'before 4 PM'. Format as HH:MM in 24-hour time, for example '16:00'. Leave null if not stated."
    )

    duration_minutes: int = Field(
        default=30,
        description="Expected duration in minutes."
    )

    tone: str = Field(
        default="professional",
        description="Overall tone of the sender's email."
    )

    notes: Optional[str] = Field(
        default=None,
        description="Any extra useful interpretation."
    )
    

class AgentOutput(BaseModel):
    parsed_request: AppointmentRequest
    proposed_slots: List[str]
    reply_draft: str