import { CloudRain, Droplets, Waves } from "lucide-react";
import Tag from "@/components/common/Tag";
import {
  FLOOD_LEVEL_COLOR,
  FLOOD_LEVEL_LABEL,
  fmtCusecs,
  fmtCusecsCompact,
} from "@/lib/risk";
import type { District, FloodLevelKey, Gauge } from "@/data/types";

type RiskDriversProps = {
  district: District;
  gauge: Gauge | null;
  gaugeLevel: FloodLevelKey;
  gaugeFlow: number;
  metrics: { rain24hMm: number; rain72hMm: number; soilSaturationPct: number };
};

function Row({
  icon: Icon,
  label,
  value,
  tag,
  sub,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tag?: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium tabular-nums">{value}</p>
          {tag}
        </div>
        {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
      </div>
    </div>
  );
}

export default function RiskDrivers({
  district,
  gauge,
  gaugeLevel,
  gaugeFlow,
  metrics,
}: RiskDriversProps) {
  return (
    <div className="space-y-3">
      <Row
        icon={CloudRain}
        label="Rainfall forecast, next 72 hours"
        value={`${metrics.rain72hMm} mm`}
        sub="Open-Meteo latest model run (ECMWF / NOAA / DWD)"
      />

      {gauge && (
      <Row
        icon={Waves}
        label={gauge ? `Nearest river — ${gauge.river} at ${gauge.name}` : "Nearest river"}
        value={fmtCusecs(gaugeFlow)}
        tag={
          gauge ? (
            <Tag label={FLOOD_LEVEL_LABEL[gaugeLevel]} color={FLOOD_LEVEL_COLOR[gaugeLevel]} />
          ) : undefined
        }
        sub={
          gauge
            ? `Thresholds (cusecs) — low ${fmtCusecsCompact(gauge.thresholds.low)} · medium ${fmtCusecsCompact(
                gauge.thresholds.medium,
              )} · high ${fmtCusecsCompact(gauge.thresholds.high)} · very high ${fmtCusecsCompact(
                gauge.thresholds.veryHigh,
              )} · exceptional ${fmtCusecsCompact(gauge.thresholds.exceptionallyHigh)}`
            : undefined
        }
      />
      )}

      <Row
        icon={Droplets}
        label={metrics.soilSaturationPct < 0 ? "Forecast rain, next 24 hours" : "Rain in the last 24 hours"}
        value={`${metrics.rain24hMm} mm`}
        sub={metrics.soilSaturationPct < 0 ? undefined : `Antecedent soil saturation ${metrics.soilSaturationPct}%`}
      />

      <ul className="space-y-1 border-t border-border pt-3">
        {district.drivers.map((driver) => (
          <li key={driver} className="flex gap-2 text-sm">
            <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
            <span className="text-muted-foreground">{driver}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}