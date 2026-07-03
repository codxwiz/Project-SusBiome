from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS
from scripts.ml.models import (
    FEATURE_COLUMNS,
    EXPERIMENTAL_TARGET_COLUMNS,
    MIN_HISTORY_DAYS,
    MIN_POSITIVE_SAMPLES,
    PRODUCTION_TARGET_COLUMNS,
    TARGET_COLUMNS,
    TRAINING_DATASET,
)
from scripts.prediction.loader import PredictionLoader
from scripts.sources.common.config import PROJECT_ROOT
from scripts.ingestion.historical_weather import GPM_EXPECTED_DAYS

MIN_INDEPENDENT_EVENTS = 10


@dataclass(frozen=True, slots=True)
class Finding:
    severity: str
    check: str
    message: str


def audit_training(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not path.exists():
        return [Finding("ERROR", "training.exists", f"Missing dataset: {path}")]

    files = [path] if path.is_file() else sorted(path.glob("year=*/features.parquet"))
    if not files:
        return [Finding("ERROR", "training.exists", f"No training partitions under: {path}")]

    required_columns = [
        "latitude",
        "longitude",
        "valid_time",
        "label_method",
        *FEATURE_COLUMNS,
        *PRODUCTION_TARGET_COLUMNS,
    ]
    columns = [*required_columns, *EXPERIMENTAL_TARGET_COLUMNS]
    import pyarrow.parquet as pq

    available = set(pq.ParquetFile(files[0]).schema.names)

    missing_required = [column for column in required_columns if column not in available]
    missing_experimental = [
        column for column in EXPERIMENTAL_TARGET_COLUMNS if column not in available
    ]
    if missing_required:
        findings.append(
            Finding(
                "ERROR",
                "training.schema",
                "Missing: " + ", ".join(missing_required),
            )
        )
    if missing_experimental:
        findings.append(
            Finding(
                "WARNING",
                "training.experimental_schema",
                "Missing: " + ", ".join(missing_experimental),
            )
        )
    columns = [column for column in columns if column in available]

    all_dates: set[pd.Timestamp] = set()
    outside_rows = 0
    nulls = 0
    methods: set[str] = set()
    target_counts = {target: {0: 0, 1: 0} for target in TARGET_COLUMNS}
    bounds = NORTHEAST_INDIA_BOUNDS
    for file in files:
        dataframe = pd.read_parquet(file, columns=columns)
        dates = pd.to_datetime(dataframe["valid_time"], utc=True, errors="coerce")
        all_dates.update(dates.dt.normalize().dropna().tolist())
        outside = ~(
            dataframe["latitude"].between(bounds["min_latitude"], bounds["max_latitude"])
            & dataframe["longitude"].between(
                bounds["min_longitude"], bounds["max_longitude"]
            )
        )
        outside_rows += int(outside.sum())
        present_features = [column for column in FEATURE_COLUMNS if column in dataframe]
        nulls += int(dataframe[present_features].isna().sum().sum())
        if "label_method" in dataframe:
            methods.update(dataframe["label_method"].dropna().astype(str).unique())
        for target in TARGET_COLUMNS:
            if target in dataframe:
                counts = dataframe[target].value_counts().to_dict()
                target_counts[target][0] += int(counts.get(0, 0))
                target_counts[target][1] += int(counts.get(1, 0))

    days = len(all_dates)
    if days < MIN_HISTORY_DAYS:
        findings.append(
            Finding(
                "ERROR",
                "training.history",
                f"Found {days} distinct days; require at least {MIN_HISTORY_DAYS}.",
            )
        )

    if outside_rows:
        findings.append(
            Finding(
                "ERROR",
                "training.geography",
                f"{outside_rows} rows are outside Northeast India.",
            )
        )

    if nulls:
        findings.append(
            Finding("ERROR", "training.completeness", f"Found {nulls} null features.")
        )

    if "label_method" in available:
        if methods != {"verified_event_alignment"}:
            findings.append(
                Finding(
                    "ERROR",
                    "training.labels",
                    "Labels are not exclusively verified_event_alignment.",
                )
            )

    for target in TARGET_COLUMNS:
        if target not in available:
            continue
        counts = target_counts[target]
        severity = "ERROR" if target in PRODUCTION_TARGET_COLUMNS else "WARNING"
        if counts.get(0, 0) == 0 or counts.get(1, 0) == 0:
            findings.append(
                Finding(severity, f"training.{target}", "Both target classes are required.")
            )
        elif int(counts.get(1, 0)) < MIN_POSITIVE_SAMPLES:
            findings.append(
                Finding(
                    severity,
                    f"training.{target}",
                    f"Only {int(counts.get(1, 0))} positive samples.",
                )
            )

    return findings


def audit_models() -> list[Finding]:
    loader = PredictionLoader()
    findings = []
    for hazard, load, severity in (
        ("flood", loader.load_flood, "ERROR"),
        ("cyclone", loader.load_cyclone, "ERROR"),
        ("drought", loader.load_drought, "WARNING"),
    ):
        try:
            load()
        except Exception as error:
            findings.append(Finding(severity, f"models.{hazard}_contract", str(error)))
    return findings


def audit_operational() -> list[Finding]:
    findings: list[Finding] = []
    boundary_path = PROJECT_ROOT / "data/silver/geospatial/district_boundary_manifest.csv"
    forecast_path = PROJECT_ROOT / "data/silver/forecast/district_horizons.parquet"
    static_path = PROJECT_ROOT / "data/silver/susceptibility/district_static.parquet"
    assessment_path = PROJECT_ROOT / "data/serving/district_assessments.parquet"
    if not boundary_path.exists():
        findings.append(Finding("ERROR", "operational.boundaries", "Boundary registry is missing."))
    else:
        boundaries = pd.read_csv(boundary_path)
        usable = int(boundaries["district_wide_usable"].astype(bool).sum())
        duplicate_ids = int(
            boundaries.loc[boundaries["district_wide_usable"].astype(bool), "source_id"]
            .duplicated().sum()
        )
        if len(boundaries) != 133:
            findings.append(
                Finding("ERROR", "operational.district_registry", f"Found {len(boundaries)}/133 districts.")
            )
        if usable != 133:
            findings.append(
                Finding(
                    "WARNING" if usable >= 130 else "ERROR",
                    "operational.boundary_coverage",
                    f"Found current usable polygons for {usable}/133 districts.",
                )
            )
        if duplicate_ids:
            findings.append(
                Finding("ERROR", "operational.boundary_uniqueness", f"Found {duplicate_ids} duplicate polygons.")
            )
    if not forecast_path.exists():
        findings.append(Finding("ERROR", "operational.forecast", "District forecast is missing."))
    else:
        forecast = pd.read_parquet(forecast_path)
        expected = 133 * 3
        if len(forecast) != expected:
            findings.append(
                Finding("ERROR", "operational.forecast_completeness", f"Found {len(forecast)}/{expected} rows.")
            )
        collected = pd.to_datetime(forecast["collected_at"], utc=True, errors="coerce").max()
        age_hours = (
            float("inf")
            if pd.isna(collected)
            else (datetime.now(UTC) - collected.to_pydatetime()).total_seconds() / 3600
        )
        if age_hours > 36:
            findings.append(
                Finding("ERROR", "operational.forecast_freshness", f"Forecast age is {age_hours:.1f} hours.")
            )
    if not static_path.exists():
        findings.append(Finding("ERROR", "operational.susceptibility", "Static factors are missing."))
    else:
        static = pd.read_parquet(static_path)
        coverage = float(static["static_factor_coverage"].mean())
        if coverage < 0.8:
            findings.append(
                Finding(
                    "ERROR", "operational.static_factor_coverage",
                    f"Mean static-factor coverage is {coverage:.1%}; require at least 80%.",
                )
            )
    if not assessment_path.exists():
        findings.append(Finding("ERROR", "operational.assessment", "Serving assessment is missing."))
    else:
        assessment = pd.read_parquet(assessment_path)
        available = int(assessment["assessment_available"].sum())
        if available != len(assessment):
            findings.append(
                Finding(
                    "ERROR", "operational.weather_assessments",
                    f"Weather-pattern assessments are available for {available}/{len(assessment)} rows.",
                )
            )
    return findings


def audit_confirmations() -> list[Finding]:
    findings = []
    chirps_path = PROJECT_ROOT / "data/quality/chirps_gpm_crosscheck.json"
    drought_path = PROJECT_ROOT / "data/quality/weather_drought_history.json"
    cyclone_path = PROJECT_ROOT / "data/silver/alerts/imd_cyclone.json"
    cyclone_history_path = PROJECT_ROOT / "data/quality/ibtracs_cyclone_provenance.json"
    if not chirps_path.exists():
        findings.append(Finding("ERROR", "validation.chirps", "CHIRPS rainfall cross-check is missing."))
    else:
        chirps = json.loads(chirps_path.read_text(encoding="utf-8"))
        if int(chirps.get("districts", 0)) != 133:
            findings.append(
                Finding(
                    "ERROR",
                    "validation.chirps_coverage",
                    f"CHIRPS cross-check covers {chirps.get('districts', 0)}/133 districts.",
                )
            )
    if not drought_path.exists():
        findings.append(Finding("ERROR", "history.drought", "Weather-derived drought history is missing."))
    else:
        drought = json.loads(drought_path.read_text(encoding="utf-8"))
        if int(drought.get("episodes", 0)) == 0:
            findings.append(Finding("ERROR", "history.drought", "No drought episodes were identified."))
    if not cyclone_path.exists():
        findings.append(Finding("ERROR", "confirmation.imd_cyclone", "IMD cyclone confirmation is missing."))
    else:
        cyclone = json.loads(cyclone_path.read_text(encoding="utf-8"))
        collected = pd.to_datetime(cyclone.get("collected_at"), utc=True, errors="coerce")
        age_hours = (
            float("inf")
            if pd.isna(collected)
            else (datetime.now(UTC) - collected.to_pydatetime()).total_seconds() / 3600
        )
        if age_hours > 24:
            findings.append(
                Finding(
                    "ERROR",
                    "confirmation.imd_cyclone_freshness",
                    f"IMD cyclone confirmation is {age_hours:.1f} hours old.",
                )
            )
    if not cyclone_history_path.exists():
        findings.append(
            Finding(
                "ERROR",
                "history.cyclone_provenance",
                "Cyclone track agency provenance is missing.",
            )
        )
    else:
        cyclone_history = json.loads(cyclone_history_path.read_text(encoding="utf-8"))
        if int(cyclone_history.get("storms", 0)) < MIN_INDEPENDENT_EVENTS:
            findings.append(
                Finding(
                    "ERROR",
                    "history.cyclone_diversity",
                    f"Found {cyclone_history.get('storms', 0)}/{MIN_INDEPENDENT_EVENTS} cyclone tracks.",
                )
            )
        if int(cyclone_history.get("imd_observation_records", 0)) == 0:
            findings.append(
                Finding(
                    "ERROR",
                    "history.cyclone_imd_observations",
                    "No IMD New Delhi agency observations were retained in cyclone history.",
                )
            )
    return findings


def audit_land_context() -> list[Finding]:
    findings = []
    terrain_path = PROJECT_ROOT / "data/silver/susceptibility/terrain.parquet"
    land_cover_path = PROJECT_ROOT / "data/silver/susceptibility/land_cover.parquet"
    if not terrain_path.exists():
        findings.append(Finding("ERROR", "land.terrain", "SRTM terrain context is missing."))
    else:
        terrain = pd.read_parquet(terrain_path)
        sources = terrain.get("terrain_source", pd.Series(dtype=str)).astype(str)
        source_ok = len(sources) == 133 and sources.str.contains("SRTMGL1").all()
        slope_ok = "slope_mean_degrees" in terrain and terrain["slope_mean_degrees"].notna().all()
        if len(terrain) != 133 or not source_ok or not slope_ok:
            findings.append(
                Finding(
                    "ERROR",
                    "land.terrain_contract",
                    "Terrain must cover 133 districts with SRTM elevation and slope.",
                )
            )
    if not land_cover_path.exists():
        findings.append(Finding("ERROR", "land.land_cover", "ESA WorldCover context is missing."))
    else:
        land_cover = pd.read_parquet(land_cover_path)
        if (
            len(land_cover) != 133
            or not land_cover["land_cover_sample_count"].gt(0).all()
            or not land_cover["land_cover_source"].astype(str).str.contains("WorldCover").all()
            or "dominant_land_cover_class" not in land_cover
            or not land_cover["dominant_land_cover_class"].notna().all()
        ):
            findings.append(
                Finding(
                    "ERROR",
                    "land.land_cover_contract",
                    "Land cover must contain valid ESA WorldCover samples for 133 districts.",
                )
            )
    if not findings:
        try:
            from scripts.serving.location_assessment import location_report

            sample = location_report(27.48, 94.91, 7)
            if not sample["context_available"]:
                raise ValueError("point context is unavailable")
        except Exception as error:
            findings.append(
                Finding("ERROR", "land.location_contract", f"Location assessment failed: {error}")
            )
    findings.append(
        Finding(
            "WARNING",
            "vulnerability.scope",
            "Scores cover weather hazard and physical land susceptibility, not people or asset exposure.",
        )
    )
    return findings


def audit_owner_review() -> list[Finding]:
    path = PROJECT_ROOT / "data/quality/production_event_review.csv"
    if not path.exists():
        return [
            Finding(
                "ERROR",
                "owner_review.exists",
                "The production flood/cyclone review package is missing.",
            )
        ]
    review = pd.read_csv(path, keep_default_na=False)
    required = {
        "hazard_type",
        "review_status",
        "event_occurred_in_district",
        "date_correct",
    }
    missing = required - set(review.columns)
    if missing:
        return [
            Finding(
                "ERROR",
                "owner_review.schema",
                "Review package is missing: " + ", ".join(sorted(missing)),
            )
        ]
    status = review["review_status"].astype(str).str.upper().str.strip()
    pending = ~status.isin({"APPROVED", "REJECTED"})
    correctness = review[["event_occurred_in_district", "date_correct"]].apply(
        lambda column: column.astype(str).str.upper().str.strip().isin({"YES", "NO"})
    )
    incomplete = pending | ~correctness.all(axis=1)
    if incomplete.any():
        return [
            Finding(
                "ERROR",
                "owner_review.pending",
                f"{int(incomplete.sum())}/{len(review)} production review rows are incomplete.",
            )
        ]
    occurred = review["event_occurred_in_district"].astype(str).str.upper().str.strip()
    date_correct = review["date_correct"].astype(str).str.upper().str.strip()
    approved = int((status.eq("APPROVED") & occurred.eq("YES") & date_correct.eq("YES")).sum())
    if approved < 20:
        return [
            Finding(
                "ERROR",
                "owner_review.approved",
                f"Only {approved}/20 required cases were approved.",
            )
        ]
    rejected = review.loc[
        status.eq("REJECTED") | occurred.eq("NO") | date_correct.eq("NO")
    ].copy()
    if not rejected.empty:
        ground_truth = pd.read_parquet(
            PROJECT_ROOT / "data/gold/ground_truth.parquet",
            columns=["event_date", "hazard_type", "state", "district", "source_event_id"],
        )
        ground_truth["event_date"] = pd.to_datetime(
            ground_truth["event_date"], utc=True
        ).dt.date.astype(str)
        keys = ["event_date", "hazard_type", "state", "district", "source_event_id"]
        retained = rejected[keys].merge(ground_truth[keys], on=keys, how="inner")
        if not retained.empty:
            return [
                Finding(
                    "ERROR",
                    "owner_review.rebuild",
                    "Rejected review cases remain in canonical ground truth; rebuild it.",
                )
            ]
    return []


def audit_calibrated_probabilities() -> list[Finding]:
    report_path = PROJECT_ROOT / "data/quality/vulnerability_calibration.json"
    probabilities_path = PROJECT_ROOT / "data/serving/district_hazard_probabilities.parquet"
    if not report_path.exists() or not probabilities_path.exists():
        return [
            Finding(
                "ERROR",
                "models.calibrated_artifacts",
                "Calibrated vulnerability report or serving probabilities are missing.",
            )
        ]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    probabilities = pd.read_parquet(probabilities_path)
    required = {
        "state", "district", "horizon_days", "flood_probability", "cyclone_probability",
    }
    missing = required - set(probabilities.columns)
    if missing:
        return [
            Finding(
                "ERROR",
                "models.calibrated_schema",
                "Serving probabilities are missing: " + ", ".join(sorted(missing)),
            )
        ]
    findings = []
    if probabilities[["state", "district"]].drop_duplicates().shape[0] != 133:
        findings.append(
            Finding("ERROR", "models.calibrated_coverage", "Probabilities do not cover 133 districts.")
        )
    if set(probabilities["horizon_days"].astype(int)) != {3, 7, 14}:
        findings.append(
            Finding("ERROR", "models.calibrated_horizons", "Expected 3, 7, and 14 day probabilities.")
        )
    for hazard in ("flood", "cyclone"):
        values = pd.to_numeric(probabilities[f"{hazard}_probability"], errors="coerce")
        if values.isna().any() or not values.between(0, 1).all():
            findings.append(
                Finding(
                    "ERROR", f"models.{hazard}_probability",
                    f"{hazard.title()} probabilities must be complete values from 0 to 1.",
                )
            )
    cyclone_status = report.get("hazards", {}).get("cyclone", {}).get("status")
    if cyclone_status != "production_eligible":
        findings.append(
            Finding(
                "WARNING",
                "models.cyclone_validation",
                "Cyclone probabilities are calibrated but have limited independent-event validation.",
            )
        )
    drought_status = report.get("hazards", {}).get("drought", {}).get("status")
    if drought_status != "production_eligible":
        findings.append(
            Finding(
                "WARNING",
                "models.drought_calibration",
                "Drought probability remains unavailable because events do not span temporal partitions.",
            )
        )
    return findings


def audit_automation() -> list[Finding]:
    findings = []
    scheduler = Path.home() / "Library/LaunchAgents/com.susbiome.refresh.plist"
    refresh = PROJECT_ROOT / "data/logs/operations/refresh.json"
    backups = sorted((PROJECT_ROOT / "data/backups/operations").glob("*.tar.gz"))
    if not scheduler.exists():
        findings.append(
            Finding("ERROR", "automation.scheduler", "The daily launchd scheduler is not installed.")
        )
    if not refresh.exists():
        findings.append(
            Finding("ERROR", "automation.refresh", "No verified automated refresh record exists.")
        )
    elif json.loads(refresh.read_text(encoding="utf-8")).get("status") != "complete":
        findings.append(Finding("ERROR", "automation.refresh", "The latest automated refresh failed."))
    if not backups:
        findings.append(Finding("ERROR", "automation.backup", "No operational backup exists."))
    return findings


def audit_sources() -> list[Finding]:
    findings = []
    era5 = list((PROJECT_ROOT / "data/silver/weather/era5").glob("year=*/*.parquet"))
    gpm = list((PROJECT_ROOT / "data/silver/weather/gpm").glob("year=*/gpm_*.parquet"))
    import pyarrow.parquet as pq

    required_era5 = {
        "soil_moisture_surface", "soil_moisture_root_zone", "runoff",
        "potential_evaporation",
    }
    valid_era5 = sum(
        required_era5.issubset(set(pq.ParquetFile(path).schema.names))
        for path in era5
    )
    if valid_era5 < 240:
        findings.append(
            Finding(
                "ERROR", "sources.era5",
                f"Found {valid_era5}/240 complete monthly partitions ({len(era5)} total).",
            )
        )
    if len(gpm) < GPM_EXPECTED_DAYS:
        findings.append(
            Finding(
                "ERROR",
                "sources.gpm",
                f"Found {len(gpm)}/{GPM_EXPECTED_DAYS} available daily partitions.",
            )
        )
    ground_truth = PROJECT_ROOT / "data/gold/ground_truth.parquet"
    if not ground_truth.exists():
        findings.append(Finding("ERROR", "ground_truth.exists", "Canonical ground truth is missing."))
    else:
        events = pd.read_parquet(
            ground_truth, columns=["hazard_type", "source", "source_event_id"]
        )
        counts = events["hazard_type"].value_counts().to_dict() if not events.empty else {}
        production_hazards = {"FLOOD", "CYCLONE"}
        for hazard in ("FLOOD", "DROUGHT", "CYCLONE"):
            if int(counts.get(hazard, 0)) < MIN_POSITIVE_SAMPLES:
                findings.append(
                    Finding(
                        "ERROR" if hazard in production_hazards else "WARNING",
                        f"ground_truth.{hazard.lower()}",
                        f"Found {int(counts.get(hazard, 0))}/{MIN_POSITIVE_SAMPLES} verified events.",
                    )
                )
            hazard_events = events.loc[events["hazard_type"].eq(hazard)].copy()
            hazard_events["source_event_id"] = (
                hazard_events["source_event_id"].fillna("").astype(str).str.strip()
            )
            independent = hazard_events.loc[
                hazard_events["source_event_id"].ne(""), ["source", "source_event_id"]
            ].drop_duplicates()
            if len(independent) < MIN_INDEPENDENT_EVENTS:
                findings.append(
                    Finding(
                        "WARNING",
                        f"ground_truth.{hazard.lower()}_diversity",
                        f"Found {len(independent)}/{MIN_INDEPENDENT_EVENTS} independent source events.",
                    )
                )
    return findings


def run(training_path: Path = TRAINING_DATASET) -> dict:
    assessment_manifest = PROJECT_ROOT / "data/serving/district_assessment_manifest.json"
    weather_mode = False
    calibrated_mode = False
    if assessment_manifest.exists():
        payload = json.loads(assessment_manifest.read_text(encoding="utf-8"))
        method = payload.get("assessment_method")
        weather_mode = method in {
            "weather_pattern_index_v1",
            "weather_land_index_v2",
        }
        calibrated_mode = method == "calibrated_weather_land_probability_v3"
    findings = [
        *audit_sources(),
        *audit_operational(),
        *audit_land_context(),
        *audit_owner_review(),
        *audit_confirmations(),
        *audit_automation(),
    ]
    if calibrated_mode:
        findings.extend(audit_calibrated_probabilities())
    elif weather_mode:
        findings.append(
            Finding(
                "WARNING",
                "models.scope",
                "ML probabilities are not required for the weather-pattern outlook.",
            )
        )
    else:
        findings.extend([*audit_training(training_path), *audit_models()])
    return {
        "ready": not any(item.severity == "ERROR" for item in findings),
        "findings": [asdict(item) for item in findings],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit SusBiome production artifacts.")
    parser.add_argument("--training-path", type=Path, default=TRAINING_DATASET)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    report = run(arguments.training_path)
    if arguments.json:
        print(json.dumps(report, indent=2))
    else:
        print("READY" if report["ready"] else "NOT READY")
        for finding in report["findings"]:
            print(f"[{finding['severity']}] {finding['check']}: {finding['message']}")
    raise SystemExit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
