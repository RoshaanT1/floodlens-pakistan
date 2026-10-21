export type RiskLevel = "low" | "moderate" | "high" | "severe";

export type District = {
  id: string;
  name: string;
  province: string;
  centroid: [number, number];
  polygon: [number, number][];
  risk: RiskLevel;
  riskForecast: { date: string; risk: RiskLevel }[];
  /** true where the pipeline has no value for that slider day (drawn grey, never guessed) */
  noData?: boolean[];
  /** rain per slider day (mm): observed wettest point for past days, forecast for today on; null = no data */
  rainByDay?: (number | null)[];
  population: number;
  exposedPopulation: number;
  croplandHa: number;
  drivers: string[];
};

export type Gauge = {
  id: string;
  name: string;
  river: string;
  location: [number, number];
  flowCusecs: number;
  thresholds: {
    low: number;
    medium: number;
    high: number;
    veryHigh: number;
    exceptionallyHigh: number;
  };
  series: { date: string; flowCusecs: number; forecast: boolean }[];
};

export type Alert = {
  id: string;
  severity: "watch" | "warning" | "emergency";
  title: string;
  reason: string;
  districtId: string;
  issuedAt: string;
  /** official document behind the alert (real NDMA alerts) */
  url?: string;
};

export type PriceSeries = {
  commodity: string;
  unit: string;
  current: number;
  history: { date: string; price: number }[];
  forecast: { date: string; price: number; low: number; high: number }[];
  floodLinked: boolean;
  reason: string;
  /** real PBS data: observed % change over the last 2 and 4 weeks (the forecast is the no-change baseline) */
  observedChange2w?: number | null;
  observedChange4w?: number | null;
};

export type Market = {
  id: string;
  name: string;
  location: [number, number];
  prices: PriceSeries[];
};

export type Source = {
  id: string;
  name: string;
  provides: string;
  updateFrequency: string;
  lastUpdated: string;
  url: string;
};

/** Not part of the shared types — additional mock metrics used by the UI. */
export type DistrictMetrics = {
  rain24hMm: number;
  rain72hMm: number;
  soilSaturationPct: number;
};

export type FloodLevelKey =
  | "normal"
  | "low"
  | "medium"
  | "high"
  | "veryHigh"
  | "exceptionallyHigh";