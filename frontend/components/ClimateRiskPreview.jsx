"use client";

import { useEffect, useMemo, useState } from "react";
import { HazardBars } from "./Charts";

const HAZARDS = [
  { key: "flood", label: "Flood", color: "#1f6fff" },
  { key: "drought", label: "Drought", color: "#d97706" },
  { key: "cyclone", label: "Storm", color: "#f4c430" },
];

const DATA_URL = "/data/susbiome-outlook.json";
const DEFAULT_STATE = "Manipur";

function scoreLabel(value) {
  return Number.isFinite(value) ? Math.round(value).toString() : "--";
}

function titleCase(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function ClimateRiskPreview() {
  const [payload, setPayload] = useState(null);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [horizon, setHorizon] = useState(30);

  useEffect(() => {
    fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load climate risk preview.");
        return response.json();
      })
      .then((data) => {
        const firstState = data.states.includes(DEFAULT_STATE) ? DEFAULT_STATE : data.states[0];
        const firstDistrict = data.districts.find((item) => item.state === firstState);
        setPayload(data);
        setState(firstState);
        setDistrict(firstDistrict?.district || "");
        setHorizon(data.meta.horizons.includes(30) ? 30 : data.meta.horizons[0]);
      })
      .catch(() => {
        setPayload({ states: [], districts: [], outlook: [], meta: { horizons: [15, 30, 60, 90] } });
      });
  }, []);

  const stateDistricts = useMemo(() => {
    if (!payload || !state) return [];
    return payload.districts.filter((item) => item.state === state);
  }, [payload, state]);

  const record = useMemo(() => {
    if (!payload) return null;
    return payload.outlook.find(
      (item) => item.state === state && item.district === district && item.horizon === horizon
    );
  }, [payload, state, district, horizon]);

  if (!payload || !record) {
    return (
      <div className="risk-preview__loading">
        Loading district risk preview...
      </div>
    );
  }

  return (
    <div className="risk-preview">
      <div className="risk-controls" aria-label="Climate risk preview controls">
        <label>
          <span>State</span>
          <select
            value={state}
            onChange={(event) => {
              const nextState = event.target.value;
              const firstDistrict = payload.districts.find((item) => item.state === nextState);
              setState(nextState);
              setDistrict(firstDistrict?.district || "");
            }}
          >
            {payload.states.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>District</span>
          <select value={district} onChange={(event) => setDistrict(event.target.value)}>
            {stateDistricts.map((item) => (
              <option key={item.district} value={item.district}>
                {item.district}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Horizon</span>
          <select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>
            {payload.meta.horizons.map((item) => (
              <option key={item} value={item}>
                {item} days
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="risk-score-row">
        {HAZARDS.map((hazard) => {
          const item = record.hazards[hazard.key];
          return (
            <button
              key={hazard.key}
              className="risk-score-card"
              style={{ "--hazard-color": hazard.color }}
              type="button"
            >
              <span>{hazard.label}</span>
              <strong>{scoreLabel(item.score)}</strong>
              <small>{titleCase(item.level)}</small>
            </button>
          );
        })}
      </div>

      <div className="risk-preview-chart-grid">
        <div className="risk-chart-card">
          <p className="story-kicker">Hazard scores</p>
          <h3>{horizon}-day risk scores</h3>
          <HazardBars record={record} variant="premium-solid" />
        </div>
      </div>
    </div>
  );
}
