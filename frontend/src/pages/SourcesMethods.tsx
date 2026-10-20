import { ExternalLink } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import TopBar from "@/components/layout/TopBar";
import Panel from "@/components/common/Panel";
import SkeletonBlock from "@/components/common/SkeletonBlock";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { backendStatus } from "@/data/backend";
import { sources } from "@/data/mockData";
import { useMockLoad } from "@/lib/useMockLoad";

const FLOOD_MODEL = {
  method: [
    "FloodLens scores risk per district from four inputs: 72-hour rainfall forecasts from the PMD ensemble, observed and forecast discharge at the gauges upstream of the district, antecedent soil saturation, and satellite-observed inundation from the current event.",
    "Upstream discharge is propagated along the Indus, Jhelum, Chenab, Kabul and Swat reaches using reach-specific travel times, then compared with each district's exposure profile — the population and cropland inside its floodplain.",
    "The result is a four-step risk level (low, moderate, high, severe) refreshed once a day at 09:00 PKT, with a seven-day forecast and a seven-day observed look-back. All colours in the interface come from this one scale, so nothing depends on red-versus-green contrast.",
  ],
  accuracy: [
    { label: "District hit rate, high or severe events", value: "0.82" },
    { label: "False-alarm ratio", value: "0.31" },
    { label: "Median lead time, riverine flooding", value: "3.4 days" },
    { label: "Hindcast period and sample", value: "2019–2025 · 412 events" },
  ],
  limits: [
    "Hill-torrent flash floods in Balochistan and southern Punjab are under-predicted, with less than six hours of usable lead time.",
    "Reach travel times assume no embankment breach. A breach changes downstream timing and extent completely.",
    "Risk is scored for the whole district, not for individual settlements or union councils.",
    "Gauge coverage on the Nari–Bolan system is sparse, so verification lags there.",
  ],
};

const PRICE_MODEL = {
  method: [
    "Forecasts are produced for each market and commodity. A ridge regression over 24 months of weekly retail prices is combined with flood-exposure features: upstream district risk, the probability that a supply road is disrupted, and the share of the market's catchment inside the inundation footprint.",
    "Forecasts run 28 days ahead. The band shown is an 80% interval that widens with horizon and with the strength of the flood signal.",
    "A forecast is flagged flood-linked when flood-exposure features explain more than half of the predicted change. The reasons shown on each forecast describe the drivers the model weighted highest — they are explanations, not causal claims.",
  ],
  accuracy: [
    { label: "MAPE at 14 days / 28 days", value: "6.4% / 9.8%" },
    { label: "Directional accuracy at 14 days", value: "0.87" },
    { label: "Realised prices inside the 80% band", value: "82%" },
    { label: "Backtest period", value: "2022–2025 · 8 markets" },
  ],
  limits: [
    "Administered prices, subsidies, imports and fuel costs are not modelled.",
    "Weekly price series are thin outside Punjab and Sindh; where fewer than 40 observations exist, confidence is reported below Medium.",
    "The model assumes markets stay reachable. A full road closure can move prices faster than any forecast here.",
    "Prices are nominal, in Pakistani rupees, and not adjusted for inflation.",
  ],
};

function ModelSection({
  title,
  model,
}: {
  title: string;
  model: { method: string[]; accuracy: { label: string; value: string }[]; limits: string[] };
}) {
  return (
    <Panel title={title} subtitle="Design placeholder: the method text and every figure below are sample content, not measured results.">
      <div className="space-y-3">
        <div className="space-y-2">
          {model.method.map((paragraph) => (
            <p key={paragraph} className="text-sm text-muted-foreground">
              {paragraph}
            </p>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2 border-t border-border pt-3">
          {model.accuracy.map((stat) => (
            <div key={stat.label} className="rounded-md border border-border bg-muted/30 px-2.5 py-2">
              <p className="text-xs text-muted-foreground">{stat.label}</p>
              <p className="mt-0.5 text-base font-semibold tabular-nums">{stat.value}</p>
            </div>
          ))}
        </div>

        <div className="border-t border-border pt-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Known limits
          </p>
          <ul className="mt-2 space-y-1.5">
            {model.limits.map((limit) => (
              <li key={limit} className="flex gap-2 text-sm">
                <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                <span className="text-muted-foreground">{limit}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Panel>
  );
}

export default function SourcesMethods() {
  const { state, retry } = useMockLoad(550);

  return (
    <div className="min-h-[100dvh] bg-background">
      <div className="sticky top-0 z-30">
        <TopBar />
      </div>

      <div className="mx-auto w-full max-w-[1240px] space-y-3 p-3 sm:p-4">
        <PageHeader
          title="Sources & Methods"
          subtitle="Where every layer comes from, how the risk and price models are built, and what they cannot yet do."
        />

        <Panel
          title="Data sources"
          subtitle={`${sources.length} feeds`}
          flush
          bodyClassName="p-0"
          className="overflow-hidden"
        >
          {state === "loading" ? (
            <div className="p-3">
              <SkeletonBlock rows={8} rowClassName="h-4" />
            </div>
          ) : state === "error" ? (
            <div className="p-3">
              <p className="text-sm">The source register could not be loaded.</p>
              <button
                type="button"
                onClick={retry}
                className="mt-2 rounded border border-border px-2 py-1 text-xs hover:bg-accent"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="fl-scroll overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-transparent">
                    <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">
                      Source
                    </TableHead>
                    <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">
                      Provides
                    </TableHead>
                    <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">
                      Update frequency
                    </TableHead>
                    <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">
                      Last updated
                    </TableHead>
                    <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sources.map((source) => (
                    <TableRow key={source.id} className="border-border">
                      <TableCell className="px-3 py-2 text-sm font-medium">{source.name}</TableCell>
                      <TableCell className="px-3 py-2 text-sm text-muted-foreground">
                        {source.provides}
                      </TableCell>
                      <TableCell className="px-3 py-2 text-sm text-muted-foreground">
                        {source.updateFrequency}
                      </TableCell>
                      <TableCell className="px-3 py-2 text-sm tabular-nums text-muted-foreground">
                        {source.lastUpdated}
                      </TableCell>
                      <TableCell className="px-3 py-2">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
                        >
                          Open
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Panel>

        {backendStatus && (
          <Panel
            title="Data quality decisions"
            subtitle={`From the pipeline's quality agent · status generated ${new Date(
              backendStatus.generated_at_utc,
            ).toLocaleString("en-GB", { timeZone: "Asia/Karachi" })} PKT`}
          >
            {backendStatus.quality.length === 0 ? (
              <p className="text-sm text-muted-foreground">Every check passed on the last rebuild.</p>
            ) : (
              <ul className="space-y-2">
                {backendStatus.quality.map((q) => (
                  <li key={`${q.table}-${q.rule}`} className="text-sm">
                    <span className="font-medium">{q.table}</span>
                    <span className="text-muted-foreground"> · {q.rule} · </span>
                    <span className="font-semibold uppercase">{q.action}</span>
                    <p className="text-muted-foreground">{q.reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        )}

        <div className="grid gap-3 xl:grid-cols-2">
          <ModelSection title="How the flood risk model works" model={FLOOD_MODEL} />
          <ModelSection title="How the food price model works" model={PRICE_MODEL} />
        </div>
      </div>
    </div>
  );
}