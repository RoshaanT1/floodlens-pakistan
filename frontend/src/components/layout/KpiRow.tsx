import { Skeleton } from "@/components/ui/skeleton";
import type { Kpis } from "@/lib/select";
import { fmtCompact, fmtInt } from "@/lib/risk";
import { backendStatus, realSituation } from "@/data/backend";

type KpiRowProps = {
  kpis: Kpis;
  loading?: boolean;
};

function realTiles(kpis: Kpis) {
  const s = backendStatus!;
  const name = (id?: string) => s.districts.find((d) => d.id === id)?.name ?? "—";
  const top = Object.entries(s.risk?.by_district ?? {})
    .map(([id, v]) => ({ id, p: v["24h"]?.p ?? 0 }))
    .sort((a, b) => b.p - a.p)[0];
  const wet = s.districts
    .map((d) => ({ id: d.id, mm: ["1", "2", "3"].reduce((t, k) => t + (s.live_forecast?.precip_mm[d.id]?.[k] ?? 0), 0) }))
    .sort((a, b) => b.mm - a.mm)[0];
  const since = Date.now() - 30 * 86_400_000;
  const adv = (s.alerts ?? []).filter((a) => a.kind === "advisory" && new Date(a.published).getTime() >= since);
  return [
    { label: "Districts at high or severe risk", value: fmtInt(kpis.districtsAtRisk), sub: `of ${s.districts.length} districts · selected day` },
    { label: "Highest heavy-rain risk, next 24 h", value: top ? `${top.p < 0.01 ? "<1" : Math.round(top.p * 100)}%` : "—", sub: top ? `${name(top.id)} · Model A` : "no model output" },
    { label: "Wettest forecast, next 3 days", value: wet ? `${wet.mm.toFixed(1)} mm` : "—", sub: wet ? `${name(wet.id)} · Open-Meteo` : "—" },
    { label: "NDMA advisories, last 30 days", value: fmtInt(adv.length), sub: adv[0] ? `latest ${adv[0].published}` : "none" },
  ];
}

export default function KpiRow({ kpis, loading }: KpiRowProps) {
  const tiles = realSituation ? realTiles(kpis) : [
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