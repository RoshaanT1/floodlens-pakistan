import { BellOff, ChevronRight } from "lucide-react";
import EmptyState from "@/components/common/EmptyState";
import SkeletonBlock from "@/components/common/SkeletonBlock";
import { cn } from "@/lib/utils";
import { districtById } from "@/lib/select";
import AlertItem from "./AlertItem";
import type { Alert } from "@/data/types";

type AlertsPanelProps = {
  alerts: Alert[];
  now: Date;
  loading?: boolean;
  onSelectAlert: (alert: Alert) => void;
  onJumpToNow: () => void;
  onCollapse?: () => void;
  className?: string;
};

export default function AlertsPanel({
  alerts,
  now,
  loading,
  onSelectAlert,
  onJumpToNow,
  onCollapse,
  className,
}: AlertsPanelProps) {
  return (
    <aside
      className={cn(
        "flex w-full shrink-0 flex-col border-border bg-card/40 md:w-[336px] md:border-l",
        className,
      )}
    >
      <header className="flex h-9 shrink-0 items-center justify-between gap-2 border-b border-border px-3">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Alerts
          </h2>
          <span className="rounded border border-border bg-muted px-1.5 text-xs tabular-nums text-muted-foreground">
            {alerts.length}
          </span>
        </div>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse alerts panel"
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </header>

      <div className="fl-scroll min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <div className="space-y-3 p-3">
            <SkeletonBlock rows={4} rowClassName="h-3" />
            <SkeletonBlock rows={4} rowClassName="h-3" />
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-3">
            <EmptyState
              icon={BellOff}
              title="No alerts in force at this time"
              description="Alerts are issued as gauges cross their flood thresholds. Nothing was active at this point on the timeline."
              actionLabel="Jump to now"
              onAction={onJumpToNow}
            />
          </div>
        ) : (
          alerts.map((alert) => (
            <AlertItem
              key={alert.id}
              alert={alert}
              now={now}
              districtName={districtById(alert.districtId)?.name ?? (alert.url ? "Pakistan (national)" : "—")}
              onSelect={() => onSelectAlert(alert)}
            />
          ))
        )}
      </div>
    </aside>
  );
}