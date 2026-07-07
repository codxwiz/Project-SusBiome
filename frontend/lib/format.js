export const hazards = ["flood", "drought", "cyclone"];

export const hazardLabels = {
  flood: "Flood",
  drought: "Drought",
  cyclone: "Cyclone",
};

export const hazardColors = {
  flood: "#2c63e4",
  drought: "#c77c10",
  cyclone: "#15867f",
};

export const levelColors = {
  LOW: "#2f9d73",
  MODERATE: "#e9c46a",
  HIGH: "#ed8f58",
  "VERY HIGH": "#c83d5a",
  UNAVAILABLE: "#94a3b8",
};

export function titleCase(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function fmtScore(value) {
  return Number.isFinite(value) ? Math.round(value).toString() : "--";
}

export function fmtNumber(value, digits = 1) {
  return Number.isFinite(value) ? value.toFixed(digits) : "--";
}

export function fmtPercent(value, digits = 0) {
  return Number.isFinite(value) ? `${value.toFixed(digits)}%` : "--";
}
