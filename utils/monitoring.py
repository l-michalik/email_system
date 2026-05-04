from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from config.constants import (
    BRIEF_EMAIL_SUBJECT,
    BRIEF_NUMBER_FIELD_NAME,
    PAGE_SIZE,
    POLL_WINDOW_MINUTES,
)
from utils.mailer import send_email


def cutoff_timestamp() -> str:
    cutoff = datetime.now(UTC) - timedelta(minutes=POLL_WINDOW_MINUTES)
    return cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_query(
    module_id: int,
    query_field_name: str,
    fields: dict[str, str],
    cutoff: str,
) -> str:
    selected_fields = ", ".join(fields.values())
    return (
        f"SELECT {selected_fields} FROM MODULE_{module_id} "
        f"WHERE {fields[query_field_name]} > '{cutoff}'"
    )


def fetch_page(
    session: requests.Session,
    url: str,
    token: str,
    query: str,
    start: int,
) -> list[dict[str, Any]]:
    response = session.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=query,
        params={
            "returnAllFields": False,
            "limit": PAGE_SIZE,
            "start": start,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["result"]


def fetch_all_pages(
    session: requests.Session,
    url: str,
    token: str,
    query: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    start = 1

    while True:
        page = fetch_page(session, url, token, query, start)
        items.extend(page)
        if len(page) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    return items


def get_field_value(item: dict[str, Any], field_name: str) -> str:
    field = next(field for field in item["fields"] if field["name"] == field_name)
    options = field["options"]
    return options[0]["value"] if options else ""


def parse_brief_created_date(value: str) -> datetime:
    return datetime.strptime(value, "%m/%d/%Y, %H:%M")


def build_brief_creation_email_text(brief_number: str) -> str:
    return (
        "Brief has been created successfully\n\n"
        f"Brief Number: {brief_number}\n\n"
        "Please make a note of this Brief ID. If you would like to update or modify this brief in the future,  "
        "simply return to the chatbot clicking the open chatbot and reference your Brief ID.\n\n"
        "Open Chatbot: https://waa.mdbgo.io/\n"
    )


def build_brief_creation_email_html(brief_number: str) -> str:
    return f"""
<div style="margin:0!important;padding:0!important">
  <div role="article" aria-label="An email from Your Brand Name" lang="en" style="background-color:white;color:#2b2b2b;font-family:'Open Sans',HelveticaNeue,Arial,Helvetica,sans-serif;font-size:18px;font-weight:400;line-height:28px;margin:0 auto;max-width:600px;padding:40px 20px 40px 20px">
    <header>
      <center>
        <img src="https://joule.weareamnet.com/amnet/public/siteelements/placeholder.png" alt="" width="80" style="height:auto">
      </center>
      <h2 style="color:#000000;font-size:32px;font-weight:800;line-height:32px;margin:48px 0;text-align:center">
        Brief has been created successfully
      </h2>
    </header>
    <img src="https://joule.weareamnet.com/amnet/public/siteelements/Joule_inline_colur_filled.png" alt="" width="600" border="0" style="border-radius:4px;display:block;max-width:100%;min-width:100px;width:100%">
    <h2 style="color:#000000;font-size:28px;font-weight:600;line-height:32px;margin:48px 0 24px 0;text-align:center">
      Brief Number: {brief_number}
    </h2>
    <p>
      Please make a note of this Brief ID. If you would like to update or modify this brief in the future,  simply return to the chatbot clicking the open chatbot and reference your Brief ID.
    </p>
    <center>
      <div style="margin:48px 0">
        <a href="https://waa.mdbgo.io/" target="_blank">
          <button style="background-color:#ee5a24;border:none;border-radius:4px;color:#ffffff;display:inline-block;font-family:'Open Sans',HelveticaNeue,Arial,Helvetica,sans-serif;font-size:18px;font-weight:bold;line-height:60px;text-align:center;text-decoration:none;width:300px">
            Open Chatbot
          </button>
        </a>
      </div>
    </center>
  </div>
</div>
""".strip()


def send_brief_creation_email(item: dict[str, Any]) -> None:
    brief_number = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
    body = build_brief_creation_email_text(brief_number)
    html_body = build_brief_creation_email_html(brief_number)
    send_email(BRIEF_EMAIL_SUBJECT, body, html_body=html_body)
