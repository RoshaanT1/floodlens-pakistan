import { Bell, Layers, Map } from "lucide-react";
import { cn } from "@/lib/utils";

type MobileTabsProps = {
  value: "alerts" | "map" | "layers";
  onChange: (value: "alerts" | "map" | "layers") => void;
  alertCount: number;
};

const TABS = [
  { value: "alerts" as const, label: "Alerts", icon: Bell },
  { value: "map" as const, label: "Map", icon: Map },
  { value: "layers" as const, label: "Layers", icon: Layers },
];

export default function MobileTabs({ value, onChange, alertCount }: MobileTabsProps) {
  return (
    <div className="flex shrink-0 gap-1 border-b border-border bg-card/40 p-1.5 md:hidden">
      {TABS.map(({ value: tabValue, label, icon: Icon }) => (
        <button
          key={tabValue}
          type="button"
          onClick={() => onChange(tabValue)}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1.5 text-sm transition-colors",
            value === tabValue
              ? "bg-accent text-foreground"
              : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
          )}
        >
          <Icon className="h-4 w-4" />
          {label}
          {tabValue === "alerts" && alertCount > 0 && (
            <span className="rounded border border-border bg-muted px-1 text-xs tabular-nums">
              {alertCount}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}