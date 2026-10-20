import { DATA_HUE } from "@/lib/risk";
import FloodLevelLegend from "./FloodLevelLegend";
import MarkerLegend from "./MarkerLegend";
import RiskScaleLegend from "./RiskScaleLegend";
import type * as Layers from "@/components/situation/layers";

export default function LayerGroupLegend({ groupKey }: { groupKey: Layers.GroupKey }) {
  if (groupKey === "hazard") {
    return (
      <div className="space-y-2.5">
        <RiskScaleLegend title="District flood risk" />
        <FloodLevelLegend title="Gauge level against thresholds" />
        <MarkerLegend
          title="Rain and satellite extent"
          items={[
            { label: "Rainfall", color: DATA_HUE.rainfall, ring: true },
            { label: "Flood extent", color: DATA_HUE.floodExtent, ring: true },
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

  return <RiskScaleLegend title="Forecast price change, 4 weeks" />;
}