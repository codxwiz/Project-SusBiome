# Project SusBiome

SusBiome is a district weather-risk outlook for Northeast India. It combines
weather observations, satellite precipitation, and 20-year district patterns
to publish explainable flood, drought, and cyclone risk indices.

## Pipeline

```text
ERA5 / NASA GPM / IMD -> Bronze -> Silver -> Fusion
                                            |
Reviewed disaster events -> Ground truth --+-> Features and labels
                                                |
                                                +-> Models -> Predictions -> Risk API
```

## Setup

Python 3.12 is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Keep provider credentials in `.env`; never commit that file.

## Production Gate

Run the artifact audit before training, deployment, or publishing results:

```bash
python -m scripts.quality.audit
```

The command exits nonzero unless all of the following are true:

- Training observations cover Northeast India only.
- At least 90 distinct historical days are available.
- Model features contain no missing values.
- Labels originate from verified event alignment.
- Every hazard has both classes and enough positive examples.
- Saved models match the current feature and class contract.

The current sample artifacts are intentionally expected to fail this gate. They
contain one global day and heuristic labels and must not be treated as production
forecasts.

Flood and cyclone are production-critical hazards. Drought remains an
experimental output: an unavailable drought model is reported explicitly and
does not prevent flood/cyclone inference or API readiness.

## Historical Collection

The production collectors default to 1 January 2006 through 31 December 2025.
They are resumable and immediately reduce provider data to the Northeast India
analysis grid.

The NASA GPM final-product archive currently supplies daily partitions through
30 September 2025 (7,213 days from 2006). Fusion uses ERA5 precipitation as the
documented fallback for the remaining 92 days of 2025.

Continue precipitation observations with the separate near-real-time Late Run:

```bash
python -m scripts.ingestion.manager start gpm-late \
  --start 2025-10-01 --end 2026-06-29
```

Late Run data is stored under `data/silver/weather/gpm_late` and is intended for
operational monitoring and serving inputs, not research-model training.

```bash
# Inspect progress
python -m scripts.ingestion.historical_weather status

# ERA5 monthly regional downloads
python -m scripts.ingestion.historical_weather era5 \
  --start 2006-01-01 --end 2025-12-31

# NASA GPM daily downloads; global raw files are deleted after regional parsing
python -m scripts.ingestion.historical_weather gpm \
  --start 2006-01-01 --end 2025-12-31
```

Use `--max-items 1` for a credential and parser smoke test. Use `--keep-raw`
only when raw provider files are required for archival purposes.

Long collections can be managed independently of the terminal:

```bash
python -m scripts.ingestion.manager start era5
python -m scripts.ingestion.manager start gpm
python -m scripts.ingestion.manager status
python -m scripts.ingestion.manager stop era5
python -m scripts.ingestion.manager stop gpm
```

Keep the machine awake and connected while workers are active. Progress and
worker logs are stored under `data/logs/ingestion`.

After collection and manual event review:

```bash
python -m ground_truth.collectors.collect_ibtracs
python -m ground_truth.collectors.collect_gdacs
python -m ground_truth.build
python -m scripts.production_pipeline prepare \
  --events data/gold/ground_truth.parquet \
  --start-year 2006 --end-year 2025
python -m scripts.production_pipeline audit
python -m scripts.production_pipeline train
```

The complete post-download workflow is resumable and can be run as one command:

```bash
python -m scripts.production_pipeline status
python -m scripts.production_pipeline finalize
```

`finalize` exits without modifying models while ERA5 or GPM collection is
incomplete. The production release is a district weather-pattern outlook and
does not require an ML model. Historical model experiments remain available as
research commands, but they cannot block the operational weather assessment.

IBTrACS supplies NOAA cyclone tracks. GDACS supplies India-filtered flood
points and drought affected-area polygons. GDACS responses are cached under
`data/bronze/events/gdacs`, allowing interrupted collection to resume.

The review queue is written to
`data/quality/ground_truth_review_queue.csv`. Correct and verify records using
`templates/ground_truth_review.csv`, then save the reviewed file as
`data/labels/reviewed_ground_truth.csv` before rebuilding ground truth.

The 3, 7, and 14 day research workflow is:

```bash
python -m scripts.labels.forecast_targets build
python -m scripts.ml.horizon_experiment --target flood_risk_7d
python -m scripts.ml.horizon_experiment --backtest-only --target flood_risk_7d
```

Horizon experiments and the former same-window trainer are explicitly
research-only. Neither can be promoted by the production model registry.

Live API inference reads `data/serving/current_features.parquet`; historical
training data is never used as the default serving input.

## District Operations

The district serving layer is separate from historical model training. It
publishes 3, 7, and 14 day weather outlooks for all 133 Northeast districts,
static land susceptibility factors, confidence grades, and mitigation actions.

```bash
# Fetch and validate the pinned 2021 ADM2 source, then reconcile current districts
python -m scripts.geospatial.districts all

# Optional: extract current OSM district overrides from a Northeast GeoPackage
python -m scripts.geospatial.osm_gpkg /path/to/north-eastern-zone.gpkg
python -m scripts.geospatial.districts build

# Collect all 133 district-point forecasts and 3/7/14 day contracts
python -m scripts.forecast.open_meteo collect

# Cache NASA SRTM terrain and ESA WorldCover, then build susceptibility factors
python -m scripts.susceptibility.static all

# Publish the district serving artifact
python -m scripts.serving.district_assessment build
```

The pinned geoBoundaries layer plus current OSM overrides provide unique usable
polygons for 132 of 133 districts. Itanagar Capital Complex remains point-based
because no unambiguous current district polygon is available.

NASA SRTM elevation and slope, ESA WorldCover land context, historical event
frequency, 20-year ERA5/GPM hydroclimate normals, and weather-derived drought
history are available. Raw terrain and land-cover tiles are cached once and
their checksums are recorded. The assessment covers weather hazard and physical
land susceptibility, not population, building, or financial vulnerability.

Open-Meteo forecasts are combined with 20-year district weather patterns,
30 m terrain, and 10 m sampled land cover to produce explainable 0-100 flood,
cyclone, and drought scores. These are weather-land risk indices, never disaster
probabilities, forecast guarantees, or official warnings.

The public risk scale is fixed: Low `0–24.9`, Moderate `25–49.9`, High
`50–74.9`, and Very High `75–100`.

Run the complete daily refresh manually with:

```bash
python -m scripts.production_pipeline operational
```

This lock-protected command catches NASA GPM Late up through yesterday, refreshes
the forecast and IMD cyclone confirmation, rebuilds district serving data,
creates a verified operational backup, and records any failure alert.

Install and inspect the daily 06:15 macOS scheduler with:

```bash
python -m scripts.operations.scheduler install
python -m scripts.operations.scheduler status
python -m scripts.operations.monitor status
```

The scheduler runs through the login shell so existing Earthdata credentials
are available without writing secrets into the plist. Backups retain the latest
14 operational archives under `data/backups/operations`. Alerts are always
written locally, the installed macOS schedule enables desktop failure
notifications, and `SUSBIOME_ALERT_WEBHOOK_URL` can optionally deliver the same
incident to an external monitor.

Rainfall validation, official cyclone confirmation, and drought history can be
refreshed independently with:

```bash
python -m scripts.quality.chirps_crosscheck crosscheck --start-year 2021 --end-year 2024
python -m scripts.alerts.imd_cyclone collect
python -m scripts.events.drought_history build
```

Open-Meteo forecast data is CC BY 4.0 and requires attribution. The free public
endpoint is intended for non-commercial use; production commercial deployment
must use an appropriate licensed endpoint or a self-hosted service.

## Tests

```bash
python -m unittest discover -s tests -v
```

Legacy exploratory checks remain under `scripts/tests`; new automated tests
belong in `tests`.

## API

```bash
uvicorn scripts.api.app:app --host 0.0.0.0 --port 8000
```

Open `/docs` for the OpenAPI interface and `/api/health/ready` for readiness.
The weather-outlook API is ready without ML artifacts. Legacy model endpoints
remain disabled unless `SUSBIOME_ENABLE_LEGACY_ML=true` is explicitly set.

API input and output paths are restricted to the project `data` directory.

Read-only district routes remain available when model services are degraded:

```text
GET /api/districts?state=Assam
GET /api/districts/{state}/{district}/forecast?horizon_days=7
GET /api/districts/{state}/{district}/assessment?horizon_days=7
GET /api/districts/{state}/{district}/report
GET /api/locations/assessment?latitude=27.48&longitude=94.91&horizon_days=7
```

Forecast responses identify representative-point spatial support and include an
official-warning disclaimer. Assessment responses keep hazard probability,
susceptibility, exposure mode, confidence, and forecast signal as separate fields.
Coordinate responses resolve the district polygon and report point SRTM elevation,
slope, and WorldCover class separately from district weather history.

Before public release, review the compact flood/cyclone evidence package:

```bash
python -m scripts.quality.production_review
# Complete data/quality/production_event_review.csv, then rebuild canonical labels
python -m ground_truth.build
python -m scripts.quality.audit --json
```

For every row, set `review_status` to `APPROVED` or `REJECTED` and set
`event_occurred_in_district` and `date_correct` to `YES` or `NO`. Rejected or
incorrect cases are excluded when canonical ground truth is rebuilt.

## Dashboard

The operational dashboard starts once the district assessment artifact exists:

```bash
streamlit run scripts/dashboard/app.py
```

## Container

```bash
docker build -t susbiome .
docker run --rm -p 8000:8000 -v "$PWD/data:/app/data" susbiome
```

Production deployments should mount a persistent data volume, terminate TLS at
the ingress, and restrict API access at the network or identity layer.

Use `docker compose up --build` for the production-shaped local deployment.
Set `SUSBIOME_API_KEY`, `SUSBIOME_ALLOWED_HOSTS`, and
`SUSBIOME_CORS_ORIGINS` in `.env`. Model releases are mounted from `models/`
instead of being embedded in the image.
