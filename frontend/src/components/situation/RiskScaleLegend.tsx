import { RISK_COLOR, RISK_LABEL, RISK_ORDER } from "@/lib/risk";

export default function RiskScaleLegend({ title }: { title?: string }) {
  return (
    <div>
      {title && <p className="text-xs text-muted-foreground">{title}</p>}
      <div className="mt-1.5 flex gap-1">
        {RISK_ORDER.map((r) => (
          <div key={r} className="flex-1">
            <div className="h-1.5 rounded-sm" style={{ backgroundColor: RISK_COLOR[r] }} />
            <p className="mt-1 text-xs text-muted-foreground">{RISK_LABEL[r]}</p>
          </div>
        ))}
      </div>
    </div>
  );
}