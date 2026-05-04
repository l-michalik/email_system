from __future__ import annotations

import unittest

from services.email_notifications import should_send_work_review_request_email
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


if __name__ == "__main__":
    unittest.main()
