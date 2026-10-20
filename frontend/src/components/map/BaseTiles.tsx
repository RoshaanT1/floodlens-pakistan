import { TileLayer } from "react-leaflet";

/**
 * OpenStreetMap standard tiles — no API key. Dark mode darkens them with a
 * CSS filter on the tile pane (see index.css) so the data colours stay true.
 */
export default function BaseTiles() {
  return (
    <TileLayer
      url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      maxZoom={19}
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    />
  );
}