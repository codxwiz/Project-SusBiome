"""Resumable historical ERA5 and NASA GPM collection for Northeast India."""

from __future__ import annotations

import argparse
import calendar
import json
import logging
import os
import tempfile
import zipfile
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlparse

import cdsapi
import numpy as np
import pandas as pd
import requests
import xarray as xr

from scripts.fusion.models import NORTHEAST_INDIA_BOUNDS
from scripts.sources.common.config import EARTHDATA_TOKEN, PROJECT_ROOT

logger = logging.getLogger("susbiome.ingestion.historical")

ERA5_DATASET = "reanalysis-era5-single-levels"
ERA5_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "surface_pressure",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "runoff",
    "potential_evaporation",
]
GPM_SHORT_NAME = "GPM_3IMERGDF"
GPM_LATE_SHORT_NAME = "GPM_3IMERGDL"
GPM_VERSION = "07"
GPM_EXPECTED_DAYS = 7_213
GPM_AVAILABLE_THROUGH = date(2025, 9, 30)
CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"

BRONZE_ERA5 = PROJECT_ROOT / "data/bronze/era5/historical"
BRONZE_GPM = PROJECT_ROOT / "data/bronze/nasa/gpm/historical"
BRONZE_GPM_LATE = PROJECT_ROOT / "data/bronze/nasa/gpm/late"
SILVER_ERA5 = PROJECT_ROOT / "data/silver/weather/era5"
SILVER_GPM = PROJECT_ROOT / "data/silver/weather/gpm"
SILVER_GPM_LATE = PROJECT_ROOT / "data/silver/weather/gpm_late"
LOG_DIR = PROJECT_ROOT / "data/logs/ingestion"


@dataclass(slots=True)
class CollectionStats:
    requested: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    downloaded_bytes: int = 0


def process_running(pid: int) -> bool:
    """Return whether a PID exists, including processes hidden by permissions."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_owner_pid(lock: Path) -> int | None:
    owner = lock.read_text(encoding="utf-8", errors="ignore")
    for field in owner.split():
        if field.startswith("pid="):
            try:
                return int(field.removeprefix("pid="))
            except ValueError:
                return None
    return None


@contextmanager
def collector_lock(provider: str):
    """Prevent two collectors from writing the same provider partitions."""
    lock = LOG_DIR / f"{provider}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        owner = lock.read_text(encoding="utf-8", errors="ignore")
        pid = lock_owner_pid(lock)
        if pid is not None and not process_running(pid):
            lock.unlink(missing_ok=True)
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        else:
            raise RuntimeError(
                f"{provider} collector lock already exists ({owner})."
            ) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()} started={datetime.now(UTC).isoformat()}")
        yield
    finally:
        lock.unlink(missing_ok=True)


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=os.getenv("SUSBIOME_LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "historical_weather.log"),
        ],
    )


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def month_periods(start: date, end: date):
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield year, month
        month += 1
        if month == 13:
            year, month = year + 1, 1


def date_periods(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def era5_request(
    year: int,
    month: int,
    *,
    start_day: int = 1,
    end_day: int | None = None,
) -> dict:
    final_day = calendar.monthrange(year, month)[1]
    end_day = final_day if end_day is None else end_day
    if not 1 <= start_day <= end_day <= final_day:
        raise ValueError(f"Invalid ERA5 day range for {year:04d}-{month:02d}.")
    bounds = NORTHEAST_INDIA_BOUNDS
    return {
        "product_type": ["reanalysis"],
        "variable": ERA5_VARIABLES,
        "year": [f"{year:04d}"],
        "month": [f"{month:02d}"],
        "day": [f"{day:02d}" for day in range(start_day, end_day + 1)],
        "time": [f"{hour:02d}:00" for hour in range(24)],
        "area": [
            bounds["max_latitude"],
            bounds["min_longitude"],
            bounds["min_latitude"],
            bounds["max_longitude"],
        ],
        "data_format": "netcdf",
        "download_format": "unarchived",
    }


def _coordinate_name(dataset: xr.Dataset, *candidates: str) -> str:
    for candidate in candidates:
        if candidate in dataset.coords or candidate in dataset.dims:
            return candidate
    raise ValueError(f"Missing coordinate; expected one of {candidates}.")


def parse_era5_month(
    source: Path,
    destination: Path,
    *,
    expected_days: int | None = None,
) -> Path:
    """Convert hourly ERA5 into daily analysis-grid observations."""
    if zipfile.is_zipfile(source):
        with tempfile.TemporaryDirectory(prefix="susbiome-era5-") as directory:
            root = Path(directory)
            with zipfile.ZipFile(source) as archive:
                members = [
                    member
                    for member in archive.namelist()
                    if member.endswith((".nc", ".nc4"))
                    and ".." not in Path(member).parts
                ]
                if not members:
                    raise ValueError("ERA5 ZIP contains no NetCDF members.")
                archive.extractall(root, members=members)
            datasets = []
            for member in members:
                with xr.open_dataset(root / member) as opened:
                    datasets.append(opened.load())
            dataset = xr.merge(datasets, compat="override", join="exact")
    else:
        with xr.open_dataset(source) as opened:
            dataset = opened.load()

    time_name = _coordinate_name(dataset, "valid_time", "time")
    latitude_name = _coordinate_name(dataset, "latitude", "lat")
    longitude_name = _coordinate_name(dataset, "longitude", "lon")
    dataset = dataset.rename(
        {time_name: "valid_time", latitude_name: "latitude", longitude_name: "longitude"}
    )

    required_variables = ("t2m", "d2m", "sp", "u10", "v10", "tp", "swvl1", "swvl2", "ro", "pev")
    missing = [name for name in required_variables if name not in dataset]
    if missing:
        raise ValueError("ERA5 response is missing variables: " + ", ".join(missing))

    wind = np.hypot(dataset["u10"], dataset["v10"])
    temperature_c = dataset["t2m"] - 273.15
    dewpoint_c = dataset["d2m"] - 273.15
    relative_humidity = 100.0 * np.exp(
        (17.625 * dewpoint_c / (243.04 + dewpoint_c))
        - (17.625 * temperature_c / (243.04 + temperature_c))
    )

    daily = xr.Dataset(
        {
            "temperature": dataset["t2m"].resample(valid_time="1D").mean(),
            "temperature_min": dataset["t2m"].resample(valid_time="1D").min(),
            "temperature_max": dataset["t2m"].resample(valid_time="1D").max(),
            "dewpoint": dataset["d2m"].resample(valid_time="1D").mean(),
            "relative_humidity": relative_humidity.resample(valid_time="1D").mean().clip(0, 100),
            "surface_pressure_hpa": dataset["sp"].resample(valid_time="1D").mean() / 100.0,
            "wind_speed": wind.resample(valid_time="1D").mean(),
            "wind_speed_max": wind.resample(valid_time="1D").max(),
            "precipitation_era5": dataset["tp"].resample(valid_time="1D").sum() * 1000.0,
            "soil_moisture_surface": dataset["swvl1"].resample(valid_time="1D").mean(),
            "soil_moisture_root_zone": dataset["swvl2"].resample(valid_time="1D").mean(),
            "runoff": dataset["ro"].resample(valid_time="1D").sum() * 1000.0,
            "potential_evaporation": -dataset["pev"].resample(valid_time="1D").sum() * 1000.0,
        }
    )
    frame = daily.to_dataframe().reset_index()
    frame["longitude"] = ((frame["longitude"] + 180) % 360) - 180
    frame["value"] = frame["temperature"]
    frame["precipitation"] = frame["precipitation_era5"].clip(lower=0)
    frame = frame[
        [
            "valid_time", "latitude", "longitude", "temperature",
            "temperature_min", "temperature_max", "dewpoint",
            "relative_humidity", "surface_pressure_hpa", "wind_speed",
            "wind_speed_max", "precipitation_era5", "value", "precipitation",
            "soil_moisture_surface", "soil_moisture_root_zone", "runoff",
            "potential_evaporation",
        ]
    ]
    frame = frame.sort_values(["valid_time", "latitude", "longitude"])

    minimum_days = 28 if expected_days is None else expected_days
    if frame.empty or frame["valid_time"].nunique() < minimum_days:
        raise ValueError("ERA5 monthly parse produced insufficient daily coverage.")
    if frame.isna().any().any():
        raise ValueError("ERA5 monthly parse contains missing values.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + f".tmp.{uuid.uuid4().hex}")
    frame.to_parquet(temporary, index=False, compression="snappy")
    temporary.replace(destination)
    return destination


class ERA5HistoricalCollector:
    def __init__(self, *, delete_raw: bool = False) -> None:
        self.client = cdsapi.Client(quiet=False)
        self.delete_raw = delete_raw
        self.stats = CollectionStats()
        self.checkpoint = LOG_DIR / "era5_checkpoint.json"

    def collect_month(
        self,
        year: int,
        month: int,
        *,
        start_day: int = 1,
        end_day: int | None = None,
    ) -> Path:
        final_day = calendar.monthrange(year, month)[1]
        end_day = final_day if end_day is None else end_day
        expected_days = end_day - start_day + 1
        output = SILVER_ERA5 / f"year={year:04d}" / f"month={month:02d}.parquet"
        if output.exists() and output.stat().st_size > 0:
            import pyarrow.parquet as pq

            schema = set(pq.ParquetFile(output).schema.names)
            required = {
                "soil_moisture_surface", "soil_moisture_root_zone", "runoff",
                "potential_evaporation",
            }
            rows = pq.ParquetFile(output).metadata.num_rows
            if required.issubset(schema) and rows >= expected_days * 2_021:
                self.stats.skipped += 1
                return output

        suffix = "" if start_day == 1 and end_day == final_day else f"_{start_day:02d}-{end_day:02d}"
        raw = BRONZE_ERA5 / f"year={year:04d}" / f"era5_{year:04d}_{month:02d}{suffix}.nc"
        raw.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            request = era5_request(
                year, month, start_day=start_day, end_day=end_day
            )
            self.client.retrieve(ERA5_DATASET, request, str(raw))
            self.stats.downloaded_bytes += raw.stat().st_size

        parse_era5_month(raw, output, expected_days=expected_days)
        if self.delete_raw:
            raw.unlink(missing_ok=True)
        self.stats.completed += 1
        atomic_json(
            self.checkpoint,
            {"updated_at": datetime.now(UTC), "last_month": f"{year:04d}-{month:02d}", **asdict(self.stats)},
        )
        return output

    def run(self, start: date, end: date, *, max_items: int | None = None) -> CollectionStats:
        periods = list(month_periods(start, end))
        if max_items is not None:
            periods = periods[:max_items]
        self.stats.requested = len(periods)
        for year, month in periods:
            try:
                logger.info("ERA5 %04d-%02d", year, month)
                first_day = start.day if (year, month) == (start.year, start.month) else 1
                last_day = (
                    end.day
                    if (year, month) == (end.year, end.month)
                    else calendar.monthrange(year, month)[1]
                )
                self.collect_month(
                    year, month, start_day=first_day, end_day=last_day
                )
            except Exception:
                self.stats.failed += 1
                logger.exception("ERA5 failed for %04d-%02d", year, month)
                atomic_json(self.checkpoint, {"updated_at": datetime.now(UTC), **asdict(self.stats)})
        return self.stats


class GPMHistoricalCollector:
    def __init__(
        self,
        *,
        delete_raw: bool = True,
        short_name: str = GPM_SHORT_NAME,
        bronze_root: Path = BRONZE_GPM,
        silver_root: Path = SILVER_GPM,
        checkpoint_name: str = "gpm_checkpoint.json",
        product: str = "IMERG_FINAL_V07B",
    ) -> None:
        if not EARTHDATA_TOKEN:
            raise RuntimeError("EARTHDATA_TOKEN is required for NASA GPM collection.")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {EARTHDATA_TOKEN}"})
        self.delete_raw = delete_raw
        self.short_name = short_name
        self.bronze_root = bronze_root
        self.silver_root = silver_root
        self.product = product
        self.stats = CollectionStats()
        self.checkpoint = LOG_DIR / checkpoint_name

    def discover_month(self, year: int, month: int) -> list[dict]:
        final_day = calendar.monthrange(year, month)[1]
        start = datetime.combine(date(year, month, 1), time.min).isoformat() + "Z"
        end = datetime.combine(date(year, month, final_day), time.max).isoformat() + "Z"
        response = self.session.get(
            CMR_URL,
            params={
                "short_name": self.short_name,
                "version": GPM_VERSION,
                "temporal": f"{start},{end}",
                "page_size": 2000,
            },
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["feed"]["entry"]

    @staticmethod
    def _download_url(entry: dict) -> str:
        for link in entry.get("links", []):
            if link.get("rel", "").endswith("/data#") and str(link.get("href", "")).startswith("https://"):
                return link["href"]
        raise ValueError(f"No HTTPS data link for {entry.get('id')}.")

    @staticmethod
    def _opendap_url(entry: dict) -> str:
        for link in entry.get("links", []):
            if (
                str(link.get("title", "")).startswith("OPeNDAP request URL")
                and str(link.get("href", "")).startswith("https://")
            ):
                return link["href"]
        raise ValueError(f"No OPeNDAP service link for {entry.get('id')}.")

    @classmethod
    def _subset_url(cls, entry: dict) -> str:
        # IMERG V07 daily grid: lon/lat start at -179.95/-89.95 with 0.1 degree spacing.
        projection = (
            "precipitation[0:1:0][2670:1:2784][1100:1:1204],"
            "lon[2670:1:2784],lat[1100:1:1204],time[0:1:0]"
        )
        return cls._opendap_url(entry) + ".nc4?" + projection

    @staticmethod
    def _event_date(entry: dict) -> date:
        return datetime.fromisoformat(entry["time_start"].replace("Z", "+00:00")).date()

    def download(self, entry: dict, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(
            destination.suffix + f".part.{os.getpid()}.{uuid.uuid4().hex}"
        )
        with self.session.get(self._subset_url(entry), stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        if temporary.stat().st_size < 1024:
            temporary.unlink(missing_ok=True)
            raise IOError("NASA returned an unexpectedly small granule.")
        temporary.replace(destination)
        self.stats.downloaded_bytes += destination.stat().st_size

    def parse_day(self, source: Path, destination: Path) -> Path:
        bounds = NORTHEAST_INDIA_BOUNDS
        with xr.open_dataset(source) as dataset:
            subset = dataset["precipitation"].sel(
                lon=slice(bounds["min_longitude"], bounds["max_longitude"]),
                lat=slice(bounds["min_latitude"], bounds["max_latitude"]),
            ).load()
        frame = subset.to_dataframe(name="precipitation_gpm").reset_index()
        frame = frame.rename(columns={"time": "valid_time", "lon": "longitude", "lat": "latitude"})
        frame["longitude"] = (frame["longitude"] / 0.25).round() * 0.25
        frame["latitude"] = (frame["latitude"] / 0.25).round() * 0.25
        frame["valid_time"] = pd.to_datetime(frame["valid_time"], utc=True).dt.normalize()
        frame = frame.groupby(
            ["valid_time", "latitude", "longitude"], as_index=False
        )["precipitation_gpm"].mean()
        frame["precipitation_gpm"] = frame["precipitation_gpm"].clip(lower=0)
        frame["precipitation_product"] = self.product
        if frame.empty or frame["precipitation_gpm"].isna().any():
            raise ValueError("GPM regional parse is empty or incomplete.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + f".tmp.{uuid.uuid4().hex}")
        frame.to_parquet(temporary, index=False, compression="snappy")
        temporary.replace(destination)
        return destination

    def collect_entry(self, entry: dict) -> Path:
        day = self._event_date(entry)
        output = self.silver_root / f"year={day.year:04d}" / f"gpm_{day:%Y%m%d}.parquet"
        if output.exists() and output.stat().st_size > 0:
            import pyarrow.parquet as pq

            parquet = pq.ParquetFile(output)
            if (
                "precipitation_gpm" in parquet.schema.names
                and parquet.metadata.num_rows == 2_021
            ):
                self.stats.skipped += 1
                return output
        url = self._download_url(entry)
        filename = Path(urlparse(url).path).name.replace(".nc4", ".subset.nc4")
        raw = self.bronze_root / f"year={day.year:04d}" / f"month={day.month:02d}" / filename
        if not raw.exists():
            self.download(entry, raw)
        try:
            self.parse_day(raw, output)
        except Exception:
            raw.unlink(missing_ok=True)
            raise
        if self.delete_raw:
            raw.unlink(missing_ok=True)
        self.stats.completed += 1
        atomic_json(
            self.checkpoint,
            {"updated_at": datetime.now(UTC), "last_date": day, **asdict(self.stats)},
        )
        return output

    def run(self, start: date, end: date, *, max_items: int | None = None) -> CollectionStats:
        remaining = max_items
        self.stats.requested = (end - start).days + 1 if max_items is None else max_items
        for year, month in month_periods(start, end):
            try:
                entries = self.discover_month(year, month)
            except Exception:
                logger.exception("GPM discovery failed for %04d-%02d", year, month)
                self.stats.failed += calendar.monthrange(year, month)[1]
                continue
            for entry in entries:
                event_date = self._event_date(entry)
                if not start <= event_date <= end:
                    continue
                if remaining is not None and remaining <= 0:
                    return self.stats
                try:
                    logger.info("GPM %s", event_date)
                    self.collect_entry(entry)
                except Exception:
                    self.stats.failed += 1
                    logger.exception("GPM failed for %s", event_date)
                if remaining is not None:
                    remaining -= 1
        return self.stats


def status() -> dict:
    era5_files = list(SILVER_ERA5.glob("year=*/*.parquet"))
    valid_era5 = 0
    if era5_files:
        import pyarrow.parquet as pq

        required = {
            "soil_moisture_surface", "soil_moisture_root_zone", "runoff",
            "potential_evaporation",
        }
        valid_era5 = sum(
            required.issubset(set(pq.ParquetFile(path).schema.names))
            for path in era5_files
        )
    return {
        "era5_months": len(era5_files),
        "era5_valid_months": valid_era5,
        "gpm_days": len(list(SILVER_GPM.glob("year=*/gpm_*.parquet"))),
        "gpm_late_days": len(list(SILVER_GPM_LATE.glob("year=*/gpm_*.parquet"))),
        "era5_checkpoint": json.loads((LOG_DIR / "era5_checkpoint.json").read_text())
        if (LOG_DIR / "era5_checkpoint.json").exists() else None,
        "gpm_checkpoint": json.loads((LOG_DIR / "gpm_checkpoint.json").read_text())
        if (LOG_DIR / "gpm_checkpoint.json").exists() else None,
        "gpm_late_checkpoint": json.loads((LOG_DIR / "gpm_late_checkpoint.json").read_text())
        if (LOG_DIR / "gpm_late_checkpoint.json").exists() else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "provider", choices=["era5", "gpm", "gpm-late", "all", "status"]
    )
    parser.add_argument("--start", type=date.fromisoformat, default=date(2006, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--keep-raw", action="store_true")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    arguments = parse_args()
    if arguments.start > arguments.end:
        raise SystemExit("--start must not be after --end")
    if arguments.provider == "status":
        print(json.dumps(status(), indent=2, default=str))
        return
    results = {}
    if arguments.provider in {"era5", "all"}:
        with collector_lock("era5"):
            results["era5"] = asdict(
                ERA5HistoricalCollector(delete_raw=not arguments.keep_raw).run(
                    arguments.start, arguments.end, max_items=arguments.max_items
                )
            )
    if arguments.provider in {"gpm", "all"}:
        with collector_lock("gpm"):
            results["gpm"] = asdict(
                GPMHistoricalCollector(delete_raw=not arguments.keep_raw).run(
                    arguments.start, arguments.end, max_items=arguments.max_items
                )
            )
    if arguments.provider == "gpm-late":
        with collector_lock("gpm-late"):
            results["gpm-late"] = asdict(
                GPMHistoricalCollector(
                    delete_raw=not arguments.keep_raw,
                    short_name=GPM_LATE_SHORT_NAME,
                    bronze_root=BRONZE_GPM_LATE,
                    silver_root=SILVER_GPM_LATE,
                    checkpoint_name="gpm_late_checkpoint.json",
                    product="IMERG_LATE_V07B",
                ).run(arguments.start, arguments.end, max_items=arguments.max_items)
            )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
