"use client";

import { levelColors, fmtScore, titleCase } from "../lib/format";

function flattenCoordinates(geometry) {
  const rings = [];
  if (!geometry) return rings;
  if (geometry.type === "Polygon") {
    for (const ring of geometry.coordinates) rings.push(ring);
  }
  if (geometry.type === "MultiPolygon") {
    for (const polygon of geometry.coordinates) {
      for (const ring of polygon) rings.push(ring);
    }
  }
  return rings;
}

function createProjection(features) {
  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;

  for (const feature of features) {
    for (const ring of flattenCoordinates(feature.geometry)) {
      for (const [lon, lat] of ring) {
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
      }
    }
  }

  const width = 1000;
  const height = 700;
  const padding = 42;
  const scaleX = (width - padding * 2) / Math.max(maxLon - minLon, 0.1);
  const scaleY = (height - padding * 2) / Math.max(maxLat - minLat, 0.1);
  const scale = Math.min(scaleX, scaleY);
  const mapWidth = (maxLon - minLon) * scale;
  const mapHeight = (maxLat - minLat) * scale;
  const offsetX = (width - mapWidth) / 2;
  const offsetY = (height - mapHeight) / 2;

  return {
    point(lon, lat) {
      return [
        offsetX + (lon - minLon) * scale,
        height - (offsetY + (lat - minLat) * scale),
      ];
    },
  };
}

function pathForGeometry(geometry, projection) {
  return flattenCoordinates(geometry)
    .map((ring) => {
      const points = ring.map(([lon, lat]) => projection.point(lon, lat));
      if (!points.length) return "";
      const [firstX, firstY] = points[0];
      const commands = [`M ${firstX.toFixed(2)} ${firstY.toFixed(2)}`];
      for (const [x, y] of points.slice(1)) {
        commands.push(`L ${x.toFixed(2)} ${y.toFixed(2)}`);
      }
      commands.push("Z");
      return commands.join(" ");
    })
    .join(" ");
}

export default function DistrictMap({
  boundaries,
  state,
  district,
  records,
  location,
  onDistrictChange,
}) {
  const features = boundaries.features.filter((feature) => feature.properties.state === state);
  const projection = createProjection(features.length ? features : boundaries.features);
  const scoreByDistrict = new Map(records.map((record) => [record.district, record]));
  const selectedPoint =
    location?.longitude && location?.latitude
      ? projection.point(location.longitude, location.latitude)
      : null;

  return (
    <svg className="district-map" viewBox="0 0 1000 700" role="img" aria-label={`${state} district risk map`}>
      {features.map((feature) => {
        const record = scoreByDistrict.get(feature.properties.district);
        if (!record) return null;
        const level = String(record.compositeLevel || "UNAVAILABLE").toUpperCase();
        return (
          <path
            key={`${feature.properties.state}-${feature.properties.district}`}
            d={pathForGeometry(feature.geometry, projection)}
            className={`district-shape${feature.properties.district === district ? " selected" : ""}`}
            fill={levelColors[level] || levelColors.UNAVAILABLE}
            onClick={() => onDistrictChange(feature.properties.district)}
          >
            <title>
              {feature.properties.district}: {fmtScore(record.compositeScore)} {titleCase(record.compositeLevel)}
            </title>
          </path>
        );
      })}
      {selectedPoint ? (
        <circle
          className="district-point"
          cx={selectedPoint[0].toFixed(2)}
          cy={selectedPoint[1].toFixed(2)}
          r="7"
        />
      ) : null}
    </svg>
  );
}
