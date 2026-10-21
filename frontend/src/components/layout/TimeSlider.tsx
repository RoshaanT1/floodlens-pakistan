import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { dayLabel, observedForecastLabel } from "@/lib/select";
import { cn } from "@/lib/utils";
import { realSituation } from "@/data/backend";

/** Last slider day: live data has Model A for 24/48/72 h, i.e. now, +1 and +2 days. */
export const sliderMax = () => (realSituation ? 2 : 7);

const REAL_TICKS = [
  { value: -7, label: "7 d ago" },
  { value: -3, label: "3 d ago" },
  { value: 0, label: "Now" },
  { value: 1, label: "+1 d" },
  { value: 2, label: "+2 d" },
];

/** What the map shows at this slider position (live data). */
function realCaption(offset: number) {
  if (offset < 0) return "Observed: each district coloured by how close that day's heaviest rain came to its own heavy-rain threshold (NASA satellite)";
  const h = 24 * (offset + 1);
  return `Forecast: Model A chance of heavy rain in the next ${h} h compared with the district's normal for this month (1.5× moderate, 3× high, 6× severe)`;
}

type TimeSliderProps = {
  offset: number;
  onOffsetChange: (offset: number) => void;
  playing: boolean;
  onTogglePlay: () => void;
};

const TICKS = [
  { value: -7, label: "7 d ago" },
  { value: -3, label: "3 d" },
  { value: 0, label: "Now" },
  { value: 3, label: "+3 d" },
  { value: 7, label: "+7 d" },
];

export default function TimeSlider({
  offset,
  onOffsetChange,
  playing,
  onTogglePlay,
}: TimeSliderProps) {
  const forecast = realSituation ? offset >= 0 : offset > 0;
  const max = sliderMax();
  const ticks = realSituation ? REAL_TICKS : TICKS;

  return (
    <div className="z-20 flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-border bg-card/40 px-3 py-2">
      <div className="flex items-center gap-2">
        <Button
          size="icon"
          variant="outline"
          className="h-7 w-7 shrink-0"
          onClick={onTogglePlay}
          aria-label={playing ? "Pause the timeline" : "Play the timeline"}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <span
          className={cn(
            "rounded border px-1.5 py-[2px] text-xs font-medium",
            forecast
              ? "border-[#EFA13C]/40 bg-[#EFA13C]/10 text-[#E8A94F]"
              : "border-border bg-muted text-muted-foreground",
          )}
        >
          {realSituation ? (forecast ? "Forecast" : "Observed") : observedForecastLabel(offset)}
        </span>
      </div>

      <div className="min-w-[200px] flex-1">
        <div className="relative">
          <div className="pointer-events-none absolute inset-x-0 top-1/2 flex h-1 -translate-y-1/2 overflow-hidden rounded-full">
            <div className="h-full bg-[#7C8798]/30" style={{ flex: 7 }} />
            <div className="h-full w-px bg-foreground/40" />
            <div className="h-full bg-[#EFA13C]/30" style={{ flex: max }} />
          </div>
          <input
            type="range"
            min={-7}
            max={max}
            step={1}
            value={offset}
            onChange={(e) => onOffsetChange(Number(e.target.value))}
            aria-label={`Timeline: 7 days observed to ${max} days forecast`}
            className="fl-range relative"
          />
        </div>
        <div className={cn("mt-0.5 text-xs text-muted-foreground", realSituation ? "relative h-4" : "flex justify-between")}>
          {ticks.map((t, i) => (
            <button
              key={t.value}
              type="button"
              onClick={() => onOffsetChange(t.value)}
              style={realSituation ? { left: `${((t.value + 7) / (max + 7)) * 100}%` } : undefined}
              className={cn(
                "tabular-nums transition-colors hover:text-foreground",
                realSituation &&
                  cn("absolute whitespace-nowrap", i === 0 ? "" : i === ticks.length - 1 ? "-translate-x-full" : "-translate-x-1/2"),
                offset === t.value && "text-foreground",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-w-[168px] text-right">
        <p className="text-sm font-medium tabular-nums">{dayLabel(offset)}</p>
        <p className="text-xs text-muted-foreground">
          {realSituation
            ? forecast ? `Model A · next ${24 * (offset + 1)} h` : `Observed −${Math.abs(offset)} d`
            : offset === 0 ? "Observed to date" : forecast ? `Forecast +${offset} d` : `Observed −${Math.abs(offset)} d`}
        </p>
      </div>
      {realSituation && <p className="basis-full text-xs text-muted-foreground">{realCaption(offset)}</p>}
    </div>
  );
}