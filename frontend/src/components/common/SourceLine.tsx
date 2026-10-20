import { Database } from "lucide-react";
import { cn } from "@/lib/utils";

type SourceLineProps = {
  name: string;
  updated: string;
  className?: string;
};

/** "source · last updated" — every data surface carries its provenance. */
export default function SourceLine({ name, updated, className }: SourceLineProps) {
  return (
    <p className={cn("flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
      <Database className="h-4 w-4 shrink-0 opacity-70" />
      <span className="truncate">
        {name} · updated {updated}
      </span>
    </p>
  );
}