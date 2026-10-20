import { Skeleton } from "@/components/ui/skeleton";
import type { Kpis } from "@/lib/select";
import { fmtCompact, fmtInt } from "@/lib/risk";

type KpiRowProps = {
  kpis: Kpis;
  loading?: boolean;
};

export default function KpiRow({ kpis, loading }: KpiRowProps) {
  const tiles = [
    {
      label: "Districts at high or severe risk",
      value: fmtInt(kpis.districtsAtRisk),
      sub: `of 10 districts monitored`,
    },
    {
      label: "People exposed",
      value: fmtCompact(kpis.peopleExposed),
      sub: "in high or severe districts",
    },
    {
      label: "Gauges above high flood level",
      value: fmtInt(kpis.gaugesAboveHigh),
      sub: "of 8 gauges and barrages",
    },
    {
      label: "Markets with a price spike",
      value: fmtInt(kpis.marketsWithSpike),
      sub: "≥ 15% forecast over 4 weeks",
    },
  ];

  return (
    <div className="z-10 grid shrink-0 grid-cols-2 divide-border border-b border-border bg-background xl:grid-cols-4 xl:divide-x">
      {tiles.map((tile) => (
        <div key={tile.label} className="border-b border-border px-3 py-2.5 last:border-b-0 xl:border-b-0">
          <p className="text-xs text-muted-foreground">{tile.label}</p>
          {loading ? (
            <Skeleton className="mt-1.5 h-6 w-16 bg-muted" />
          ) : (
            <p className="mt-0.5 text-2xl font-semibold leading-none tabular-nums">{tile.value}</p>
          )}
          <p className="mt-1 text-xs text-muted-foreground">{tile.sub}</p>
        </div>
      ))}
    </div>
  );
}