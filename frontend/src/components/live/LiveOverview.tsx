import type { BackendStatus } from "@/data/backend";
import { formatPkt } from "@/data/backend";

const LIVE_SOURCES: Record<string, number> = {
  open_meteo_previous_runs: 24, open_meteo_live_forecast: 6, imerg_late_daily: 24, pbs_spi_annex: 168,
};

function ago(iso: string) {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  return m < 60 ? `${m} min ago` : m < 48 * 60 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
}

/** Headline tiles: is the pipeline alive, is the data fresh and clean, where is risk highest. */
export function KpiTiles({ status, names }: { status: BackendStatus; names: Record<string, string> }) {
  const live = status.sources.filter((s) => s.source in LIVE_SOURCES);
  const fresh = live.filter(
    (s) => (Date.now() - new Date(s.last_fetched_utc).getTime()) / 3_600_000 <= LIVE_SOURCES[s.source] * 1.5,
  ).length;
  const flags = status.quality.filter((q) => q.action === "flag").length;
  const top = status.risk
    ? Object.entries(status.risk.by_district)
        .map(([id, v]) => ({ id, p: v["24h"]?.p ?? 0 }))
        .sort((a, b) => b.p - a.p)[0]
    : null;
  const lastRun = status.pipeline?.last_success_utc ?? status.generated_at_utc;
  const tiles = [
    { label: "Last successful run", value: ago(lastRun), sub: formatPkt(lastRun), tone: "" },
    {
      label: "Live sources fresh",
      value: `${fresh} / ${live.length}`,
      sub: "fetched within 1.5× their cadence",
      tone: fresh === live.length ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400",
    },
    {
      label: "Quality decisions",
      value: String(status.quality.length),
      sub: `${flags} flagged · logged with reason and row count`,
      tone: "",
    },
    {
      label: "Highest 24 h heavy-rain risk",
      value: top ? `${top.p < 0.01 ? "<1" : Math.round(top.p * 100)}%` : "—",
      sub: top ? `${names[top.id] ?? top.id} · Model A` : "no model output",
      tone: "",
    },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="rounded-lg border border-border bg-card px-4 py-3 shadow-sm">
          <p className="text-xs font-medium text-muted-foreground">{t.label}</p>
          <p className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${t.tone}`}>{t.value}</p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{t.sub}</p>
        </div>
      ))}
    </div>
  );
}

/** The ten districts with the highest 24 h probability (or forecast rain if no model). */
export function TopDistricts({ status }: { status: BackendStatus }) {
  const names = Object.fromEntries(status.districts.map((d) => [d.id, d]));
  const rows = status.risk
    ? Object.entries(status.risk.by_district).map(([id, v]) => ({ id, value: v["24h"]?.p ?? 0, kind: "p" as const }))
    : Object.entries(status.live_forecast?.precip_mm ?? {}).map(([id, v]) => ({ id, value: v["1"] ?? 0, kind: "mm" as const }));
  const top = rows.sort((a, b) => b.value - a.value).slice(0, 10);
  const max = Math.max(...top.map((r) => r.value), 1e-9);
  return (
    <ul className="space-y-1.5">
      {top.map((r, i) => (
        <li key={r.id} className="text-sm">
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate">
              <span className="mr-1.5 text-xs text-muted-foreground tabular-nums">{i + 1}</span>
              {names[r.id]?.name ?? r.id}
              <span className="text-xs text-muted-foreground"> · {names[r.id]?.province}</span>
            </span>
            <span className="tabular-nums font-medium">
              {r.kind === "p" ? (r.value < 0.01 ? "<1%" : `${Math.round(r.value * 100)}%`) : `${r.value.toFixed(1)} mm`}
            </span>
          </div>
          <div className="mt-0.5 h-1 rounded bg-muted">
            <div className="h-1 rounded bg-orange-600/80" style={{ width: `${(100 * r.value) / max}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** One line per fetch step of the last run. */
export function RunDetails({ status }: { status: BackendStatus }) {
  if (!status.pipeline) return null;
  return (
    <dl className="grid gap-x-4 gap-y-1 text-xs sm:grid-cols-[max-content_1fr]">
      {Object.entries(status.pipeline.fetch).map(([source, result]) => (
        <div key={source} className="contents">
          <dt className="text-muted-foreground">{source}</dt>
          <dd className={result.startsWith("failed") ? "text-amber-600" : ""}>{result}</dd>
        </div>
      ))}
    </dl>
  );
}
