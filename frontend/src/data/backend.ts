import { districts, sources } from "./mockData";
import type { Source } from "./types";

/* ------------------------------------------------------------------ *
 * Pipeline output — ../backend writes public/data/status.json with
 * `make export`. Whatever it holds replaces the matching mock values;
 * everything else (risk, gauges, alerts, prices) stays mock until the
 * models publish it.
 * ------------------------------------------------------------------ */
export type QualityDecision = {
  table: string;
  rule: string;
  action: "fix" | "fill" | "flag";
  reason: string;
  n_rows: number;
  decided_at_utc: string;
};

export type BackendStatus = {
  generated_at_utc: string;
  sources: {
    source: string;
    licence: string;
    files: number;
    bytes: number;
    last_fetched_utc: string;
  }[];
  districts: {
    id: string;
    name: string;
    province: string;
    centroid: [number, number];
    polygon: [number, number][];
  }[];
  forecast: { date_utc: string; precip_mm_by_lead: Record<string, Record<string, number>> } | null;
  quality: QualityDecision[];
  /** Latest-run forecast rain, keyed by district then days ahead ("1".."3"). Not a risk score. */
  live_forecast?: {
    fetched_at_utc: string | null;
    label: string;
    precip_mm: Record<string, Record<string, number>>;
  } | null;
  /** Model A output; absent until a validation-stage artifact exists. */
  risk?: {
    model_version: string;
    label: string;
    by_district: Record<string, Record<"24h" | "48h" | "72h", { p: number; row_id: string; date_utc: string }>>;
  } | null;
  pipeline?: {
    last_success_utc: string;
    run_started_utc: string;
    fetch: Record<string, string>;
  } | null;
};

/** Set once at startup; null means the pipeline file was missing and the UI is all mock. */
export let backendStatus: BackendStatus | null = null;

const SOURCE_INFO: Record<string, Omit<Source, "id" | "lastUpdated">> = {
  ocha_cod_ab: {
    name: "OCHA COD-AB via HDX",
    provides: "District boundaries (admin level 2), names, provinces and centroids",
    updateFrequency: "Static snapshot",
    url: "https://data.humdata.org/dataset/cod-ab-pak",
  },
  open_meteo_live_forecast: {
    name: "Open-Meteo latest forecast run",
    provides: "Next 3 days of forecast rainfall per district (live view only, never training)",
    updateFrequency: "Every 6 hours",
    url: "https://open-meteo.com/en/docs/previous-runs-api",
  },
  open_meteo_previous_runs: {
    name: "Open-Meteo Previous Runs",
    provides: "Day 1–3 forecast rainfall, humidity, pressure, cloud and wind per district",
    updateFrequency: "Hourly model runs",
    url: "https://open-meteo.com/en/docs/previous-runs-api",
  },
  imerg_late_daily: {
    name: "NASA GPM IMERG Late (daily)",
    provides: "Observed satellite rainfall, wettest pixel and mean per district",
    updateFrequency: "Daily, ~14 h latency",
    url: "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary",
  },
};

export const formatPkt = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", {
    timeZone: "Asia/Karachi",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }) + " PKT";

function apply(status: BackendStatus) {
  // Real OCHA outlines for the mock scenario districts; ids stay so alerts and markets still link.
  const byName = new Map(status.districts.map((d) => [d.name.toLowerCase(), d]));
  for (const d of districts) {
    const real = byName.get(d.name.toLowerCase());
    if (!real) continue;
    d.centroid = real.centroid;
    d.polygon = real.polygon;
  }

  const pipeline: Source[] = status.sources.map((s) => ({
    id: `pipeline-${s.source}`,
    ...(SOURCE_INFO[s.source] ?? {
      name: s.source,
      provides: `${s.files} raw files`,
      updateFrequency: "—",
      url: "",
    }),
    lastUpdated: formatPkt(s.last_fetched_utc),
  }));
  sources.unshift(...pipeline);
}

export async function loadBackendStatus(): Promise<void> {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/status.json`, { cache: "no-cache" });
    if (!res.ok) return;
    backendStatus = (await res.json()) as BackendStatus;
    apply(backendStatus);
  } catch {
    backendStatus = null; // no pipeline output yet: keep the mock scenario
  }
}
