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
  layers: { key: LayerKey; label: string; icon: LucideIcon }[];
};

export const DEFAULT_LAYERS: LayerState = {
  districtRisk: true,
  gauges: true,
  rainfall: false,
  satellite: false,
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
    source: { name: "FFD / PMD", updated: "09:00 PKT · 2 h ago" },
    layers: [
      { key: "districtRisk", label: "Flood risk forecast by district", icon: Map },
      { key: "gauges", label: "River gauges and barrages", icon: Waves },
      { key: "rainfall", label: "Rainfall", icon: CloudRain },
      { key: "satellite", label: "Satellite flood extent", icon: Globe },
    ],
  },
  {
    key: "exposure",
    label: "Exposure",
    source: { name: "Census 2023 · PBS", updated: "2023 census · static" },
    layers: [
      { key: "population", label: "Population exposed", icon: Users },
      { key: "cropland", label: "Cropland affected", icon: Sprout },
    ],
  },
  {
    key: "impact",
    label: "Impact",
    source: { name: "WFP VAM · PBS", updated: "18 Oct 2026 · 2 d ago" },
    layers: [{ key: "markets", label: "Food-price forecast by market", icon: Store }],
  },
];