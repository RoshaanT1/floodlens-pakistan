import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { NOW_INDEX } from "@/data/mockData";
import { FLOOD_LEVEL_COLOR, fmtCusecs, fmtDay, fmtDayLong } from "@/lib/risk";
import type { FloodLevelKey, Gauge } from "@/data/types";

type GaugeHydrographProps = {
  gauge: Gauge;
  height?: number;
  compact?: boolean;
};

const THRESHOLD_KEYS: (keyof Gauge["thresholds"])[] = [
  "low",
  "medium",
  "high",
  "veryHigh",
  "exceptionallyHigh",
];

const LEVEL_KEY: Record<keyof Gauge["thresholds"], FloodLevelKey> = {
  low: "low",
  medium: "medium",
  high: "high",
  veryHigh: "veryHigh",
  exceptionallyHigh: "exceptionallyHigh",
};

const SHORT: Record<FloodLevelKey, string> = {
  normal: "below low",
  low: "low",
  medium: "medium",
  high: "high",
  veryHigh: "very high",
  exceptionallyHigh: "exceptional",
};

function HydroTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: { date: string; observed: number | null; forecast: number | null } }[];
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const value = point.observed ?? point.forecast;
  if (value == null) return null;
  return (
    <div className="rounded border border-border bg-popover px-2 py-1 text-xs shadow-md">
      <p className="text-muted-foreground">
        {fmtDayLong(point.date)} · {point.forecast != null ? "forecast" : "observed"}
      </p>
      <p className="font-medium tabular-nums">{fmtCusecs(value)}</p>
    </div>
  );
}

export default function GaugeHydrograph({
  gauge,
  height = 148,
  compact = false,
}: GaugeHydrographProps) {
  const data = gauge.series.map((s, i) => ({
    date: s.date,
    observed: i <= NOW_INDEX ? s.flowCusecs : null,
    forecast: i >= NOW_INDEX ? s.flowCusecs : null,
  }));

  const top = gauge.thresholds.exceptionallyHigh;

  return (
    <div className="text-muted-foreground" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 62, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="date"
            tickFormatter={fmtDay}
            interval={compact ? 6 : 4}
            tick={{ fontSize: 10, fill: "currentColor" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            width={40}
            domain={[0, top + 60_000]}
            tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
            tick={{ fontSize: 10, fill: "currentColor" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<HydroTooltip />} />
          {THRESHOLD_KEYS.map((key) => {
            const level = LEVEL_KEY[key];
            return (
              <ReferenceLine
                key={key}
                y={gauge.thresholds[key]}
                stroke={FLOOD_LEVEL_COLOR[level]}
                strokeDasharray="3 3"
                strokeOpacity={0.7}
                label={{
                  value: SHORT[level],
                  position: "insideRight",
                  fontSize: 9,
                  fill: FLOOD_LEVEL_COLOR[level],
                }}
              />
            );
          })}
          <ReferenceLine x={gauge.series[NOW_INDEX].date} stroke="currentColor" strokeOpacity={0.35} />
          <Line
            type="monotone"
            dataKey="observed"
            name="Observed"
            stroke="#8FA0B5"
            strokeWidth={1.8}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            name="Forecast"
            stroke="#EFA13C"
            strokeWidth={1.8}
            strokeDasharray="4 3"
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}