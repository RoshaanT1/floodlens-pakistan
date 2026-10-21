import type { LucideIcon } from "lucide-react";
import { CloudRain, Globe, Map, Sprout, Store, Users, Waves } from "lucide-react";

export type LayerKey =
  | "districtRisk"
  | "gauges"
  | "rainfall"
  | "satellite"
  | "population"
  | "cropland"
  | "markets";

export type GroupKey = "hazard" | "exposure" | "impact";

export type LayerState = Record<LayerKey, boolean>;

export type MapFocus = { lat: number; lng: number; zoom: number; nonce: number };

export type LayerGroup = {
  key: GroupKey;
  label: string;
  source: { name: string; updated: string };
  layers: { key: LayerKey; label: string; icon: LucideIcon; unavailable?: boolean }[];
};

export const DEFAULT_LAYERS: LayerState = {
  districtRisk: true,
  gauges: false,
  rainfall: false,
  satellite: true,
  population: false,
  cropland: false,
  markets: true,
};

export const DEFAULT_OPACITY: Record<GroupKey, number> = {
  hazard: 0.6,
  exposure: 0.5,
  impact: 0.6,
};

export const LAYER_GROUPS: LayerGroup[] = [
  {
    key: "hazard",
    label: "Hazard",
    source: { name: "Model A · Open-Meteo · NASA IMERG", updated: "hourly pipeline" },
    layers: [
      { key: "districtRisk", label: "Heavy-rain risk by district", icon: Map },
      { key: "gauges", label: "River gauges (not available yet)", icon: Waves, unavailable: true },
      { key: "rainfall", label: "Rainfall", icon: CloudRain },
      { key: "satellite", label: "Satellite rainfall, last 7 days", icon: Globe },
    ],
  },
  {
    key: "exposure",
    label: "Exposure",
    source: { name: "not connected yet", updated: "—" },
    layers: [
      { key: "population", label: "Population exposed (not available yet)", icon: Users, unavailable: true },
      { key: "cropland", label: "Cropland affected (not available yet)", icon: Sprout, unavailable: true },
    ],
  },
  {
    key: "impact",
    label: "Impact",
    source: { name: "PBS weekly SPI, 17 cities", updated: "weekly (Thursday)" },
    layers: [{ key: "markets", label: "Sudden food-price changes", icon: Store }],
  },
];