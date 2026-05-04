from __future__ import annotations

import logging

import requests

from config.constants import BRIEF_NUMBER_FIELD_NAME
from config.settings import load_settings
from utils import get_token
from utils.brief_storage import brief_exists, store_chatbot_brief
from utils.monitoring import fetch_all_pages, get_field_value


PAGE_SIZE = 250


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = load_settings()
    query = "SELECT * FROM MODULE_3 WHERE FD_4747 = 6366"

    with requests.Session() as session:
        token = get_token()
        items = fetch_all_pages(
            session,
            settings.search_url,
            token,
            query,
            page_size=PAGE_SIZE,
        )

    stored_count = 0
    skipped_count = 0
    for item in items:
        brief_number = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
        if brief_exists(brief_number):
            skipped_count += 1
            continue
        store_chatbot_brief(item)
        stored_count += 1

    logging.info("Fetched %s briefs", len(items))
    logging.info("Stored %s new briefs", stored_count)
    logging.info("Skipped %s existing briefs", skipped_count)


if __name__ == "__main__":
    main()
