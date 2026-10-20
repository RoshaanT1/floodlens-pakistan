import { MapPin } from "lucide-react";
import Tag from "@/components/common/Tag";
import { SEVERITY_COLOR, SEVERITY_LABEL, alpha, relativeHours } from "@/lib/risk";
import type { Alert } from "@/data/types";

type AlertItemProps = {
  alert: Alert;
  districtName: string;
  now: Date;
  onSelect: () => void;
};

export default function AlertItem({ alert, districtName, now, onSelect }: AlertItemProps) {
  const color = SEVERITY_COLOR[alert.severity];

  return (
    <button
      type="button"
      onClick={onSelect}
      className="group w-full border-b border-border px-3 py-2.5 text-left transition-colors last:border-b-0 hover:bg-accent/50"
      style={{ boxShadow: `inset 2px 0 0 ${alpha(color, 0.85)}` }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug">{alert.title}</p>
        <Tag label={SEVERITY_LABEL[alert.severity]} color={color} dot={false} />
      </div>
      <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
        <MapPin className="h-4 w-4 opacity-70" />
        {districtName} · issued {relativeHours(alert.issuedAt, now)}
      </p>
      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{alert.reason}</p>
    </button>
  );
}