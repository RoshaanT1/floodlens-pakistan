import { MapContainer, Polygon, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import BaseTiles from "@/components/map/BaseTiles";
import type { BackendStatus } from "@/data/backend";
import { DATA_HUE, alpha } from "@/lib/risk";

export type LiveMetric = "rain1" | "rain2" | "rain3" | "p24" | "p48" | "p72";

export const METRIC_LABEL: Record<LiveMetric, string> = {
  rain1: "Forecast rain +1 d",
  rain2: "Forecast rain +2 d",
  rain3: "Forecast rain +3 d",
  p24: "P(heavy rain) 24 h",
  p48: "P(heavy rain) 48 h",
  p72: "P(heavy rain) 72 h",
};

const RISK_HUE = "#C2410C";
const PAKISTAN: [[number, number], [number, number]] = [[23.6, 60.9], [37.1, 77.8]];

/** Value per district for the chosen metric; undefined when the pipeline has none. */
export function metricValue(status: BackendStatus, districtId: string, metric: LiveMetric): number | undefined {
  if (metric.startsWith("rain")) return status.live_forecast?.precip_mm[districtId]?.[metric.slice(4)];
  const horizon = `${metric.slice(1)}h` as "24h" | "48h" | "72h";
  return status.risk?.by_district[districtId]?.[horizon]?.p;
}

/** Fill strength: rain saturates at 50 mm a day, probability at 1. */
function strength(metric: LiveMetric, v: number) {
  return metric.startsWith("rain") ? Math.min(v / 50, 1) : Math.min(Math.max(v, 0), 1);
}

export default function LiveMap({ status, metric }: { status: BackendStatus; metric: LiveMetric }) {
  const hue = metric.startsWith("rain") ? DATA_HUE.rainfall : RISK_HUE;
  const fmt = (v: number) => (metric.startsWith("rain") ? `${v.toFixed(1)} mm` : `${Math.round(v * 100)}%`);

  return (
    <div className="relative h-[460px] overflow-hidden rounded-md border border-border">
      <MapContainer bounds={PAKISTAN} minZoom={4} scrollWheelZoom className="h-full w-full">
        <BaseTiles />
        {status.districts.map((d) => {
          const v = metricValue(status, d.id, metric);
          return (
            <Polygon
              key={d.id}
              positions={d.polygon}
              pathOptions={{
                color: alpha(hue, 0.55),
                weight: 0.8,
                fillColor: hue,
                fillOpacity: v == null ? 0.02 : 0.08 + 0.72 * strength(metric, v),
              }}
            >
              <Tooltip sticky>
                <span className="font-medium">{d.name}</span>
                <span className="text-muted-foreground"> · {d.province}</span>
                <br />
                {METRIC_LABEL[metric]}: {v == null ? "no data" : fmt(v)}
              </Tooltip>
            </Polygon>
          );
        })}
      </MapContainer>
      <div className="pointer-events-none absolute bottom-2 left-2 z-[400] rounded border border-border bg-card/90 px-2 py-1 text-xs">
        <div className="mb-1 font-medium">{METRIC_LABEL[metric]}</div>
        <div className="flex items-center gap-1">
          <span>{metric.startsWith("rain") ? "0 mm" : "0%"}</span>
          <span
            className="h-2 w-24 rounded"
            style={{ background: `linear-gradient(to right, ${alpha(hue, 0.08)}, ${alpha(hue, 0.8)})` }}
          />
          <span>{metric.startsWith("rain") ? "≥50 mm" : "100%"}</span>
        </div>
      </div>
    </div>
  );
}
