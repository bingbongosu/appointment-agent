import os
import logging
from email.utils import parseaddr

from dotenv import load_dotenv

from parser import parse_email
from reply_writer import write_reply
from models import AgentOutput

from google_client import get_google_services
from gmail_reader import get_unprocessed_message_ids, get_message_by_id
from gmail_writer import send_reply
from gmail_actions import get_or_create_label, mark_as_processed
from scheduler import generate_available_slots
from sms_sender_code import send_sms
from daily_log import log_report_entry
from calendar_actions import create_appointment

from logger_config import setup_logger


def get_log_level(level_name: str) -> int:
    """
    Convert a string from .env into a real logging level.

    Example:
    LOG_LEVEL=DEBUG -> logging.DEBUG
    LOG_LEVEL=INFO  -> logging.INFO
    """

    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    return levels.get(level_name.upper(), logging.INFO)


def main() -> None:
    """
    Main entry point for the appointment email agent.

    Responsibilities:
    - Load environment variables
    - Set up logging
    - Connect to Google services
    - Find unprocessed emails
    - Parse scheduling requests
    - Generate calendar slots
    - Send replies
    - Mark handled emails as processed
    """

    load_dotenv()

    log_mode = os.getenv("LOG_MODE", "console")
    valid_modes = {"console", "file", "both", "silent"}

    if log_mode.lower() not in valid_modes:
        raise ValueError(f"Invalid LOG_MODE '{log_mode}'. Must be one of {valid_modes}")

    alert_phone_number = os.getenv("ALERT_PHONE_NUMBER")

    log_file = os.getenv("LOG_FILE", "app.log")
    log_level = get_log_level(os.getenv("LOG_LEVEL", "INFO"))

    logger = setup_logger(
        name="appointment_agent",
        log_file=log_file,
        log_level=log_level,
        output_mode=log_mode,
    )

    logger.info("Appointment agent started.")

    gmail_service, calendar_service = get_google_services()

    message_ids = get_unprocessed_message_ids(gmail_service)

    if not message_ids:
        logger.info("No unprocessed emails found.")
        return

    logger.info(f"Found {len(message_ids)} unprocessed email(s).")

    processed_label_id = get_or_create_label(gmail_service, "PROCESSED")

    # Process each unhandled email
    for msg_id in message_ids:
        
        # Log the message ID being processed at INFO level
        logger.info(f"Processing message ID: {msg_id}")

        message = get_message_by_id(gmail_service, msg_id)

        logger.debug("=== EMAIL OUTPUT ===")
        logger.debug(f"ID: {message['id']}")
        logger.debug(f"Thread: {message['thread_id']}")
        logger.debug(f"From: {message['sender']}")
        logger.debug(f"Subject: {message['subject']}")
        logger.debug(f"Body:\n{message['body']}")

        sender_email = parseaddr(message["sender"])[1]
        email_text = message["body"] or ""
        subject_text = message["subject"] or ""

        # If both the email body and subject are empty, log a warning and skip processing this email.
        if not email_text and not subject_text:
            logger.warning("Email body and subject were empty. Skipping.")
            continue

        # Parse the email content to determine if it's a scheduling request and extract relevant information.
        parsed = parse_email(f"Subject: {subject_text}\n\nBody: {email_text}")

        # If the email is not recognized as a scheduling request, log this information and skip further processing for this email.
        if not parsed.is_scheduling_request:
            logger.info(
                f"Email from {sender_email} is not a scheduling request. Skipping."
            )
            continue

        logger.info(f"Scheduling request detected from {sender_email}.")

        # Generate available calendar slots based on the parsed request and the user's calendar.
        slot_result = generate_available_slots(
            calendar_service=calendar_service,
            request=parsed,
            days_ahead=7,
            max_slots=3,
        )

        # If an exact requested time is available, create a calendar appointment immediately and include that information in the reply.
        appointment_created = False

        if (
            slot_result.exact_requested_time_available
            and slot_result.exact_start
            and slot_result.exact_end
        ):
            logger.info("Exact requested time is available. Creating appointment.")

            try:
                appointment = create_appointment(
                    calendar_service=calendar_service,
                    title=parsed.topic or "Appointment",
                    start_dt=slot_result.exact_start,
                    end_dt=slot_result.exact_end,
                    description=f"Appointment requested by {sender_email}",
                    attendee_emails=[sender_email],
                )

                if appointment:
                    appointment_created = True
                    logger.info("Appointment created successfully.")
                else:
                    logger.error("Appointment creation returned no result.")

            except Exception as e:
                logger.error(f"Appointment creation failed: {e}")
                continue

        reply = write_reply(parsed, slot_result)

        result = AgentOutput(
            parsed_request=parsed,
            proposed_slots=slot_result.slots,
            reply_draft=reply,
        )

        logger.debug("Parsed request:")
        logger.debug(result.parsed_request.model_dump_json(indent=2))

        if result.proposed_slots:
            logger.info(f"Proposed {len(result.proposed_slots)} slot(s).")
            for slot in result.proposed_slots:
                logger.debug(f"Proposed slot: {slot}")
        else:
            logger.warning("No slots available.")

        logger.debug(f"Reply draft:\n{result.reply_draft}")

        logger.info("Sending reply.")

        sent = send_reply(
            gmail_service=gmail_service,
            to=sender_email,
            subject=f"Re: {message['subject']}",
            body=reply,
            thread_id=message["thread_id"],
            original_message_id_header=message["message_id_header"],
        )

        if sent:
            logger.info("Reply sent successfully.")

            try:
                log_report_entry(
                    comment=f"Processed email from {sender_email} with subject: {message['subject']}",
                    process_name="email_reply",
                )
            except PermissionError:
                logger.error("Could not write to daily log because the CSV is open.")

            mark_as_processed(gmail_service, message["id"], processed_label_id)
            logger.info("Marked email as processed.")

            if alert_phone_number:
                send_sms(
                    alert_phone_number,
                    f"Processed email from {sender_email} with subject: {message['subject']}",
                )
                logger.info("SMS notification sent.")
            else:
                logger.info("No ALERT_PHONE_NUMBER found. SMS skipped.")

        else:
            logger.error("Reply failed. Email was not marked as processed.")

    logger.info("Appointment agent finished.")


if __name__ == "__main__":
    main()