import Tag from "@/components/common/Tag";
import { RISK_COLOR, cropToColor, fmtPct, fmtPkr } from "@/lib/risk";
import { confidenceBand, seriesChangePct } from "@/lib/select";
import type { PriceSeries } from "@/data/types";

export default function MarketPriceRows({ series }: { series: PriceSeries[] }) {
  return (
    <div className="divide-y divide-border">
      {series.map((s) => {
        const predicted = s.forecast[s.forecast.length - 1];
        const change = seriesChangePct(s);
        const band = confidenceBand(s);

        return (
          <div key={s.commodity} className="py-2">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm">{s.commodity}</p>
                <p className="text-xs text-muted-foreground">
                  now <span className="tabular-nums">{fmtPkr(s.current)}</span> → 4 weeks{" "}
                  <span className="tabular-nums text-foreground">{fmtPkr(predicted.price)}</span>
                </p>
                <p className="text-xs text-muted-foreground">
                  80% band <span className="tabular-nums">{fmtPkr(band.low)} – {fmtPkr(band.high)}</span>
                  {s.floodLinked && " · flood-linked"}
                </p>
              </div>
              <Tag label={fmtPct(change)} color={RISK_COLOR[cropToColor(change)]} dot={false} />
            </div>
          </div>
        );
      })}
    </div>
  );
}