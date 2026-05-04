from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from utils import brief_storage


class BriefStorageTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = brief_storage.DB_PATH
        self.original_is_table_created = brief_storage._is_table_created
        brief_storage.DB_PATH = Path(self.temp_dir.name) / "briefs.sqlite3"
        brief_storage._is_table_created = False

    def tearDown(self) -> None:
        brief_storage.DB_PATH = self.original_db_path
        brief_storage._is_table_created = self.original_is_table_created
        self.temp_dir.cleanup()

    def test_sync_checkpoint_roundtrip(self) -> None:
        self.assertIsNone(brief_storage.get_sync_checkpoint("brief"))

        brief_storage.set_sync_checkpoint("brief", "2026-05-04T20:00:00Z")

        self.assertEqual(
            brief_storage.get_sync_checkpoint("brief"),
            "2026-05-04T20:00:00Z",
        )

    def test_notification_history_roundtrip(self) -> None:
        self.assertFalse(
            brief_storage.has_sent_notification(
                "job_client_review",
                "JOB-1",
                "2026-05-04T20:00:00Z",
            )
        )

        brief_storage.record_notification(
            "job_client_review",
            "JOB-1",
            "2026-05-04T20:00:00Z",
        )

        self.assertTrue(
            brief_storage.has_sent_notification(
                "job_client_review",
                "JOB-1",
                "2026-05-04T20:00:00Z",
            )
        )


if __name__ == "__main__":
    unittest.main()
