import { useEffect, useMemo, useState } from "react";
import { MapContainer, Pane, Polygon, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { LucideIcon } from "lucide-react";
import { CloudRain, Droplets, TriangleAlert, Waves, X } from "lucide-react";
import "leaflet/dist/leaflet.css";
import type { BackendStatus } from "@/data/backend";

export type LiveMetric = "p24" | "p48" | "p72" | "rain1" | "rain2" | "rain3" | "obs7" | "flood2022";

export const METRIC_LABEL: Record<LiveMetric, string> = {
  p24: "Heavy-rain risk · next 24 h",
  p48: "Heavy-rain risk · 48 h",
  p72: "Heavy-rain risk · 72 h",
  rain1: "Forecast rain · tomorrow",
  rain2: "Forecast rain · +2 days",
  rain3: "Forecast rain · +3 days",
  obs7: "Observed rain · last 7 days",
  flood2022: "2022 floods · share of district under water",
};

type Scale = { breaks: number[]; colors: string[]; fmt: (v: number) => string; icon: LucideIcon; unit: string };

// Discrete classes so every colour means one thing; break i is the lower edge of colour i+1.
const RISK: Scale = {
  breaks: [0.01, 0.02, 0.05, 0.1, 0.2],
  colors: ["#fff7cc", "#fed976", "#fd8d3c", "#f03b20", "#bd0026", "#67000d"],
  fmt: (v) => `${Math.round(v * 100)}%`, icon: TriangleAlert, unit: "",
};
const RAIN: Scale = {
  breaks: [1, 5, 10, 25, 50],
  colors: ["#f1f7fd", "#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"],
  fmt: (v) => `${v}`, icon: CloudRain, unit: "mm",
};
const OBS: Scale = { ...RAIN, breaks: [5, 25, 50, 100, 200], icon: Droplets };
const FLOOD: Scale = {
  breaks: [0.01, 0.05, 0.1, 0.25, 0.5],
  colors: ["#f7fcfb", "#c7eae5", "#80cdc1", "#35978f", "#01665e", "#003c30"],
  fmt: (v) => `${Math.round(v * 100)}%`, icon: Waves, unit: "",
};
const SCALE: Record<LiveMetric, Scale> = {
  p24: RISK, p48: RISK, p72: RISK, rain1: RAIN, rain2: RAIN, rain3: RAIN, obs7: OBS, flood2022: FLOOD,
};

const PAKISTAN: [[number, number], [number, number]] = [[23.6, 60.9], [37.1, 77.8]];
const ESRI = "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors";
const ESRI_BASE = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}";
const ESRI_LABELS = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}";

/** Value per district for the chosen layer; undefined when the pipeline has none. */
export function metricValue(status: BackendStatus, id: string, metric: LiveMetric): number | undefined {
  const info = status.district_info?.[id];
  if (metric === "obs7") return info?.obs_7d_mm ?? undefined;
  if (metric === "flood2022") return info?.flood_share_2022 ?? undefined;
  if (metric.startsWith("rain")) return status.live_forecast?.precip_mm[id]?.[metric.slice(4)];
  const horizon = `${metric.slice(1)}h` as "24h" | "48h" | "72h";
  return status.risk?.by_district[id]?.[horizon]?.p;
}

function colorOf(scale: Scale, v: number | undefined) {
  if (v == null) return null;
  const i = scale.breaks.findIndex((b) => v < b);
  return scale.colors[i === -1 ? scale.colors.length - 1 : i];
}

function legendLabels(s: Scale) {
  const f = (v: number) => `${s.fmt(v)}${s.unit ? ` ${s.unit}` : ""}`;
  return s.colors.map((_, i) =>
    i === 0 ? `< ${f(s.breaks[0])}` : i === s.colors.length - 1 ? `≥ ${f(s.breaks[i - 1])}` : `${f(s.breaks[i - 1])} – ${f(s.breaks[i])}`,
  );
}

function fmtPct(p?: number) {
  return p == null ? "—" : p > 0 && p < 0.01 ? "<1%" : `${Math.round(p * 100)}%`;
}

/** Flies to the selected district when it changes from outside the map (e.g. a list click). */
function FlyTo({ status, id }: { status: BackendStatus; id: string | null }) {
  const map = useMap();
  useEffect(() => {
    const d = id ? status.districts.find((x) => x.id === id) : null;
    if (d) map.flyTo(d.centroid, Math.max(map.getZoom(), 7), { duration: 0.8 });
  }, [id, status, map]);
  return null;
}

type LiveMapProps = {
  status: BackendStatus;
  metric: LiveMetric;
  heightClass?: string;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
};

export default function LiveMap({ status, metric, heightClass = "h-[460px]", selected: selectedProp, onSelect }: LiveMapProps) {
  const scale = SCALE[metric];
  const [hover, setHover] = useState<string | null>(null);
  const [selectedLocal, setSelectedLocal] = useState<string | null>(null);
  const selected = selectedProp !== undefined ? selectedProp : selectedLocal;
  const setSelected = (id: string | null) => (onSelect ? onSelect(id) : setSelectedLocal(id));
  const district = useMemo(() => status.districts.find((d) => d.id === selected), [status, selected]);
  const Icon = scale.icon;
  const obsUntil = status.district_info?._meta?.obs_until;

  return (
    <div className={`relative overflow-hidden rounded-md border border-border ${heightClass}`}>
      <MapContainer bounds={PAKISTAN} minZoom={4} scrollWheelZoom className="h-full w-full bg-[#e9eef2]">
        <TileLayer url={ESRI_BASE} attribution={ESRI} maxZoom={16} />
        {status.districts.map((d) => {
          const v = metricValue(status, d.id, metric);
          const fill = colorOf(scale, v);
          const active = hover === d.id || selected === d.id;
          return (
            <Polygon
              key={d.id}
              positions={d.polygon}
              eventHandlers={{
                mouseover: () => setHover(d.id),
                mouseout: () => setHover((h) => (h === d.id ? null : h)),
                click: () => setSelected(d.id),
              }}
              pathOptions={{
                color: active ? "#111827" : "#ffffff",
                weight: active ? 2.2 : 0.7,
                fillColor: fill ?? "#d1d5db",
                fillOpacity: fill ? 0.82 : 0.35,
              }}
            >
              <Tooltip sticky>
                <span className="font-semibold">{d.name}</span>
                <span className="text-muted-foreground"> · {d.province}</span>
                <br />
                {METRIC_LABEL[metric]}:{" "}
                {v == null ? "no data" : metric.startsWith("p") || metric === "flood2022" ? fmtPct(v) : `${v.toFixed(1)} mm`}
              </Tooltip>
            </Polygon>
          );
        })}
        {onSelect && <FlyTo status={status} id={selected} />}
        <Pane name="labels" style={{ zIndex: 650, pointerEvents: "none" }}>
          <TileLayer url={ESRI_LABELS} maxZoom={16} />
        </Pane>
      </MapContainer>

      <div className="pointer-events-none absolute bottom-3 left-3 z-[400] w-56 rounded-md border border-border bg-white/95 p-2.5 text-xs text-slate-800 shadow-md">
        <div className="mb-1.5 flex items-center gap-1.5 font-semibold">
          <Icon className="h-3.5 w-3.5" />
          {METRIC_LABEL[metric]}
        </div>
        <ul className="space-y-0.5">
          {legendLabels(scale).map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              <span className="h-3 w-5 rounded-sm border border-black/10" style={{ background: scale.colors[i] }} />
              <span className="tabular-nums">{label}</span>
            </li>
          ))}
          <li className="flex items-center gap-2 text-slate-500">
            <span className="h-3 w-5 rounded-sm border border-black/10 bg-gray-300/60" /> no data
          </li>
        </ul>
        {metric === "obs7" && obsUntil && <p className="mt-1 text-slate-500">NASA IMERG, 7 days to {obsUntil}</p>}
        {metric === "flood2022" && <p className="mt-1 text-slate-500">UNOSAT, 25 Aug – 7 Sep 2022</p>}
      </div>

      {district && (
        <DistrictCard status={status} id={district.id} name={district.name} province={district.province}
                      onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function DistrictCard({ status, id, name, province, onClose }: {
  status: BackendStatus; id: string; name: string; province: string; onClose: () => void;
}) {
  const risk = status.risk?.by_district[id];
  const rain = status.live_forecast?.precip_mm[id];
  const info = status.district_info?.[id];
  const market = status.market?.nearest_city[id];
  const rows: [string, string][] = [
    ["Heavy-rain risk 24 / 48 / 72 h", `${fmtPct(risk?.["24h"]?.p)} / ${fmtPct(risk?.["48h"]?.p)} / ${fmtPct(risk?.["72h"]?.p)}`],
    ["Forecast rain +1 / +2 / +3 d", rain ? `${["1", "2", "3"].map((k) => (rain[k] ?? 0).toFixed(1)).join(" / ")} mm` : "—"],
    ["Heavy-rain threshold (95th pct)", info?.threshold_mm != null ? `${info.threshold_mm} mm in a day` : "—"],
    ["Observed rain, last 7 days", info?.obs_7d_mm != null ? `${info.obs_7d_mm} mm (wettest pixel ${info.obs_7d_wettest_mm} mm)` : "—"],
    ["2022 floods", info?.flood_share_2022 != null ? `${Math.round(info.flood_share_2022 * 100)}% of district under water` : "—"],
    ["Elevation (centre)", info?.elevation_m != null ? `${info.elevation_m} m${info.coastal ? " · coastal" : ""}` : "—"],
    ["Nearest PBS market", market ? `${market.city} (${market.km} km)` : "—"],
  ];
  return (
    <div className="absolute right-3 top-3 z-[400] w-72 rounded-md border border-border bg-white/97 p-3 text-xs text-slate-800 shadow-lg">
      <div className="mb-2 flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold">{name}</p>
          <p className="text-slate-500">{province}</p>
        </div>
        <button type="button" onClick={onClose} aria-label="Close" className="rounded p-0.5 hover:bg-slate-100">
          <X className="h-4 w-4" />
        </button>
      </div>
      <dl className="space-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3">
            <dt className="text-slate-500">{k}</dt>
            <dd className="text-right font-medium tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>
      {risk?.["24h"]?.row_id && <p className="mt-2 text-[10px] text-slate-400">row {risk["24h"].row_id}</p>}
    </div>
  );
}
