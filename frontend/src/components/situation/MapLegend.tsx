import FloodLevelLegend from "./FloodLevelLegend";
import RiskScaleLegend from "./RiskScaleLegend";

type MapLegendProps = {
  showRisk: boolean;
  showLevels: boolean;
  showMarkets: boolean;
};

export default function MapLegend({ showRisk, showLevels, showMarkets }: MapLegendProps) {
  if (!showRisk && !showLevels && !showMarkets) return null;

  return (
    <div className="pointer-events-none absolute bottom-7 left-3 z-[700] hidden w-[236px] space-y-2.5 rounded-md border border-border bg-card/90 p-2.5 backdrop-blur sm:block">
      {showRisk && <RiskScaleLegend title="District flood risk" />}
      {showLevels && <FloodLevelLegend title="River gauge level" />}
      {showMarkets && <RiskScaleLegend title="Market price change, 4 weeks" />}
    </div>
  );
}