from __future__ import annotations

import logging

import requests

from config.settings import load_settings
from utils import get_token
from utils.brief_storage import (
    brief_exists,
    job_exists,
    store_chatbot_brief,
    store_chatbot_job,
)
from utils.monitoring import fetch_all_pages, get_field_value


PAGE_SIZE = 250
JOB_QUERY = "SELECT FD_471, FD_1291, FD_1285, FD_316, FD_229, FD_4406 FROM MODULE_14"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = load_settings()

    with requests.Session() as session:
        token = get_token()
        briefs = fetch_all_pages(
            session,
            settings.search_url,
            token,
            "SELECT * FROM MODULE_3 WHERE FD_4747 = 6366",
            page_size=PAGE_SIZE,
        )

        brief_numbers = set()
        for item in briefs:
            brief_number = get_field_value(item, "Brief Number")
            if brief_number:
                brief_numbers.add(brief_number)
        jobs = fetch_all_pages(
            session,
            settings.search_url,
            token,
            JOB_QUERY,
            page_size=PAGE_SIZE,
        )

    stored_count = 0
    skipped_count = 0
    for item in briefs:
        brief_number = get_field_value(item, "Brief Number")
        if not brief_number:
            continue
        if brief_exists(brief_number):
            skipped_count += 1
            continue
        store_chatbot_brief(item)
        stored_count += 1

    stored_jobs_count = 0
    skipped_jobs_count = 0
    for item in jobs:
        brief_number = get_field_value(item, "Brief Number")
        if not brief_number:
            continue
        if brief_number not in brief_numbers:
            continue

        job_number = get_field_value(item, "Job Number")
        if not job_number:
            continue
        if job_exists(job_number):
            skipped_jobs_count += 1
            continue

        store_chatbot_job(item)
        stored_jobs_count += 1

    logging.info("Fetched %s briefs", len(briefs))
    logging.info("Stored %s new briefs", stored_count)
    logging.info("Skipped %s existing briefs", skipped_count)
    logging.info("Fetched %s jobs", len(jobs))
    logging.info("Stored %s new jobs", stored_jobs_count)
    logging.info("Skipped %s existing jobs", skipped_jobs_count)


if __name__ == "__main__":
    main()
