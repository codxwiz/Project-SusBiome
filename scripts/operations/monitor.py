"""Persist refresh incidents and report operational health."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import requests

from scripts.operations.backup import latest
from scripts.sources.common.config import PROJECT_ROOT

LOG_DIR = PROJECT_ROOT / "data/logs/operations"
REFRESH_PATH = LOG_DIR / "refresh.json"
ALERT_LOG = LOG_DIR / "alerts.jsonl"
LATEST_ALERT = LOG_DIR / "latest_alert.json"


def emit_alert(summary: str, details: dict, *, severity: str = "ERROR") -> dict:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    alert = {
        "created_at": datetime.now(UTC).isoformat(),
        "severity": severity,
        "summary": summary,
        "details": details,
    }
    with ALERT_LOG.open("a", encoding="utf-8") as destination:
        destination.write(json.dumps(alert, default=str) + "\n")
    LATEST_ALERT.write_text(json.dumps(alert, indent=2, default=str), encoding="utf-8")
    webhook = os.getenv("SUSBIOME_ALERT_WEBHOOK_URL")
    if webhook:
        try:
            response = requests.post(webhook, json=alert, timeout=15)
            response.raise_for_status()
            alert["webhook_delivered"] = True
        except requests.RequestException as error:
            alert["webhook_delivered"] = False
            alert["webhook_error"] = str(error)
    if os.getenv("SUSBIOME_DESKTOP_ALERTS", "false").lower() == "true":
        message = summary.replace('"', "'")[:180]
        subprocess.run(
            [
                "/usr/bin/osascript",
                "-e",
                f'display notification "{message}" with title "SusBiome"',
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
    return alert


def status(*, refresh_max_age_hours: float = 36, backup_max_age_hours: float = 48) -> dict:
    now = datetime.now(UTC)
    findings = []
    refresh_payload = None
    if not REFRESH_PATH.exists():
        findings.append("No operational refresh record exists.")
    else:
        refresh_payload = json.loads(REFRESH_PATH.read_text(encoding="utf-8"))
        finished = datetime.fromisoformat(refresh_payload["finished_at"])
        age = (now - finished).total_seconds() / 3600
        if refresh_payload.get("status") != "complete":
            findings.append("The latest operational refresh failed.")
        if age > refresh_max_age_hours:
            findings.append(f"The latest operational refresh is {age:.1f} hours old.")
    backup_payload = None
    try:
        backup_payload = latest()
        backup_time = datetime.fromtimestamp(Path(backup_payload["path"]).stat().st_mtime, UTC)
        age = (now - backup_time).total_seconds() / 3600
        if age > backup_max_age_hours:
            findings.append(f"The latest operational backup is {age:.1f} hours old.")
    except (FileNotFoundError, ValueError, tarfile.ReadError) as error:
        findings.append(f"Operational backup unavailable: {error}")
    return {
        "healthy": not findings,
        "checked_at": now.isoformat(),
        "findings": findings,
        "refresh": refresh_payload,
        "backup": backup_payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "test-alert"), nargs="?", default="status")
    arguments = parser.parse_args()
    result = (
        emit_alert("SusBiome monitoring test", {"test": True}, severity="INFO")
        if arguments.command == "test-alert"
        else status()
    )
    print(json.dumps(result, indent=2, default=str))
    if arguments.command == "status" and not result["healthy"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
