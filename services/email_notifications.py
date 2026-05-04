from __future__ import annotations

import logging
from datetime import datetime

from clients import CrmItem
from config.settings import AppSettings
from utils.brief_storage import (
    should_send_change_request_updated_email,
    update_chatbot_brief,
)
from utils.email_templates import EmailTemplateContent, build_email_html, build_email_text
from utils.mailer import send_email
from utils.monitoring import get_field_email, get_field_value, parse_brief_last_modified_date

logger = logging.getLogger(__name__)

CLIENT_REVIEW_STATUSES = {"2828"}
CHATBOT_URL = "https://waa.mdbgo.io/"


def create_brief_creation_email(brief_number: str) -> EmailTemplateContent:
    return EmailTemplateContent(
        subject="Your Brief Has Been Created - Please Save the Brief ID",
        title="Brief has been created successfully",
        subtitle=f"Brief Number: {brief_number}",
        body_text=(
            "Please make a note of this Brief ID. If you would like to update or "
            "modify this brief in the future, simply return to the chatbot by "
            "clicking Open Chatbot and reference your Brief ID."
        ),
        button_label="Open Chatbot",
        button_link=CHATBOT_URL,
    )


def create_brief_update_email(brief_id: str) -> EmailTemplateContent:
    return EmailTemplateContent(
        subject="Your change request has been successfully updated",
        title="Your change request has been successfully updated",
        subtitle=f"Brief ID: {brief_id}",
        body_text=(
            "We are pleased to inform you that your requested change has been "
            "successfully updated in Joule. To view your updated brief, simply "
            "click on Open Chatbot below and reference your Brief ID."
        ),
        button_label="Open Chatbot",
        button_link=CHATBOT_URL,
    )


def create_work_review_request_email(
    brief_number: str,
    job_name: str,
    job_number: str,
) -> EmailTemplateContent:
    return EmailTemplateContent(
        subject="Action Required: Review Your Asset",
        title="Your Asset is Ready for Review",
        subtitle=(
            f"Brief Number: {brief_number}\n"
            f"Job Name: {job_name}\n"
            f"Job Number: {job_number}"
        ),
        body_text=(
            "To review the asset, please click the chatbot link below. You will have "
            "the option to approve or reject it based on your requirements."
        ),
        button_label="Open Chatbot",
        button_link=CHATBOT_URL,
    )


def send_template_email(content: EmailTemplateContent, recipient: str | None = None) -> None:
    logger.info("Sending email with subject=%s recipient=%s", content.subject, recipient)
    send_email(
        content.subject,
        build_email_text(content),
        recipient=recipient,
        html_body=build_email_html(content),
    )
    logger.info("Email sent with subject=%s recipient=%s", content.subject, recipient)


def send_brief_creation_email(brief_id: str, recipient: str | None = None) -> None:
    send_template_email(create_brief_creation_email(brief_id), recipient=recipient)


def send_change_request_updated_email(brief_id: str, recipient: str | None = None) -> None:
    send_template_email(create_brief_update_email(brief_id), recipient=recipient)


def send_work_review_request_email(
    brief_number: str,
    job_name: str,
    job_number: str,
    recipient: str | None = None,
) -> None:
    content = create_work_review_request_email(brief_number, job_name, job_number)
    send_template_email(content, recipient=recipient)


def process_recent_briefs(settings: AppSettings, items: list[CrmItem]) -> None:
    logger.info("Processing %s recent briefs", len(items))

    for item in items:
        brief_number = get_field_value(item, "Brief Number")
        created_date = get_field_value(item, "Created Date")
        last_modified_date = get_field_value(item, "Last Modified Date")
        recipient = _resolve_recipient(settings, item)

        if not brief_number or not created_date or not last_modified_date:
            logger.info(
                "Skipping brief notification because required fields are missing: "
                "brief=%s created=%s modified=%s",
                brief_number,
                created_date,
                last_modified_date,
            )
            continue

        created_at = parse_brief_last_modified_date(created_date)
        modified_at = parse_brief_last_modified_date(last_modified_date)

        if modified_at == created_at:
            logger.info("Brief %s was created in this window", brief_number)
            if recipient is None:
                logger.info("Skipping brief %s creation email: missing recipient", brief_number)
                continue
            send_brief_creation_email(brief_number, recipient=recipient)
            continue

        if should_send_change_request_updated_email(item):
            logger.info("Brief %s has a change request update", brief_number)
            if recipient is None:
                logger.info("Skipping brief %s update email: missing recipient", brief_number)
                continue
            send_change_request_updated_email(brief_number, recipient=recipient)
            update_chatbot_brief(item)


def process_review_jobs(
    settings: AppSettings,
    items: list[CrmItem],
    window_start: datetime,
) -> None:
    logger.info("Processing %s recent jobs", len(items))

    for item in items:
        if not should_send_work_review_request_email(item, window_start):
            continue

        brief_number = get_field_value(item, "Brief Number")
        job_number = get_field_value(item, "Job Number")
        job_name = get_field_value(item, "Job Name") or job_number
        if not brief_number or not job_number or not job_name:
            logger.info(
                "Skipping work review email because required job fields are missing: "
                "brief=%s job=%s name=%s",
                brief_number,
                job_number,
                job_name,
            )
            continue

        recipient = _resolve_recipient(settings, item)
        if recipient is None:
            logger.info("Skipping work review email for job %s: missing recipient", job_number)
            continue

        logger.info(
            "Sending work review email for job %s (brief %s, name %s) to %s",
            job_number,
            brief_number,
            job_name,
            recipient,
        )
        send_work_review_request_email(
            brief_number,
            job_name,
            job_number,
            recipient=recipient,
        )


def should_send_work_review_request_email(
    item: CrmItem,
    window_start: datetime,
) -> bool:
    job_number = get_field_value(item, "Job Number")
    brief_number = get_field_value(item, "Brief Number")
    last_modified_date = get_field_value(item, "Last Modified Date")
    status = get_field_value(item, "Status")
    if not last_modified_date or not status:
        logger.info(
            "Skipping work review email for job %s: missing last modified date or status",
            job_number or "<unknown>",
        )
        return False

    modified_at = parse_brief_last_modified_date(last_modified_date)
    if modified_at < window_start:
        logger.info(
            "Skipping work review email for job %s: modified %s is outside the poll window",
            job_number or "<unknown>",
            modified_at.strftime("%Y-%m-%d %H:%M"),
        )
        return False

    normalized_status = status.strip().lower()
    if normalized_status not in CLIENT_REVIEW_STATUSES:
        logger.info(
            "Skipping work review email for job %s: status=%s",
            job_number or "<unknown>",
            status,
        )
        return False

    if not _job_has_review_assets(item):
        logger.info(
            "Skipping work review email for job %s: no assets or output files link found",
            job_number or "<unknown>",
        )
        return False

    logger.info(
        "Work review email is eligible for job %s (brief %s)",
        job_number or "<unknown>",
        brief_number or "<unknown>",
    )
    return True


def _job_has_review_assets(item: CrmItem) -> bool:
    return bool(
        get_field_value(item, "Assets")
        or get_field_value(item, "Link to Output Files (Client)")
    )


def _resolve_recipient(settings: AppSettings, item: CrmItem) -> str | None:
    if settings.default_recipient:
        return settings.default_recipient
    return get_field_email(item, "Main Client Contact")
