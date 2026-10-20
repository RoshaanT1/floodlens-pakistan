import { Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { dayLabel, observedForecastLabel } from "@/lib/select";
import { cn } from "@/lib/utils";

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
  const forecast = offset > 0;

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
          {observedForecastLabel(offset)}
        </span>
      </div>

      <div className="min-w-[200px] flex-1">
        <div className="relative">
          <div className="pointer-events-none absolute inset-x-0 top-1/2 flex h-1 -translate-y-1/2 overflow-hidden rounded-full">
            <div className="h-full flex-1 bg-[#7C8798]/30" />
            <div className="h-full w-px bg-foreground/40" />
            <div className="h-full flex-1 bg-[#EFA13C]/30" />
          </div>
          <input
            type="range"
            min={-7}
            max={7}
            step={1}
            value={offset}
            onChange={(e) => onOffsetChange(Number(e.target.value))}
            aria-label="Timeline: 7 days observed to 7 days forecast"
            className="fl-range relative"
          />
        </div>
        <div className="mt-0.5 flex justify-between text-xs text-muted-foreground">
          {TICKS.map((t) => (
            <button
              key={t.value}
              type="button"
              onClick={() => onOffsetChange(t.value)}
              className={cn(
                "tabular-nums transition-colors hover:text-foreground",
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
          {offset === 0 ? "Observed to date" : forecast ? `Forecast +${offset} d` : `Observed −${Math.abs(offset)} d`}
        </p>
      </div>
    </div>
  );
}