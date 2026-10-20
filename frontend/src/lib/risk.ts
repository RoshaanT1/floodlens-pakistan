import type { FloodLevelKey, RiskLevel } from "@/data/types";

/**
 * Colour is reserved for data. The risk ramp is a sequential,
 * colour-blind-safe scale: pale yellow -> amber -> orange -> deep magenta.
 * It never relies on red-versus-green contrast.
 */
export const RISK_COLOR: Record<RiskLevel, string> = {
  low: "#E7D66A",
  moderate: "#EFA13C",
  high: "#E0613F",
  severe: "#A32A8C",
};

export const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  severe: "Severe",
};

export const RISK_ORDER: RiskLevel[] = ["low", "moderate", "high", "severe"];
export const RISK_RANK: Record<RiskLevel, number> = {
  low: 0,
  moderate: 1,
  high: 2,
  severe: 3,
};

export const FLOOD_LEVEL_ORDER: FloodLevelKey[] = [
  "normal",
  "low",
  "medium",
  "high",
  "veryHigh",
  "exceptionallyHigh",
];

export const FLOOD_LEVEL_COLOR: Record<FloodLevelKey, string> = {
  normal: "#7C8798",
  low: "#E7D66A",
  medium: "#EFA13C",
  high: "#E0613F",
  veryHigh: "#C23A8B",
  exceptionallyHigh: "#7A1E6B",
};

export const FLOOD_LEVEL_LABEL: Record<FloodLevelKey, string> = {
  normal: "Below low flood level",
  low: "Low flood level",
  medium: "Medium flood level",
  high: "High flood level",
  veryHigh: "Very high flood level",
  exceptionallyHigh: "Exceptionally high flood level",
};

export const SEVERITY_COLOR: Record<string, string> = {
  watch: "#E7D66A",
  warning: "#EFA13C",
  emergency: "#A32A8C",
};

export const SEVERITY_LABEL: Record<string, string> = {
  watch: "Watch",
  warning: "Warning",
  emergency: "Emergency",
};

/** Informational hues (non-risk data: rainfall, cropland, flood extent). */
export const DATA_HUE = {
  rainfall: "#4C8FD1",
  cropland: "#57A773",
  floodExtent: "#3E7BB6",
  population: "#9AA6B8",
};

export function alpha(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

/** Mix a hex colour towards another colour — used for legible tints in each theme. */
export function mix(hex: string, toward: string, amount: number): string {
  const a = parseInt(hex.slice(1), 16);
  const b = parseInt(toward.slice(1), 16);
  const channel = (shift: number) => {
    const va = (a >> shift) & 255;
    const vb = (b >> shift) & 255;
    return Math.round(va + (vb - va) * amount);
  };
  return `#${[16, 8, 0]
    .map((s) => channel(s).toString(16).padStart(2, "0"))
    .join("")}`;
}

export const fmtInt = (n: number) => n.toLocaleString("en-US");

export const fmtCompact = (n: number) =>
  n >= 1_000_000
    ? `${(n / 1_000_000).toFixed(2)}M`
    : n >= 1_000
      ? `${Math.round(n / 1_000)}k`
      : `${n}`;

export const fmtPkr = (n: number) =>
  `PKR ${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtPkrShort = (n: number) => `PKR ${Math.round(n)}`;

export const fmtPct = (n: number, digits = 1) =>
  `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n).toFixed(digits)}%`;

export function fmtDay(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
  });
}

export function fmtDayLong(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

export function fmtClock(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function relativeHours(iso: string, now: Date): string {
  const diffMs = now.getTime() - new Date(iso).getTime();
  const h = Math.abs(diffMs) / 3_600_000;
  const label = h < 1 ? `${Math.round(h * 60)} min` : h < 48 ? `${Math.round(h)} h` : `${Math.round(h / 24)} d`;
  return diffMs >= 0 ? `${label} ago` : `in ${label}`;
}

/** Compact cusecs label, e.g. 412,000 cusecs -> "412k cusecs". */
export const fmtCusecs = (n: number) => `${fmtInt(n)} cusecs`;

export const fmtCusecsCompact = (n: number) =>
  n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`;

export function cropToColor(pct: number): RiskLevel {
  const p = Math.abs(pct);
  if (p >= 15) return "severe";
  if (p >= 9) return "high";
  if (p >= 5) return "moderate";
  return "low";
}