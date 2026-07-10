"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AgriPageNav from "./AgriPageNav";
import DistrictMap from "./DistrictMap";
import { HazardBars, HorizonLines } from "./Charts";
import {
  hazards,
  hazardLabels,
  hazardColors,
  titleCase,
  hazardLabel,
  displayCopy,
  fmtScore,
  fmtNumber,
  fmtPercent,
} from "../lib/format";

const DATA_URL = "/data/susbiome-outlook.json";
const BOUNDARIES_URL = "/data/ne-district-boundaries.geojson";
const PRODUCTION_API_BASE = "https://dashboard.susbiome.com";

function defaultApiBase() {
  if (typeof window === "undefined") return "";

  if (window.SUSBIOME_API_BASE) {
    return window.SUSBIOME_API_BASE;
  }

  if (window.location.hostname === "susbiome.com" || window.location.hostname === "www.susbiome.com") {
    return PRODUCTION_API_BASE;
  }

  return "";
}

function Metric({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export default function RiskConsole() {
  const [payload, setPayload] = useState(null);
  const [boundaries, setBoundaries] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [horizon, setHorizon] = useState(30);

  useEffect(() => {
    const apiBase = String(process.env.NEXT_PUBLIC_SUSBIOME_API_BASE || defaultApiBase()).replace(/\/$/, "");

    const loadPayload = (dataUrl, boundariesUrl) =>
      Promise.all([fetch(dataUrl), fetch(boundariesUrl)])
        .then(async ([dataResponse, boundaryResponse]) => {
          if (!dataResponse.ok || !boundaryResponse.ok) {
            throw new Error(
              `Unable to load SusBiome data (${dataResponse.status}/${boundaryResponse.status}).`
            );
          }
          return Promise.all([dataResponse.json(), boundaryResponse.json()]);
        });

    const liveDataUrl = apiBase ? `${apiBase}/api/outlook` : DATA_URL;
    const liveBoundariesUrl = apiBase ? `${apiBase}/api/outlook/boundaries` : BOUNDARIES_URL;

    loadPayload(liveDataUrl, liveBoundariesUrl)
      .catch((error) => {
        if (!apiBase) {
          throw error;
        }
        console.warn("Live SusBiome API unavailable, loading bundled data.", error);
        return loadPayload(DATA_URL, BOUNDARIES_URL);
      })
      .then(async ([dataResponse, boundaryResponse]) => {
        setPayload(dataResponse);
        setBoundaries(boundaryResponse);
        setState(dataResponse.states[0]);
        setDistrict(dataResponse.districts.find((item) => item.state === dataResponse.states[0]).district);
        setHorizon(dataResponse.meta.horizons.includes(30) ? 30 : dataResponse.meta.horizons[0]);
      })
      .catch((error) => {
        console.error(error);
        setLoadError(error.message || "Unable to load SusBiome data.");
      });
  }, []);

  const stateDistricts = useMemo(() => {
    if (!payload || !state) return [];
    return payload.districts.filter((item) => item.state === state);
  }, [payload, state]);

  const districtRecords = useMemo(() => {
    if (!payload) return [];
    return payload.outlook
      .filter((item) => item.state === state && item.district === district)
      .sort((a, b) => a.horizon - b.horizon);
  }, [payload, state, district]);

  const record = districtRecords.find((item) => item.horizon === horizon);
  const stateRecords =
    payload?.outlook.filter((item) => item.state === state && item.horizon === horizon) || [];
  const location = payload?.districts.find((item) => item.state === state && item.district === district);

  if (!payload || !boundaries || !record || !location) {
    return (
      <div className="console-page">
        <AgriPageNav />
        <main className="console-loading">
          <span className="brand-icon">S</span>
          <p>{loadError || "Loading SusBiome console..."}</p>
        </main>
      </div>
    );
  }

  const collected = record.forecast.collectedAt ? new Date(record.forecast.collectedAt) : null;
  const staticCoverage =
    Number.isFinite(record.quality.staticCoverage)
      ? fmtPercent(record.quality.staticCoverage * 100, 0)
      : "--";

  return (
    <div className="console-page">
      <AgriPageNav />
      <main className="console-shell">
        <aside className="console-sidebar">
          <Link href="/" className="brand dark">
            <span className="brand-icon">S</span>
            <span>SusBiome</span>
            <small>Toolkit Console</small>
          </Link>

        <div className="control-stack">
          <label htmlFor="stateSelect">State</label>
          <select
            id="stateSelect"
            value={state}
            onChange={(event) => {
              const nextState = event.target.value;
              const firstDistrict = payload.districts.find((item) => item.state === nextState).district;
              setState(nextState);
              setDistrict(firstDistrict);
            }}
          >
            {payload.states.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>

          <label htmlFor="districtSelect">District</label>
          <select
            id="districtSelect"
            value={district}
            onChange={(event) => setDistrict(event.target.value)}
          >
            {stateDistricts.map((item) => (
              <option key={item.district} value={item.district}>
                {item.district}
              </option>
            ))}
          </select>

          <label>Planning horizon</label>
          <div className="segmented" role="radiogroup" aria-label="Planning horizon">
            {payload.meta.horizons.map((item) => (
              <button
                key={item}
                type="button"
                role="radio"
                aria-checked={item === horizon}
                onClick={() => setHorizon(item)}
              >
                {item}d
              </button>
            ))}
          </div>
        </div>

        <div className="status-panel">
          <span className="status-dot"></span>
          <div>
            <strong>
              {collected
                ? `Forecast refreshed ${collected.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
                : "Forecast loaded"}
            </strong>
            <span>Planning outlook, not a disaster probability.</span>
          </div>
        </div>

        <nav className="side-nav" aria-label="Toolkit Console sections">
          <a href="#outlook">Outlook</a>
          <a href="#horizons">Horizons</a>
          <a href="#map">Map</a>
          <a href="#quality">Quality</a>
          <a href="#sources">Sources</a>
        </nav>
        </aside>

        <section className="console-main">
        <header id="outlook" className="console-header">
          <div>
            <p className="section-kicker">{state}</p>
            <h1>{district}</h1>
            <p className="district-meta">
              {fmtNumber(location.latitude, 3)} deg N, {fmtNumber(location.longitude, 3)} deg E |{" "}
              {horizon}-day planning outlook
            </p>
          </div>
          <div className="composite-card">
            <span>Composite risk</span>
            <strong>{fmtScore(record.compositeScore)}</strong>
            <small>{titleCase(record.compositeLevel)}</small>
            <p>{hazardLabel(record.dominantHazard)} is the dominant current signal</p>
          </div>
        </header>

        <section className="hazard-tiles" aria-label="Hazard scores">
          {hazards.map((hazard) => (
            <article key={hazard} style={{ "--hazard": hazardColors[hazard] }}>
              <span>{hazardLabels[hazard]}</span>
              <strong>{fmtScore(record.hazards[hazard].score)}</strong>
              <small>{titleCase(record.hazards[hazard].level)}</small>
            </article>
          ))}
        </section>

        <section id="horizons" className="chart-grid">
          <div className="panel chart-card">
            <p className="section-kicker">Three-hazard outlook</p>
            <h2>{horizon}-day risk scores</h2>
            <HazardBars record={record} variant="premium-solid" />
          </div>
          <div className="panel chart-card">
            <p className="section-kicker">Risk across horizons</p>
            <h2>15 - 30 - 60 - 90 days</h2>
            <HorizonLines records={districtRecords} horizons={payload.meta.horizons} />
          </div>
        </section>

        <section className="console-grid">
          <div id="map" className="panel map-card">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">District map</p>
                <h2>{state} risk field</h2>
              </div>
              <div className="map-legend">
                <span><i className="legend-low"></i>Low</span>
                <span><i className="legend-moderate"></i>Moderate</span>
                <span><i className="legend-high"></i>High</span>
                <span><i className="legend-very-high"></i>Very high</span>
              </div>
            </div>
            <DistrictMap
              boundaries={boundaries}
              state={state}
              district={district}
              records={stateRecords}
              location={location}
              onDistrictChange={setDistrict}
            />
          </div>

          <aside className="panel weather-card">
            <p className="section-kicker">Weather signal</p>
            <h2>Near-term inputs</h2>
            <dl className="metric-list">
              <Metric label="Rainfall" value={`${fmtNumber(record.forecast.rainfallMm, 1)} mm`} />
              <Metric label="Rain probability" value={fmtPercent(record.forecast.rainProbability, 0)} />
              <Metric label="Max wind gust" value={`${fmtNumber(record.forecast.windGustKmh, 1)} km/h`} />
              <Metric
                label="Temperature range"
                value={`${fmtNumber(record.forecast.temperatureMinC, 1)} to ${fmtNumber(record.forecast.temperatureMaxC, 1)} deg C`}
              />
            </dl>
            <div className="attention-box">
              <p className="section-kicker">Recommended attention</p>
              <ul>
                {record.actions.map((action) => (
                  <li key={action}>{displayCopy(action)}</li>
                ))}
              </ul>
            </div>
          </aside>
        </section>

        <section id="quality" className="quality-grid">
          <div className="panel">
            <p className="section-kicker">Model and data quality</p>
            <h2>Production signals we can defend</h2>
            <div className="quality-metrics">
              <div><strong>{payload.meta.districts}</strong><span>districts</span></div>
              <div><strong>{payload.meta.states}</strong><span>states</span></div>
              <div><strong>{fmtPercent(payload.meta.boundaryCoveragePercent, 1)}</strong><span>boundary coverage</span></div>
              <div><strong>{record.quality.confidenceGrade}</strong><span>confidence</span></div>
            </div>
          </div>
          <div className="panel">
            <p className="section-kicker">Selected district</p>
            <h2>Physical land context</h2>
            <dl className="metric-list slim">
              <Metric label="Elevation" value={`${fmtNumber(location.elevationMeanM, 0)} m`} />
              <Metric label="Slope" value={`${fmtNumber(location.slopeMeanDegrees, 1)} deg`} />
              <Metric label="Static coverage" value={staticCoverage} />
              <Metric label="Rainfall cross-check" value={titleCase(record.quality.rainfallCrosscheck)} />
            </dl>
          </div>
        </section>

        <section id="sources" className="panel source-panel">
          <div>
            <p className="section-kicker">Attribution</p>
            <h2>Sources and public wording</h2>
            <p>{payload.meta.disclaimer}</p>
          </div>
          <details className="source-collection-dropdown">
            <summary>View all data sources</summary>
            <div className="source-list source-list--accordion">
              {payload.meta.sources.map((source) => (
                <details className="source-disclosure" key={source.name}>
                  <summary>
                    <strong>{source.name}</strong>
                    <span>{source.license}</span>
                  </summary>
                  <p>{displayCopy(source.role)}</p>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    View source
                  </a>
                </details>
              ))}
            </div>
          </details>
        </section>
        </section>
      </main>
    </div>
  );
}
