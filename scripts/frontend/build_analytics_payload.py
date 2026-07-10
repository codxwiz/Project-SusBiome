from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "gold" / "ground_truth.parquet"
DISTRICT_EVENTS_PATH = PROJECT_ROOT / "data" / "gold" / "events" / "district_events.csv"
ASSESSMENTS_PATH = PROJECT_ROOT / "data" / "serving" / "district_assessments.parquet"
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "lib" / "analyticsPayload.json"

HAZARD_COLORS = {
    "Flood": "#2c63e4",
    "Drought": "#c77c10",
    "Cyclone": "#f1c84b",
}

HAZARD_LABELS = {
    "FLOOD": "Flood",
    "DROUGHT": "Drought",
    "CYCLONE": "Cyclone",
}


def compact_number(value: int | float) -> str:
    value = int(round(float(value)))
    if value >= 10_000_000:
        return f"{value / 10_000_000:.2f} Cr"
    if value >= 100_000:
        return f"{value / 100_000:.2f} L"
    return f"{value:,}"


def load_ground_truth() -> pd.DataFrame:
    events = pd.read_parquet(GROUND_TRUTH_PATH).copy()
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce", utc=True)
    if "verified" in events.columns:
        events = events[events["verified"].fillna(False)]
    events["hazard_label"] = (
        events["hazard_type"].astype(str).str.upper().map(HAZARD_LABELS).fillna(events["hazard_type"].astype(str).str.title())
    )
    return events.dropna(subset=["event_date", "hazard_label"])


def load_supplemental_district_events() -> pd.DataFrame:
    if not DISTRICT_EVENTS_PATH.exists():
        return pd.DataFrame(columns=["event_date", "hazard_label", "state", "district", "source"])

    events = pd.read_csv(DISTRICT_EVENTS_PATH).copy()
    events = events[
        events["district"].notna()
        & (events["district"].astype(str).str.upper() != "UNKNOWN")
        & (events["match_method"].astype(str) == "district_name")
    ]
    if events.empty:
        return pd.DataFrame(columns=["event_date", "hazard_label", "state", "district", "source"])

    return pd.DataFrame(
        {
            "event_date": pd.to_datetime(events["date"], errors="coerce", utc=True),
            "hazard_label": events["event_type"].astype(str).str.upper().map(HAZARD_LABELS),
            "state": events["state"],
            "district": events["district"],
            "source": events["source"],
        }
    ).dropna(subset=["event_date", "hazard_label"])


def load_events() -> pd.DataFrame:
    events = pd.concat([load_ground_truth(), load_supplemental_district_events()], ignore_index=True)
    events = events[events["hazard_label"].isin(HAZARD_COLORS)]
    return events.sort_values("event_date").reset_index(drop=True)


def build_event_series(events: pd.DataFrame) -> tuple[list[list[int]], dict[str, list[list[int]]]]:
    years = list(range(int(events["event_date"].dt.year.min()), int(events["event_date"].dt.year.max()) + 1))
    by_year = events.groupby(events["event_date"].dt.year).size()
    events_by_year = [[year, int(by_year.get(year, 0))] for year in years]

    hazard_series: dict[str, list[list[int]]] = {}
    for hazard in [label for label in HAZARD_COLORS if label in set(events["hazard_label"])]:
        hazard_events = events[events["hazard_label"] == hazard]
        counts = hazard_events.groupby(hazard_events["event_date"].dt.year).size()
        hazard_series[hazard] = [[year, int(counts.get(year, 0))] for year in years]
    return events_by_year, hazard_series


def build_top_districts(events: pd.DataFrame) -> list[list[str | int]]:
    assessments = pd.read_parquet(ASSESSMENTS_PATH).copy()
    horizon = int(assessments["horizon_days"].max())
    current = assessments[assessments["horizon_days"] == horizon].copy()

    score_columns = {
        "Flood": "flood_weather_risk_score",
        "Drought": "drought_weather_risk_score",
        "Cyclone": "cyclone_weather_risk_score",
    }
    for column in score_columns.values():
        current[column] = pd.to_numeric(current[column], errors="coerce").fillna(0)

    current["composite_risk"] = current[list(score_columns.values())].max(axis=1)
    current_year_events = events[events["event_date"].dt.year == 2026]
    event_counts = (
        current_year_events.dropna(subset=["state", "district"])
        .groupby(["state", "district"])
        .size()
        .rename("total_events")
        .reset_index()
    )
    current = current.merge(event_counts, on=["state", "district"], how="left")
    current["total_events"] = current["total_events"].fillna(0).astype(int)

    ranked = current[current["total_events"] > 0]
    if ranked.empty:
        ranked = current
    top = ranked.sort_values("composite_risk", ascending=False).head(8)
    return [
        [
            str(row.district),
            str(row.state),
            int(round(float(row.composite_risk))),
            int(row.total_events),
        ]
        for row in top.itertuples(index=False)
    ]


def build_payload() -> dict:
    events = load_events()
    events_by_year, hazard_series = build_event_series(events)

    hazard_totals = events["hazard_label"].value_counts().to_dict()
    hazard_config = {
        hazard: {"color": HAZARD_COLORS[hazard], "total": int(hazard_totals[hazard])}
        for hazard in HAZARD_COLORS
        if hazard in hazard_totals
    }

    assessments = pd.read_parquet(ASSESSMENTS_PATH, columns=["state", "district"]).drop_duplicates()
    unique_event_districts = events[["state", "district"]].dropna().drop_duplicates().shape[0]
    unique_states = int(events["state"].dropna().nunique())
    return {
        "generatedFrom": [
            "data/gold/ground_truth.parquet",
            "data/gold/events/district_events.csv",
            "data/serving/district_assessments.parquet",
        ],
        "latestEventDate": events["event_date"].max().date().isoformat(),
        "topDistrictEventYear": 2026,
        "kpis": [
            ["Stored events", compact_number(len(events))],
            ["Event districts", compact_number(unique_event_districts)],
            ["States", compact_number(unique_states)],
            ["Serving districts", compact_number(len(assessments))],
        ],
        "eventsByYear": events_by_year,
        "hazardConfig": hazard_config,
        "hazardSeries": hazard_series,
        "stateCounts": [[state, int(value)] for state, value in events["state"].value_counts().items()],
        "topDistricts": build_top_districts(events),
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(build_payload(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
