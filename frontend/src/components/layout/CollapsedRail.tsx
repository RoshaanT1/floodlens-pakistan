import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

type CollapsedRailProps = {
  side: "left" | "right";
  label: string;
  onExpand: () => void;
  badge?: number;
};

export default function CollapsedRail({ side, label, onExpand, badge }: CollapsedRailProps) {
  return (
    <div
      className={cn(
        "flex w-9 shrink-0 flex-col items-center gap-2 bg-card/40 py-2",
        side === "left" ? "border-r border-border" : "border-l border-border",
      )}
    >
      <button
        type="button"
        onClick={onExpand}
        aria-label={`Expand ${label} panel`}
        className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        {side === "left" ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </button>
      {badge != null && <span className="text-xs tabular-nums text-muted-foreground">{badge}</span>}
      <span
        className="text-xs text-muted-foreground"
        style={{ writingMode: "vertical-rl" }}
      >
        {label}
      </span>
    </div>
  );
}