from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from config.constants import BRIEF_PAGE_SIZE
from services.email_notifications import should_send_work_review_request_email
from services.monitoring import _prime_missing_job_briefs
from utils.monitoring import build_query


def _field(name: str, value: str) -> dict[str, object]:
    return {"name": name, "options": [{"value": value}]}


class MonitoringLogicTestCase(unittest.TestCase):
    def test_build_query_uses_inclusive_checkpoint_and_filter(self) -> None:
        query = build_query(
            3,
            "Last Modified Date",
            {
                "Last Modified Date": "3100",
                "Created By ChatBot": "4747",
            },
            "2026-05-04T20:00:00Z",
            select_all_fields=True,
            filter_condition="FD_4747 = 6366",
        )

        self.assertEqual(
            query,
            "SELECT * FROM MODULE_3 WHERE FD_3100 >= '2026-05-04T20:00:00Z' "
            "AND FD_4747 = 6366",
        )

    def test_review_email_requires_transition_into_client_review(self) -> None:
        item = {
            "fields": [
                _field("Job Number", "JOB-1"),
                _field("Brief Number", "BRIEF-1"),
                _field("Last Modified Date", "05/04/2026, 20:00"),
                _field("Status", "2828"),
                _field("Assets", "asset.pdf"),
            ]
        }

        self.assertTrue(should_send_work_review_request_email(item, previous_job=None))
        self.assertFalse(
            should_send_work_review_request_email(
                item,
                previous_job={"status": "2828"},
            )
        )

    def test_review_email_requires_assets(self) -> None:
        item = {
            "fields": [
                _field("Job Number", "JOB-1"),
                _field("Brief Number", "BRIEF-1"),
                _field("Last Modified Date", "05/04/2026, 20:00"),
                _field("Status", "2828"),
            ]
        }

        self.assertFalse(should_send_work_review_request_email(item, previous_job=None))

    def test_prime_missing_job_briefs_fetches_each_brief_once(self) -> None:
        job_items = [
            {
                "fields": [
                    _field("Job Number", "JOB-1"),
                    _field("Brief Number", "BRIEF-1"),
                ]
            },
            {
                "fields": [
                    _field("Job Number", "JOB-2"),
                    _field("Brief Number", "BRIEF-1"),
                ]
            },
            {
                "fields": [
                    _field("Job Number", "JOB-3"),
                    _field("Brief Number", "BRIEF-2"),
                ]
            },
        ]
        client = Mock()
        client.fetch_all_pages.side_effect = [
            [{"fields": [_field("Brief Number", "BRIEF-1")]}],
            [{"fields": [_field("Brief Number", "BRIEF-2")]}],
        ]

        with (
            patch("services.monitoring.get_chatbot_brief", return_value=None),
            patch("services.monitoring.save_chatbot_brief") as save_chatbot_brief,
        ):
            _prime_missing_job_briefs(client, "token", job_items)

        self.assertEqual(
            client.fetch_all_pages.call_args_list,
            [
                unittest.mock.call(
                    "token",
                    "SELECT * FROM MODULE_3 WHERE FD_4660 = 'BRIEF-1'",
                    page_size=BRIEF_PAGE_SIZE,
                ),
                unittest.mock.call(
                    "token",
                    "SELECT * FROM MODULE_3 WHERE FD_4660 = 'BRIEF-2'",
                    page_size=BRIEF_PAGE_SIZE,
                ),
            ],
        )
        self.assertEqual(save_chatbot_brief.call_count, 2)


if __name__ == "__main__":
    unittest.main()
