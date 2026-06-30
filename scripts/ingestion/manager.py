"""Start and inspect long-running historical collection workers."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.ingestion.historical_weather import (
    lock_owner_pid,
    process_running,
    status as collection_status,
)
from scripts.sources.common.config import PROJECT_ROOT

RUN_DIR = PROJECT_ROOT / "data/logs/ingestion/workers"
PROVIDERS = ("era5", "gpm", "gpm-late")


def metadata_path(provider: str) -> Path:
    return RUN_DIR / f"{provider}.json"


def worker_status(provider: str) -> dict:
    path = metadata_path(provider)
    metadata = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.exists()
        else {"provider": provider, "pid": None}
    )
    lock = PROJECT_ROOT / f"data/logs/ingestion/{provider}.lock"
    lock_pid = lock_owner_pid(lock) if lock.exists() else None
    if lock_pid is not None and process_running(lock_pid):
        metadata["pid"] = lock_pid
        metadata["running"] = True
        metadata["status_source"] = "collector_lock"
    else:
        pid = metadata.get("pid")
        metadata["running"] = bool(pid and process_running(int(pid)))
        metadata["status_source"] = "manager_metadata"
    return metadata


def start(provider: str, start_date: str, end_date: str) -> dict:
    existing = worker_status(provider)
    if existing.get("running"):
        raise RuntimeError(f"{provider} collector is already running as PID {existing['pid']}.")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RUN_DIR / f"{provider}.log"
    command = [
        sys.executable,
        "-m",
        "scripts.ingestion.historical_weather",
        provider,
        "--start",
        start_date,
        "--end",
        end_date,
    ]
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    metadata = {
        "provider": provider,
        "pid": process.pid,
        "running": True,
        "started_at": datetime.now(UTC).isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "log": str(log_path),
        "command": command,
    }
    metadata_path(provider).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def stop(provider: str) -> dict:
    metadata = worker_status(provider)
    if metadata.get("running"):
        os.killpg(int(metadata["pid"]), signal.SIGTERM)
        metadata["running"] = False
        metadata["stopped_at"] = datetime.now(UTC).isoformat()
        metadata_path(provider).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("provider", choices=PROVIDERS)
    start_parser.add_argument("--start", default="2006-01-01")
    start_parser.add_argument("--end", default="2025-12-31")
    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("provider", choices=PROVIDERS)
    subparsers.add_parser("status")
    arguments = parser.parse_args()
    if arguments.command == "start":
        result = start(arguments.provider, arguments.start, arguments.end)
    elif arguments.command == "stop":
        result = stop(arguments.provider)
    else:
        result = {
            "workers": {provider: worker_status(provider) for provider in PROVIDERS},
            "collection": collection_status(),
        }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
