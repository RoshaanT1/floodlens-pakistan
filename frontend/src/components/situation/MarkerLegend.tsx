import { cn } from "@/lib/utils";

type MarkerLegendItem = { label: string; color: string; ring?: boolean };

export default function MarkerLegend({
  title,
  items,
  className,
}: {
  title?: string;
  items: MarkerLegendItem[];
  className?: string;
}) {
  return (
    <div className={className}>
      {title && <p className="text-xs text-muted-foreground">{title}</p>}
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
        {items.map((item) => (
          <span key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span
              className={cn("h-2 w-2 rounded-full", item.ring && "ring-1 ring-inset")}
              style={{
                backgroundColor: item.ring ? "transparent" : item.color,
                borderColor: item.color,
                borderWidth: item.ring ? 1.5 : 0,
              }}
            />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}