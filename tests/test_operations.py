from __future__ import annotations

import json
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.operations import backup, monitor, scheduler
from scripts.operations import refresh as refresh_module


class BackupTests(unittest.TestCase):
    def test_backup_is_verified_and_uses_relative_paths(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data/serving"
            source.mkdir(parents=True)
            (source / "assessment.json").write_text("{}", encoding="utf-8")
            destination = root / "backups"
            with (
                patch.object(backup, "PROJECT_ROOT", root),
                patch.object(backup, "BACKUP_DIR", destination),
                patch.object(backup, "BACKUP_PATHS", (source,)),
            ):
                result = backup.create(retention=2)

            self.assertTrue(result["verified"])
            with tarfile.open(result["path"], "r:gz") as archive:
                self.assertIn("data/serving/assessment.json", archive.getnames())

    def test_retention_removes_oldest_archive(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data/serving"
            source.mkdir(parents=True)
            (source / "value").write_text("1", encoding="utf-8")
            destination = root / "backups"
            with (
                patch.object(backup, "PROJECT_ROOT", root),
                patch.object(backup, "BACKUP_DIR", destination),
                patch.object(backup, "BACKUP_PATHS", (source,)),
                patch("scripts.operations.backup.datetime") as clock,
            ):
                for index in range(3):
                    clock.now.return_value.strftime.return_value = f"2026010{index + 1}T000000Z"
                    clock.now.return_value.isoformat.return_value = "2026-01-01T00:00:00+00:00"
                    result = backup.create(retention=2)

            self.assertEqual(len(list(destination.glob("*.tar.gz"))), 2)
            self.assertEqual(len(result["removed"]), 1)


class MonitorTests(unittest.TestCase):
    def test_alert_is_persisted_without_optional_delivery(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(monitor, "LOG_DIR", root),
                patch.object(monitor, "ALERT_LOG", root / "alerts.jsonl"),
                patch.object(monitor, "LATEST_ALERT", root / "latest.json"),
                patch.dict("os.environ", {}, clear=True),
            ):
                result = monitor.emit_alert("Refresh failed", {"step": "forecast"})

            saved = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["summary"], "Refresh failed")
            self.assertEqual(saved["details"]["step"], "forecast")


class SchedulerTests(unittest.TestCase):
    def test_payload_runs_daily_refresh_without_embedding_secrets(self):
        result = scheduler.payload(hour=6, minute=15)

        self.assertEqual(result["Label"], "com.susbiome.refresh")
        self.assertEqual(result["StartCalendarInterval"], {"Hour": 6, "Minute": 15})
        self.assertIn("scripts.operations.refresh", result["ProgramArguments"][-1])
        self.assertNotIn("EARTHDATA_TOKEN", result["EnvironmentVariables"])


class RefreshWorkflowTests(unittest.TestCase):
    def test_successful_refresh_creates_backup(self):
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "refresh.json"
            completed = {"name": "step", "status": "complete", "returncode": 0}
            with (
                patch.object(refresh_module, "MANIFEST_PATH", manifest),
                patch.object(refresh_module, "_run", return_value=completed),
                patch.object(
                    refresh_module,
                    "create_backup",
                    return_value={"verified": True, "path": "backup.tar.gz"},
                ) as create_backup,
            ):
                result = refresh_module.refresh(skip_gpm=True)

            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["steps"][-1]["name"], "backup")
            create_backup.assert_called_once()

    def test_failed_refresh_persists_alert_and_skips_backup(self):
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "refresh.json"
            failed = {"name": "forecast", "status": "failed", "returncode": 1}
            with (
                patch.object(refresh_module, "MANIFEST_PATH", manifest),
                patch.object(refresh_module, "_run", return_value=failed),
                patch.object(refresh_module, "create_backup") as create_backup,
                patch.object(refresh_module, "emit_alert") as emit_alert,
            ):
                result = refresh_module.refresh(skip_gpm=True)

            self.assertEqual(result["status"], "failed")
            create_backup.assert_not_called()
            emit_alert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
