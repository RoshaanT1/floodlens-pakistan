# FloodLens Pakistan

**District heavy-rain warnings one to three days ahead, plus a weekly food-price watch,
for disaster planners in Pakistan.** HackInsight 2026, team Spark H.

> Status on 21 Oct 2026: pipeline, dashboard, Model A and Insight Agent are running. The live
> dashboard shows Model A probabilities for all 160 districts every hour. The test set (Jan to
> Sep 2026) was run once on 21 Oct with the frozen model: it beats the declared baseline.

**Deployed:** https://huggingface.co/spaces/RoshaanT1/floodlens-pakistan
(full screen: https://roshaant1-floodlens-pakistan.static.hf.space/)

## Team Spark H

| Member | Role | Main work |
| --- | --- | --- |
| Roshaan Tahir | Team Lead, Lead Architect | Open-Meteo forecast pipeline, Model A, Insight Agent, dashboard integration |
| M Hammad Khan | Lead Backend | NASA IMERG satellite-rain fetcher, district rain, thresholds and labels, data quality checks |
| M Huzaifa | Lead Data Sources | Hugging Face Space deployment (Docker server, build script, deploy checklist), AI-use records |

## Submission links

| | |
| --- | --- |
| Live dashboard (Hugging Face Space, no login) | https://huggingface.co/spaces/RoshaanT1/floodlens-pakistan |
| Demo video (2:52, no login) | https://roshaant1-floodlens-pakistan.static.hf.space/demo.mp4 |
| One-page summary | [`Summary.pdf`](Summary.pdf) |
| Dataset proposal | [`datasetproposal.pdf`](datasetproposal.pdf) |
| Run history, Tue 16:00 to Wed 16:00 PKT (unedited) | [`backend/docs/prefect_runs.csv`](backend/docs/prefect_runs.csv) + [`backend/docs/screenshots/`](backend/docs/screenshots/) |
| AI use log | [`AI_Use_Log.md`](AI_Use_Log.md) |
| Participant guide, answered | [`HackInsight_Guide_SparkH.pdf`](HackInsight_Guide_SparkH.pdf), [`GUIDE_ANSWERS.md`](GUIDE_ANSWERS.md) |

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
 frontend/ (React + Vite) → Hugging Face Space https://huggingface.co/spaces/RoshaanT1/floodlens-pakistan
 (the flow uploads status.json after every run): freshness per source, quality status, last
 successful run, Model A map and table, market watch; sample-scenario pages are labelled
```

- **Warehouse layers:** `data/raw/` (untouched downloads + `manifest.csv`), `data/clean/`
  (cleaned, quality-checked tables as Parquet: districts, forecasts, district rain, prices,
  documents, quality log) and `data/gold/` (processed: thresholds, labels, baseline, Model A
  features, live risk scores), all rebuilt by `make data` and mirrored in `data/floodlens.duckdb`.
- **Reproducible:** `make data` rebuilds every table from the frozen raw snapshot and
  refuses to run if any file's SHA-256 differs from the manifest.
- **No leakage:** forecast features come only from the archived `_previous_day1..3` values;
  observed rain only from UTC days that ended ≥14 h before the forecast was issued.
  `backend/tests/test_model_a.py` proves both.
- **Fixed splits:** train to 30 Jun 2025, validate 1 Jul–31 Dec 2025, test 1 Jan–30 Sep
  2026, run once. Code refuses to load test rows unless `FLOODLENS_RUN_TEST=1`.
- **Model swaps never touch flow code:** the flow scores with whatever
  `backend/models/model_a/current.json` points to.
- **Insight Agent:** NDMA sitreps and advisories split into sections and indexed with a
  multilingual embedding model (FAISS). Answers quote sections with their ids, insert numbers from
  tables with row ids, say "I don't know" below a tested retrieval threshold, put Rescue 1122 and
  NDMA/PDMA first for emergencies, and switch to Urdu (Ask page). Tests: `tests/test_insight.py`.

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

# Insight Agent (separate venv; builds the document index once, ~8 min on CPU)
python3 -m venv .venv-insight && .venv-insight/bin/pip install -r requirements-insight.txt
.venv-insight/bin/python -m src.doc_index build
.venv-insight/bin/uvicorn src.insight_api:app --port 8001   # serves the dashboard's Ask page

# frontend
cd ../frontend && npm install && npx vite       # open /live and /ask
```

## Results

**Test set (1 Jan to 30 Sep 2026, run once with the frozen model, 138,720 district-day-leads):**

| Brier [95% CI] | 24 h | 48 h | 72 h | Monsoon months (Jun–Sep), 24 h |
| --- | --- | --- | --- | --- |
| Climatology (declared baseline) | 0.0192 [0.0156, 0.0231] | 0.0192 | 0.0192 | 0.0251 [0.0193, 0.0316] |
| Raw forecast cut at threshold | 0.0246 [0.0207, 0.0290] | 0.0245 | 0.0244 | 0.0305 |
| **Model A (gradient boosting)** | **0.0177 [0.0146, 0.0213]** | **0.0178** | **0.0179** | **0.0237 [0.0181, 0.0299]** |

Paired bootstrap, model − climatology: 24 h −0.0014 [−0.0022, −0.0008], 48 h −0.0013 [−0.0021, −0.0008],
72 h −0.0013 [−0.0020, −0.0007]. **The model beats the declared baseline on the test set at every lead, and also
in monsoon months**, as the declaration requires. Source: `backend/docs/model_a_test.json`.

**Validation (used for model choice and calibration):**

Validation, 1 Jul to 31 Dec 2025 (29,440 district-days per lead; heavy rain on 2.6% of them).
Brier score with 95% day-block bootstrap intervals; lower is better. Model probabilities are
Platt-calibrated on validation, cross-fitted by ISO week so no day is scored by a calibrator that
saw it. Sources: `backend/docs/model_a_validation.json`, `backend/docs/model_a_analysis.md`.

| Brier [95% CI] | 24 h | 48 h | 72 h |
| --- | --- | --- | --- |
| Climatology (declared baseline) | 0.0249 [0.0188, 0.0320] | 0.0249 [0.0188, 0.0320] | 0.0249 [0.0188, 0.0320] |
| Raw forecast cut at threshold | 0.0290 [0.0217, 0.0371] | 0.0297 [0.0224, 0.0378] | 0.0294 [0.0226, 0.0376] |
| Logistic regression | 0.0238 [0.0182, 0.0305] | 0.0244 [0.0186, 0.0310] | 0.0243 [0.0185, 0.0308] |
| **Gradient boosting (chosen)** | **0.0233 [0.0177, 0.0297]** | **0.0236 [0.0180, 0.0300]** | **0.0235 [0.0180, 0.0298]** |

- **Better than climatology at every lead.** Paired bootstrap of the difference (GBM − climatology)
  at 24 h: −0.0016 [−0.0025, −0.0008], so the gain is larger than day-to-day noise (also at 48 h and 72 h).
- **The gain holds in monsoon months** (Jun–Sep validation days: Brier skill score +0.058) and in
  every group: provinces, mountain/plain, coastal/inland, 2022 flood-prone or not. **Weakest group:
  Azad Kashmir** (skill +0.015).
- **The raw forecast cut at the threshold is worse than climatology**: centroid forecasts rarely
  reach a wettest-pixel threshold, which is why calibration matters.
- **Buner, 15 Aug 2025:** IMERG's wettest Buner pixel was 43 mm, under Buner's 57.5 mm
  threshold, so the day is labelled 0 even though a flash flood killed more than 100 people there (126 listed in NDMA Sitrep No. 52). The model gave
  0.15 at 24 h, about 4× climatology (0.039). The limit here is the label: a daily 0.1° satellite
  estimate smooths out a local cloudburst.
- **Local validation (E2):** with the 0.5 flag rule fixed before results, only 1 district
  (Diamir) is ever flagged at 24 h in Jul–Sep 2025, against 125 districts named in NDMA's 87
  monsoon 2025 sitreps. With a 2.6% base rate, 0.5 is too high a bar; a lower rule has to be set
  by the team and reported as chosen after seeing validation.
- **Model B:** quantile gradient boosting did not beat "no change" on validation (MAE 1.667 vs
  1.665 percentage points; 80% interval coverage 0.89). Prices ship as data plus baseline.

Data assembled so far:
- 160 districts (OCHA admin-2), with elevation, coastal and 2022 flood-prone attributes;
- archived forecasts from Feb 2024 onward, backfilled within the 10,000 calls/day free tier;
- PBS weekly prices for **169 weeks** (5 Jan 2023 to 15 Oct 2026), every week complete
  (17 cities × 51 items), 1,810 values flagged by the quality rules and none filled;
- 157 NDMA documents (98 sitreps, incl. 86 from monsoon 2025; 59 advisories); 1,708 sections indexed so far.

## Impact analysis

- **Who acts on it:** 160 district disaster-management offices and the PDMAs above them. FloodLens gives each a
  daily, district-specific probability of rain beyond that district's own 95th percentile, 1–3 days ahead,
  refreshed every hour.
- **How much better than what they have:** against the district-by-month climatology that planners can already
  read off a calendar, Model A cuts the Brier score by about 6% at 24 h on validation (0.0233 vs 0.0249; paired
  95% interval of the difference −0.0025 to −0.0008). The gain holds in monsoon months, when it matters, and in
  every province. Taking the raw weather-model forecast at face value is worse than climatology (0.0290),
  so the calibration step is what makes the forecasts usable.
- **Where it helps least:** Azad Kashmir (smallest gain). Local cloudbursts like Buner on 15 Aug 2025 are
  smoothed out by daily satellite rain, so neither the labels nor the model can be trusted for single-valley
  flash floods. That is stated on the dashboard.
- **Reach at almost no cost:** the whole system runs on one CPU at an Open-Meteo free-tier budget, so a PDMA could
  run it without new infrastructure (see the business model).
- **Food security link:** each district is mapped to its nearest PBS market, so a planner looking at a high-risk
  district also sees whether staple and fuel prices there are already above their 52-week range.

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
[`DATASET_DECLARATION.md`](DATASET_DECLARATION.md).

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
backend/   pipeline, models, flow, tests, docs (optimisation log, analysis, sources)
space/     Hugging Face Docker Space files (alternative to the static Space)
*.md, *.pdf at the root: TASKS, DATASET_DECLARATION, AI_Use_Log, Summary.pdf, datasetproposal.pdf
frontend/  React dashboard (Base44 template); Live data page reads status.json
```

AI assistance is logged in [`AI_Use_Log.md`](AI_Use_Log.md).
