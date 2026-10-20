import { useMemo, useState } from "react";
import { Droplets, SearchX } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import TopBar from "@/components/layout/TopBar";
import Panel from "@/components/common/Panel";
import EmptyState from "@/components/common/EmptyState";
import SkeletonBlock from "@/components/common/SkeletonBlock";
import SourceLine from "@/components/common/SourceLine";
import Tag from "@/components/common/Tag";
import { Switch } from "@/components/ui/switch";
import MarketPriceTable from "@/components/food/MarketPriceTable";
import MarketsMap from "@/components/food/MarketsMap";
import PriceForecastChart from "@/components/food/PriceForecastChart";
import { COMMODITIES, markets } from "@/data/mockData";
import { DATA_HUE, RISK_COLOR, cropToColor, fmtPct, fmtPkr } from "@/lib/risk";
import {
  confidenceBand,
  confidenceOf,
  marketSpikePct,
  seriesChangePct,
  seriesChangePctAt,
} from "@/lib/select";
import type { PriceSeries } from "@/data/types";
import { cn } from "@/lib/utils";
import { useMockLoad } from "@/lib/useMockLoad";

type MarketPriceRow = { marketId: string; marketName: string; series: PriceSeries };

const CONFIDENCE_COLOR: Record<string, string> = {
  High: "#9AA6B8",
  Medium: "#7C8798",
  Low: "#5F6875",
};

export default function FoodPrices() {
  const { state, retry } = useMockLoad(600);
  const [marketId, setMarketId] = useState(markets[0].id);
  const [commodity, setCommodity] = useState(COMMODITIES[0]);
  const [commodityFilter, setCommodityFilter] = useState<string>("all");
  const [floodLinkedOnly, setFloodLinkedOnly] = useState(false);

  const rows = useMemo(() => {
    const out: MarketPriceRow[] = [];
    for (const market of markets) {
      for (const series of market.prices) {
        if (commodityFilter !== "all" && series.commodity !== commodityFilter) continue;
        if (floodLinkedOnly && !series.floodLinked) continue;
        out.push({ marketId: market.id, marketName: market.name, series });
      }
    }
    return out;
  }, [commodityFilter, floodLinkedOnly]);

  const market = markets.find((m) => m.id === marketId) ?? markets[0];
  const series =
    market.prices.find((p) => p.commodity === commodity) ?? market.prices[0];

  const change4 = seriesChangePct(series);
  const change2 = seriesChangePctAt(series, 14);
  const band = confidenceBand(series);
  const spiking = markets.filter((m) => marketSpikePct(m) >= 15).length;

  return (
    <div className="min-h-[100dvh] bg-background">
      <div className="sticky top-0 z-30">
        <TopBar />
      </div>

      <div className="mx-auto w-full max-w-[1240px] space-y-3 p-3 sm:p-4">
        <PageHeader
          title="Food Prices"
          subtitle={`${markets.length} markets tracked · ${spiking} with a four-week forecast spike of 15% or more · prices in PKR`}
        />

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_384px]">
          <Panel
            title="Markets and commodities"
            subtitle={`${rows.length} series shown`}
            flush
            bodyClassName="p-0"
            className="overflow-hidden"
          >
            <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
              {["all", ...COMMODITIES].map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setCommodityFilter(option)}
                  className={cn(
                    "rounded border px-2 py-1 text-xs transition-colors",
                    commodityFilter === option
                      ? "border-border bg-accent text-foreground"
                      : "border-transparent text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                  )}
                >
                  {option === "all" ? "All commodities" : option}
                </button>
              ))}
              <label className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                Flood-linked only
                <Switch
                  checked={floodLinkedOnly}
                  onCheckedChange={setFloodLinkedOnly}
                  aria-label="Show flood-linked forecasts only"
                  className="scale-[0.78]"
                />
              </label>
            </div>

            {state === "loading" ? (
              <div className="p-3">
                <SkeletonBlock rows={8} rowClassName="h-4" />
              </div>
            ) : state === "error" ? (
              <div className="p-3">
                <p className="text-sm">Market prices could not be loaded.</p>
                <button
                  type="button"
                  onClick={retry}
                  className="mt-2 rounded border border-border px-2 py-1 text-xs hover:bg-accent"
                >
                  Retry
                </button>
              </div>
            ) : rows.length === 0 ? (
              <div className="p-3">
                <EmptyState
                  icon={SearchX}
                  title="No commodities match this filter"
                  description="Nothing in the tracked markets fits the current filter combination."
                  actionLabel="Clear filters"
                  onAction={() => {
                    setCommodityFilter("all");
                    setFloodLinkedOnly(false);
                  }}
                />
              </div>
            ) : (
              <div className="fl-scroll max-h-[560px] overflow-y-auto">
                <MarketPriceTable
                  rows={rows}
                  selectedMarketId={marketId}
                  selectedCommodity={commodity}
                  onSelect={(nextMarketId, nextCommodity) => {
                    setMarketId(nextMarketId);
                    setCommodity(nextCommodity);
                  }}
                />
              </div>
            )}

            <div className="border-t border-border px-3 py-2">
              <SourceLine name="PBS weekly retail · WFP VAM market baselines" updated="17 Oct 2026 · 3 d ago" />
            </div>
          </Panel>

          <div className="space-y-3 lg:sticky lg:top-[68px] lg:self-start">
            <Panel
              title="Markets by forecast change"
              subtitle="Colour shows the largest four-week change in each market"
              flush
              bodyClassName="p-0"
              className="overflow-hidden"
            >
              {state === "loading" ? (
                <div className="h-[240px] w-full animate-pulse bg-muted" />
              ) : (
                <MarketsMap
                  markets={markets}
                  selectedMarketId={marketId}
                  onSelect={setMarketId}
                />
              )}
            </Panel>

            <Panel
              title={`${market.name} — ${series.commodity}`}
              subtitle="Observed history, four-week forecast and its 80% confidence band"
            >
              {state === "loading" ? (
                <SkeletonBlock rows={6} rowClassName="h-5" />
              ) : (
                <>
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="text-sm tabular-nums">
                      {fmtPkr(series.current)} now
                    </span>
                    <Tag
                      label={`${fmtPct(change4)} by 4 weeks`}
                      color={RISK_COLOR[cropToColor(change4)]}
                      dot={false}
                    />
                    <Tag
                      label={`Confidence ${confidenceOf(series)}`}
                      color={CONFIDENCE_COLOR[confidenceOf(series)]}
                    />
                    {series.floodLinked && (
                      <Tag label="Flood-linked" color={DATA_HUE.floodExtent} icon={Droplets} />
                    )}
                  </div>

                  <PriceForecastChart series={series} />

                  <div className="mt-2 space-y-1 border-t border-border pt-2">
                    <p className="text-xs text-muted-foreground">
                      <span className="text-foreground">Why: </span>
                      {series.reason}
                    </p>
                    <p className="text-xs text-muted-foreground tabular-nums">
                      2-week change {fmtPct(change2)} · 80% band at 4 weeks{" "}
                      {fmtPkr(band.low)} – {fmtPkr(band.high)}
                    </p>
                    <SourceLine
                      name="PBS weekly retail · WFP VAM"
                      updated="17 Oct 2026 · 3 d ago"
                      className="pt-1"
                    />
                  </div>
                </>
              )}
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}