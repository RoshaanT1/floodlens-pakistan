import FloodLevelLegend from "./FloodLevelLegend";
import RiskScaleLegend from "./RiskScaleLegend";
import MarkerLegend from "./MarkerLegend";
import { realSituation } from "@/data/backend";

type MapLegendProps = {
  showRisk: boolean;
  showLevels: boolean;
  showMarkets: boolean;
};

export default function MapLegend({ showRisk, showLevels, showMarkets }: MapLegendProps) {
  if (!showRisk && !showLevels && !showMarkets) return null;

  return (
    <div className="pointer-events-none absolute bottom-7 left-3 z-[700] hidden w-[236px] space-y-2.5 rounded-md border border-border bg-card/90 p-2.5 backdrop-blur sm:block">
      {showRisk && <RiskScaleLegend title={realSituation ? "Heavy-rain risk vs this month's normal" : "District heavy-rain risk"} />}
      {showLevels && <FloodLevelLegend title="River gauge level" />}
      {showMarkets &&
        (realSituation ? (
          <MarkerLegend
            title="Food prices: change since last week (≥ 10%)"
            items={[
              { label: "▲ rose", color: "#d7301f" },
              { label: "▼ fell", color: "#1a9850" },
              { label: "⇅ both (rises and falls)", color: "#7b3294" },
              { label: "no sudden change", color: "#9ca3af" },
            ]}
          />
        ) : (
          <RiskScaleLegend title="Market price change, 4 weeks" />
        ))}
    </div>
  );
}