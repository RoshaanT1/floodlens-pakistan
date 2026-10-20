export type RiskLevel = "low" | "moderate" | "high" | "severe";

export type District = {
  id: string;
  name: string;
  province: string;
  centroid: [number, number];
  polygon: [number, number][];
  risk: RiskLevel;
  riskForecast: { date: string; risk: RiskLevel }[];
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
};

export type PriceSeries = {
  commodity: string;
  unit: string;
  current: number;
  history: { date: string; price: number }[];
  forecast: { date: string; price: number; low: number; high: number }[];
  floodLinked: boolean;
  reason: string;
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