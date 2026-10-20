import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
};

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border px-4 py-8 text-center",
        className,
      )}
    >
      <Icon className="h-4 w-4 text-muted-foreground" />
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="max-w-[36ch] text-xs text-muted-foreground">{description}</p>}
      {actionLabel && onAction && (
        <Button size="sm" variant="outline" className="mt-1 h-7" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}