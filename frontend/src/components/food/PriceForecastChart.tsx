import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { realSituation } from "@/data/backend";
import { RISK_COLOR, alpha, cropToColor, fmtDay, fmtDayLong, fmtPkr } from "@/lib/risk";
import { seriesChangePct } from "@/lib/select";
import type { PriceSeries } from "@/data/types";

type PriceForecastChartProps = {
  series: PriceSeries;
  height?: number;
};

type Point = {
  date: string;
  actual?: number;
  forecast?: number;
  base?: number;
  band?: number;
  low?: number;
  high?: number;
};

function PriceTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean;
  payload?: { payload: Point }[];
  unit: string;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const value = point.actual ?? point.forecast;
  if (value == null) return null;

  return (
    <div className="rounded border border-border bg-popover px-2 py-1.5 text-xs shadow-md">
      <p className="text-muted-foreground">
        {fmtDayLong(point.date)} · {point.actual != null ? "observed" : "forecast"}
      </p>
      <p className="font-medium tabular-nums">
        {fmtPkr(value)} <span className="font-normal text-muted-foreground">{unit}</span>
      </p>
      {point.low != null && point.high != null && point.actual == null && (
        <p className="text-muted-foreground tabular-nums">
          80% band {fmtPkr(point.low)} – {fmtPkr(point.high)}
        </p>
      )}
    </div>
  );
}

export default function PriceForecastChart({ series, height = 240 }: PriceForecastChartProps) {
  const lastActual = series.history[series.history.length - 1];
  const color = RISK_COLOR[cropToColor(seriesChangePct(series))];

  const data: Point[] = [
    ...series.history.slice(0, -1).map((h) => ({ date: h.date, actual: h.price })),
    {
      date: lastActual.date,
      actual: lastActual.price,
      forecast: lastActual.price,
      base: lastActual.price,
      band: 0,
    },
    ...series.forecast.map((f) => ({
      date: f.date,
      forecast: f.price,
      base: f.low,
      band: Number((f.high - f.low).toFixed(2)),
      low: f.low,
      high: f.high,
    })),
  ];

  return (
    <div className="text-muted-foreground" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 12, right: 8, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="date"
            tickFormatter={fmtDay}
            interval={5}
            tick={{ fontSize: 10, fill: "currentColor" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            width={56}
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => `${Math.round(v)}`}
            tick={{ fontSize: 10, fill: "currentColor" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<PriceTooltip unit={series.unit} />} />
          <Area
            type="monotone"
            dataKey="base"
            stackId="band"
            stroke="none"
            fill="transparent"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="band"
            stackId="band"
            stroke="none"
            fill={alpha(color, 0.22)}
            isAnimationActive={false}
          />
          <ReferenceLine
            x={lastActual.date}
            stroke="currentColor"
            strokeOpacity={0.35}
            label={{ value: "now", position: "insideTopRight", fontSize: 10, fill: "currentColor" }}
          />
          <Line
            type="monotone"
            dataKey="actual"
            name="Observed"
            stroke="#8FA0B5"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            name={realSituation ? "No-change baseline" : "Forecast"}
            stroke={color}
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}