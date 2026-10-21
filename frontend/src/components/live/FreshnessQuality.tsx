import Panel from "@/components/common/Panel";
import type { BackendStatus } from "@/data/backend";
import { formatPkt } from "@/data/backend";

/** Expected refresh interval per source, in hours; null = static snapshot. */
const CADENCE_H: Record<string, number | null> = {
  open_meteo_previous_runs: 24,
  open_meteo_live_forecast: 6,
  imerg_late_daily: 24,
  pbs_spi_annex: 24 * 7,
  pbs_media_listing: 24,
  ndma_listing: 24,
  ndma_sitrep: null,
  ndma_advisory: null,
  ocha_cod_ab: null,
  open_meteo_elevation: null,
  natural_earth_coastline: null,
  unosat_flood_2022: null,
  pbs_spi_annex_archived: null,
};

const GRACE = 1.5; // a source counts as stale after 1.5x its cadence

function freshness(lastIso: string, cadenceH: number | null | undefined) {
  if (cadenceH == null) return { label: "static snapshot", tone: "text-muted-foreground" };
  const ageH = (Date.now() - new Date(lastIso).getTime()) / 3_600_000;
  return ageH <= cadenceH * GRACE
    ? { label: `fresh (${ageH < 1 ? "<1" : Math.round(ageH)} h old; every ${cadenceH} h)`, tone: "text-emerald-600 dark:text-emerald-400" }
    : { label: `stale (${Math.round(ageH)} h old; expected every ${cadenceH} h)`, tone: "text-amber-600 dark:text-amber-400" };
}

/** Freshness per source against its own cadence, and the Data Quality Agent's decisions. */
export default function FreshnessQuality({ status }: { status: BackendStatus }) {
  const sources = [...status.sources].sort((a, b) => a.source.localeCompare(b.source));
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Panel title="Data freshness" subtitle="Last fetch per source vs its expected cadence (your clock)">
        <ul className="space-y-1 text-sm">
          {sources.map((s) => {
            const f = freshness(s.last_fetched_utc, CADENCE_H[s.source]);
            return (
              <li key={s.source} className="flex flex-wrap justify-between gap-x-3">
                <span>
                  {s.source} <span className="text-muted-foreground">· {s.files} files</span>
                </span>
                <span className={f.tone}>
                  {formatPkt(s.last_fetched_utc)} · {f.label}
                </span>
              </li>
            );
          })}
        </ul>
      </Panel>
      <Panel
        title="Quality status"
        subtitle="Data Quality Agent: each failed check becomes fix, fill or flag, logged with reason and row count"
      >
        {status.quality.length === 0 ? (
          <p className="text-sm text-emerald-600 dark:text-emerald-400">All checks passed on the last rebuild.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {status.quality.map((q) => (
              <li key={`${q.table}-${q.rule}`}>
                <span className="font-semibold uppercase">{q.action}</span>{" "}
                <span className="font-medium">{q.table}</span>
                <span className="text-muted-foreground"> · {q.rule} · {q.n_rows} rows</span>
                <p className="text-muted-foreground">{q.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
