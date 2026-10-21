import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import ErrorState from "@/components/common/ErrorState";
import SkeletonBlock from "@/components/common/SkeletonBlock";
import SourceLine from "@/components/common/SourceLine";
import { cn } from "@/lib/utils";
import LayerGroupLegend from "./LayerGroupLegend";
import LayerRow from "./LayerRow";
import { LAYER_GROUPS } from "./layers";
import { backendStatus, realSituation } from "@/data/backend";
import type * as Layers from "@/components/situation/layers";

type LayersPanelProps = {
  offset: number;
  layers: Layers.LayerState;
  opacity: Record<Layers.GroupKey, number>;
  onToggleLayer: (key: Layers.LayerKey) => void;
  onOpacityChange: (group: Layers.GroupKey, value: number) => void;
  onCollapse?: () => void;
  className?: string;
};

export default function LayersPanel({
  offset,
  layers,
  opacity,
  onToggleLayer,
  onOpacityChange,
  onCollapse,
  className,
}: LayersPanelProps) {
  const [feed, setFeed] = useState<"error" | "loading" | "ok">("error");

  const retry = () => {
    setFeed("loading");
    window.setTimeout(() => setFeed("ok"), 800);
  };

  return (
    <aside
      className={cn(
        "flex w-full shrink-0 flex-col border-border bg-card/40 md:w-[296px] md:border-r",
        className,
      )}
    >
      <header className="flex h-9 shrink-0 items-center justify-between border-b border-border px-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Layers
        </h2>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse layers panel"
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </header>

      <div className="fl-scroll min-h-0 flex-1 overflow-y-auto">
        {LAYER_GROUPS.map((g) => ({ ...g, layers: realSituation ? g.layers.filter((l) => !l.unavailable) : g.layers }))
          .filter((group) => group.layers.length > 0)
          .map((group) => (
          <section key={group.key} className="border-b border-border px-3 py-3 last:border-b-0">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {group.label}
            </h3>

            <div className="mt-2 space-y-2">
              {group.layers.map((layer) => (
                <LayerRow
                  key={layer.key}
                  layerKey={layer.key}
                  label={layer.label}
                  icon={layer.icon}
                  active={layers[layer.key]}
                  offset={offset}
                  unavailable={layer.unavailable}
                  onToggle={() => onToggleLayer(layer.key)}
                />
              ))}
            </div>

            {group.key === "hazard" && layers.satellite && realSituation && (
              <div className="mt-3">
                <SourceLine
                  name="NASA GPM IMERG Late · 7-day total"
                  updated={`to ${backendStatus?.district_info?._meta?.obs_until ?? "—"}`}
                />
              </div>
            )}

            {group.key === "hazard" && layers.satellite && !realSituation && (
              <div className="mt-3">
                {feed === "error" && (
                  <ErrorState
                    message="SUPARCO Sentinel-1 extent did not return for the 03:10 PKT pass."
                    onRetry={retry}
                  />
                )}
                {feed === "loading" && <SkeletonBlock rows={2} />}
                {feed === "ok" && (
                  <SourceLine name="SUPARCO · Sentinel-1 extent" updated="03:10 PKT · 6 h ago" />
                )}
              </div>
            )}

            <div className="mt-3 border-t border-border/70 pt-3">
              <LayerGroupLegend groupKey={group.key} />
            </div>

            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Opacity</span>
              <Slider
                min={10}
                max={100}
                step={5}
                value={[Math.round(opacity[group.key] * 100)]}
                onValueChange={([v]) => onOpacityChange(group.key, v / 100)}
                aria-label={`${group.label} layer opacity`}
                className="flex-1"
              />
              <span className="w-8 text-right text-xs tabular-nums text-muted-foreground">
                {Math.round(opacity[group.key] * 100)}%
              </span>
            </div>

            <SourceLine name={group.source.name} updated={group.source.updated} className="mt-2" />
          </section>
        ))}
      </div>
    </aside>
  );
}