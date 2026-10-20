import { fmtInt, fmtPct } from "@/lib/risk";
import type { District } from "@/data/types";

export default function ExposureStats({ district }: { district: District }) {
  const share = (district.exposedPopulation / district.population) * 100;

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
        <p className="text-xs text-muted-foreground">Population exposed</p>
        <p className="mt-0.5 text-xl font-semibold tabular-nums">
          {fmtInt(district.exposedPopulation)}
        </p>
        <p className="text-xs text-muted-foreground">
          {fmtPct(share, 0).replace("+", "")} of {fmtInt(district.population)}
        </p>
      </div>
      <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
        <p className="text-xs text-muted-foreground">Cropland affected</p>
        <p className="mt-0.5 text-xl font-semibold tabular-nums">{fmtInt(district.croplandHa)}</p>
        <p className="text-xs text-muted-foreground">hectares inside the risk footprint</p>
      </div>
    </div>
  );
}