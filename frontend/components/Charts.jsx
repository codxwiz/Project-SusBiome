import { hazards, hazardLabels, hazardColors, fmtScore, titleCase } from "../lib/format";

function axisLabel(x, y, value, anchor = "middle", className = "chart-label") {
  return (
    <text x={x} y={y} textAnchor={anchor} className={className}>
      {value}
    </text>
  );
}

export function HazardBars({ record }) {
  const width = 680;
  const chartLeft = 64;
  const chartBottom = 302;
  const chartTop = 34;
  const chartHeight = chartBottom - chartTop;
  const barWidth = 94;
  const gap = 70;

  return (
    <svg className="chart-svg" viewBox="0 0 680 360" role="img" aria-label="Hazard risk scores">
      {[0, 25, 50, 75, 100].map((tick) => {
        const y = chartBottom - (tick / 100) * chartHeight;
        return (
          <g key={tick}>
            <line className="grid-line" x1={chartLeft} y1={y} x2={width - 26} y2={y} />
            {axisLabel(48, y + 4, tick, "end")}
          </g>
        );
      })}
      <line className="axis-line" x1={chartLeft} y1={chartTop} x2={chartLeft} y2={chartBottom} />
      <line className="axis-line" x1={chartLeft} y1={chartBottom} x2={width - 26} y2={chartBottom} />
      {hazards.map((hazard, index) => {
        const item = record.hazards[hazard];
        const x = chartLeft + 54 + index * (barWidth + gap);
        const barHeight = (item.score / 100) * chartHeight;
        const y = chartBottom - barHeight;
        return (
          <g key={hazard} className="chart-bar-group" tabIndex="0">
            <rect
              className="chart-bar-hit"
              x={x - 16}
              y={chartTop}
              width={barWidth + 32}
              height={chartHeight}
              rx="8"
            />
            <rect
              className="chart-bar-rect"
              x={x}
              y={y}
              width={barWidth}
              height={barHeight}
              rx="3"
              fill={hazardColors[hazard]}
            />
            {axisLabel(x + barWidth / 2, y - 9, fmtScore(item.score), "middle", "bar-label")}
            {axisLabel(x + barWidth / 2, chartBottom + 28, hazardLabels[hazard])}
            {axisLabel(x + barWidth / 2, chartBottom + 50, titleCase(item.level))}
          </g>
        );
      })}
    </svg>
  );
}

export function HorizonLines({ records, horizons }) {
  const width = 680;
  const left = 64;
  const right = width - 34;
  const top = 34;
  const bottom = 294;
  const chartHeight = bottom - top;
  const xFor = (value) => left + (horizons.indexOf(value) / (horizons.length - 1)) * (right - left);
  const yFor = (value) => bottom - (value / 100) * chartHeight;

  return (
    <svg className="chart-svg" viewBox="0 0 680 360" role="img" aria-label="Risk across horizons">
      {[0, 25, 50, 75, 100].map((tick) => {
        const y = yFor(tick);
        return (
          <g key={tick}>
            <line className="grid-line" x1={left} y1={y} x2={right} y2={y} />
            {axisLabel(48, y + 4, tick, "end")}
          </g>
        );
      })}
      <line className="axis-line" x1={left} y1={top} x2={left} y2={bottom} />
      <line className="axis-line" x1={left} y1={bottom} x2={right} y2={bottom} />
      {horizons.map((value) => (
        <text key={value} x={xFor(value)} y={bottom + 28} textAnchor="middle" className="chart-label">
          {value}d
        </text>
      ))}
      {hazards.map((hazard) => {
        const points = records.map((record) => [
          xFor(record.horizon),
          yFor(record.hazards[hazard].score),
          record.hazards[hazard].score,
        ]);
        const path = points
          .map(([x, y], index) => `${index ? "L" : "M"} ${x.toFixed(2)} ${y.toFixed(2)}`)
          .join(" ");
        const [labelX, labelY] = points[points.length - 1];
        return (
          <g key={hazard} className="chart-line-group" tabIndex="0">
            <path
              className="chart-line-hit"
              d={path}
              fill="none"
              stroke="transparent"
              strokeWidth="18"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              className="chart-line-path"
              d={path}
              fill="none"
              stroke={hazardColors[hazard]}
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {points.map(([x, y, value]) => (
              <circle
                className="chart-point"
                key={`${hazard}-${x}-${y}`}
                cx={x}
                cy={y}
                r="5"
                fill={hazardColors[hazard]}
                stroke="#fff"
                strokeWidth="2"
              >
                <title>
                  {hazardLabels[hazard]} {fmtScore(value)}
                </title>
              </circle>
            ))}
            {axisLabel(labelX + 8, labelY + 4, hazardLabels[hazard], "start", "line-label")}
          </g>
        );
      })}
    </svg>
  );
}
