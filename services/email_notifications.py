from __future__ import annotations

import logging
from typing import Callable

from clients import CrmItem
from config.settings import AppSettings
from utils.brief_storage import (
    get_chatbot_brief,
    get_chatbot_job,
    has_sent_notification,
    is_chatbot_brief,
    mark_create_email_sent,
    record_notification,
    save_chatbot_brief,
    save_chatbot_job,
    should_send_change_request_updated_email,
)
from utils.email_templates import EmailTemplateContent, build_email_html, build_email_text
from utils.mailer import send_email
from utils.monitoring import get_field_email, get_field_value

CLIENT_REVIEW_STATUSES = {"client review"}
CHATBOT_URL = "https://waa.mdbgo.io/"
logger = logging.getLogger(__name__)


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


def send_template_email(
    content: EmailTemplateContent,
    recipient: str | None = None,
    log_message_factory: Callable[[str], str] | None = None,
) -> None:
    send_email(
        content.subject,
        build_email_text(content),
        recipient=recipient,
        html_body=build_email_html(content),
        log_message_factory=log_message_factory,
    )


def send_brief_creation_email(brief_id: str, recipient: str | None = None) -> None:
    content = create_brief_creation_email(brief_id)
    send_email(
        content.subject,
        build_email_text(content),
        recipient=recipient,
        html_body=build_email_html(content),
        log_message_factory=lambda resolved_recipient: (
            f"Email for brief id {brief_id} has been sent to "
            f"'{resolved_recipient}' - New Brief"
        ),
    )


def send_change_request_updated_email(brief_id: str, recipient: str | None = None) -> None:
    content = create_brief_update_email(brief_id)
    send_email(
        content.subject,
        build_email_text(content),
        recipient=recipient,
        html_body=build_email_html(content),
        log_message_factory=lambda resolved_recipient: (
            f"Email for brief id {brief_id} has been sent to "
            f"'{resolved_recipient}' - Change Request Updated"
        ),
    )


def send_work_review_request_email(
    brief_number: str,
    job_name: str,
    job_number: str,
    recipient: str | None = None,
) -> None:
    content = create_work_review_request_email(brief_number, job_name, job_number)
    send_template_email(
        content,
        recipient=recipient,
        log_message_factory=lambda resolved_recipient: (
            f"Email for brief id {brief_number} has been sent to "
            f"'{resolved_recipient}' - Job Moved to Client Review"
        ),
    )


def process_recent_briefs(settings: AppSettings, items: list[CrmItem]) -> None:
    for item in items:
        brief_number = get_field_value(item, "Brief Number")
        created_by_chatbot = get_field_value(item, "Created By ChatBot")
        created_date = get_field_value(item, "Created Date")
        last_modified_date = get_field_value(item, "Last Modified Date")

        if created_by_chatbot != "Yes":
            continue

        if not brief_number or not created_date or not last_modified_date:
            continue

        recipient = _resolve_recipient(settings, item)
        is_new_brief = get_chatbot_brief(brief_number) is None

        if is_new_brief:
            if recipient is None:
                continue
            if not has_sent_notification("brief_created", brief_number):
                send_brief_creation_email(brief_number, recipient=recipient)
                mark_create_email_sent(brief_number)
        elif should_send_change_request_updated_email(item):
            if recipient is None:
                continue
            if not has_sent_notification("brief_updated", brief_number, last_modified_date):
                send_change_request_updated_email(brief_number, recipient=recipient)
                record_notification("brief_updated", brief_number, last_modified_date)

        save_chatbot_brief(item)


def process_review_jobs(settings: AppSettings, items: list[CrmItem]) -> None:
    for item in items:
        brief_number = get_field_value(item, "Brief Number")
        job_number = get_field_value(item, "Job Number")
        last_modified_date = get_field_value(item, "Last Modified Date")
        job_name = get_field_value(item, "Job Name") or job_number
        if not brief_number or not job_number or not job_name or not last_modified_date:
            logger.info(
                "Skipping job_client_review: job_number=%s brief_number=%s job_name=%s last_modified_date=%s (missing required field)",
                job_number or "<missing>",
                brief_number or "<missing>",
                job_name or "<missing>",
                last_modified_date or "<missing>",
            )
            continue

        previous_job = get_chatbot_job(job_number)
        review_skip_reason = _get_work_review_skip_reason(item, previous_job)
        if review_skip_reason is not None:
            logger.info(
                "Skipping job_client_review for job_number=%s brief_number=%s: %s",
                job_number,
                brief_number,
                review_skip_reason,
            )
            save_chatbot_job(item)
            continue

        if not is_chatbot_brief(brief_number):
            logger.info(
                "Skipping job_client_review for job_number=%s brief_number=%s: brief is not stored as chatbot brief",
                job_number,
                brief_number,
            )
            save_chatbot_job(item)
            continue

        recipient = _resolve_recipient(settings, item)
        if recipient is None:
            logger.info(
                "Skipping job_client_review for job_number=%s brief_number=%s: recipient could not be resolved from default_recipient or Main Client Contact",
                job_number,
                brief_number,
            )
            save_chatbot_job(item)
            continue

        if has_sent_notification("job_client_review", job_number, last_modified_date):
            logger.info(
                "Skipping job_client_review for job_number=%s brief_number=%s: notification already sent for event_key=job_client_review:%s:%s",
                job_number,
                brief_number,
                job_number,
                last_modified_date,
            )
            save_chatbot_job(item)
            continue

        logger.info(
            "Sending job_client_review email for job_number=%s brief_number=%s recipient=%s event_key=job_client_review:%s:%s",
            job_number,
            brief_number,
            recipient,
            job_number,
            last_modified_date,
        )
        send_work_review_request_email(
            brief_number,
            job_name,
            job_number,
            recipient=recipient,
        )
        record_notification("job_client_review", job_number, last_modified_date)

        save_chatbot_job(item)


def should_send_work_review_request_email(
    item: CrmItem,
    previous_job: dict[str, str] | None,
) -> bool:
    return _get_work_review_skip_reason(item, previous_job) is None


def _get_work_review_skip_reason(
    item: CrmItem,
    previous_job: dict[str, str] | None,
) -> str | None:
    job_number = get_field_value(item, "Job Number") or "<unknown>"
    brief_number = get_field_value(item, "Brief Number") or "<unknown>"
    last_modified_date = get_field_value(item, "Last Modified Date")
    status = get_field_value(item, "Status")
    if not last_modified_date or not status:
        missing_fields = []
        if not last_modified_date:
            missing_fields.append("Last Modified Date")
        if not status:
            missing_fields.append("Status")
        return f"missing required field(s): {', '.join(missing_fields)}"

    normalized_status = status.strip().lower()
    if normalized_status not in CLIENT_REVIEW_STATUSES:
        return (
            "status is not client review: "
            f"status={status!r} expected_status_codes={sorted(CLIENT_REVIEW_STATUSES)!r}"
        )

    if not _job_has_review_assets(item):
        assets = get_field_value(item, "Assets")
        output_files_link = get_field_value(item, "Link to Output Files (Client)")
        return (
            "missing review assets: "
            f"Assets={assets!r} Link to Output Files (Client)={output_files_link!r}"
        )

    previous_status = (previous_job or {}).get("status")
    if previous_status and previous_status.strip().lower() in CLIENT_REVIEW_STATUSES:
        return (
            "previous status is already client review: "
            f"previous_status={previous_status!r}"
        )

    return None


def _job_has_review_assets(item: CrmItem) -> bool:
    return bool(
        get_field_value(item, "Assets")
        or get_field_value(item, "Link to Output Files (Client)")
    )


def _resolve_recipient(settings: AppSettings, item: CrmItem) -> str | None:
    if settings.default_recipient:
        return settings.default_recipient
    return get_field_email(item, "Main Client Contact")
