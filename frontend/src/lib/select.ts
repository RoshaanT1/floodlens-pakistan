import {
  DAY_MS,
  DISTRICT_METRICS,
  MARKET_DISTRICT,
  MOCK_NOW,
  NOW_INDEX,
  alerts,
  districts,
  gauges,
  markets,
  timeAtOffset,
} from "@/data/mockData";
import type {
  Alert,
  District,
  FloodLevelKey,
  Gauge,
  Market,
  PriceSeries,
  RiskLevel,
} from "@/data/types";
import { RISK_RANK } from "./risk";
import { realSituation } from "@/data/backend";

export { dateAtOffset, timeAtOffset, LIVE_LABEL } from "@/data/mockData";

export const indexForOffset = (offset: number) =>
  Math.max(0, Math.min(14, offset + NOW_INDEX));

export function riskAt(district: District, offset: number): RiskLevel {
  return district.riskForecast[indexForOffset(offset)].risk;
}

export function flowAt(gauge: Gauge, offset: number): number {
  return gauge.series[indexForOffset(offset)].flowCusecs;
}

export function levelAt(gauge: Gauge, offset: number): FloodLevelKey {
  const flow = flowAt(gauge, offset);
  const t = gauge.thresholds;
  if (flow >= t.exceptionallyHigh) return "exceptionallyHigh";
  if (flow >= t.veryHigh) return "veryHigh";
  if (flow >= t.high) return "high";
  if (flow >= t.medium) return "medium";
  if (flow >= t.low) return "low";
  return "normal";
}

export const isAboveHighFlood = (gauge: Gauge, offset: number) =>
  flowAt(gauge, offset) >= gauge.thresholds.high;

/** Alerts still in force at the selected time (issued at or before it, within 96 hours). */
export function activeAlerts(offset: number): Alert[] {
  if (realSituation) return [...alerts]; // official NDMA documents, newest first
  const t = timeAtOffset(offset);
  const order = { emergency: 0, warning: 1, watch: 2 } as const;
  return alerts
    .filter((a) => {
      const issued = new Date(a.issuedAt).getTime();
      return issued <= t.getTime() && t.getTime() - issued <= 96 * 3_600_000;
    })
    .sort(
      (a, b) =>
        order[a.severity] - order[b.severity] ||
        new Date(b.issuedAt).getTime() - new Date(a.issuedAt).getTime(),
    );
}

export function alertsByDistrict(offset: number): Record<string, Alert["severity"]> {
  const rank = { watch: 0, warning: 1, emergency: 2 } as const;
  const out: Record<string, Alert["severity"]> = {};
  for (const a of activeAlerts(offset)) {
    const current = out[a.districtId];
    if (!current || rank[a.severity] > rank[current]) out[a.districtId] = a.severity;
  }
  return out;
}

export function seriesChangePct(series: PriceSeries): number {
  if (series.observedChange4w !== undefined) return series.observedChange4w ?? 0; // real: last 4 weeks, observed
  const last = series.forecast[series.forecast.length - 1];
  return ((last.price - series.current) / series.current) * 100;
}

/** Forecast change over the next 2 weeks (day 14 of the forecast). */
export function seriesChangePctAt(series: PriceSeries, day: number): number {
  if (series.observedChange4w !== undefined) return (day <= 14 ? series.observedChange2w : series.observedChange4w) ?? 0;
  const point = series.forecast[Math.min(day, series.forecast.length) - 1];
  return ((point.price - series.current) / series.current) * 100;
}

export function marketSpikePct(market: Market): number {
  return Math.max(...market.prices.map(seriesChangePct));
}

export function marketFloodLinked(market: Market): boolean {
  return market.prices.some((p) => p.floodLinked);
}

export function confidenceOf(series: PriceSeries): "High" | "Medium" | "Low" {
  const last = series.forecast[series.forecast.length - 1];
  const width = (last.high - last.low) / series.current;
  if (width <= 0.08) return "High";
  if (width <= 0.15) return "Medium";
  return "Low";
}

export function confidenceBand(series: PriceSeries) {
  const last = series.forecast[series.forecast.length - 1];
  return { low: last.low, high: last.high, width: ((last.high - last.low) / series.current) * 100 };
}

export type Kpis = {
  districtsAtRisk: number;
  peopleExposed: number;
  gaugesAboveHigh: number;
  marketsWithSpike: number;
  newAlerts: number;
};

export const SPIKE_THRESHOLD = 15;

export function computeKpis(offset: number): Kpis {
  const atRisk = districts.filter((d) => RISK_RANK[riskAt(d, offset)] >= 2);
  return {
    districtsAtRisk: atRisk.length,
    peopleExposed: atRisk.reduce((sum, d) => sum + d.exposedPopulation, 0),
    gaugesAboveHigh: gauges.filter((g) => isAboveHighFlood(g, offset)).length,
    marketsWithSpike: markets.filter((m) => marketSpikePct(m) >= SPIKE_THRESHOLD).length,
    newAlerts: activeAlerts(offset).length,
  };
}

function distanceKm(a: [number, number], b: [number, number]): number {
  const dLat = (b[0] - a[0]) * 111;
  const dLng = (b[1] - a[1]) * 111 * Math.cos(((a[0] + b[0]) / 2) * (Math.PI / 180));
  return Math.sqrt(dLat * dLat + dLng * dLng);
}

export function nearestGauges(district: District, count = 3): Gauge[] {
  return [...gauges]
    .sort(
      (a, b) =>
        distanceKm(district.centroid, a.location) - distanceKm(district.centroid, b.location),
    )
    .slice(0, count);
}

export function nearestMarkets(district: District, count = 3): Market[] {
  return [...markets]
    .sort(
      (a, b) =>
        distanceKm(district.centroid, a.location) - distanceKm(district.centroid, b.location),
    )
    .slice(0, count);
}

export function marketAt(index: number): Market {
  return markets[Math.max(0, Math.min(markets.length - 1, index))];
}

export const marketDistrictId = (market: Market) => MARKET_DISTRICT[market.id];

export function metricsFor(district: District) {
  return (
    DISTRICT_METRICS[district.id] ?? { rain24hMm: 0, rain72hMm: 0, soilSaturationPct: 0 }
  );
}

export function districtById(id: string | null): District | null {
  return id ? districts.find((d) => d.id === id) ?? null : null;
}

/** Rainfall layer label flips between observed and forecast with the time slider. */
export function rainfallLabel(offset: number) {
  if (realSituation) return offset < 0 ? "Rainfall (observed that day)" : "Rainfall (forecast for that day)";
  return offset <= 0 ? "Rainfall (last 24 hours)" : "Rainfall (next 72 hours)";
}

export function rainfallValue(district: District, offset: number) {
  if (district.rainByDay) return district.rainByDay[indexForOffset(offset)] ?? 0;
  const m = metricsFor(district);
  return offset <= 0 ? m.rain24hMm : m.rain72hMm;
}

export function sliderLabel(offset: number) {
  if (offset === 0) return "Now";
  if (offset < 0) return `Observed · ${Math.abs(offset)} d ago`;
  return `Forecast · +${offset} d`;
}

export function observedForecastLabel(offset: number) {
  return offset <= 0 ? "Observed" : "Forecast";
}

export const dayLabel = (offset: number) =>
  new Date(MOCK_NOW.getTime() + offset * DAY_MS).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });