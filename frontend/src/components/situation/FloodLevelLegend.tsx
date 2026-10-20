import { FLOOD_LEVEL_COLOR, FLOOD_LEVEL_LABEL, FLOOD_LEVEL_ORDER } from "@/lib/risk";

const SHORT: Record<string, string> = {
  normal: "Below low",
  low: "Low",
  medium: "Medium",
  high: "High",
  veryHigh: "Very high",
  exceptionallyHigh: "Exceptional",
};

export default function FloodLevelLegend({ title }: { title?: string }) {
  return (
    <div>
      {title && <p className="text-xs text-muted-foreground">{title}</p>}
      <div className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-1">
        {FLOOD_LEVEL_ORDER.map((k) => (
          <span key={k} className="flex items-center gap-1 text-xs text-muted-foreground">
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: FLOOD_LEVEL_COLOR[k] }}
            />
            {SHORT[k] ?? FLOOD_LEVEL_LABEL[k]}
          </span>
        ))}
      </div>
    </div>
  );
}