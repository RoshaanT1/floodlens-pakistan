import { CircleMarker, MapContainer, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import BaseTiles from "@/components/map/BaseTiles";
import { RISK_COLOR, alpha, cropToColor, fmtPct } from "@/lib/risk";
import { marketSpikePct } from "@/lib/select";
import type { Market } from "@/data/types";

type MarketsMapProps = {
  markets: Market[];
  selectedMarketId: string;
  onSelect: (marketId: string) => void;
};

export default function MarketsMap({ markets, selectedMarketId, onSelect }: MarketsMapProps) {
  return (
    <div className="relative h-[240px] w-full overflow-hidden rounded-b-lg">
      <MapContainer
        center={[29.8, 69.4]}
        zoom={5}
        minZoom={4}
        maxZoom={10}
        zoomControl={false}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <BaseTiles />
        {markets.map((market) => {
          const change = marketSpikePct(market);
          const color = RISK_COLOR[cropToColor(change)];
          const selected = market.id === selectedMarketId;

          return (
            <CircleMarker
              key={market.id}
              center={market.location}
              radius={selected ? 9 : 7}
              pathOptions={{
                color: selected ? "#ffffff" : alpha(color, 0.9),
                weight: selected ? 2 : 1,
                fillColor: color,
                fillOpacity: 0.8,
              }}
              eventHandlers={{ click: () => onSelect(market.id) }}
            >
              <Tooltip className="fl-tip" direction="top">
                <span className="font-medium">{market.name}</span>
                <br />
                4-week forecast {fmtPct(change)} · wheat flour
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}