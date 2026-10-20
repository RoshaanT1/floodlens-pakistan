import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { NOW_INDEX } from "@/data/mockData";
import { RISK_COLOR, RISK_LABEL, fmtDay, fmtDayLong } from "@/lib/risk";
import type { RiskLevel } from "@/data/types";

type RiskTrendChartProps = {
  forecast: { date: string; risk: RiskLevel }[];
  height?: number;
};

function RiskTooltip({ active, payload }: { active?: boolean; payload?: { payload: { date: string; risk: RiskLevel } }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded border border-border bg-popover px-2 py-1 text-xs shadow-md">
      <p className="text-muted-foreground">{fmtDayLong(point.date)}</p>
      <p className="font-medium" style={{ color: RISK_COLOR[point.risk] }}>
        {RISK_LABEL[point.risk]} risk
      </p>
    </div>
  );
}

export default function RiskTrendChart({ forecast, height = 104 }: RiskTrendChartProps) {
  const data = forecast.map((f) => ({ ...f, value: 1 }));

  return (
    <div className="text-muted-foreground" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 14, right: 4, bottom: 0, left: 4 }} barCategoryGap={2}>
          <XAxis
            dataKey="date"
            tickFormatter={fmtDay}
            interval={2}
            tick={{ fontSize: 10, fill: "currentColor" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide domain={[0, 1]} />
          <Tooltip content={<RiskTooltip />} cursor={{ fill: "rgba(128,140,160,0.12)" }} />
          <ReferenceLine
            x={forecast[NOW_INDEX]?.date}
            stroke="currentColor"
            strokeOpacity={0.4}
            label={{ value: "now", position: "insideTopRight", fontSize: 10, fill: "currentColor" }}
          />
          <Bar dataKey="value" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={d.date} fill={RISK_COLOR[d.risk]} fillOpacity={i === NOW_INDEX ? 1 : 0.82} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}