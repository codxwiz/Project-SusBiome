"""Version, verify, promote, and roll back trained model releases."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from scripts.ml.models import MODEL_DIRECTORY

REQUIRED_HAZARDS = {"flood", "cyclone"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(temporary, path)


class ModelRegistry:
    def __init__(self, model_directory: Path = MODEL_DIRECTORY) -> None:
        self.root = model_directory
        self.releases = self.root / "releases"
        self.state_path = self.root / "registry.json"

    def state(self) -> dict:
        if not self.state_path.exists():
            return {"schema_version": 1, "active_release": None, "previous_release": None}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def register(
        self,
        artifacts: dict[str, Path],
        metrics: dict,
        *,
        release_id: str | None = None,
    ) -> str:
        missing = REQUIRED_HAZARDS - set(artifacts)
        if missing:
            raise ValueError("Release is missing required models: " + ", ".join(sorted(missing)))
        release_id = release_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        release_directory = self.releases / release_id
        if release_directory.exists():
            raise FileExistsError(f"Model release already exists: {release_id}")
        release_directory.mkdir(parents=True)
        models = {}
        for hazard, source in sorted(artifacts.items()):
            if not source.exists():
                raise FileNotFoundError(source)
            destination = release_directory / f"{hazard}_model.joblib"
            shutil.copy2(source, destination)
            models[hazard] = {
                "path": destination.name,
                "sha256": sha256(destination),
                "bytes": destination.stat().st_size,
            }
        atomic_json(
            release_directory / "manifest.json",
            {
                "schema_version": 1,
                "release_id": release_id,
                "created_at": datetime.now(UTC).isoformat(),
                "models": models,
                "metrics": metrics,
            },
        )
        return release_id

    def manifest(self, release_id: str) -> dict:
        path = self.releases / release_id / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown model release: {release_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self, release_id: str) -> dict:
        manifest = self.manifest(release_id)
        missing = REQUIRED_HAZARDS - set(manifest.get("models", {}))
        if missing:
            raise ValueError("Release manifest is missing: " + ", ".join(sorted(missing)))
        for hazard, metadata in manifest["models"].items():
            path = self.releases / release_id / metadata["path"]
            if not path.exists() or sha256(path) != metadata["sha256"]:
                raise ValueError(f"Checksum verification failed for {hazard} in {release_id}")
        return manifest

    def promote(self, release_id: str) -> dict:
        self.verify(release_id)
        previous = self.state().get("active_release")
        state = {
            "schema_version": 1,
            "active_release": release_id,
            "previous_release": previous,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        atomic_json(self.state_path, state)
        return state

    def active_model_path(self, hazard: str, fallback: Path | None = None) -> Path:
        state = self.state()
        active = state.get("active_release")
        if not active:
            if not self.state_path.exists() and fallback is not None:
                return fallback
            reason = state.get("quarantine_reason")
            detail = f" Quarantine reason: {reason}" if reason else ""
            raise FileNotFoundError(f"No active release for {hazard}.{detail}")
        manifest = self.verify(active)
        metadata = manifest.get("models", {}).get(hazard)
        if metadata is None:
            raise FileNotFoundError(f"Active release {active} has no {hazard} model.")
        return self.releases / active / metadata["path"]

    def rollback(self) -> dict:
        previous = self.state().get("previous_release")
        if not previous:
            raise RuntimeError("No previous model release is available.")
        return self.promote(previous)

    def deactivate(self, reason: str) -> dict:
        """Atomically disable inference while retaining immutable release artifacts."""
        current = self.state().get("active_release")
        state = {
            "schema_version": 1,
            "active_release": None,
            "previous_release": None,
            "quarantined_release": current,
            "quarantine_reason": reason,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        atomic_json(self.state_path, state)
        return state
