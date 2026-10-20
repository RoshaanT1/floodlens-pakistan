import { Droplets } from "lucide-react";
import Tag from "@/components/common/Tag";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DATA_HUE, RISK_COLOR, cropToColor, fmtPct, fmtPkr } from "@/lib/risk";
import { confidenceOf, seriesChangePct, seriesChangePctAt } from "@/lib/select";
import { cn } from "@/lib/utils";
import type { PriceSeries } from "@/data/types";

type MarketPriceRow = {
  marketId: string;
  marketName: string;
  series: PriceSeries;
};

type MarketPriceTableProps = {
  rows: MarketPriceRow[];
  selectedMarketId: string;
  selectedCommodity: string;
  onSelect: (marketId: string, commodity: string) => void;
};

const CONFIDENCE_COLOR: Record<string, string> = {
  High: "#9AA6B8",
  Medium: "#7C8798",
  Low: "#5F6875",
};

export default function MarketPriceTable({
  rows,
  selectedMarketId,
  selectedCommodity,
  onSelect,
}: MarketPriceTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="border-border hover:bg-transparent">
          <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">Market</TableHead>
          <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">
            Commodity
          </TableHead>
          <TableHead className="h-6 px-3 text-right text-xs font-medium text-muted-foreground">
            Now
          </TableHead>
          <TableHead className="h-6 px-3 text-right text-xs font-medium text-muted-foreground">
            2 wk / 4 wk
          </TableHead>
          <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">
            Confidence
          </TableHead>
          <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map(({ marketId, marketName, series }) => {
          const change4 = seriesChangePct(series);
          const change2 = seriesChangePctAt(series, 14);
          const color = RISK_COLOR[cropToColor(change4)];
          const selected =
            marketId === selectedMarketId && series.commodity === selectedCommodity;

          return (
            <TableRow
              key={`${marketId}-${series.commodity}`}
              onClick={() => onSelect(marketId, series.commodity)}
              className={cn(
                "cursor-pointer border-border",
                selected ? "bg-accent/60" : "hover:bg-accent/30",
              )}
            >
              <TableCell className="px-3 py-2 text-sm">{marketName}</TableCell>
              <TableCell className="px-3 py-2 text-sm text-muted-foreground">
                {series.commodity}
                <span className="ml-1 text-xs">({series.unit})</span>
              </TableCell>
              <TableCell className="px-3 py-2 text-right text-sm tabular-nums">
                {fmtPkr(series.current)}
              </TableCell>
              <TableCell className="px-3 py-2 text-right">
                <Tag
                  label={`${fmtPct(change4)} · 4 wk`}
                  color={color}
                  dot={false}
                  className="justify-end"
                />
                <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">
                  {fmtPct(change2)} at 2 weeks
                </p>
              </TableCell>
              <TableCell className="px-3 py-2">
                <Tag
                  label={confidenceOf(series)}
                  color={CONFIDENCE_COLOR[confidenceOf(series)]}
                />
              </TableCell>
              <TableCell className="px-3 py-2">
                {series.floodLinked ? (
                  <Tag label="Flood-linked" color={DATA_HUE.floodExtent} icon={Droplets} />
                ) : (
                  <span className="text-xs text-muted-foreground">—</span>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}