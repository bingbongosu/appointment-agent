from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# This file defines the data models used in the appointment scheduling agent, 
# including the structure of the parsed appointment request, 
# the proposed time slots, and the overall agent output that will be logged and used to generate replies.
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


# This model holds the results of the slot generation process, 
# including the proposed time slots and whether the exact requested time was available. 
# It also includes the exact start and end times if the requested time was available, which can be used to create a calendar appointment immediately.
class SlotResult(BaseModel):
    """
    Holds scheduler output.

    slots:
        The proposed time slots.

    exact_requested_time_available:
        True when the sender requested a specific day/time
        and that exact slot was available, so the reply
        should confirm instead of asking.
    """
    slots: List[str]
    exact_requested_time_available: bool = False
    exact_start: Optional[datetime] = None
    exact_end: Optional[datetime] = None


# This model compiles all the relevant information about the appointment request and the agent's processing of it, 
# including the parsed request details, the proposed time slots, and the draft reply content. 
# It is used for structured logging and to pass comprehensive information to the reply sending function, 
# which can use it to customize the reply based on what was proposed and whether an appointment was created.
class AgentOutput(BaseModel):
    parsed_request: AppointmentRequest
    proposed_slots: List[str]
    reply_draft: str
    
