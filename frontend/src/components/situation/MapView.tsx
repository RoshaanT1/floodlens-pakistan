import { useEffect, useRef } from "react";
import { Circle, CircleMarker, MapContainer, Marker, Polygon, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import { Crosshair, Minus, Plus } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { districts, gauges, markets, satelliteFloodExtent } from "@/data/mockData";
import {
  DATA_HUE,
  FLOOD_LEVEL_COLOR,
  FLOOD_LEVEL_LABEL,
  RISK_COLOR,
  RISK_LABEL,
  alpha,
  cropToColor,
  fmtCusecs,
  fmtInt,
  fmtPkrShort,
} from "@/lib/risk";
import { flowAt, indexForOffset, levelAt, marketSpikePct, rainfallValue, riskAt } from "@/lib/select";
import { backendStatus, realSituation } from "@/data/backend";
import BaseTiles from "@/components/map/BaseTiles";
import MapLegend from "./MapLegend";
import type * as Layers from "@/components/situation/layers";

type MapViewProps = {
  offset: number;
  layers: Layers.LayerState;
  opacity: Record<Layers.GroupKey, number>;
  selectedDistrictId: string | null;
  focus: Layers.MapFocus | null;
  onSelectDistrict: (id: string) => void;
};

type MapInstance = {
  zoomIn: () => void;
  zoomOut: () => void;
  flyTo: (latlng: [number, number], zoom: number, options?: object) => void;
};

const HOME: [number, number] = [30.2, 69.4];

// Real-data rendering (pipeline): rain in blue bands, sudden PBS price moves as red/green markers.
const RAIN_BREAKS = [0.5, 2, 5, 10, 25];
const RAIN_BLUES = ["#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"];
const rainColor = (mm: number) => (mm < RAIN_BREAKS[0] ? null : RAIN_BLUES[Math.min(RAIN_BREAKS.filter((b) => mm >= b).length - 1, 4)]);
const SUDDEN_PCT = 10;
const PRICE_UP = "#d7301f";
const PRICE_DOWN = "#1a9850";
const PRICE_MIXED = "#7b3294";

/** Price tag icon: arrow + biggest move, coloured by direction (rose / fell / both). */
function priceTag(moves: { item: string; wow_pct: number | null }[]) {
  const up = moves.filter((m) => (m.wow_pct ?? 0) > 0);
  const down = moves.filter((m) => (m.wow_pct ?? 0) < 0);
  const mixed = up.length > 0 && down.length > 0;
  const top = moves[0];
  const color = mixed ? PRICE_MIXED : up.length ? PRICE_UP : PRICE_DOWN;
  // short tag (arrow + size); item names are in the hover tooltip so tags don't collide
  const text = mixed ? `&#8645; ${moves.length}` : `${up.length ? "&#9650;" : "&#9660;"} ${Math.abs(top.wow_pct ?? 0).toFixed(0)}%`;
  return L.divIcon({
    className: "",
    iconSize: undefined,
    iconAnchor: [0, 10],
    html: `<div style="display:inline-flex;align-items:center;white-space:nowrap;padding:2px 7px;border-radius:999px;background:${color};color:#fff;font:600 11px/16px system-ui,sans-serif;box-shadow:0 1px 3px rgba(0,0,0,.35);border:1.5px solid #fff;transform:translate(-50%,0)">${text}</div>`,
  });
}

function suddenMoves() {
  const m = backendStatus?.market;
  if (!m?.city_xy) return [];
  return Object.entries(m.cities).flatMap(([city, rows]) => {
    const xy = m.city_xy?.[city];
    if (!xy) return [];
    const moves = rows
      .filter((r) => r.wow_pct != null && Math.abs(r.wow_pct) >= SUDDEN_PCT)
      .sort((a, b) => Math.abs(b.wow_pct ?? 0) - Math.abs(a.wow_pct ?? 0));
    const top = moves[0]?.wow_pct ?? 0;
    return [{ city, xy, moves, top, week: m.week_end }];
  });
}

const maxFlow = Math.max(...gauges.map((g) => g.thresholds.exceptionallyHigh));
const maxExposed = Math.max(...districts.map((d) => d.exposedPopulation));
const maxCropland = Math.max(...districts.map((d) => d.croplandHa));

function MapFocus({ focus }: { focus: Layers.MapFocus | null }) {
  const map = useMap();
  useEffect(() => {
    if (focus) map.flyTo([focus.lat, focus.lng], focus.zoom, { duration: 0.8 });
  }, [focus, map]);
  return null;
}

export default function MapView({
  offset,
  layers,
  opacity,
  selectedDistrictId,
  focus,
  onSelectDistrict,
}: MapViewProps) {
  const mapRef = useRef<MapInstance | null>(null);

  return (
    <div className="relative h-full w-full">
      <MapContainer
        ref={mapRef}
        center={HOME}
        zoom={5}
        minZoom={4}
        maxZoom={11}
        zoomControl={false}
        className="h-full w-full"
      >
        <BaseTiles />
        <MapFocus focus={focus} />

        {layers.population &&
          districts.map((d) => (
            <CircleMarker
              key={`pop-${d.id}`}
              center={d.centroid}
              radius={5 + (d.exposedPopulation / maxExposed) * 14}
              pathOptions={{
                color: DATA_HUE.population,
                weight: 1,
                fillColor: DATA_HUE.population,
                fillOpacity: 0.22 * opacity.exposure,
              }}
            >
              <Tooltip className="fl-tip" direction="top">
                <span className="font-medium">{d.name}</span> — {fmtInt(d.exposedPopulation)} people
                exposed
              </Tooltip>
            </CircleMarker>
          ))}

        {layers.cropland &&
          districts.map((d) => (
            <CircleMarker
              key={`crop-${d.id}`}
              center={d.centroid}
              radius={4 + (d.croplandHa / maxCropland) * 16}
              pathOptions={{
                color: DATA_HUE.cropland,
                weight: 1,
                dashArray: "3 3",
                fillColor: DATA_HUE.cropland,
                fillOpacity: 0.2 * opacity.exposure,
              }}
            >
              <Tooltip className="fl-tip" direction="top">
                <span className="font-medium">{d.name}</span> — {fmtInt(d.croplandHa)} ha cropland
                affected
              </Tooltip>
            </CircleMarker>
          ))}

        {layers.districtRisk &&
          districts.map((d) => {
            const risk = riskAt(d, offset);
            const missing = d.noData?.[indexForOffset(offset)] ?? false;
            const fill = missing ? "#9ca3af" : RISK_COLOR[risk];
            const selected = d.id === selectedDistrictId;
            return (
              <Polygon
                key={d.id}
                positions={d.polygon}
                pathOptions={{
                  color: alpha(fill, selected ? 0.95 : 0.6),
                  weight: selected ? 2 : 1,
                  fillColor: fill,
                  fillOpacity: (missing ? 0.18 : 0.42) * opacity.hazard,
                }}
                eventHandlers={{ click: () => onSelectDistrict(d.id) }}
              >
                <Tooltip className="fl-tip" sticky>
                  <span className="font-medium">{d.name}</span> · {d.province}
                  <br />
                  {missing
                    ? "No data for this day"
                    : `Heavy-rain risk ${RISK_LABEL[risk].toLowerCase()}`}
                  {d.exposedPopulation > 0 && ` — ${fmtInt(d.exposedPopulation)} people exposed`}
                </Tooltip>
              </Polygon>
            );
          })}

        {layers.rainfall && realSituation &&
          districts.map((d) => {
            const mm = rainfallValue(d, offset);
            const color = rainColor(mm);
            if (!color) return null;
            return (
              <Polygon
                key={`rain-${d.id}`}
                positions={d.polygon}
                pathOptions={{ color: "#08306b", weight: 0.8, fillColor: color, fillOpacity: Math.max(0.65, 0.9 * opacity.hazard) }}
              >
                <Tooltip className="fl-tip" sticky>
                  <span className="font-medium">{d.name}</span>
                  <br />
                  {mm.toFixed(1)} mm {offset < 0 ? "observed (wettest point, NASA IMERG)" : "forecast (Open-Meteo)"}
                </Tooltip>
              </Polygon>
            );
          })}

        {layers.rainfall && !realSituation &&
          districts.map((d) => {
            const mm = rainfallValue(d, offset);
            return (
              <Circle
                key={`rain-${d.id}`}
                center={d.centroid}
                radius={mm * 900}
                pathOptions={{
                  color: DATA_HUE.rainfall,
                  weight: 1,
                  fillColor: DATA_HUE.rainfall,
                  fillOpacity: 0.16 * opacity.hazard,
                }}
              >
                <Tooltip className="fl-tip" direction="top">
                  {mm} mm {offset <= 0 ? "in the last 24 hours" : "forecast (next 72 h)"}
                  <br />
                  {d.name}
                </Tooltip>
              </Circle>
            );
          })}

        {layers.satellite &&
          satelliteFloodExtent.map((f) => (
            <Polygon
              key={f.id}
              positions={f.polygon}
              pathOptions={{
                color: DATA_HUE.floodExtent,
                weight: 1,
                dashArray: "4 3",
                fillColor: DATA_HUE.floodExtent,
                fillOpacity: (f.value != null ? Math.min(0.12 + f.value / 160, 0.75) : 0.3) * opacity.hazard,
              }}
            >
              <Tooltip className="fl-tip" direction="top">
                {f.label}
              </Tooltip>
            </Polygon>
          ))}

        {layers.markets && realSituation &&
          suddenMoves().map((c) => {
            const tooltip = (
              <Tooltip className="fl-tip" direction="top" offset={[0, -6]}>
                <span className="font-medium">{c.city}</span> · PBS week ending {c.week}
                <br />
                {c.moves.length === 0
                  ? `No item moved ${SUDDEN_PCT}% or more since last week`
                  : c.moves.slice(0, 6).map((r) => (
                      <span key={r.item_no}>
                        {(r.wow_pct ?? 0) > 0 ? "▲" : "▼"} {r.item}: {(r.wow_pct ?? 0) > 0 ? "+" : ""}
                        {(r.wow_pct ?? 0).toFixed(1)}%
                        <br />
                      </span>
                    ))}
              </Tooltip>
            );
            return c.moves.length === 0 ? (
              <CircleMarker
                key={`spi-${c.city}`}
                center={c.xy}
                radius={4}
                pathOptions={{ color: "#ffffff", weight: 1, fillColor: "#9ca3af", fillOpacity: 0.9 * opacity.impact }}
              >
                {tooltip}
              </CircleMarker>
            ) : (
              <Marker key={`spi-${c.city}`} position={c.xy} icon={priceTag(c.moves)} opacity={opacity.impact}>
                {tooltip}
              </Marker>
            );
          })}

        {layers.markets && !realSituation &&
          markets.map((m) => {
            const change = marketSpikePct(m);
            const color = RISK_COLOR[cropToColor(change)];
            return (
              <CircleMarker
                key={m.id}
                center={m.location}
                radius={6}
                pathOptions={{
                  color: alpha(color, 0.95),
                  weight: 1,
                  fillColor: color,
                  fillOpacity: 0.65 * opacity.impact,
                }}
              >
                <Tooltip className="fl-tip" direction="top">
                  <span className="font-medium">{m.name}</span>
                  <br />
                  4-week forecast {change > 0 ? "+" : ""}
                  {change.toFixed(1)}% · wheat flour {fmtPkrShort(m.prices[0].current)}/kg now
                </Tooltip>
              </CircleMarker>
            );
          })}

        {layers.gauges &&
          gauges.map((g) => {
            const level = levelAt(g, offset);
            const flow = flowAt(g, offset);
            const color = FLOOD_LEVEL_COLOR[level];
            return (
              <CircleMarker
                key={g.id}
                center={g.location}
                radius={4 + (flow / maxFlow) * 7}
                pathOptions={{
                  color: "#ffffff",
                  weight: 1,
                  fillColor: color,
                  fillOpacity: 0.95,
                }}
              >
                <Tooltip className="fl-tip" direction="top">
                  <span className="font-medium">
                    {g.name} ({g.river})
                  </span>
                  <br />
                  {fmtCusecs(flow)}
                  <br />
                  {FLOOD_LEVEL_LABEL[level]}
                </Tooltip>
              </CircleMarker>
            );
          })}
      </MapContainer>

      <MapLegend
        showRisk={layers.districtRisk}
        showLevels={layers.gauges}
        showMarkets={layers.markets}
      />

      <div className="absolute right-3 top-3 z-[700] flex flex-col gap-1">
        {[
          { icon: Plus, label: "Zoom in", onClick: () => mapRef.current?.zoomIn() },
          { icon: Minus, label: "Zoom out", onClick: () => mapRef.current?.zoomOut() },
          {
            icon: Crosshair,
            label: "Reset view",
            onClick: () => mapRef.current?.flyTo(HOME, 5, { duration: 0.6 }),
          },
        ].map(({ icon: Icon, label, onClick }) => (
          <button
            key={label}
            type="button"
            aria-label={label}
            onClick={onClick}
            className="flex h-7 w-7 items-center justify-center rounded border border-border bg-card/90 text-foreground backdrop-blur transition-colors hover:bg-accent"
          >
            <Icon className="h-4 w-4" />
          </button>
        ))}
      </div>
    </div>
  );
}