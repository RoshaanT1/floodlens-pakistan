import { ExternalLink } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import TopBar from "@/components/layout/TopBar";
import Panel from "@/components/common/Panel";
import SkeletonBlock from "@/components/common/SkeletonBlock";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { sources } from "@/data/mockData";
import { backendStatus, realSituation } from "@/data/backend";
import type { Score } from "@/data/backend";

const f4 = (x: number) => x.toFixed(4);
const ci = (s?: Score) => (s ? `${f4(s.brier)} [${f4(s.lo)}, ${f4(s.hi)}]` : "—");

/** Accuracy tiles from the published result files (fallback: none). */
function floodAccuracy() {
  const t = backendStatus?.model_results?.a_test;
  if (!t) return [];
  const d = t.diff_vs_climatology["24h"];
  return [
    { label: "Test Brier score, 24 h (lower is better)", value: `${f4(t.model.all["24h"].brier)} vs ${f4(t.climatology.all["24h"].brier)}` },
    { label: "Gain over the declared baseline (climatology)", value: `${d.diff.toFixed(4)} [${d.lo.toFixed(4)}, ${d.hi.toFixed(4)}]` },
    { label: "Monsoon months (Jun–Sep), 24 h", value: `${f4(t.model.monsoon["24h"].brier)} vs ${f4(t.climatology.monsoon["24h"].brier)}` },
    { label: "Test sample", value: `${t.n.toLocaleString("en-US")} district-days` },
  ];
}

function priceAccuracy() {
  const b = backendStatus?.model_results?.b_validation;
  if (!b) return [];
  const a = b.by_group.all;
  return [
    { label: "Validation MAE, weekly % change", value: `${a.mae_gbm_median.toFixed(3)} pp` },
    { label: "Baseline (no change) MAE", value: `${a.mae_no_change.toFixed(3)} pp` },
    { label: "80% interval coverage", value: a.coverage_80.toFixed(2) },
    { label: "Decision", value: b.beats_no_change ? "Kept" : "Rejected" },
  ];
}

const th = "h-6 px-3 text-xs font-medium text-muted-foreground";
const td = "px-3 py-1.5 text-sm tabular-nums";

/** A5: Brier skill against climatology per group (validation, 24 h); weakest group highlighted. */
function GroupsTable() {
  const g = backendStatus?.model_results?.a_groups;
  if (!g) return null;
  const weakest = g.weakest;
  return (
    <Panel
      title="Errors by group (validation, 24 h)"
      subtitle={`Skill = 1 − model Brier / climatology Brier; above 0 means better than the baseline${weakest ? ` · weakest: ${weakest.group}` : ""}`}
      flush
      bodyClassName="p-0"
      className="overflow-hidden"
    >
      <div className="fl-scroll max-h-[420px] overflow-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className={th}>Grouping</TableHead>
              <TableHead className={th}>Group</TableHead>
              <TableHead className={`${th} text-right`}>District-days</TableHead>
              <TableHead className={`${th} text-right`}>Heavy-rain days</TableHead>
              <TableHead className={`${th} text-right`}>Model Brier [95% CI]</TableHead>
              <TableHead className={`${th} text-right`}>Climatology</TableHead>
              <TableHead className={`${th} text-right`}>Skill</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {g.groups.map((r) => {
              const weak = weakest && r.grouping === weakest.grouping && r.group === weakest.group;
              return (
                <TableRow key={`${r.grouping}-${r.group}`} className={`border-border ${weak ? "bg-amber-500/10" : ""}`}>
                  <TableCell className="px-3 py-1.5 text-sm text-muted-foreground">{r.grouping}</TableCell>
                  <TableCell className="px-3 py-1.5 text-sm font-medium">{r.group}{weak && " · weakest"}</TableCell>
                  <TableCell className={`${td} text-right`}>{r.n.toLocaleString("en-US")}</TableCell>
                  <TableCell className={`${td} text-right`}>{r.events}</TableCell>
                  <TableCell className={`${td} text-right`}>{`${f4(r.brier)} [${f4(r.lo)}, ${f4(r.hi)}]`}</TableCell>
                  <TableCell className={`${td} text-right`}>{f4(r.climatology)}</TableCell>
                  <TableCell className={`${td} text-right font-medium ${r.bss > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600"}`}>
                    {r.bss > 0 ? "+" : ""}{r.bss.toFixed(3)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}

/** P6 + A6: what the model said during the August 2025 floods, and the Buner case. */
function ReplayPanel() {
  const r = backendStatus?.replay;
  const buner = backendStatus?.model_results?.a_groups?.buner ?? [];
  if (!r) return null;
  return (
    <Panel
      title="Replay: 10–20 August 2025 floods"
      subtitle="Each day, the districts that really got heavy rain (satellite) and where the model ranked them, 24 h ahead. Validation period; not a test result."
      flush
      bodyClassName="p-0"
      className="overflow-hidden"
    >
      <div className="fl-scroll overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className={th}>Day</TableHead>
              <TableHead className={`${th} text-right`}>Districts with heavy rain</TableHead>
              <TableHead className={`${th} text-right`}>Correct in model's top 10</TableHead>
              <TableHead className={th}>Highest-ranked real events (rank)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {r.days.map((d) => (
              <TableRow key={d.day} className="border-border">
                <TableCell className="px-3 py-1.5 text-sm font-medium tabular-nums">{d.day}</TableCell>
                <TableCell className={`${td} text-right`}>{d.events}</TableCell>
                <TableCell className={`${td} text-right font-medium`}>{d.events ? `${d.hits_top10} / 10` : "—"}</TableCell>
                <TableCell className="px-3 py-1.5 text-sm text-muted-foreground">
                  {d.event_districts.slice(0, 5).map((e) => `${e.name} (${e.rank})`).join(", ") || "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {buner.length > 0 && (
        <div className="border-t border-border px-3 py-2 text-sm">
          <p className="font-medium">Buner, 14–15 Aug 2025</p>
          <p className="text-muted-foreground">
            {buner
              .filter((b) => b.lead === 1)
              .map((b) => `${b.day}: model ${(b.p_model * 100).toFixed(0)}% vs climatology ${(b.p_climatology * 100).toFixed(0)}%; satellite wettest pixel ${b.observed_mm} mm vs threshold ${b.threshold_mm} mm (label ${b.label})`)
              .join(" · ")}
            . The deadly 15 Aug flash flood stayed under the threshold in the daily satellite data, so it is not a labelled
            event: a limit of 0.1° daily rain, not of the forecast.
          </p>
        </div>
      )}
    </Panel>
  );
}

/** Model A results by lead time: test (run once) and validation, with 95% intervals. */
function ResultsTable() {
  const t = backendStatus?.model_results?.a_test;
  const v = backendStatus?.model_results?.a_validation;
  if (!t || !v) return null;
  const H = ["24h", "48h", "72h"] as const;
  const rows: [string, string, Record<(typeof H)[number], Score> | undefined][] = [
    ["Test · 1 Jan–16 Oct 2026", "Model A (gradient boosting, frozen)", t.model.all],
    ["", "Climatology (declared baseline)", t.climatology.all],
    ["", "Raw forecast cut at the threshold", t.raw_forecast_cut.all],
    ["Validation · Jul–Dec 2025", "Gradient boosting (chosen)", v.models.gbm],
    ["", "Logistic regression", v.models.logreg],
    ["", "Climatology (declared baseline)", v.baselines.climatology],
  ];
  return (
    <Panel
      title="Model A results: Brier score by lead time"
      subtitle={`Lower is better · 95% day-block bootstrap intervals · heavy rain on ${(t.positive_rate * 100).toFixed(1)}% of test district-days`}
      flush
      bodyClassName="p-0"
      className="overflow-hidden"
    >
      <div className="fl-scroll overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">Period</TableHead>
              <TableHead className="h-6 px-3 text-xs font-medium text-muted-foreground">Model</TableHead>
              {H.map((h) => (
                <TableHead key={h} className="h-6 px-3 text-right text-xs font-medium text-muted-foreground">{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(([period, name, sc], i) => (
              <TableRow key={i} className="border-border">
                <TableCell className="px-3 py-2 text-sm font-medium">{period}</TableCell>
                <TableCell className={`px-3 py-2 text-sm ${i === 0 ? "font-semibold" : "text-muted-foreground"}`}>{name}</TableCell>
                {H.map((h) => (
                  <TableCell key={h} className={`px-3 py-2 text-right text-sm tabular-nums ${i === 0 ? "font-semibold" : ""}`}>{ci(sc?.[h])}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}
import { useMockLoad } from "@/lib/useMockLoad";

// Real model cards (numbers from backend/docs/model_a_test.json, model_a_validation.json,
// model_b_validation.json); shown whenever the pipeline output is loaded.
const REAL_FLOOD_MODEL = {
  method: [
    "For each of Pakistan's 160 districts, FloodLens predicts the probability that the day's wettest-pixel rainfall exceeds that district's own 95th percentile of wet-day rain (NASA IMERG Late, 2015–2023), for the next 24, 48 and 72 hours.",
    "Inputs are weather-model forecasts exactly as they were issued 1–3 days ahead (Open-Meteo Previous Runs: rain, humidity, pressure, cloud, wind), the district's threshold and monthly climatology, satellite rain only from days that ended at least 14 hours before the forecast was issued, and district attributes (elevation, coastline, 2022 flood exposure). Tests prove no feature uses information from after issue time.",
    "A gradient-boosting classifier was trained on Feb 2024–Jun 2025 and its probabilities were calibrated on Jul–Dec 2025. The frozen model was scored once on the held-out test period, 1 Jan–16 Oct 2026 (the declared window ended 30 Sep; the test script had no end date, so it also scored 1–16 Oct). It now runs every hour on the latest forecast.",
  ],
  accuracy: [] as { label: string; value: string }[], // filled from status.json at render
  limits: [
    "Daily 0.1° satellite rain smooths out single-valley cloudbursts: on 15 Aug 2025 IMERG's wettest Buner pixel (43 mm) stayed below Buner's threshold (57.5 mm) despite a deadly flash flood.",
    "Weakest group on validation: Azad Kashmir (smallest gain over climatology).",
    "Forecast inputs are taken at district centroids, and the archive starts in Feb 2024, so the model learned from 17 months.",
    "It predicts heavy rain, not floods or damage, and is not an official warning: follow NDMA and PDMA.",
  ],
};

const REAL_PRICE_MODEL = {
  method: [
    "Weekly city prices from the Pakistan Bureau of Statistics (SPI annex): 51 items in 17 cities, 169 weeks from Jan 2023 to Oct 2026, 146,523 prices. Prices PBS did not collect stay empty and flagged; nothing is filled.",
    "We tried to forecast next week's % change per item and city with quantile gradient boosting (10th, 50th, 90th percentiles), using recent changes, the same week last year, fuel-price changes and rain anomalies near each city.",
    "It did not beat the declared baseline (\"no change\") on validation, so no price forecast is shown. The dashboard shows observed prices, their 52-week range and sudden week-on-week changes instead.",
  ],
  accuracy: [] as { label: string; value: string }[], // filled from status.json at render
  limits: [
    "Most weekly prices do not move, so \"no change\" is hard to beat.",
    "Weeks before 30 Apr 2025 come from Internet Archive copies of PBS's old site; a few weeks are missing.",
    "17 cities only, not rural markets.",
  ],
};

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
    <Panel
      title={title}
      subtitle={realSituation ? undefined : "Design placeholder: the method text and every figure below are sample content, not measured results."}
    >
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
  const shown = realSituation ? sources.filter((src) => src.id.startsWith("pipeline-")) : sources;

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
          subtitle={`${shown.length} feeds`}
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
                  {shown.map((source) => (
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

        {realSituation && <ResultsTable />}
        {realSituation && (
          <div className="grid gap-3 xl:grid-cols-2">
            <GroupsTable />
            <ReplayPanel />
          </div>
        )}

        <div className="grid gap-3 xl:grid-cols-2">
          <ModelSection
            title={realSituation ? "How the heavy-rain risk model works (Model A)" : "How the flood risk model works"}
            model={realSituation ? { ...REAL_FLOOD_MODEL, accuracy: floodAccuracy() } : FLOOD_MODEL}
          />
          <ModelSection
            title={realSituation ? "The food price model (Model B)" : "How the food price model works"}
            model={realSituation ? { ...REAL_PRICE_MODEL, accuracy: priceAccuracy() } : PRICE_MODEL}
          />
        </div>
      </div>
    </div>
  );
}