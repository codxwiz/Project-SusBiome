# Project SusBiome

SusBiome is a climate and disaster-risk data platform for Northeast India. It
combines weather observations, satellite precipitation, and reviewed disaster
events to produce flood, drought, and cyclone risk datasets.

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
incomplete. Once inputs are complete, it builds ground truth, fuses yearly
weather, aligns event groups, creates features, trains isolated candidates,
audits them, and atomically promotes a checksummed release. Restore the previous
release with `python -m scripts.production_pipeline rollback`.

IBTrACS supplies NOAA cyclone tracks. GDACS supplies India-filtered flood
points and drought affected-area polygons. GDACS responses are cached under
`data/bronze/events/gdacs`, allowing interrupted collection to resume.

The review queue is written to
`data/quality/ground_truth_review_queue.csv`. Correct and verify records using
`templates/ground_truth_review.csv`, then save the reviewed file as
`data/labels/reviewed_ground_truth.csv` before rebuilding ground truth.

Live API inference reads `data/serving/current_features.parquet`; historical
training data is never used as the default serving input.

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
The API starts in degraded mode when model artifacts fail validation and does
not serve prediction requests until valid models are installed.

API input and output paths are restricted to the project `data` directory.

## Dashboard

After prediction and risk datasets have been generated:

```bash
streamlit run scripts/dashboard/app.py
```

## Container

```bash
docker build -t susbiome .
docker run --rm -p 8000:8000 -v "$PWD/data:/app/data" susbiome
```

Production deployments should mount immutable validated models and a persistent
data volume, terminate TLS at the ingress, and restrict API access at the
network or identity layer.

Use `docker compose up --build` for the production-shaped local deployment.
Set `SUSBIOME_API_KEY`, `SUSBIOME_ALLOWED_HOSTS`, and
`SUSBIOME_CORS_ORIGINS` in `.env`. Model releases are mounted from `models/`
instead of being embedded in the image.
