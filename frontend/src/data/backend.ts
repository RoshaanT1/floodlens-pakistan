import {
  COMMODITIES, DAY_OFFSETS, DISTRICT_METRICS, MOCK_NOW, NOW_INDEX, alerts as mockAlerts, dateAtOffset, districts,
  gauges, markets, satelliteFloodExtent, sources,
} from "./mockData";
import type { District, Market, PriceSeries, RiskLevel, Source } from "./types";

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

export type MarketRow = {
  item_no: number;
  item: string;
  unit: string;
  group: "staples" | "perishables" | "fuel";
  avg_pkr: number | null;
  wow_pct: number | null;
  p10: number | null;
  p90: number | null;
  n_weeks: number | null;
  row_id: string;
  quality_flags: string | null;
};

export type DistrictInfo = {
  threshold_mm?: number;
  obs_7d_mm?: number | null;
  obs_7d_wettest_mm?: number | null;
  elevation_m?: number | null;
  coastal?: boolean;
  flood_share_2022?: number | null;
  flood_prone?: boolean | null;
  /** wettest pixel per UTC day, last ~10 days (NASA IMERG) */
  obs_daily_wettest_mm?: Record<string, number | null>;
  /** declared baseline: this month's share of heavy-rain days (2015-2023) */
  clim_p_month?: number | null;
};

export type Score = { brier: number; lo: number; hi: number; n: number };

export type OfficialAlert = { title: string; published: string; url: string; kind: string };

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
  /** B6: real PBS SPI prices; the range is history, not a forecast. */
  market?: {
    week_end: string;
    source: string;
    range_label: string;
    cities: Record<string, MarketRow[]>;
    city_xy?: Record<string, [number, number]>;
    nearest_city: Record<string, { city: string; km: number }>;
  } | null;
  /** Per-district facts for the map layers and click card; `_meta.obs_until` = newest satellite day. */
  district_info?: Record<string, DistrictInfo> & { _meta?: { obs_until?: string } };
  /** Newest NDMA advisories and situation reports (real titles, dates, links). */
  alerts?: OfficialAlert[];
  /** Model results from backend/docs/*.json (Brier with 95% bootstrap intervals). */
  model_results?: {
    a_test?: {
      model_version: string; n: number; positive_rate: number;
      model: Record<"all" | "monsoon", Record<"24h" | "48h" | "72h", Score>>;
      climatology: Record<"all" | "monsoon", Record<"24h" | "48h" | "72h", Score>>;
      raw_forecast_cut: Record<"all" | "monsoon", Record<"24h" | "48h" | "72h", Score>>;
      diff_vs_climatology: Record<"24h" | "48h" | "72h", { diff: number; lo: number; hi: number }>;
    };
    a_validation?: {
      chosen: string | null; n_train: number; n_validation: number;
      baselines: Record<string, Record<"24h" | "48h" | "72h", Score>>;
      models: Record<string, Record<"24h" | "48h" | "72h", Score>>;
    };
    a_groups?: {
      model: string; period: string;
      groups: { grouping: string; group: string; n: number; events: number; brier: number; lo: number; hi: number; climatology: number; bss: number }[];
      weakest: { grouping: string; group: string; bss: number } | null;
      buner: { day: string; lead: number; forecast_mm: number; threshold_mm: number; observed_mm: number; label: number; p_model: number; p_climatology: number }[];
    };
    b_validation?: {
      n_train: number; n_validation: number; beats_no_change: boolean;
      by_group: Record<string, { n: number; mae_no_change: number; mae_gbm_median: number; coverage_80: number }>;
    };
  };
  /** 52 weeks of PBS city prices for the Food Prices page */
  food?: {
    items: Record<string, string>;
    series: Record<string, Record<string, { unit: string; history: [string, number][]; chg4_p10: number | null; chg4_p90: number | null }>>;
  } | null;
  /** P6 replay of 10-20 Aug 2025 (24 h lead), per day */
  replay?: {
    label: string;
    days: { day: string; districts: number; events: number; hits_top10: number;
            top: { name: string; p: number; event: number }[];
            event_districts: { name: string; rank: number; p: number }[] }[];
  } | null;
  /** Public URL of the Insight API (Cloudflare tunnel to the backend machine). */
  insight_url?: string | null;
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
  ndma_sitrep: {
    name: "NDMA situation reports",
    provides: "Daily monsoon situation reports (casualties, damage, districts named); Insight Agent citations",
    updateFrequency: "Daily in monsoon",
    url: "https://www.ndma.gov.pk/sitreps",
  },
  ndma_advisory: {
    name: "NDMA advisories",
    provides: "Weather, flood and GLOF advisories; alerts panel and Insight Agent citations",
    updateFrequency: "As issued",
    url: "https://www.ndma.gov.pk/advisories",
  },
  ndma_listing: {
    name: "NDMA listing pages",
    provides: "Titles and dates of NDMA documents (catalogue)",
    updateFrequency: "Daily check",
    url: "https://www.ndma.gov.pk",
  },
  pbs_spi_annex: {
    name: "PBS weekly SPI, city annex",
    provides: "Prices of 51 items in 17 cities (min / average / max)",
    updateFrequency: "Weekly (Thursday)",
    url: "https://www.pbs.gov.pk/price-statistics/",
  },
  pbs_spi_annex_archived: {
    name: "PBS weekly SPI, 2023 to Apr 2025",
    provides: "Same annex from PBS's previous site, via Internet Archive copies",
    updateFrequency: "Historical",
    url: "https://web.archive.org/",
  },
  pbs_media_listing: {
    name: "PBS file listings",
    provides: "Index of weekly SPI files (PBS media API, Internet Archive index)",
    updateFrequency: "Daily check",
    url: "https://www.pbs.gov.pk",
  },
  unosat_flood_2022: {
    name: "UNOSAT 2022 flood extent (HDX)",
    provides: "Share of each district under water, Aug–Sep 2022: flood-prone group",
    updateFrequency: "Static",
    url: "https://data.humdata.org/organization/unosat",
  },
  natural_earth_coastline: {
    name: "Natural Earth coastline",
    provides: "Coastal vs inland districts",
    updateFrequency: "Static",
    url: "https://www.naturalearthdata.com",
  },
  open_meteo_elevation: {
    name: "Copernicus DEM via Open-Meteo",
    provides: "Elevation of each district centre: mountain vs plain",
    updateFrequency: "Static",
    url: "https://open-meteo.com/en/docs/elevation-api",
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

/** True once the Situation Room runs on pipeline data instead of the template's sample scenario. */
export let realSituation = false;

// Risk bands: Model A probability of rain above the
// district's own 95th percentile, and for past days the observed wettest pixel vs that threshold.
// Risk relative to the district's normal for this month (the declared climatology baseline):
// 1.5x moderate, 3x high, 6x severe. Without a climatology value, fall back to absolute bands.
const levelFromP = (p: number, clim?: number | null): RiskLevel => {
  if (clim && clim > 0) {
    const r = p / clim;
    return r >= 6 ? "severe" : r >= 3 ? "high" : r >= 1.5 ? "moderate" : "low";
  }
  return p >= 0.2 ? "severe" : p >= 0.1 ? "high" : p >= 0.05 ? "moderate" : "low";
};
const levelFromObs = (mm: number, thr: number): RiskLevel =>
  mm >= thr ? "severe" : mm >= 0.8 * thr ? "high" : mm >= 0.5 * thr ? "moderate" : "low";

/** Replace the Situation Room's sample districts, metrics, gauges and alerts with pipeline data. */
function applySituation(status: BackendStatus) {
  if (!status.districts.length) return;
  MOCK_NOW.setTime(Date.now());
  const real: District[] = status.districts.map((d) => {
    const info = status.district_info?.[d.id];
    const risk = status.risk?.by_district[d.id];
    const rain = status.live_forecast?.precip_mm[d.id];
    const noData: boolean[] = [];
    const rainByDay: (number | null)[] = [];
    const riskForecast = DAY_OFFSETS.map((off) => {
      const date = dateAtOffset(off);
      let level: RiskLevel = "low";
      let missing = true;
      if (off >= 0 && off <= 2) {  // now = next 24 h, +1 = 48 h, +2 = 72 h
        const p = risk?.[(["24h", "48h", "72h"] as const)[off]]?.p;
        if (p != null) { level = levelFromP(p, info?.clim_p_month); missing = false; }
      } else if (off < 0) {
        const mm = info?.obs_daily_wettest_mm?.[date];
        if (mm != null && info?.threshold_mm != null) { level = levelFromObs(mm, info.threshold_mm); missing = false; }
      }
      noData.push(missing);
      // rain for the same day: observed (wettest point) before today, forecast from today on
      rainByDay.push(
        off < 0 ? (info?.obs_daily_wettest_mm?.[date] ?? null)
          : off <= 2 ? (rain?.[String(off + 1)] ?? null) : null,
      );
      return { date, risk: level };
    });
    const drivers = [
      rain ? `Forecast rain next 3 days: ${["1", "2", "3"].map((k) => (rain[k] ?? 0).toFixed(1)).join(" / ")} mm (Open-Meteo latest run)` : null,
      info?.threshold_mm != null ? `Heavy-rain threshold for this district: ${info.threshold_mm} mm in a day (95th percentile, 2015-2023)` : null,
      risk?.["24h"] ? `Model A: ${Math.round(risk["24h"].p * 1000) / 10}% chance in the next 24 h${info?.clim_p_month != null ? ` vs ${Math.round(info.clim_p_month * 1000) / 10}% normal for this month` : ""}` : null,
      info?.obs_7d_mm != null ? `Observed rain, last 7 days: ${info.obs_7d_mm} mm district mean, wettest pixel ${info.obs_7d_wettest_mm} mm (NASA IMERG)` : null,
      info?.flood_share_2022 ? `2022 floods: ${Math.round(info.flood_share_2022 * 100)}% of the district under water (UNOSAT)` : null,
    ].filter((x): x is string => !!x);
    return {
      id: d.id, name: d.name, province: d.province, centroid: d.centroid, polygon: d.polygon,
      risk: riskForecast[NOW_INDEX].risk, riskForecast, noData, rainByDay,
      population: 0, exposedPopulation: 0, croplandHa: 0, drivers,
    };
  });
  districts.splice(0, districts.length, ...real);
  for (const k of Object.keys(DISTRICT_METRICS)) delete DISTRICT_METRICS[k];
  for (const d of real) {
    const rain = status.live_forecast?.precip_mm[d.id];
    DISTRICT_METRICS[d.id] = {
      rain24hMm: Math.round((rain?.["1"] ?? 0) * 10) / 10,
      rain72hMm: Math.round(["1", "2", "3"].reduce((s, k) => s + (rain?.[k] ?? 0), 0) * 10) / 10,
      soilSaturationPct: -1, // no soil-moisture source yet
    };
  }
  gauges.splice(0); // no river-gauge source yet
  // Official NDMA advisories and situation reports as alerts (national documents, real titles).
  const severityOf = (title: string, kind: string): "watch" | "warning" | "emergency" =>
    /exceptionally|very high flood|emergency/i.test(title) ? "emergency"
      : /flood|glof|cyclone|heavy rain|urban flooding/i.test(title) || kind === "advisory" ? "warning"
        : "watch";
  mockAlerts.splice(
    0,
    mockAlerts.length,
    ...(status.alerts ?? []).slice(0, 12).map((a, i) => ({
      id: `ndma-${i}`,
      severity: severityOf(a.title, a.kind),
      title: a.title.replace(/\s*-\s*$/, ""),
      reason: `NDMA ${a.kind}. National document: open it for the districts named and the actions advised.`,
      districtId: "",
      issuedAt: `${a.published}T00:00:00+05:00`,
      url: a.url,
    })),
  );
  // Satellite layer: NASA IMERG rain over the last 7 days (current), districts with >= 10 mm
  const obsUntil = status.district_info?._meta?.obs_until ?? "";
  satelliteFloodExtent.splice(
    0,
    satelliteFloodExtent.length,
    ...status.districts
      .filter((d) => (status.district_info?.[d.id]?.obs_7d_mm ?? 0) >= 10)
      .map((d) => {
        const info = status.district_info?.[d.id];
        return {
          id: `imerg7-${d.id}`,
          label: `${d.name}: ${info?.obs_7d_mm} mm in 7 days to ${obsUntil} (wettest point ${info?.obs_7d_wettest_mm} mm, NASA IMERG)`,
          polygon: d.polygon,
          value: info?.obs_7d_mm ?? 0,
        };
      }),
  );
  realSituation = true;
}

/** Food Prices page on real PBS prices: history, observed changes, and the no-change baseline. */
function applyFood(status: BackendStatus) {
  const food = status.food;
  const xy = status.market?.city_xy;
  if (!food || !xy) return;
  const order = Object.keys(food.items);
  const DAY = 86_400_000;
  const real: Market[] = Object.entries(food.series)
    .filter(([city]) => xy[city])
    .map(([city, items]) => ({
      id: `pbs-${city}`,
      name: city,
      location: xy[city],
      prices: order
        .filter((no) => items[no]?.history.length)
        .map((no): PriceSeries => {
          const s = items[no];
          const hist = s.history.map(([date, price]) => ({ date, price }));
          const current = hist[hist.length - 1].price;
          const back = (k: number) => (hist.length > k ? hist[hist.length - 1 - k].price : null);
          const chg = (k: number) => { const b = back(k); return b ? ((current / b) - 1) * 100 : null; };
          const lastDay = new Date(hist[hist.length - 1].date).getTime();
          const p10 = s.chg4_p10 ?? 0;
          const p90 = s.chg4_p90 ?? 0;
          return {
            commodity: food.items[no],
            unit: s.unit,
            current,
            history: hist,
            // declared baseline (Model B rejected): flat at today's price; band = the series' own past 4-week moves
            forecast: Array.from({ length: 28 }, (_, i) => {
              const f = Math.sqrt((i + 1) / 28);
              return {
                date: new Date(lastDay + (i + 1) * DAY).toISOString().slice(0, 10),
                price: current,
                low: current * (1 + (p10 / 100) * f),
                high: current * (1 + (p90 / 100) * f),
              };
            }),
            floodLinked: false,
            reason: `Forecast = the declared "no change" baseline: Model B did not beat it on validation. The band is the 10th–90th percentile of this item's own 4-week moves in ${city} since 2023 (${p10.toFixed(0)}% to +${p90.toFixed(0)}%).`,
            observedChange2w: chg(2),
            observedChange4w: chg(4),
          };
        }),
    }));
  if (!real.length) return;
  markets.splice(0, markets.length, ...real);
  COMMODITIES.splice(0, COMMODITIES.length, ...order.map((no) => food.items[no]));
}

function apply(status: BackendStatus) {
  applySituation(status);
  applyFood(status);

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
