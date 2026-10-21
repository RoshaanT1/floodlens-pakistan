import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { rainfallLabel } from "@/lib/select";
import type * as Layers from "@/components/situation/layers";

type LayerRowProps = {
  layerKey: Layers.LayerKey;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  offset: number;
  onToggle: () => void;
  unavailable?: boolean;
};

export default function LayerRow({
  layerKey,
  label,
  icon: Icon,
  active,
  offset,
  onToggle,
  unavailable = false,
}: LayerRowProps) {
  const text = layerKey === "rainfall" ? rainfallLabel(offset) : label;

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={unavailable ? undefined : onToggle}
        disabled={unavailable}
        className={cn("flex min-w-0 flex-1 items-center gap-2 text-left", unavailable && "cursor-not-allowed opacity-50")}
      >
        <Icon className={cn("h-4 w-4 shrink-0", active ? "text-foreground" : "text-muted-foreground")} />
        <span className={cn("truncate text-sm", active ? "text-foreground" : "text-muted-foreground")}>
          {text}
        </span>
      </button>
      <Switch
        checked={active && !unavailable}
        onCheckedChange={onToggle}
        disabled={unavailable}
        aria-label={text}
        className="scale-[0.78]"
      />
    </div>
  );
}