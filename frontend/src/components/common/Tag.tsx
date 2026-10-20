import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { alpha, mix } from "@/lib/risk";
import { useTheme } from "@/lib/theme";

type TagProps = {
  label: string;
  color: string;
  icon?: LucideIcon;
  className?: string;
  dot?: boolean;
};

/** Small data chip. The colour always comes from the data, never from the chrome. */
export default function Tag({ label, color, icon: Icon, className, dot = true }: TagProps) {
  const { theme } = useTheme();
  const text = theme === "dark" ? mix(color, "#ffffff", 0.3) : mix(color, "#000000", 0.24);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-[1px] text-xs font-medium tabular-nums",
        className,
      )}
      style={{
        backgroundColor: alpha(color, theme === "dark" ? 0.16 : 0.12),
        borderColor: alpha(text, 0.32),
        color: text,
      }}
    >
      {Icon ? (
        <Icon className="h-4 w-4 shrink-0" />
      ) : dot ? (
        <span
          className="h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: color }}
        />
      ) : null}
      {label}
    </span>
  );
}