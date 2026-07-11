"use client";

import { useMemo, useState } from "react";
import analyticsPayload from "../lib/analyticsPayload.json";

const {
  eventsByYear,
  hazardConfig,
  hazardSeries,
  kpis,
  stateCounts,
  topDistrictEventYear,
  topDistricts,
} = analyticsPayload;

const hazardDistribution = Object.entries(hazardConfig).map(([label, meta]) => [
  label,
  meta.total,
  meta.color,
]);

function getMaxValue(data, floor = 5) {
  return Math.max(floor, Math.ceil(Math.max(...data.map(([, value]) => value)) / 5) * 5);
}

function InteractiveLineChart({ data, color = "#2c63e4", label, max }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const width = 680;
  const height = 280;
  const left = 54;
  const right = width - 24;
  const top = 28;
  const bottom = height - 48;
  const chartMax = max ?? getMaxValue(data);
  const active = data[activeIndex ?? data.length - 1];
  const xFor = (index) => left + (index / (data.length - 1)) * (right - left);
  const yFor = (value) => bottom - (value / chartMax) * (bottom - top);
  const path = data
    .map(([, value], index) => `${index ? "L" : "M"} ${xFor(index).toFixed(2)} ${yFor(value).toFixed(2)}`)
    .join(" ");
  const ticks = Array.from({ length: 5 }, (_, index) => Math.round((chartMax / 4) * index));
  const focusX = xFor(activeIndex ?? data.length - 1);
  const focusY = yFor(active[1]);
  const tooltipX = Math.min(Math.max(focusX - 64, left), right - 128);
  const tooltipY = Math.max(focusY - 72, top + 4);

  return (
    <div className="analytics-chart-shell">
      <svg
        className="analytics-chart analytics-chart--interactive"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={label}
        style={{ "--chart-color": color }}
        onMouseLeave={() => setActiveIndex(null)}
      >
        <defs>
          <linearGradient id={`area-${label.replace(/\W/g, "")}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.2" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((tick) => {
          const y = yFor(tick);
          return (
            <g key={tick}>
              <line className="analytics-grid-line" x1={left} y1={y} x2={right} y2={y} />
              <text className="analytics-axis-label" x={left - 12} y={y + 4} textAnchor="end">
                {tick}
              </text>
            </g>
          );
        })}
        <line className="analytics-axis-line" x1={left} y1={top} x2={left} y2={bottom} />
        <line className="analytics-axis-line" x1={left} y1={bottom} x2={right} y2={bottom} />
        <path
          className="analytics-area-path"
          d={`${path} L ${right} ${bottom} L ${left} ${bottom} Z`}
          fill={`url(#area-${label.replace(/\W/g, "")})`}
        />
        <path className="analytics-line-path" d={path} />
        <line className="analytics-focus-line" x1={focusX} y1={top} x2={focusX} y2={bottom} />
        {data.map(([year, value], index) => (
          <g key={year}>
            <circle
              className={`analytics-point ${index === activeIndex ? "is-active" : ""}`}
              cx={xFor(index)}
              cy={yFor(value)}
              r={index === activeIndex ? "7" : "5"}
            />
            <rect
              className="analytics-hit-zone"
              x={xFor(index) - 18}
              y={top}
              width="36"
              height={bottom - top}
              onMouseEnter={() => setActiveIndex(index)}
              onFocus={() => setActiveIndex(index)}
              tabIndex={0}
              role="button"
              aria-label={`${year}: ${value} events`}
            />
            {index % 2 === 0 && (
              <text className="analytics-axis-label" x={xFor(index)} y={bottom + 28} textAnchor="middle">
                {year}
              </text>
            )}
          </g>
        ))}
        <g className="analytics-tooltip" transform={`translate(${tooltipX} ${tooltipY})`}>
          <rect width="128" height="58" rx="14" />
          <text x="16" y="24">
            {active[0]}
          </text>
          <text x="16" y="45" className="analytics-tooltip-value">
            {active[1]} events
          </text>
        </g>
      </svg>
    </div>
  );
}

function DonutChart({ data, activeHazard, onSelect }) {
  const total = data.reduce((sum, [, value]) => sum + value, 0);
  const segments = data.reduce(
    (acc, [label, value, color]) => {
      const dash = (value / total) * 452;
      return {
        offset: acc.offset + dash,
        items: [...acc.items, { label, value, color, dash, offset: acc.offset }],
      };
    },
    { offset: 25, items: [] }
  ).items;
  const activeTotal = hazardConfig[activeHazard].total;

  return (
    <div className="analytics-donut-wrap">
      <svg className="analytics-donut" viewBox="0 0 220 220" role="img" aria-label="Hazard distribution">
        <circle cx="110" cy="110" r="72" fill="none" stroke="#edf2e6" strokeWidth="34" />
        {segments.map(({ label, color, dash, offset }) => (
          <circle
            key={label}
            className={label === activeHazard ? "is-active" : ""}
            cx="110"
            cy="110"
            r="72"
            fill="none"
            stroke={color}
            strokeDasharray={`${dash} ${452 - dash}`}
            strokeDashoffset={-offset}
            strokeLinecap="round"
            strokeWidth={label === activeHazard ? "38" : "30"}
            transform="rotate(-90 110 110)"
            onClick={() => onSelect(label)}
            role="button"
            tabIndex={0}
            aria-label={`Show ${label} trend`}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(label);
              }
            }}
          />
        ))}
        <text x="110" y="104" textAnchor="middle" className="analytics-donut-value">
          {activeTotal}
        </text>
        <text x="110" y="130" textAnchor="middle" className="analytics-donut-label">
          {activeHazard}
        </text>
      </svg>
      <div className="analytics-legend">
        {data.map(([label, value, color]) => (
          <button
            className={label === activeHazard ? "is-active" : ""}
            key={label}
            type="button"
            onClick={() => onSelect(label)}
          >
            <i style={{ "--legend-color": color }}></i>
            {label} <strong>{value}</strong>
          </button>
        ))}
      </div>
    </div>
  );
}

function HorizontalBars({ data }) {
  const max = Math.max(...data.map(([, value]) => value));

  return (
    <div className="analytics-bars" aria-label="Events by state">
      {data.map(([label, value]) => (
        <div className="analytics-bar-row" key={label}>
          <span>{label}</span>
          <div>
            <i style={{ width: `${(value / max) * 100}%` }}></i>
          </div>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsDashboard() {
  const [activeHazard, setActiveHazard] = useState("Flood");
  const activeSeries = hazardSeries[activeHazard];
  const activeMeta = hazardConfig[activeHazard];
  const activePeak = useMemo(
    () => activeSeries.reduce((peak, item) => (item[1] > peak[1] ? item : peak), activeSeries[0]),
    [activeSeries]
  );

  return (
    <section className="analytics-section site-section subpage-section" aria-labelledby="analytics-title">
      <div className="section-copy section-copy--wide analytics-intro">
        <h1 id="analytics-title">Climate disaster analytics for Northeast India.</h1>
        <p>
          A compact view of historical events, hazard distribution, state exposure, and district
          composite risk for awareness, planning, and consultation.
        </p>
      </div>

      <div className="analytics-kpi-grid" aria-label="Climate disaster metrics">
        {kpis.map(([label, value]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      <div className="analytics-grid">
        <article className="analytics-card analytics-card--wide">
          <div className="analytics-card-heading">
            <div>
              <p className="section-kicker">Events by year</p>
              <h2>19-year trend</h2>
            </div>
            <p className="analytics-live-note">Hover the line to inspect event count</p>
          </div>
          <InteractiveLineChart data={eventsByYear} color="#2f8f6a" label="Events by year" />
        </article>

        <article className="analytics-card">
          <p className="section-kicker">By hazard</p>
          <h2>Distribution</h2>
          <DonutChart data={hazardDistribution} activeHazard={activeHazard} onSelect={setActiveHazard} />
        </article>

        <article className="analytics-card analytics-card--wide">
          <div className="analytics-card-heading">
            <div>
              <p className="section-kicker">Hazard-specific trend</p>
              <h2>{activeHazard} events per year</h2>
            </div>
            <div className="analytics-hazard-tabs" aria-label="Hazard filters">
              {Object.keys(hazardConfig).map((item) => (
                <button
                  className={item === activeHazard ? "is-active" : ""}
                  key={item}
                  type="button"
                  onClick={() => setActiveHazard(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <div className="analytics-insight-strip">
            <span style={{ "--legend-color": activeMeta.color }}>{activeHazard}</span>
            <strong>{activeMeta.total} reviewed events</strong>
            <em>Peak year: {activePeak[0]} with {activePeak[1]} events</em>
          </div>
          <InteractiveLineChart
            key={activeHazard}
            data={activeSeries}
            color={activeMeta.color}
            label={`${activeHazard} events per year`}
            max={getMaxValue(activeSeries, 5)}
          />
        </article>

        <article className="analytics-card">
          <p className="section-kicker">By state</p>
          <h2>Event count</h2>
          <HorizontalBars data={stateCounts} />
        </article>

        <article className="analytics-card analytics-table-card">
          <p className="section-kicker">Current serving layer</p>
          <h2>Top risk districts {topDistrictEventYear}</h2>
          <div className="analytics-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>District</th>
                  <th>State</th>
                  <th>Risk score</th>
                  <th>Total events</th>
                </tr>
              </thead>
              <tbody>
                {topDistricts.map(([district, state, composite, totalEvents]) => (
                  <tr key={`${district}-${state}`}>
                    <td>{district}</td>
                    <td>{state}</td>
                    <td>{composite}</td>
                    <td>{totalEvents}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </section>
  );
}
