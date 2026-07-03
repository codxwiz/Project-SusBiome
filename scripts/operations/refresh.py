"""Refresh near-real-time precipitation, forecasts, and district serving data."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from scripts.operations.backup import create as create_backup
from scripts.operations.monitor import emit_alert
from scripts.sources.common.config import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

LOG_DIR = PROJECT_ROOT / "data/logs/operations"
MANIFEST_PATH = LOG_DIR / "refresh.json"
LOCK_PATH = LOG_DIR / "refresh.lock"
GPM_CHECKPOINT = PROJECT_ROOT / "data/logs/ingestion/gpm_late_checkpoint.json"


@contextmanager
def refresh_lock():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError("An operational refresh is already running.") from error
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        LOCK_PATH.unlink(missing_ok=True)


def _run(name: str, arguments: list[str]) -> dict:
    started_at = datetime.now(UTC)
    try:
        process = subprocess.run(
            [sys.executable, "-m", *arguments],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=60 * 30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "name": name,
            "status": "failed",
            "returncode": None,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "stdout": (error.stdout or "")[-4000:],
            "stderr": f"Step exceeded 30 minute timeout. {(error.stderr or '')[-3500:]}",
        }
    return {
        "name": name,
        "status": "complete" if process.returncode == 0 else "failed",
        "returncode": process.returncode,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "stdout": process.stdout[-4000:],
        "stderr": process.stderr[-4000:],
    }


def _next_gpm_date() -> date:
    if not GPM_CHECKPOINT.exists():
        return date.today() - timedelta(days=7)
    checkpoint = json.loads(GPM_CHECKPOINT.read_text(encoding="utf-8"))
    return date.fromisoformat(checkpoint["last_date"]) + timedelta(days=1)


def refresh(*, skip_gpm: bool = False) -> dict:
    started_at = datetime.now(UTC)
    steps = []
    target = date.today() - timedelta(days=1)
    next_gpm = _next_gpm_date()
    if not skip_gpm and next_gpm <= target:
        steps.append(
            _run(
                "gpm_late",
                [
                    "scripts.ingestion.historical_weather", "gpm-late",
                    "--start", next_gpm.isoformat(), "--end", target.isoformat(),
                ],
            )
        )
    else:
        steps.append(
            {
                "name": "gpm_late",
                "status": "skipped",
                "reason": "already current" if not skip_gpm else "disabled by flag",
            }
        )
    steps.append(_run("forecast", ["scripts.forecast.open_meteo", "collect"]))
    steps.append(_run("imd_cyclone", ["scripts.alerts.imd_cyclone", "collect"]))
    steps.append(_run("boundaries", ["scripts.geospatial.districts", "build"]))
    steps.append(_run("susceptibility", ["scripts.susceptibility.static", "build"]))
    steps.append(_run("assessment", ["scripts.serving.district_assessment", "build"]))
    successful = not any(step["status"] == "failed" for step in steps)
    if successful:
        try:
            backup = create_backup()
            steps.append({"name": "backup", "status": "complete", **backup})
        except Exception as error:
            successful = False
            steps.append({"name": "backup", "status": "failed", "error": str(error)})
    manifest = {
        "status": "complete" if successful else "failed",
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "gpm_target_date": target.isoformat(),
        "steps": steps,
    }
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(temporary, MANIFEST_PATH)
    if not successful:
        emit_alert(
            "SusBiome daily refresh failed",
            {
                "manifest": str(MANIFEST_PATH),
                "failed_steps": [
                    step for step in steps if step["status"] == "failed"
                ],
            },
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "status"), nargs="?", default="run")
    parser.add_argument("--skip-gpm", action="store_true")
    arguments = parser.parse_args()
    if arguments.command == "status":
        if not MANIFEST_PATH.exists():
            raise SystemExit("No operational refresh has run yet.")
        result = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        with refresh_lock():
            result = refresh(skip_gpm=arguments.skip_gpm)
    print(json.dumps(result, indent=2))
    if result.get("status") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
