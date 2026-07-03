"""Generate, install, and inspect the macOS launchd refresh schedule."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shlex
import subprocess
from pathlib import Path

from scripts.sources.common.config import PROJECT_ROOT

LABEL = "com.susbiome.refresh"
DEFAULT_DESTINATION = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"


def payload(*, hour: int = 6, minute: int = 15) -> dict:
    project_root = shlex.quote(str(PROJECT_ROOT))
    python = shlex.quote(str(PROJECT_ROOT / "venv312/bin/python"))
    return {
        "Label": LABEL,
        "ProgramArguments": [
            "/bin/zsh",
            "-lc",
            f"cd {project_root} && exec {python} -m scripts.operations.refresh run",
        ],
        "WorkingDirectory": str(PROJECT_ROOT),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(PROJECT_ROOT / "data/logs/operations/launchd.out.log"),
        "StandardErrorPath": str(PROJECT_ROOT / "data/logs/operations/launchd.err.log"),
        "EnvironmentVariables": {
            "PYTHONUNBUFFERED": "1",
            "SUSBIOME_DESKTOP_ALERTS": "true",
        },
        "RunAtLoad": False,
        "ProcessType": "Background",
    }


def write(destination: Path = DEFAULT_DESTINATION, *, hour: int = 6, minute: int = 15) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data/logs/operations").mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".plist.tmp")
    with temporary.open("wb") as output:
        plistlib.dump(payload(hour=hour, minute=minute), output, sort_keys=False)
    os.replace(temporary, destination)
    return {"label": LABEL, "path": str(destination), "hour": hour, "minute": minute}


def launchctl(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/launchctl", *arguments], text=True, capture_output=True, check=False
    )


def install(destination: Path = DEFAULT_DESTINATION, *, hour: int = 6, minute: int = 15) -> dict:
    written = write(destination, hour=hour, minute=minute)
    domain = f"gui/{os.getuid()}"
    launchctl("bootout", domain, str(destination))
    loaded = launchctl("bootstrap", domain, str(destination))
    if loaded.returncode:
        raise RuntimeError(loaded.stderr.strip() or loaded.stdout.strip())
    return {**written, "installed": True, "domain": domain}


def status() -> dict:
    domain = f"gui/{os.getuid()}/{LABEL}"
    result = launchctl("print", domain)
    return {
        "label": LABEL,
        "installed": result.returncode == 0,
        "path": str(DEFAULT_DESTINATION),
        "launchctl": (result.stdout or result.stderr)[-4000:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "install", "status"), nargs="?", default="status")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--hour", type=int, default=6)
    parser.add_argument("--minute", type=int, default=15)
    arguments = parser.parse_args()
    if arguments.command == "install":
        result = install(arguments.destination, hour=arguments.hour, minute=arguments.minute)
    elif arguments.command == "write":
        result = write(arguments.destination, hour=arguments.hour, minute=arguments.minute)
    else:
        result = status()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
