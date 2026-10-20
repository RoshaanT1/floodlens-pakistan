import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import Panel from "@/components/common/Panel";
import SourceLine from "@/components/common/SourceLine";
import Tag from "@/components/common/Tag";
import { NOW_INDEX, sources } from "@/data/mockData";
import {
  FLOOD_LEVEL_COLOR,
  FLOOD_LEVEL_LABEL,
  RISK_COLOR,
  RISK_LABEL,
  RISK_RANK,
  fmtCusecs,
  fmtDayLong,
} from "@/lib/risk";
import {
  flowAt,
  levelAt,
  metricsFor,
  nearestGauges,
  nearestMarkets,
  riskAt,
} from "@/lib/select";
import { cn } from "@/lib/utils";
import type { District } from "@/data/types";
import ExposureStats from "./ExposureStats";
import GaugeHydrograph from "./GaugeHydrograph";
import MarketPriceRows from "./MarketPriceRows";
import RiskDrivers from "./RiskDrivers";
import RiskTrendChart from "./RiskTrendChart";

type DistrictDrawerProps = {
  district: District | null;
  offset: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const SOURCE_IDS = ["src-ffd", "src-pmd", "src-wapda", "src-suparco", "src-pbs"];

export default function DistrictDrawer({
  district,
  offset,
  open,
  onOpenChange,
}: DistrictDrawerProps) {
  const [marketIndex, setMarketIndex] = useState(0);

  useEffect(() => {
    setMarketIndex(0);
  }, [district?.id]);

  const forecast = district?.riskForecast ?? [];
  const upcoming = forecast.slice(NOW_INDEX);
  const peak = upcoming.reduce(
    (best, point) => (RISK_RANK[point.risk] >= RISK_RANK[best.risk] ? point : best),
    upcoming[0] ?? { date: "", risk: "low" as const },
  );
  const gauges = district ? nearestGauges(district, 2) : [];
  const markets = district ? nearestMarkets(district, 2) : [];
  const market = markets[marketIndex] ?? markets[0] ?? null;
  const risk = district ? riskAt(district, offset) : "low";

  return (
    <Sheet open={open && !!district} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-[480px]"
      >
        {district && (
          <>
            <SheetHeader className="shrink-0 space-y-0 border-b border-border px-4 py-3 text-left">
              <div className="flex items-start justify-between gap-3 pr-7">
                <div className="min-w-0">
                  <SheetTitle className="text-2xl font-semibold leading-tight tracking-tight">
                    {district.name}
                  </SheetTitle>
                  <SheetDescription className="mt-0.5 text-xs text-muted-foreground">
                    {district.province} · population {district.population.toLocaleString("en-US")}
                  </SheetDescription>
                </div>
                <Tag label={`${RISK_LABEL[risk]} risk`} color={RISK_COLOR[risk]} />
              </div>
            </SheetHeader>

            <div className="fl-scroll min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
              <Panel
                title="Risk — now and next 7 days"
                subtitle={`Peak risk ${RISK_LABEL[peak.risk].toLowerCase()} on ${fmtDayLong(peak.date)}`}
              >
                <RiskTrendChart forecast={forecast} />
                <SourceLine name="FFD / PMD risk ensemble" updated="09:00 PKT · 2 h ago" className="mt-1" />
              </Panel>

              <Panel title="What's driving the risk">
                <RiskDrivers
                  district={district}
                  gauge={gauges[0] ?? null}
                  gaugeLevel={gauges[0] ? levelAt(gauges[0], offset) : "normal"}
                  gaugeFlow={gauges[0] ? flowAt(gauges[0], offset) : 0}
                  metrics={metricsFor(district)}
                />
              </Panel>

              <Panel title="Nearest gauges" subtitle="Hydrograph with flood-level thresholds">
                <div className="space-y-4">
                  {gauges.map((gauge) => {
                    const level = levelAt(gauge, offset);
                    const flow = flowAt(gauge, offset);
                    return (
                      <div key={gauge.id}>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium">
                              {gauge.name} <span className="text-muted-foreground">· {gauge.river}</span>
                            </p>
                            <p className="text-xs text-muted-foreground tabular-nums">
                              {fmtCusecs(flow)}
                            </p>
                          </div>
                          <Tag
                            label={FLOOD_LEVEL_LABEL[level]}
                            color={FLOOD_LEVEL_COLOR[level]}
                          />
                        </div>
                        <GaugeHydrograph gauge={gauge} />
                        <SourceLine name="WAPDA gauge telemetry" updated="3 h ago" />
                      </div>
                    );
                  })}
                </div>
              </Panel>

              <Panel title="Exposure">
                <ExposureStats district={district} />
              </Panel>

              <Panel
                title="Food prices in nearby markets"
                subtitle={market ? `${market.name} · current against 4-week forecast` : undefined}
              >
                <div className="mb-2 flex gap-1">
                  {markets.map((m, i) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setMarketIndex(i)}
                      className={cn(
                        "rounded border px-2 py-1 text-xs transition-colors",
                        i === marketIndex
                          ? "border-border bg-accent text-foreground"
                          : "border-transparent text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                      )}
                    >
                      {m.name}
                    </button>
                  ))}
                </div>
                {market && <MarketPriceRows series={market.prices} />}
                <SourceLine name="PBS weekly retail · WFP VAM" updated="17 Oct 2026 · 3 d ago" className="mt-2" />
              </Panel>

              <Panel title="Sources used">
                <ul className="space-y-2">
                  {sources
                    .filter((s) => SOURCE_IDS.includes(s.id))
                    .map((source) => (
                      <li key={source.id} className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm">{source.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {source.provides} · updated {source.lastUpdated}
                          </p>
                        </div>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`Open ${source.name}`}
                          className="mt-0.5 text-muted-foreground transition-colors hover:text-foreground"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </li>
                    ))}
                </ul>
              </Panel>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}