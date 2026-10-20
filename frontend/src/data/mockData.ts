import type {
  Alert,
  District,
  DistrictMetrics,
  Gauge,
  Market,
  PriceSeries,
  RiskLevel,
  Source,
} from "./types";

/* ------------------------------------------------------------------ *
 * Time base — the situation room is pinned to this mock "now".
 * ------------------------------------------------------------------ */
export const MOCK_NOW_ISO = "2026-10-20T09:00:00+05:00";
export const MOCK_NOW = new Date(MOCK_NOW_ISO);
export const DAY_MS = 86_400_000;
export const DAY_OFFSETS = Array.from({ length: 15 }, (_, i) => i - 7);
export const NOW_INDEX = 7;
// Situation Room and Food Prices run on this sample scenario; real pipeline output is on /live.
export const LIVE_LABEL = "Map and prices: sample scenario";

export const dateAtOffset = (offset: number) =>
  new Date(MOCK_NOW.getTime() + offset * DAY_MS).toISOString().slice(0, 10);

export const timeAtOffset = (offset: number) => new Date(MOCK_NOW.getTime() + offset * DAY_MS);

export const hoursAgo = (hours: number) =>
  new Date(MOCK_NOW.getTime() - hours * 3_600_000).toISOString();

/* ------------------------------------------------------------------ *
 * Deterministic generators — keeps the mock data stable between renders
 * ------------------------------------------------------------------ */
function mulberry(seed: number) {
  let s = seed;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const RANK: Record<RiskLevel, number> = { low: 0, moderate: 1, high: 2, severe: 3 };
const LEVELS: RiskLevel[] = ["low", "moderate", "high", "severe"];

/** Risk ramps towards a crest day, then recedes — a flood wave, not a step. */
export function buildRiskForecast(base: RiskLevel, peak: RiskLevel, peakAt: number) {
  const b = RANK[base];
  const p = RANK[peak];
  return DAY_OFFSETS.map((off) => {
    const t =
      off <= peakAt
        ? (off + 7) / (peakAt + 7)
        : Math.max(0, 1 - ((off - peakAt) / (7 - peakAt + 1)) * 1.05);
    const v = b + (p - b) * Math.pow(t, 1.15);
    const idx = Math.max(0, Math.min(3, Math.round(v)));
    return { date: dateAtOffset(off), risk: LEVELS[idx] };
  });
}

/** Simplified district outline (hand-replaceable with real GeoJSON). */
function poly(
  centroid: [number, number],
  dLat: number,
  dLng: number,
  seed: number,
): [number, number][] {
  const rnd = mulberry(seed);
  const points: [number, number][] = [];
  const n = 7;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + (rnd() - 0.5) * 0.35;
    const r = 0.72 + rnd() * 0.5;
    points.push([
      Number((centroid[0] + Math.sin(a) * dLat * r).toFixed(3)),
      Number((centroid[1] + Math.cos(a) * dLng * r).toFixed(3)),
    ]);
  }
  return points;
}

/* ------------------------------------------------------------------ *
 * Districts
 * ------------------------------------------------------------------ */
type DistrictSpec = {
  id: string;
  name: string;
  province: string;
  centroid: [number, number];
  dLat: number;
  dLng: number;
  seed: number;
  base: RiskLevel;
  peak: RiskLevel;
  peakAt: number;
  population: number;
  exposedPopulation: number;
  croplandHa: number;
  drivers: string[];
};

const DISTRICT_SPECS: DistrictSpec[] = [
  {
    id: "dadu",
    name: "Dadu",
    province: "Sindh",
    centroid: [26.73, 67.78],
    dLat: 0.62,
    dLng: 0.78,
    seed: 11,
    base: "moderate",
    peak: "severe",
    peakAt: 1,
    population: 1_720_000,
    exposedPopulation: 684_000,
    croplandHa: 186_000,
    drivers: [
      "Indus crest from Guddu–Sukkur reach arriving within 24 hours",
      "Riverine embankment stress near Khairpur Nathan Shah",
      "Rice and wheat cropland already saturated from 20–21 October rain",
    ],
  },
  {
    id: "jacobabad",
    name: "Jacobabad",
    province: "Sindh",
    centroid: [28.28, 68.44],
    dLat: 0.5,
    dLng: 0.62,
    seed: 17,
    base: "moderate",
    peak: "severe",
    peakAt: 3,
    population: 1_006_000,
    exposedPopulation: 356_000,
    croplandHa: 121_000,
    drivers: [
      "Upstream Indus crest propagating south along the Guddu barrage canal system",
      "72-hour rainfall forecast of 62 mm over the Jacobabad plain",
      "Begari and Sindh feeder canals already at capacity",
    ],
  },
  {
    id: "larkana",
    name: "Larkana",
    province: "Sindh",
    centroid: [27.56, 68.21],
    dLat: 0.46,
    dLng: 0.6,
    seed: 23,
    base: "moderate",
    peak: "severe",
    peakAt: 4,
    population: 1_524_000,
    exposedPopulation: 448_000,
    croplandHa: 154_000,
    drivers: [
      "Rice Canal and Dadu Canal head discharges above medium flood level",
      "Sukkur–Larkana road section at risk of inundation on day 3",
      "Rain last 24 hours: 34 mm, soils saturated",
    ],
  },
  {
    id: "rajanpur",
    name: "Rajanpur",
    province: "Punjab",
    centroid: [29.1, 70.33],
    dLat: 0.72,
    dLng: 0.68,
    seed: 29,
    base: "low",
    peak: "high",
    peakAt: 4,
    population: 2_050_000,
    exposedPopulation: 214_000,
    croplandHa: 208_000,
    drivers: [
      "Hill torrent flow expected from the Suleiman range after 48 hours",
      "Indus at Taunsa rising through medium flood level",
      "Cotton and wheat cropland in the Katchi canal belt exposed",
    ],
  },
  {
    id: "dg-khan",
    name: "Dera Ghazi Khan",
    province: "Punjab",
    centroid: [30.05, 70.64],
    dLat: 0.7,
    dLng: 0.66,
    seed: 31,
    base: "low",
    peak: "moderate",
    peakAt: 5,
    population: 2_872_000,
    exposedPopulation: 176_000,
    croplandHa: 232_000,
    drivers: [
      "Taunsa–Panjnad reach rising steadily, no crest above high flood level forecast",
      "Rod Kohi torrent channels carrying moderate flow",
      "Rain last 24 hours: 12 mm",
    ],
  },
  {
    id: "swat",
    name: "Swat",
    province: "Khyber Pakhtunkhwa",
    centroid: [34.77, 72.36],
    dLat: 0.5,
    dLng: 0.72,
    seed: 37,
    base: "low",
    peak: "high",
    peakAt: 2,
    population: 2_309_000,
    exposedPopulation: 236_000,
    croplandHa: 88_000,
    drivers: [
      "96 mm rainfall forecast over upper Swat in the next 72 hours",
      "Swat river at Khwazakhela rising through medium flood level",
      "Steep catchments give under 6 hours of lead time",
    ],
  },
  {
    id: "nowshera",
    name: "Nowshera",
    province: "Khyber Pakhtunkhwa",
    centroid: [34.01, 71.98],
    dLat: 0.36,
    dLng: 0.4,
    seed: 41,
    base: "high",
    peak: "severe",
    peakAt: 2,
    population: 1_510_000,
    exposedPopulation: 412_000,
    croplandHa: 64_000,
    drivers: [
      "Kabul river at Nowshera above high flood level and rising",
      "Swat river backflow holding Kabul levels up",
      "Urban flooding in Nowshera Kalan expected within 12 hours",
    ],
  },
  {
    id: "charsadda",
    name: "Charsadda",
    province: "Khyber Pakhtunkhwa",
    centroid: [34.15, 71.74],
    dLat: 0.34,
    dLng: 0.42,
    seed: 43,
    base: "moderate",
    peak: "high",
    peakAt: 1,
    population: 1_624_000,
    exposedPopulation: 298_000,
    croplandHa: 71_000,
    drivers: [
      "Kabul and Swat confluence raising local levels",
      "Sugarcane and maize cropland along the Sardaryab channel exposed",
      "Rain last 24 hours: 41 mm",
    ],
  },
  {
    id: "muzaffargarh",
    name: "Muzaffargarh",
    province: "Punjab",
    centroid: [30.07, 71.19],
    dLat: 0.72,
    dLng: 0.6,
    seed: 47,
    base: "low",
    peak: "high",
    peakAt: 5,
    population: 4_322_000,
    exposedPopulation: 302_000,
    croplandHa: 341_000,
    drivers: [
      "Taunsa barrage discharge above high flood level, rising",
      "Indus floodplain between Taunsa and Panjnad under watch",
      "Large wheat cropland share inside the riverine belt",
    ],
  },
  {
    id: "sibi",
    name: "Sibi",
    province: "Balochistan",
    centroid: [29.55, 67.88],
    dLat: 0.58,
    dLng: 0.74,
    seed: 53,
    base: "low",
    peak: "moderate",
    peakAt: 3,
    population: 402_000,
    exposedPopulation: 48_000,
    croplandHa: 27_000,
    drivers: [
      "Hill torrent risk from Balochistan catchments in the next 72 hours",
      "Nari–Bolan channels carrying moderate flow",
      "Sparse gauge coverage limits verification in this district",
    ],
  },
];

export const districts: District[] = DISTRICT_SPECS.map((s) => {
  const riskForecast = buildRiskForecast(s.base, s.peak, s.peakAt);
  return {
    id: s.id,
    name: s.name,
    province: s.province,
    centroid: s.centroid,
    polygon: poly(s.centroid, s.dLat, s.dLng, s.seed),
    risk: riskForecast[NOW_INDEX].risk,
    riskForecast,
    population: s.population,
    exposedPopulation: s.exposedPopulation,
    croplandHa: s.croplandHa,
    drivers: s.drivers,
  };
});

/** Extra per-district metrics used by the drawer (not part of the shared types). */
export const DISTRICT_METRICS: Record<string, DistrictMetrics> = {
  dadu: { rain24hMm: 46, rain72hMm: 38, soilSaturationPct: 88 },
  jacobabad: { rain24hMm: 28, rain72hMm: 62, soilSaturationPct: 81 },
  larkana: { rain24hMm: 34, rain72hMm: 44, soilSaturationPct: 84 },
  rajanpur: { rain24hMm: 9, rain72hMm: 52, soilSaturationPct: 62 },
  "dg-khan": { rain24hMm: 12, rain72hMm: 34, soilSaturationPct: 57 },
  swat: { rain24hMm: 21, rain72hMm: 96, soilSaturationPct: 69 },
  nowshera: { rain24hMm: 52, rain72hMm: 71, soilSaturationPct: 91 },
  charsadda: { rain24hMm: 41, rain72hMm: 66, soilSaturationPct: 87 },
  muzaffargarh: { rain24hMm: 7, rain72hMm: 41, soilSaturationPct: 64 },
  sibi: { rain24hMm: 4, rain72hMm: 58, soilSaturationPct: 41 },
};

/* ------------------------------------------------------------------ *
 * River gauges and barrages
 * ------------------------------------------------------------------ */
type GaugeSpec = {
  id: string;
  name: string;
  river: string;
  location: [number, number];
  base: number;
  peak: number;
  peakAt: number;
  seed: number;
  thresholds: Gauge["thresholds"];
};

const GAUGE_SPECS: GaugeSpec[] = [
  {
    id: "g-tarbela",
    name: "Tarbela",
    river: "Indus",
    location: [34.09, 72.7],
    base: 288_000,
    peak: 402_000,
    peakAt: 3,
    seed: 101,
    thresholds: { low: 150_000, medium: 250_000, high: 350_000, veryHigh: 450_000, exceptionallyHigh: 600_000 },
  },
  {
    id: "g-chashma",
    name: "Chashma",
    river: "Indus",
    location: [32.43, 71.38],
    base: 418_000,
    peak: 508_000,
    peakAt: 2,
    seed: 103,
    thresholds: { low: 200_000, medium: 300_000, high: 400_000, veryHigh: 500_000, exceptionallyHigh: 650_000 },
  },
  {
    id: "g-taunsa",
    name: "Taunsa",
    river: "Indus",
    location: [30.5, 70.86],
    base: 452_000,
    peak: 615_000,
    peakAt: 4,
    seed: 107,
    thresholds: { low: 200_000, medium: 300_000, high: 450_000, veryHigh: 600_000, exceptionallyHigh: 750_000 },
  },
  {
    id: "g-guddu",
    name: "Guddu",
    river: "Indus",
    location: [28.42, 69.7],
    base: 612_000,
    peak: 806_000,
    peakAt: 3,
    seed: 109,
    thresholds: { low: 300_000, medium: 450_000, high: 600_000, veryHigh: 750_000, exceptionallyHigh: 900_000 },
  },
  {
    id: "g-sukkur",
    name: "Sukkur",
    river: "Indus",
    location: [27.68, 68.85],
    base: 498_000,
    peak: 742_000,
    peakAt: 5,
    seed: 113,
    thresholds: { low: 300_000, medium: 450_000, high: 600_000, veryHigh: 750_000, exceptionallyHigh: 900_000 },
  },
  {
    id: "g-kotri",
    name: "Kotri",
    river: "Indus",
    location: [25.45, 68.31],
    base: 318_000,
    peak: 486_000,
    peakAt: 6,
    seed: 127,
    thresholds: { low: 250_000, medium: 400_000, high: 550_000, veryHigh: 700_000, exceptionallyHigh: 900_000 },
  },
  {
    id: "g-marala",
    name: "Marala",
    river: "Chenab",
    location: [32.65, 74.46],
    base: 268_000,
    peak: 392_000,
    peakAt: 4,
    seed: 131,
    thresholds: { low: 150_000, medium: 250_000, high: 350_000, veryHigh: 450_000, exceptionallyHigh: 600_000 },
  },
  {
    id: "g-nowshera",
    name: "Nowshera",
    river: "Kabul",
    location: [34.01, 71.98],
    base: 186_000,
    peak: 268_000,
    peakAt: 2,
    seed: 137,
    thresholds: { low: 60_000, medium: 100_000, high: 150_000, veryHigh: 200_000, exceptionallyHigh: 300_000 },
  },
];

function buildGaugeSeries(spec: GaugeSpec) {
  const rnd = mulberry(spec.seed);
  return DAY_OFFSETS.map((off) => {
    const t =
      off <= spec.peakAt
        ? (off + 7) / (spec.peakAt + 7)
        : Math.max(0, 1 - (off - spec.peakAt) / (7 - spec.peakAt + 1));
    const v = spec.base + (spec.peak - spec.base) * Math.pow(t, 1.4);
    const wobble = 1 + (rnd() - 0.5) * 0.045;
    return {
      date: dateAtOffset(off),
      flowCusecs: Math.round((v * wobble) / 100) * 100,
      forecast: off > 0,
    };
  });
}

export const gauges: Gauge[] = GAUGE_SPECS.map((s) => {
  const series = buildGaugeSeries(s);
  return {
    id: s.id,
    name: s.name,
    river: s.river,
    location: s.location,
    flowCusecs: series[NOW_INDEX].flowCusecs,
    thresholds: s.thresholds,
    series,
  };
});

/* ------------------------------------------------------------------ *
 * Alerts
 * ------------------------------------------------------------------ */
export const alerts: Alert[] = [
  {
    id: "a-01",
    severity: "emergency",
    title: "Kabul river above very high flood level",
    reason:
      "Discharge 186,000 cusecs and rising; urban flooding in Nowshera Kalan expected within 12 hours.",
    districtId: "nowshera",
    issuedAt: hoursAgo(2),
  },
  {
    id: "a-02",
    severity: "emergency",
    title: "Indus cresting at Sukkur barrage reach",
    reason:
      "Guddu–Sukkur reach at 612,000 cusecs; embankment stress near Khairpur Nathan Shah, Dadu district.",
    districtId: "dadu",
    issuedAt: hoursAgo(5),
  },
  {
    id: "a-03",
    severity: "warning",
    title: "Flood risk upgraded to high for three days",
    reason: "Upstream Indus crest propagating south with 62 mm rain forecast over the Jacobabad plain.",
    districtId: "jacobabad",
    issuedAt: hoursAgo(9),
  },
  {
    id: "a-04",
    severity: "warning",
    title: "Rice cropland inundation risk along Rice Canal",
    reason: "Canal head discharge above medium flood level; 154,000 ha of cropland inside the belt.",
    districtId: "larkana",
    issuedAt: hoursAgo(15),
  },
  {
    id: "a-05",
    severity: "warning",
    title: "Kabul and Swat confluence raising local levels",
    reason: "41 mm rain in 24 hours; sugarcane and maize cropland along Sardaryab channel exposed.",
    districtId: "charsadda",
    issuedAt: hoursAgo(22),
  },
  {
    id: "a-06",
    severity: "warning",
    title: "96 mm rainfall forecast over upper Swat",
    reason: "Steep catchments give less than six hours of lead time; watch Khwazakhela gauge.",
    districtId: "swat",
    issuedAt: hoursAgo(30),
  },
  {
    id: "a-07",
    severity: "watch",
    title: "Hill torrent flow expected from Suleiman range",
    reason: "Rod Kohi channels likely to carry water after 48 hours; Katchi belt cropland at risk.",
    districtId: "rajanpur",
    issuedAt: hoursAgo(44),
  },
  {
    id: "a-08",
    severity: "watch",
    title: "Indus floodplain under watch near Taunsa–Panjnad",
    reason: "Taunsa discharge above high flood level and rising steadily; 341,000 ha cropland in belt.",
    districtId: "muzaffargarh",
    issuedAt: hoursAgo(52),
  },
  {
    id: "a-09",
    severity: "watch",
    title: "Hill torrent risk from Balochistan catchments",
    reason: "Nari–Bolan channels carrying moderate flow; limited gauge coverage for verification.",
    districtId: "sibi",
    issuedAt: hoursAgo(68),
  },
];

/* ------------------------------------------------------------------ *
 * Satellite flood extent (simplified observed footprints)
 * ------------------------------------------------------------------ */
export const satelliteFloodExtent: { id: string; label: string; polygon: [number, number][] }[] = [
  {
    id: "sfe-dadu",
    label: "Sukkur–Dadu riverine inundation",
    polygon: [
      [26.95, 68.05],
      [26.82, 68.24],
      [26.58, 68.2],
      [26.44, 67.94],
      [26.62, 67.72],
      [26.86, 67.78],
    ],
  },
  {
    id: "sfe-nowshera",
    label: "Kabul river backflow, Nowshera",
    polygon: [
      [34.14, 71.92],
      [34.05, 72.04],
      [33.94, 71.98],
      [33.96, 71.84],
      [34.08, 71.82],
    ],
  },
  {
    id: "sfe-charsadda",
    label: "Swat confluence floodplain",
    polygon: [
      [34.24, 71.66],
      [34.16, 71.82],
      [34.04, 71.76],
      [34.08, 71.58],
      [34.2, 71.56],
    ],
  },
];

/* ------------------------------------------------------------------ *
 * Markets and food prices (PKR)
 * ------------------------------------------------------------------ */
type PriceSpec = {
  commodity: string;
  unit: string;
  current: number;
  drift: number; // total fractional change over the next 21 days
  band: number; // fractional half-width of the 80% interval at 21 days
  floodLinked: boolean;
  reason: string;
};

type MarketSpec = {
  id: string;
  name: string;
  location: [number, number];
  districtId: string;
  prices: PriceSpec[];
};

const MARKET_SPECS: MarketSpec[] = [
  {
    id: "mkt-dadu",
    name: "Dadu Mandi",
    location: [26.73, 67.78],
    districtId: "dadu",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 112.5,
        drift: 0.11,
        band: 0.05,
        floodLinked: true,
        reason:
          "Mehar–Khairpur Nathan Shah road likely submerged by day 2, cutting mill dispatches from Larkana.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 168,
        drift: 0.08,
        band: 0.06,
        floodLinked: true,
        reason: "Rice mills in the Sukkur–Dadu belt lose inbound paddy from inundated fields.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 148,
        drift: 0.19,
        band: 0.09,
        floodLinked: true,
        reason: "Perishable produce rerouted 90 km north; spoilage on the longer route.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 96,
        drift: 0.12,
        band: 0.07,
        floodLinked: true,
        reason: "Storage godowns at Mehar inside the inundation footprint of the satellite pass.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 268,
        drift: 0.04,
        band: 0.04,
        floodLinked: false,
        reason: "Supplies continue from Punjab; only a small transport premium expected.",
      },
    ],
  },
  {
    id: "mkt-sukkur",
    name: "Sukkur",
    location: [27.7, 68.86],
    districtId: "dadu",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 108,
        drift: 0.09,
        band: 0.04,
        floodLinked: true,
        reason: "Flour mills on the Sukkur bypass lose road access to Dadu and Khairpur markets.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 172,
        drift: 0.06,
        band: 0.05,
        floodLinked: true,
        reason: "Paddy arrivals to Sukkur markets down as riverine fields are inundated.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 132,
        drift: 0.14,
        band: 0.08,
        floodLinked: true,
        reason: "Trucking from Balochistan delayed by the closure of the N-55 spur.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 88,
        drift: 0.1,
        band: 0.06,
        floodLinked: true,
        reason: "Local storage stock reduced; imports via the Indus Highway carry a premium.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 255,
        drift: 0.03,
        band: 0.03,
        floodLinked: false,
        reason: "Stable pipeline from Punjab mills; demand effect minimal so far.",
      },
    ],
  },
  {
    id: "mkt-larkana",
    name: "Larkana",
    location: [27.56, 68.21],
    districtId: "larkana",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 115,
        drift: 0.13,
        band: 0.05,
        floodLinked: true,
        reason: "Mills drawing on reduced stock as dispatch routes through the riverine belt close.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 164,
        drift: 0.09,
        band: 0.05,
        floodLinked: true,
        reason: "Standing crop losses upstream of the Rice Canal head.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 155,
        drift: 0.21,
        band: 0.1,
        floodLinked: true,
        reason: "Sukkur–Larkana road section inundation on day 3 lengthens every supply route.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 102,
        drift: 0.15,
        band: 0.07,
        floodLinked: true,
        reason: "Wholesale arrivals down 30% week on week as godown access is cut.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 262,
        drift: 0.05,
        band: 0.04,
        floodLinked: false,
        reason: "Adequate wholesale stock; forecast driven by transport costs only.",
      },
    ],
  },
  {
    id: "mkt-jacobabad",
    name: "Jacobabad",
    location: [28.28, 68.44],
    districtId: "jacobabad",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 119.5,
        drift: 0.14,
        band: 0.06,
        floodLinked: true,
        reason: "Supplies routed via the Sindh feeder canal road, expected to flood on day 3.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 176,
        drift: 0.07,
        band: 0.06,
        floodLinked: true,
        reason: "Local milling capacity offline where the town supply road is submerged.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 162,
        drift: 0.18,
        band: 0.09,
        floodLinked: true,
        reason: "Quetta–Sibi–Jacobabad corridor disrupted by hill torrent flow.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 110,
        drift: 0.16,
        band: 0.08,
        floodLinked: true,
        reason: "Storage across the border districts of Sindh and Balochistan affected.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 275,
        drift: 0.06,
        band: 0.04,
        floodLinked: true,
        reason: "Small flood-linked premium as pulses move on the same disrupted corridors.",
      },
    ],
  },
  {
    id: "mkt-nowshera",
    name: "Nowshera",
    location: [34.01, 71.98],
    districtId: "nowshera",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 122,
        drift: 0.1,
        band: 0.05,
        floodLinked: true,
        reason: "Flour mills on the Kabul river bank at risk; Peshawar road diversions expected.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 182,
        drift: 0.05,
        band: 0.05,
        floodLinked: false,
        reason: "Supplied from Punjab; unaffected supply chain so far.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 175,
        drift: 0.22,
        band: 0.11,
        floodLinked: true,
        reason: "Swat valley vegetable arrivals halted while the highway is closed at Chakdara.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 118,
        drift: 0.17,
        band: 0.09,
        floodLinked: true,
        reason: "Urban flooding in Nowshera Kalan disrupts the main wholesale bazaar.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 288,
        drift: 0.04,
        band: 0.03,
        floodLinked: false,
        reason: "Peshawar supply pipeline intact; transport cost only.",
      },
    ],
  },
  {
    id: "mkt-charsadda",
    name: "Charsadda",
    location: [34.15, 71.74],
    districtId: "charsadda",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 124.5,
        drift: 0.08,
        band: 0.05,
        floodLinked: true,
        reason: "Mill access roads through the floodplain at risk on day 2.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 186,
        drift: 0.04,
        band: 0.04,
        floodLinked: false,
        reason: "Punjab pipeline unaffected; forecast follows the national trend.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 168,
        drift: 0.16,
        band: 0.09,
        floodLinked: true,
        reason: "Local vegetable belt along Sardaryab channel exposed to inundation.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 122,
        drift: 0.14,
        band: 0.08,
        floodLinked: true,
        reason: "Bazaar closed during flooding; re-supply delayed by road closures.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 292,
        drift: 0.03,
        band: 0.03,
        floodLinked: false,
        reason: "No flood exposure on the supply route; stable wholesale prices.",
      },
    ],
  },
  {
    id: "mkt-dgkhan",
    name: "Dera Ghazi Khan",
    location: [30.05, 70.64],
    districtId: "dg-khan",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 110,
        drift: 0.05,
        band: 0.04,
        floodLinked: false,
        reason: "Local mill capacity healthy; no route closures forecast this week.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 158,
        drift: 0.04,
        band: 0.04,
        floodLinked: false,
        reason: "Supplies from Punjab markets continue normally.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 128,
        drift: 0.1,
        band: 0.07,
        floodLinked: true,
        reason: "Hill torrent flow expected to interrupt the Suleiman range supply road.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 92,
        drift: 0.07,
        band: 0.05,
        floodLinked: true,
        reason: "Indus Highway diversions add a small transport premium.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 258,
        drift: 0.02,
        band: 0.03,
        floodLinked: false,
        reason: "Stable pipeline; forecast driven by seasonal trend only.",
      },
    ],
  },
  {
    id: "mkt-rajanpur",
    name: "Rajanpur",
    location: [29.1, 70.33],
    districtId: "rajanpur",
    prices: [
      {
        commodity: "Wheat flour",
        unit: "PKR/kg",
        current: 113.5,
        drift: 0.09,
        band: 0.05,
        floodLinked: true,
        reason: "Katchi belt mill access at risk if hill torrent flow crosses the Indus Highway.",
      },
      {
        commodity: "Rice (IRRI-6)",
        unit: "PKR/kg",
        current: 162,
        drift: 0.05,
        band: 0.04,
        floodLinked: false,
        reason: "Local supply adequate; no upstream disruption to this market.",
      },
      {
        commodity: "Tomatoes",
        unit: "PKR/kg",
        current: 141,
        drift: 0.13,
        band: 0.08,
        floodLinked: true,
        reason: "Rod Kohi channels expected to cut the Rajanpur–Jampur road for 48 hours.",
      },
      {
        commodity: "Onions",
        unit: "PKR/kg",
        current: 99,
        drift: 0.11,
        band: 0.06,
        floodLinked: true,
        reason: "Storage in the floodplain under watch; stock repositioning adds cost.",
      },
      {
        commodity: "Pulses (chana dal)",
        unit: "PKR/kg",
        current: 264,
        drift: 0.03,
        band: 0.03,
        floodLinked: false,
        reason: "Supplies from Muzaffargarh continue; minimal flood exposure.",
      },
    ],
  },
];

function buildPriceSeries(spec: PriceSpec, seed: number): PriceSeries {
  const rnd = mulberry(seed);
  const history = Array.from({ length: 30 }, (_, i) => {
    const offset = i - 29;
    const trend = 1 + spec.drift * 0.5 * (offset / 21);
    const noise = 1 + (rnd() - 0.5) * 0.022;
    const price = i === 29 ? spec.current : spec.current * trend * noise;
    return { date: dateAtOffset(offset), price: Number(price.toFixed(2)) };
  });

  const forecast = Array.from({ length: 28 }, (_, i) => {
    const day = i + 1;
    const t = day / 28;
    const price = spec.current * (1 + spec.drift * t);
    const halfBand = spec.current * spec.band * Math.pow(t, 0.85);
    return {
      date: dateAtOffset(day),
      price: Number(price.toFixed(2)),
      low: Number(Math.max(0, price - halfBand).toFixed(2)),
      high: Number((price + halfBand).toFixed(2)),
    };
  });

  return {
    commodity: spec.commodity,
    unit: spec.unit,
    current: spec.current,
    history,
    forecast,
    floodLinked: spec.floodLinked,
    reason: spec.reason,
  };
}

export const markets: Market[] = MARKET_SPECS.map((m, mi) => ({
  id: m.id,
  name: m.name,
  location: m.location,
  prices: m.prices.map((p, pi) => buildPriceSeries(p, 900 + mi * 17 + pi * 7)),
}));

/** Which district each market sits in — used to link prices to flood risk. */
export const MARKET_DISTRICT: Record<string, string> = Object.fromEntries(
  MARKET_SPECS.map((m) => [m.id, m.districtId]),
);

export const COMMODITIES = [
  "Wheat flour",
  "Rice (IRRI-6)",
  "Tomatoes",
  "Onions",
  "Pulses (chana dal)",
];

/* ------------------------------------------------------------------ *
 * Sources
 * ------------------------------------------------------------------ */
export const sources: Source[] = [
  {
    id: "src-pmd",
    name: "Pakistan Meteorological Department (PMD)",
    provides: "Rainfall observations and 72-hour numerical rainfall forecasts",
    updateFrequency: "Every 6 hours",
    lastUpdated: "20 Oct 2026, 05:00 PKT",
    url: "https://www.pmd.gov.pk",
  },
  {
    id: "src-ffd",
    name: "Flood Forecasting Division (FFD), PMD",
    provides: "River discharge forecasts and official flood warnings",
    updateFrequency: "Daily, 09:00 PKT",
    lastUpdated: "20 Oct 2026, 09:00 PKT",
    url: "https://ffd.pmd.gov.pk",
  },
  {
    id: "src-wapda",
    name: "WAPDA",
    provides: "Barrage and reservoir releases, gauge readings in cusecs",
    updateFrequency: "Every 3 hours",
    lastUpdated: "20 Oct 2026, 08:00 PKT",
    url: "https://www.wapda.gov.pk",
  },
  {
    id: "src-ndma",
    name: "National Disaster Management Authority (NDMA)",
    provides: "District flood alerts and damage reports",
    updateFrequency: "Daily",
    lastUpdated: "20 Oct 2026, 07:30 PKT",
    url: "https://www.ndma.gov.pk",
  },
  {
    id: "src-suparco",
    name: "SUPARCO",
    provides: "Sentinel-1 and Landsat derived satellite flood extent",
    updateFrequency: "Two passes daily (12 hours)",
    lastUpdated: "20 Oct 2026, 03:10 PKT",
    url: "https://www.suparco.gov.pk",
  },
  {
    id: "src-wfp",
    name: "WFP VAM",
    provides: "Food price monitoring and market baselines",
    updateFrequency: "Weekly",
    lastUpdated: "18 Oct 2026, 12:00 PKT",
    url: "https://dataviz.vam.wfp.org",
  },
  {
    id: "src-pbs",
    name: "Pakistan Bureau of Statistics (PBS)",
    provides: "Weekly retail and wholesale price indices",
    updateFrequency: "Weekly",
    lastUpdated: "17 Oct 2026, 10:00 PKT",
    url: "https://www.pbs.gov.pk",
  },
  {
    id: "src-gloflas",
    name: "Copernicus GloFAS",
    provides: "Global flood awareness, 30-day river discharge forecast",
    updateFrequency: "Daily",
    lastUpdated: "20 Oct 2026, 02:00 PKT",
    url: "https://globalfloods.eu",
  },
  {
    id: "src-osm",
    name: "OpenStreetMap",
    provides: "District outlines, settlement locations and road network",
    updateFrequency: "Continuous",
    lastUpdated: "20 Oct 2026, 06:40 PKT",
    url: "https://www.openstreetmap.org",
  },
];

/** Layer provenance lines shown under each layer group. */
export const LAYER_SOURCES = {
  hazard: { name: "FFD / PMD", updated: "09:00 PKT · 2 h ago" },
  exposure: { name: "Census 2023 · PBS", updated: "2023 census · static" },
  impact: { name: "WFP VAM · PBS", updated: "18 Oct 2026 · 2 d ago" },
} as const;