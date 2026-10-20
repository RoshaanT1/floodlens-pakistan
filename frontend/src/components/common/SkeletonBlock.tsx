import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type SkeletonBlockProps = {
  rows?: number;
  className?: string;
  rowClassName?: string;
};

export default function SkeletonBlock({ rows = 3, className, rowClassName }: SkeletonBlockProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={cn("h-4 w-full bg-muted", rowClassName)} />
      ))}
    </div>
  );
}