"""Collect reproducible 14-day district weather forecasts from Open-Meteo."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from scripts.sources.common.config import PROJECT_ROOT

LOCATIONS_PATH = PROJECT_ROOT / "data/raw/locations.csv"
OUTPUT_PATH = PROJECT_ROOT / "data/silver/forecast/district_daily.parquet"
HORIZONS_PATH = PROJECT_ROOT / "data/silver/forecast/district_horizons.parquet"
MANIFEST_PATH = PROJECT_ROOT / "data/silver/forecast/manifest.json"
ENDPOINT = "https://api.open-meteo.com/v1/forecast"
DAILY_VARIABLES = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "et0_fao_evapotranspiration",
)
HORIZONS = (3, 7, 14)


def _atomic_parquet(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    dataframe.to_parquet(temporary, index=False)
    os.replace(temporary, path)


class OpenMeteoForecastCollector:
    """Fetch all district points in bounded multi-location requests."""

    def __init__(self, session: requests.Session | None = None, batch_size: int = 40) -> None:
        self.session = session or requests.Session()
        self.batch_size = batch_size

    @staticmethod
    def locations(path: str | Path = LOCATIONS_PATH) -> pd.DataFrame:
        locations = pd.read_csv(path)
        required = {"state", "district", "latitude", "longitude"}
        missing = required - set(locations.columns)
        if missing:
            raise ValueError("Location registry is missing: " + ", ".join(sorted(missing)))
        if locations.duplicated(["state", "district"]).any():
            raise ValueError("Location registry contains duplicate districts.")
        return locations.sort_values(["state", "district"]).reset_index(drop=True)

    def _request(self, locations: pd.DataFrame) -> list[dict]:
        params = {
            "latitude": ",".join(locations["latitude"].astype(str)),
            "longitude": ",".join(locations["longitude"].astype(str)),
            "daily": ",".join(DAILY_VARIABLES),
            "timezone": "Asia/Kolkata",
            "forecast_days": 14,
        }
        error: Exception | None = None
        for attempt in range(4):
            try:
                response = self.session.get(ENDPOINT, params=params, timeout=90)
                response.raise_for_status()
                payload = response.json()
                results = payload if isinstance(payload, list) else [payload]
                if len(results) != len(locations):
                    raise ValueError(
                        f"Forecast response has {len(results)} locations; expected {len(locations)}."
                    )
                return results
            except (requests.RequestException, ValueError) as caught:
                error = caught
                if attempt < 3:
                    time.sleep(2**attempt)
        raise RuntimeError(f"Forecast provider failed after retries: {error}") from error

    @staticmethod
    def _rows(location: pd.Series, payload: dict, collected_at: str) -> list[dict]:
        daily = payload.get("daily", {})
        dates = daily.get("time", [])
        if len(dates) != 14:
            raise ValueError(
                f"{location['district']} forecast has {len(dates)} days; expected 14."
            )
        rows = []
        for index, valid_date in enumerate(dates):
            row = {
                "state": location["state"],
                "district": location["district"],
                "latitude": float(location["latitude"]),
                "longitude": float(location["longitude"]),
                "valid_date": pd.Timestamp(valid_date),
                "lead_day": index + 1,
                "provider": "Open-Meteo",
                "model": "best_match",
                "spatial_support": "representative_point",
                "collected_at": collected_at,
                "provider_elevation_m": payload.get("elevation"),
            }
            for variable in DAILY_VARIABLES:
                values = daily.get(variable)
                if not isinstance(values, list) or len(values) != len(dates):
                    raise ValueError(f"Forecast response is missing complete {variable} values.")
                row[variable] = values[index]
            rows.append(row)
        return rows

    @staticmethod
    def build_horizons(daily: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for (state, district), group in daily.groupby(["state", "district"], sort=True):
            group = group.sort_values("lead_day")
            for horizon in HORIZONS:
                window = group.loc[group["lead_day"].le(horizon)]
                rows.append(
                    {
                        "state": state,
                        "district": district,
                        "latitude": float(window["latitude"].iloc[0]),
                        "longitude": float(window["longitude"].iloc[0]),
                        "horizon_days": horizon,
                        "valid_from": window["valid_date"].min(),
                        "valid_to": window["valid_date"].max(),
                        "precipitation_sum_mm": float(window["precipitation_sum"].sum()),
                        "precipitation_probability_max": float(
                            window["precipitation_probability_max"].max()
                        ),
                        "temperature_max_c": float(window["temperature_2m_max"].max()),
                        "temperature_min_c": float(window["temperature_2m_min"].min()),
                        "wind_speed_max_kmh": float(window["wind_speed_10m_max"].max()),
                        "wind_gust_max_kmh": float(window["wind_gusts_10m_max"].max()),
                        "et0_sum_mm": float(window["et0_fao_evapotranspiration"].sum()),
                        "provider": "Open-Meteo",
                        "model": "best_match",
                        "spatial_support": "representative_point",
                        "collected_at": window["collected_at"].iloc[0],
                    }
                )
        return pd.DataFrame(rows)

    def collect(
        self,
        output_path: str | Path = OUTPUT_PATH,
        horizons_path: str | Path = HORIZONS_PATH,
    ) -> dict:
        locations = self.locations()
        collected_at = datetime.now(UTC).isoformat()
        rows = []
        batches = 0
        for start in range(0, len(locations), self.batch_size):
            batch = locations.iloc[start : start + self.batch_size]
            payloads = self._request(batch)
            for (_, location), payload in zip(batch.iterrows(), payloads, strict=True):
                rows.extend(self._rows(location, payload, collected_at))
            batches += 1
        daily = pd.DataFrame(rows).sort_values(["state", "district", "valid_date"])
        if len(daily) != len(locations) * 14:
            raise ValueError("Forecast output failed the district-by-day completeness check.")
        horizons = self.build_horizons(daily)
        if len(horizons) != len(locations) * len(HORIZONS):
            raise ValueError("Forecast horizon output failed its completeness check.")
        _atomic_parquet(daily, Path(output_path))
        _atomic_parquet(horizons, Path(horizons_path))
        manifest = {
            "collected_at": collected_at,
            "provider": "Open-Meteo",
            "endpoint": ENDPOINT,
            "model": "best_match",
            "districts": len(locations),
            "daily_rows": len(daily),
            "horizon_rows": len(horizons),
            "batches": batches,
            "horizons_days": list(HORIZONS),
            "spatial_support": "representative_point",
            "output": str(Path(output_path)),
            "horizons_output": str(Path(horizons_path)),
        }
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "status"), nargs="?", default="collect")
    arguments = parser.parse_args()
    if arguments.command == "collect":
        result = OpenMeteoForecastCollector().collect()
    else:
        if not MANIFEST_PATH.exists():
            raise SystemExit("Forecast manifest does not exist. Run collect first.")
        result = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
