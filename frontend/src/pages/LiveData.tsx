import { useMemo, useState } from "react";
import { Database } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import TopBar from "@/components/layout/TopBar";
import Panel from "@/components/common/Panel";
import EmptyState from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { backendStatus, formatPkt } from "@/data/backend";
import LiveMap, { METRIC_LABEL, type LiveMetric } from "@/components/live/LiveMap";
import MarketWatch from "@/components/live/MarketWatch";
import FreshnessQuality from "@/components/live/FreshnessQuality";

const LEADS = ["1", "2", "3"] as const;
const HORIZONS = ["24h", "48h", "72h"] as const;

const head = "h-6 px-3 text-xs font-medium text-muted-foreground";
const cell = "px-3 py-1.5 text-sm tabular-nums";

/** Pipeline output only (status.json): no mock values on this page. */
export default function LiveData() {
  const status = backendStatus;
  const [sortBy, setSortBy] = useState<"rain" | "name">("rain");
  const [metric, setMetric] = useState<LiveMetric>(status?.risk ? "p24" : "rain1");
  // default market: the SPI city nearest the district with the highest 24 h probability
  const topDistrictCity = useMemo(() => {
    if (!status?.risk || !status.market) return undefined;
    const best = Object.entries(status.risk.by_district).sort(
      (a, b) => (b[1]["24h"]?.p ?? 0) - (a[1]["24h"]?.p ?? 0),
    )[0];
    return best ? status.market.nearest_city[best[0]]?.city : undefined;
  }, [status]);
  const metrics: LiveMetric[] = status?.risk
    ? ["p24", "p48", "p72", "rain1", "rain2", "rain3"]
    : ["rain1", "rain2", "rain3"];

  const rows = useMemo(() => {
    if (!status) return [];
    const rain = status.live_forecast?.precip_mm ?? {};
    const out = status.districts.map((d) => ({
      ...d,
      rain: LEADS.map((l) => rain[d.id]?.[l]),
      risk: HORIZONS.map((h) => status.risk?.by_district[d.id]?.[h]),
    }));
    const total = (r: (typeof out)[number]) => r.rain.reduce<number>((s, v) => s + (v ?? 0), 0);
    return out.sort((a, b) => (sortBy === "rain" ? total(b) - total(a) : a.name.localeCompare(b.name)));
  }, [status, sortBy]);

  return (
    <div className="min-h-[100dvh] bg-background">
      <div className="sticky top-0 z-30">
        <TopBar />
      </div>

      <div className="mx-auto w-full max-w-[1240px] space-y-3 p-3 sm:p-4">
        <PageHeader
          title="Live data"
          subtitle="Straight from the hourly pipeline. Nothing on this page is sample data."
        />

        {!status ? (
          <EmptyState
            icon={Database}
            title="No pipeline output found"
            description="Run `make data` and `make export` in backend/ to publish public/data/status.json."
          />
        ) : (
          <>
            <Panel title="Pipeline run">
              <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                <dt className="text-muted-foreground">Status published</dt>
                <dd className="tabular-nums">{formatPkt(status.generated_at_utc)}</dd>
                {status.pipeline && (
                  <>
                    <dt className="text-muted-foreground">Last successful run</dt>
                    <dd className="tabular-nums">{formatPkt(status.pipeline.last_success_utc)}</dd>
                    {Object.entries(status.pipeline.fetch).map(([source, result]) => (
                      <div key={source} className="contents">
                        <dt className="text-muted-foreground">{source}</dt>
                        <dd>{result}</dd>
                      </div>
                    ))}
                  </>
                )}
              </dl>
            </Panel>

            <FreshnessQuality status={status} />

            <Panel
              title="Map"
              subtitle={status.risk ? `Model A: ${status.risk.label}` : "Raw forecast rain; Model A not trained yet"}
              action={
                <div className="flex flex-wrap gap-1">
                  {metrics.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMetric(m)}
                      className={`rounded border border-border px-2 py-1 text-xs ${m === metric ? "bg-accent" : "hover:bg-accent/60"}`}
                    >
                      {METRIC_LABEL[m]}
                    </button>
                  ))}
                </div>
              }
            >
              <LiveMap status={status} metric={metric} />
            </Panel>

            <Panel
              title="Districts"
              subtitle={[
                status.live_forecast?.fetched_at_utc
                  ? `${status.live_forecast.label}, fetched ${formatPkt(status.live_forecast.fetched_at_utc)}`
                  : "No live forecast yet",
                status.risk
                  ? `Heavy-rain probability: ${status.risk.label} (${status.risk.model_version})`
                  : "Heavy-rain probability: no Model A artifact yet",
              ].join(" · ")}
              action={
                <button
                  type="button"
                  onClick={() => setSortBy(sortBy === "rain" ? "name" : "rain")}
                  className="rounded border border-border px-2 py-1 text-xs hover:bg-accent"
                >
                  Sort by {sortBy === "rain" ? "name" : "forecast rain"}
                </button>
              }
              flush
              bodyClassName="p-0"
              className="overflow-hidden"
            >
              <div className="fl-scroll max-h-[70vh] overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead className={head}>District</TableHead>
                      <TableHead className={head}>Province</TableHead>
                      <TableHead className={head}>Nearest market</TableHead>
                      {LEADS.map((l) => (
                        <TableHead key={l} className={`${head} text-right`}>
                          Rain +{l} d (mm)
                        </TableHead>
                      ))}
                      {HORIZONS.map((h) => (
                        <TableHead key={h} className={`${head} text-right`}>
                          P(heavy) {h}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((r) => (
                      <TableRow key={r.id} className="border-border">
                        <TableCell className="px-3 py-1.5 text-sm font-medium">{r.name}</TableCell>
                        <TableCell className="px-3 py-1.5 text-sm text-muted-foreground">{r.province}</TableCell>
                        <TableCell className="px-3 py-1.5 text-sm text-muted-foreground">
                          {status.market?.nearest_city[r.id]
                            ? `${status.market.nearest_city[r.id].city} (${status.market.nearest_city[r.id].km} km)`
                            : "—"}
                        </TableCell>
                        {r.rain.map((v, i) => (
                          <TableCell key={i} className={`${cell} text-right`}>
                            {v == null ? "—" : v.toFixed(1)}
                          </TableCell>
                        ))}
                        {r.risk.map((v, i) => (
                          <TableCell key={i} className={`${cell} text-right`} title={v?.row_id}>
                            {v == null ? "—" : v.p > 0 && v.p < 0.01 ? "<1%" : `${Math.round(v.p * 100)}%`}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </Panel>
            <MarketWatch status={status} defaultCity={topDistrictCity} />
          </>
        )}
      </div>
    </div>
  );
}
