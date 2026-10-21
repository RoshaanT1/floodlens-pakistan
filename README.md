# FloodLens Pakistan

**District heavy-rain warnings one to three days ahead, plus a weekly food-price watch,
for disaster planners in Pakistan.** HackInsight 2026, team Spark H.

> Status on 21 Oct 2026: the pipeline, dashboard and every model and analysis step are
> built and tested. Model A's validation results are still pending, because the 2015–2026
> satellite rainfall download (IMERG) only became possible on 21 Oct. Numbers appear in
> [Results](#results) once `src.model_a train` has run. Nothing below is a placeholder
> number.

## The problem

The 2025 monsoon killed more than 1,000 people in Pakistan (NDMA). District and provincial
planners need 24 to 72 hours of warning to pre-position teams and supplies, and they need
the warning per district, not per weather-model grid cell.

**User:** a district or PDMA planner. **Decision:** where to pre-position resources and
issue local warnings in the next one to three days.

## What it does

| | Model A: district rain risk (primary) | Model B: weekly food prices (secondary) |
| --- | --- | --- |
| Predicts | Probability that tomorrow's (or +2, +3 days) wettest-pixel rain in a district exceeds that district's 95th percentile of wet-day rain | Next week's % price change per item and city |
| Inputs | Archived numerical forecasts (Open-Meteo Previous Runs, issued 1–3 days ahead), observed satellite rain lagged ≥14 h, month, district attributes | PBS weekly prices (17 cities × 51 items), past changes |
| Labels | NASA GPM IMERG Late, 2015–2023 thresholds | PBS weekly SPI |
| Baseline | District-by-month climatology | No change |
| Metric | Brier score at 24 h (48, 72 h also) | MAE of % change, 80% interval coverage |

Model A predicts **heavy rain, not floods**, and outputs are not official warnings: follow
NDMA/PDMA advisories and call Rescue 1122 in an emergency.

## Architecture

```
             hourly Prefect flow (backend/flows/hourly.py, cron 5 * * * *)
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ fetch new data ──► raw files + manifest.csv (source, query, UTC time, SHA-256, │
 │  Open-Meteo        licence; raw files are never edited or overwritten)       │
 │  IMERG Late                                                                  │
 │  PBS SPI, NDMA (daily)                                                       │
 │        │                                                                     │
 │        ▼                                                                     │
 │ make data (in a scratch copy of the DuckDB file, swapped in only on success) │
 │  verify every SHA-256 → districts, forecasts, rain, thresholds, labels,      │
 │  attributes, documents, prices → Data Quality Agent (pandera checks;         │
 │  fix/fill/flag decisions cached and replayed) → Model A features → score     │
 │  with the current model artifact                                             │
 │        │                                                                     │
 │        ▼                                                                     │
 │ make export → frontend/public/data/status.json                               │
 └──────────────────────────────────────────────────────────────────────────────┘
                     │
                     ▼
 frontend/ (React + Vite): Live data page reads status.json; sample-scenario pages
 are labelled as such
```

- **Reproducible:** `make data` rebuilds every table from the frozen raw snapshot and
  refuses to run if any file's SHA-256 differs from the manifest.
- **No leakage:** forecast features come only from the archived `_previous_day1..3` values;
  observed rain only from UTC days that ended ≥14 h before the forecast was issued.
  `backend/tests/test_model_a.py` proves both.
- **Fixed splits:** train to 30 Jun 2025, validate 1 Jul–31 Dec 2025, test 1 Jan–30 Sep
  2026, run once. Code refuses to load test rows unless `FLOODLENS_RUN_TEST=1`.
- **Model swaps never touch flow code:** the flow scores with whatever
  `backend/models/model_a/current.json` points to.
- **Insight Agent (in progress):** NDMA monsoon 2025 sitreps and advisories, split into
  sections and indexed with a multilingual embedding model (Urdu-capable) in FAISS.

## How to run

Linux, Python 3.11, Node 20.

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # add EARTHDATA_TOKEN (NASA Earthdata, GES DISC approved)

# fetch (network; every fetcher is resumable and skips what the manifest already has)
.venv/bin/python -m src.districts fetch && .venv/bin/python -m src.districts build
.venv/bin/python -m src.forecasts fetch --budget 9000   # Open-Meteo free tier; rerun daily until complete
.venv/bin/python -m src.forecasts live
.venv/bin/python -m src.imerg fetch --workers 2
.venv/bin/python -m src.attributes fetch
.venv/bin/python -m src.documents fetch
.venv/bin/python -m src.spi fetch && .venv/bin/python -m src.spi fetch-archived

make data        # offline: verify + rebuild every table + quality summary
make test
.venv/bin/python -m src.model_a train          # baselines + models on validation, writes the artifact
.venv/bin/python -m src.analysis_a ndma && .venv/bin/python -m src.analysis_a report
make export      # frontend/public/data/status.json

# hourly flow
.venv/bin/prefect server start &                # UI on http://127.0.0.1:4200
.venv/bin/python -m flows.hourly serve          # or the systemd units in deploy/
.venv/bin/python -m flows.export_runs           # docs/prefect_runs.csv for the run window

# frontend
cd ../frontend && npm install && npx vite       # open /live
```

## Results

*Pending: filled in from `backend/docs/model_a_validation.json` and
`backend/docs/model_a_analysis.md` after training.* Validation-stage results only; the test
set (Jan–Sep 2026) is run once by the team and reported separately.

| Validation, 24 h | Brier [95% CI] |
| --- | --- |
| Climatology baseline | pending |
| Raw forecast cut at threshold | pending |
| Logistic regression (calibrated) | pending |
| Gradient boosting (calibrated) | pending |

Data assembled so far:
- 160 districts (OCHA admin-2), with elevation, coastal and 2022 flood-prone attributes;
- archived forecasts from Jul 2024 onward, backfilled within the 10,000 calls/day free tier;
- PBS weekly prices for **169 weeks** (5 Jan 2023 to 15 Oct 2026), every week complete
  (17 cities × 51 items), 1,810 values flagged by the quality rules and none filled;
- 158 NDMA documents (98 sitreps, incl. 86 from monsoon 2025; 60 advisories); 1,708 sections indexed so far.

## Business model (X2)

| | |
| --- | --- |
| **User** | District disaster-management officers and PDMA planners; NGOs that pre-position relief (e.g. WFP, IRC, Alkhidmat). |
| **Payer** | PDMAs and NDMA through provincial disaster-preparedness budgets, or humanitarian donors funding anticipatory action (pre-agreed money released when a forecast trigger is hit). The district map and Insight Agent stay free for the public. |
| **Value** | One to three days of district-level notice of rain beyond the district's own norm, with the evidence (forecast vs threshold, official sources) in one place; anticipatory-action triggers need exactly this kind of auditable, pre-agreed signal. |
| **Running costs measured during the event** | Compute: one hourly run is ~28 min of rate-limited downloading plus ~1 min of rebuild on a laptop CPU, peak ~770 MB RAM. Storage: ~1.3 GB of raw data, growing ~10 MB a day. Data: NASA IMERG and OCHA, UNOSAT and PBS data are free; Open-Meteo is free for non-commercial use (<10,000 calls a day), and a paid plan is needed for commercial use (price to confirm with Open-Meteo). Hosting: a free-tier VM (Oracle Always Free) or ~€4/month (Hetzner CX22) is enough. |
| **Risks** | Upstream availability (NASA endpoints blocked this machine for hours on 21 Oct; the flow kept running and logged it); forecast skill limits in hill-torrent catchments; users mistaking a rain signal for an official flood warning (mitigated by labelling and by pointing to NDMA/PDMA); free-tier terms changing. |

## Limits

- Model A forecasts heavy rain, not floods, damage or deaths.
- Forecast features are taken at the district centroid; the label is the district's
  wettest pixel, so small intense storms can be missed by the inputs.
- IMERG is a satellite estimate. Fill values are flagged and never read as zero, and
  low-sample days are marked low confidence.
- District attributes are coarse: elevation is a single centroid value, and the 1,000 m
  mountain cut-off was chosen before seeing results.
- PBS prices cover 17 cities, not rural markets. Weeks before 30 Apr 2025 come from the
  Internet Archive's copies of PBS's old site; the provenance is recorded per file.
- The run history covers only part of the judged window: the first run was at 01:28 PKT
  on 21 Oct, and the laptop slept 04:33–06:10. See `backend/docs/overnight_report.md`.

## Data sources and licences

Full list with URLs: [`backend/docs/sources.md`](backend/docs/sources.md). Binding plan:
[`backend/DATASET_DECLARATION.md`](backend/DATASET_DECLARATION.md).

| Source | Publisher | Licence |
| --- | --- | --- |
| Previous Runs + forecast API | Open-Meteo (ECMWF, NOAA, DWD models) | CC BY 4.0 |
| GPM IMERG V07 Late daily | NASA GES DISC | NASA EOSDIS open data policy |
| District boundaries | OCHA via HDX | CC BY-IGO |
| Elevation (Copernicus DEM) | Open-Meteo | CC BY 4.0, © Copernicus |
| Coastline | Natural Earth | Public domain |
| 2022 flood extent per district | UNOSAT via HDX | CC BY-SA |
| Weekly SPI city annex | Pakistan Bureau of Statistics | Public statistics; terms to be confirmed |
| Sitreps, advisories | NDMA | Website EULA; stored locally, not redistributed |

## Repository

```
backend/   pipeline, models, flow, tests, docs (TASKS.md, DATASET_DECLARATION.md, AI_Use_Log.md)
frontend/  React dashboard (Base44 template); Live data page reads status.json
```

AI assistance is logged in [`backend/AI_Use_Log.md`](backend/AI_Use_Log.md).
