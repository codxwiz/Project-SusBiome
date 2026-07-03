"""Create and verify compact operational backups with bounded retention."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT

BACKUP_DIR = PROJECT_ROOT / "data/backups/operations"
DEFAULT_RETENTION = 14
BACKUP_PATHS = (
    PROJECT_ROOT / "data/serving",
    PROJECT_ROOT / "data/silver/forecast",
    PROJECT_ROOT / "data/silver/alerts",
    PROJECT_ROOT / "data/silver/validation/chirps",
    PROJECT_ROOT / "data/silver/events/weather_drought_episodes.parquet",
    PROJECT_ROOT / "data/silver/geospatial",
    PROJECT_ROOT / "data/silver/susceptibility",
    PROJECT_ROOT / "data/quality",
    PROJECT_ROOT / "data/logs/operations",
    PROJECT_ROOT / "models/registry.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(path)
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise ValueError("Operational backup is empty.")
        unsafe = [
            member.name
            for member in members
            if member.name.startswith("/") or ".." in Path(member.name).parts
        ]
        if unsafe:
            raise ValueError("Operational backup contains unsafe paths.")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "files": sum(member.isfile() for member in members),
        "sha256": _sha256(path),
        "verified": True,
    }


def create(*, retention: int = DEFAULT_RETENTION) -> dict:
    if retention < 2:
        raise ValueError("Backup retention must keep at least two archives.")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = BACKUP_DIR / f"susbiome-operational-{timestamp}.tar.gz"
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    included = []
    with tarfile.open(temporary, "w:gz") as archive:
        for path in BACKUP_PATHS:
            if path.exists():
                archive.add(path, arcname=str(path.relative_to(PROJECT_ROOT)))
                included.append(str(path.relative_to(PROJECT_ROOT)))
    os.replace(temporary, destination)
    result = {
        **verify(destination),
        "created_at": datetime.now(UTC).isoformat(),
        "included": included,
    }
    destination.with_suffix(".json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    archives = sorted(BACKUP_DIR.glob("susbiome-operational-*.tar.gz"), reverse=True)
    removed = []
    for obsolete in archives[retention:]:
        obsolete.unlink()
        obsolete.with_suffix(".json").unlink(missing_ok=True)
        removed.append(str(obsolete))
    result["retention"] = retention
    result["removed"] = removed
    return result


def latest() -> dict:
    archives = sorted(BACKUP_DIR.glob("susbiome-operational-*.tar.gz"), reverse=True)
    if not archives:
        raise FileNotFoundError("No operational backup exists.")
    return verify(archives[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify"), nargs="?", default="create")
    parser.add_argument("--retention", type=int, default=DEFAULT_RETENTION)
    arguments = parser.parse_args()
    result = create(retention=arguments.retention) if arguments.command == "create" else latest()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
