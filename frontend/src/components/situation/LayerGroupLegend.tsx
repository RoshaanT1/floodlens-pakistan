import { DATA_HUE } from "@/lib/risk";
import FloodLevelLegend from "./FloodLevelLegend";
import MarkerLegend from "./MarkerLegend";
import RiskScaleLegend from "./RiskScaleLegend";
import type * as Layers from "@/components/situation/layers";
import { realSituation } from "@/data/backend";

export default function LayerGroupLegend({ groupKey }: { groupKey: Layers.GroupKey }) {
  if (groupKey === "hazard") {
    return (
      <div className="space-y-2.5">
        <RiskScaleLegend title={realSituation ? "Heavy-rain risk vs this month's normal (1.5× · 3× · 6×)" : "District heavy-rain risk"} />
        {!realSituation && <FloodLevelLegend title="Gauge level against thresholds" />}
        <MarkerLegend
          title={realSituation ? "Rainfall" : "Rain and satellite extent"}
          items={[
            { label: realSituation ? "Rain that day" : "Rainfall", color: DATA_HUE.rainfall, ring: true },
            { label: realSituation ? "Satellite rain, 7 days" : "Flood extent", color: DATA_HUE.floodExtent, ring: true },
          ]}
        />
      </div>
    );
  }

  if (groupKey === "exposure") {
    return (
      <MarkerLegend
        title="Area of circle = people or hectares"
        items={[
          { label: "Population exposed", color: DATA_HUE.population, ring: true },
          { label: "Cropland affected", color: DATA_HUE.cropland, ring: true },
        ]}
      />
    );
  }

  if (realSituation) {
    return (
      <MarkerLegend
        title="Change since last week (≥ 10%)"
        items={[
              { label: "▲ rose", color: "#d7301f" },
              { label: "▼ fell", color: "#1a9850" },
              { label: "⇅ both (rises and falls)", color: "#7b3294" },
              { label: "no sudden change", color: "#9ca3af" },
        ]}
      />
    );
  }
  return <RiskScaleLegend title="Forecast price change, 4 weeks" />;
}