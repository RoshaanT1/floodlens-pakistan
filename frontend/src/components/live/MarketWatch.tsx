import { useMemo, useState } from "react";
import Panel from "@/components/common/Panel";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { BackendStatus, MarketRow } from "@/data/backend";

const head = "h-6 px-3 text-xs font-medium text-muted-foreground";
const cell = "px-3 py-1.5 text-sm tabular-nums";
const fmt = (v: number | null) =>
  v == null ? "—" : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Where the latest price sits against its own recent history. */
function position(r: MarketRow): "above" | "below" | "within" | null {
  if (r.avg_pkr == null || r.p10 == null || r.p90 == null) return null;
  if (r.avg_pkr > r.p90) return "above";
  if (r.avg_pkr < r.p10) return "below";
  return "within";
}

/** B6 market watch: real PBS SPI prices. No price forecast is shown (Model B did not beat "no change"). */
export default function MarketWatch({ status, defaultCity }: { status: BackendStatus; defaultCity?: string }) {
  const market = status.market;
  const cities = useMemo(() => Object.keys(market?.cities ?? {}).sort(), [market]);
  const [city, setCity] = useState(defaultCity && cities.includes(defaultCity) ? defaultCity : cities[0]);
  if (!market || !city) return null;
  const rows = market.cities[city] ?? [];

  return (
    <Panel
      title="Market watch"
      subtitle={`${market.source}, week ending ${market.week_end}. Range: ${market.range_label}.`}
      action={
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="rounded border border-border bg-background px-2 py-1 text-xs"
          aria-label="City"
        >
          {cities.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      }
      flush
      bodyClassName="p-0"
      className="overflow-hidden"
    >
      <div className="fl-scroll max-h-[60vh] overflow-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className={head}>Item</TableHead>
              <TableHead className={head}>Group</TableHead>
              <TableHead className={`${head} text-right`}>Avg price (Rs)</TableHead>
              <TableHead className={`${head} text-right`}>vs last week</TableHead>
              <TableHead className={`${head} text-right`}>Typical range (Rs)</TableHead>
              <TableHead className={head}>vs history</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => {
              const pos = position(r);
              return (
                <TableRow key={r.row_id} className="border-border" title={r.row_id}>
                  <TableCell className="px-3 py-1.5 text-sm">
                    {r.item} <span className="text-muted-foreground">({r.unit})</span>
                  </TableCell>
                  <TableCell className="px-3 py-1.5 text-sm text-muted-foreground">{r.group}</TableCell>
                  <TableCell className={`${cell} text-right`}>
                    {r.avg_pkr == null ? "not collected" : fmt(r.avg_pkr)}
                  </TableCell>
                  <TableCell className={`${cell} text-right`}>
                    {r.wow_pct == null ? "—" : `${r.wow_pct > 0 ? "+" : ""}${r.wow_pct.toFixed(1)}%`}
                  </TableCell>
                  <TableCell className={`${cell} text-right text-muted-foreground`}>
                    {r.p10 == null ? "—" : `${fmt(r.p10)} – ${fmt(r.p90)}`}
                  </TableCell>
                  <TableCell className="px-3 py-1.5 text-sm">
                    {pos === "above" ? (
                      <span className="font-medium text-amber-600 dark:text-amber-400">above range</span>
                    ) : pos === "below" ? (
                      <span className="text-sky-600 dark:text-sky-400">below range</span>
                    ) : pos === "within" ? (
                      <span className="text-muted-foreground">within</span>
                    ) : (
                      "—"
                    )}
                    {r.quality_flags && <span className="ml-1 text-xs text-muted-foreground">(flagged)</span>}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}
