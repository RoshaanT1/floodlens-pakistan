import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import TopBar from "@/components/layout/TopBar";
import TimeSlider from "@/components/layout/TimeSlider";
import KpiRow from "@/components/layout/KpiRow";
import MobileTabs from "@/components/layout/MobileTabs";
import CollapsedRail from "@/components/layout/CollapsedRail";
import AlertsPanel from "@/components/situation/AlertsPanel";
import LayersPanel from "@/components/situation/LayersPanel";
import MapView from "@/components/situation/MapView";
import DistrictDrawer from "@/components/situation/DistrictDrawer";
import { DEFAULT_LAYERS, DEFAULT_OPACITY } from "@/components/situation/layers";
import type * as Layers from "@/components/situation/layers";
import type { Alert } from "@/data/types";
import { activeAlerts, computeKpis, districtById, timeAtOffset } from "@/lib/select";
import { useMedia } from "@/lib/useMedia";
import { useMockLoad } from "@/lib/useMockLoad";

type MobileTabValue = "alerts" | "map" | "layers";

export default function SituationRoom() {
  const [offset, setOffset] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [layers, setLayers] = useState<Layers.LayerState>(DEFAULT_LAYERS);
  const [opacity, setOpacity] = useState<Record<Layers.GroupKey, number>>(DEFAULT_OPACITY);
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [focus, setFocus] = useState<Layers.MapFocus | null>(null);
  const [mobileTab, setMobileTab] = useState<MobileTabValue>("alerts");

  const isDesktop = useMedia("(min-width: 768px)");
  const [layersOpen, setLayersOpen] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(min-width: 1280px)").matches,
  );
  const [alertsOpen, setAlertsOpen] = useState(true);

  const { state, retry } = useMockLoad(700);

  const kpis = useMemo(() => computeKpis(offset), [offset]);
  const alerts = useMemo(() => activeAlerts(offset), [offset]);
  const now = useMemo(() => timeAtOffset(offset), [offset]);
  const selectedDistrict = districtById(selectedDistrictId);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setOffset((current) => {
        if (current >= 7) {
          setPlaying(false);
          return 7;
        }
        return current + 1;
      });
    }, 900);
    return () => window.clearInterval(id);
  }, [playing]);

  const togglePlay = () => {
    if (!playing && offset >= 7) setOffset(-7);
    setPlaying((p) => !p);
  };

  const selectDistrict = useCallback((id: string) => {
    const district = districtById(id);
    if (!district) return;
    setSelectedDistrictId(id);
    setFocus({
      lat: district.centroid[0],
      lng: district.centroid[1],
      zoom: 7,
      nonce: Date.now(),
    });
    setDrawerOpen(true);
  }, []);

  // clicking a district on the map selects it without moving the map
  const selectDistrictInPlace = useCallback((id: string) => {
    if (!districtById(id)) return;
    setSelectedDistrictId(id);
    setDrawerOpen(true);
  }, []);

  const selectAlert = useCallback(
    (alert: Alert) => {
      if (alert.url) window.open(alert.url, "_blank", "noopener"); // official NDMA document
      else selectDistrict(alert.districtId);
    },
    [selectDistrict],
  );

  const toggleLayer = (key: Layers.LayerKey) =>
    setLayers((current) => ({ ...current, [key]: !current[key] }));

  const changeOpacity = (group: Layers.GroupKey, value: number) =>
    setOpacity((current) => ({ ...current, [group]: value }));

  const jumpToNow = () => {
    setOffset(0);
    setPlaying(false);
  };

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-background">
      <TopBar />
      <TimeSlider
        offset={offset}
        onOffsetChange={(value) => {
          setOffset(value);
          setPlaying(false);
        }}
        playing={playing}
        onTogglePlay={togglePlay}
      />
      <KpiRow kpis={kpis} loading={state === "loading"} />
      {!isDesktop && (
        <MobileTabs value={mobileTab} onChange={setMobileTab} alertCount={alerts.length} />
      )}

      <div className="flex min-h-0 flex-1">
        {isDesktop &&
          (layersOpen ? (
            <LayersPanel
              offset={offset}
              layers={layers}
              opacity={opacity}
              onToggleLayer={toggleLayer}
              onOpacityChange={changeOpacity}
              onCollapse={() => setLayersOpen(false)}
            />
          ) : (
            <CollapsedRail side="left" label="Layers" onExpand={() => setLayersOpen(true)} />
          ))}

        <main
          className={
            isDesktop || mobileTab === "map"
              ? "relative min-h-0 flex-1"
              : "relative hidden min-h-0 flex-1"
          }
        >
          <MapView
            offset={offset}
            layers={layers}
            opacity={opacity}
            selectedDistrictId={selectedDistrictId}
            focus={focus}
            onSelectDistrict={selectDistrictInPlace}
          />
          {state === "loading" && (
            <div className="absolute inset-0 z-[750] flex flex-col items-center justify-center gap-2 bg-background/75">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              <p className="text-xs text-muted-foreground">
                Loading district risk, gauge and market feeds
              </p>
            </div>
          )}
        </main>

        {isDesktop &&
          (alertsOpen ? (
            <AlertsPanel
              alerts={alerts}
              now={now}
              loading={state === "loading"}
              onSelectAlert={selectAlert}
              onJumpToNow={jumpToNow}
              onCollapse={() => setAlertsOpen(false)}
            />
          ) : (
            <CollapsedRail
              side="right"
              label="Alerts"
              badge={alerts.length}
              onExpand={() => setAlertsOpen(true)}
            />
          ))}

        {!isDesktop && mobileTab === "alerts" && (
          <AlertsPanel
            alerts={alerts}
            now={now}
            loading={state === "loading"}
            onSelectAlert={selectAlert}
            onJumpToNow={jumpToNow}
            className="min-h-0 flex-1"
          />
        )}

        {!isDesktop && mobileTab === "layers" && (
          <LayersPanel
            offset={offset}
            layers={layers}
            opacity={opacity}
            onToggleLayer={toggleLayer}
            onOpacityChange={changeOpacity}
            className="min-h-0 flex-1 overflow-hidden"
          />
        )}
      </div>

      {state === "error" && (
        <div className="absolute bottom-3 left-3 z-[800] w-[280px] rounded-md border border-border bg-card p-3 shadow-lg">
          <p className="text-sm font-medium">Live feeds could not be loaded</p>
          <p className="mt-1 text-xs text-muted-foreground">
            The situation room could not reach the risk and gauge feeds.
          </p>
          <button
            type="button"
            onClick={retry}
            className="mt-2 rounded border border-border px-2 py-1 text-xs hover:bg-accent"
          >
            Retry
          </button>
        </div>
      )}

      <DistrictDrawer
        district={selectedDistrict}
        offset={offset}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </div>
  );
}