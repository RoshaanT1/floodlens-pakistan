# Overnight report, 20–21 Oct 2026

Branch: `overnight/2026-10-20` (pushed). Work by Claude Code (Opus 5.5) on Roshaan's machine.
`main` was synced first: it was only ahead of origin, so it was pushed as is (8d4d4c5) with
38/38 tests passing.

## 1. The blocker: no NASA Earthdata login on this machine

`backend/.env` doesn't exist. GES DISC serves IMERG metadata without a login, but every data
request redirects to urs.earthdata.nasa.gov (checked 01:30 PKT). With no IMERG there are
**no labels, thresholds or climatology**, so:

- **Model A could not be trained, validated or scored tonight.** There are no A2, A3, A5 or
  A6 numbers, and no model output in the dashboard. I have not made any up.
- All of that code is written, tested on made-up fixtures, wired into `make data` and the
  flow, and runs with the commands in section 8 as soon as IMERG is in.

To unblock (Hammad's AI-use log says his login works):

```bash
cd backend
cp .env.example .env     # set EARTHDATA_USERNAME and EARTHDATA_PASSWORD (GES DISC authorised)
.venv/bin/python -m src.imerg fetch --workers 8   # 2015 to yesterday, resumable, ~100 KB a day
```

The hourly flow picks up `.env` by itself, but it takes only 300 IMERG days per run. Run the
command above by hand: about 4,300 days.

I did **not** switch to the ERA5 reserve source. The declaration allows it only "if IMERG
access fails", and access works for the team; only this machine lacks the login. ERA5 for
2015–2023 would also cost ~40k Open-Meteo calls, about four days of quota.

## 2. Done, by task (commits on `overnight/2026-10-20`)

| Task | Status | Commits |
| --- | --- | --- |
| P0 sync | `main` pushed (8d4d4c5); branch created | – |
| **P1** hourly flow | `flows/hourly.py`: fetch new data → `make data` into a scratch DB, swapped in only on success → `make export`. Running locally under a Prefect server. | 9b0d9f5, 39fdc19 |
| **P3** (partly) | retries, idempotent fetches, one run at a time, atomic DB and status.json writes. **Still on this laptop, not an always-on host** (see decisions). | 9b0d9f5 |
| **P5** | `flows/export_runs.py` writes `docs/prefect_runs.csv` for Tue 16:00 to Wed 16:00 PKT. Tested on the live server; **final export not run**. | 9b0d9f5 |
| **D3** backfill | runs inside the flow, oldest month first, under a 9,000 calls-per-UTC-day cap read from the manifest. See section 3. | a9c9a22, 39fdc19 |
| **D7** | `district_attributes`: centroid elevation (56 mountain at ≥1000 m), coastline within 10 km (12 coastal), UNOSAT 2022 flood share ≥10% (33 flood-prone); all 160 matched | e2e31fd |
| **A1** | `src/model_a.py features` → `features_a` (forecast leads 1–3, threshold ratio, climatology, month, observed rain lagged ≥14 h, D7). **Leakage tests**: `tests/test_model_a.py` | 4a1b841, e2e31fd |
| **A2** | climatology and raw-forecast-cut baselines, Brier with 95% day-block bootstrap per lead | 4a1b841 |
| **A3** | logistic regression, then gradient boosting; Platt calibration on validation, cross-fitted by ISO week so the reported validation Brier is honest; fixed seed; each experiment appended to `docs/optimisation_log.md` automatically | 4a1b841 |
| **A4** | versioned artifact `models/model_a/<version>/` + `current.json`; the build's `score_live` loads whatever is current, so upgrades never touch flow code | 4a1b841 |
| **P4** | `make export` adds Model A probabilities (24/48/72 h, each with its row_id and the label "validation-stage model") once `risk_live` exists; new **Live data** page (all 160 districts, real data only); sample pages and placeholder accuracy figures are now labelled as such | 4a1b841, 2c2bb60, 15075ca |
| **A5/A6/E2** | `src/analysis_a.py report` (groups, weakest group, Buner 14–15 Aug 2025, NDMA comparison) is written and tested on fixtures. NDMA half of E2 done: `docs/ndma_districts_2025.csv` (86 sitreps; 125 districts named) | 8c679d8, 91f369f |
| **R1** | `src/documents.py`: 86 NDMA monsoon 2025 sitreps, 55 advisories (Jun–Oct 2025), listing pages, all with manifest rows | 7d7f46c |
| **R2** | `src/doc_index.py`: 1,516 sections from 128 documents, multilingual-e5-small + FAISS, in a separate `.venv-insight` | 7d7f46c |
| **B1–B3** (start) | `src/spi.py`: 55 weekly annex xlsx (30 Apr 2025 to 15 Oct 2026), parsed to 47,685 rows; all 55 weeks complete (17 × 51); 337 rows flagged, none filled | 09b6ece, a70b548, 4115c13 |
| dedup | `docs/dedup_notes.md` compares the two D4–D6/Q1 implementations; nothing deleted | af8ca52 |

Tests: **56 passing** (`make test`). `make data` passes on the current snapshot (17 s, 767 MB peak).

## 3. Flow status

See the "Flow log" at the end for the run-by-run record.

- Prefect server: http://127.0.0.1:4200 (UI). Deployment `floodlens-hourly/hourly`, cron `5 * * * *`.
- **Lost window time:** the window opened Tue 16:00 PKT, but the first run was at 01:28 PKT
  (Wed). Tue 16:00 to Wed 01:28 has no runs.
- Each run spends ≤2,000 Open-Meteo calls on the backfill (~28 min of paced requests), then
  rebuilds (~1 min). Once the day's 9,000 cap is used, runs take ~2 minutes.
- **Backfill reach:** about 17 months of history (Jul 2024 to about Nov 2025) by Wed
  afternoon; 2026 is fetched afterwards. Validation ends 31 Dec 2025.

### Start and stop

```bash
cd backend
# start (both survive closing the terminal)
setsid nohup .venv/bin/prefect server start --host 127.0.0.1 --port 4200 > logs/prefect_server.log 2>&1 < /dev/null &
setsid nohup .venv/bin/python -m flows.hourly serve > logs/flow_serve.log 2>&1 < /dev/null &
# one manual run now (the served deployment picks it up)
.venv/bin/prefect deployment run floodlens-hourly/hourly
# stop
pkill -f "flows.hourly serve"; pkill -f "prefect server start"
# run history for the judged window (Wednesday, once)
.venv/bin/python -m flows.export_runs        # -> docs/prefect_runs.csv
```

`fastapi` is pinned to 0.153.0: newer versions break the Prefect 3.8.8 server
(`Body(min_items=...)`). The pin is in `requirements.txt`.

## 4. Validation results

None yet; this needs IMERG (section 1). After IMERG is in:
`make data && .venv/bin/python -m src.model_a train && .venv/bin/python -m src.analysis_a report`
writes `docs/model_a_validation.json`, rows in `docs/optimisation_log.md` and
`docs/model_a_analysis.md`. `train` reports honestly when no model beats climatology: it writes
no artifact, and the dashboard keeps showing raw forecasts only.

## 5. Failed or skipped

- **IMERG / Model A numbers / A5 / A6**: blocked (section 1).
- **P3 always-on host**: not done; the flow runs on this laptop because the brief said so.
- **PMD**: `cdpc.pmd.gov.pk` returned HTTP 500 for the 2025 monsoon update and for robots.txt;
  `www.pmd.gov.pk` errors as well. Logged; no PMD files stored.
- **PDMA sites**: not crawled.
- **PBS SPI before 30 Apr 2025**: not in PBS's media listing under "annex"; older file names
  differ. B1 asks for Jan 2023 onward, so ~2.3 years are still missing (docs/sources.md).
- **Model B (B4–B6)**: not started.
- **R2 Urdu**: an Urdu query for Buner floods returns related flood advisories but not the
  Buner sitrep sections that the English query finds. Cross-lingual retrieval with the
  small model is weak, so R3 should translate Urdu questions to English before retrieval, or
  use a larger model.
- **E2 caveat**: name matching is exact. NDMA also writes "Bunner", so variant spellings are
  undercounted. Islamabad, Lahore and Rawalpindi appear in every sitrep (addresses, station
  tables).

## 6. Decisions that need a human

1. **Earthdata login.** Add `.env` on this machine, or have Hammad run the IMERG fetch and
   share `data/raw/imerg_late_daily/` plus the manifest rows. *Recommendation: add `.env`
   here and run the fetch by hand now; Model A needs ~2 h of compute after that.*
2. **Which D4–D6/Q1 implementation.** *Recommendation: A (see docs/dedup_notes.md). B's wet-day
   rule (>0 mm) and baseline (mean rain) differ from the declaration.*
3. **Open-Meteo budget.** I count 9,000 calls per UTC day. If Open-Meteo actually counts a
   rolling 24 h, the API stops runs with a 429 and the flow logs it and carries on.
   *Recommendation: keep it.*
4. **Always-on host for P3.** *Recommendation: if the laptop can't stay on until Wed 16:00,
   move to a small VM (same commands; copy `data/raw` and the manifest).*
5. **Mountain cut-off (1000 m at the centroid)** and the **E2 flag rule (p ≥ 0.5)** were
   chosen tonight, before any model results. Confirm or change them *before* looking at
   validation results.
6. **ERA5 fallback**: only if the login can't be sorted today. That is the declared reserve,
   and the labels would then have to be described as modelled.

## 7. Notes for the viva

- Leakage proof: `tests/test_model_a.py::test_observed_days_end_14h_before_issue` and
  `::test_features_never_see_rain_after_cutoff`. For target day D at lead N, the earliest
  issue time is (D−N) 00:00 UTC, and the newest observed day allowed is D−N−2.
- The test split is locked: `model_a.split(..., "test")` raises unless `FLOODLENS_RUN_TEST=1`.

## 8. Reproduce

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.districts fetch && .venv/bin/python -m src.districts build
.venv/bin/python -m src.forecasts fetch --budget 9000     # rerun daily until complete
.venv/bin/python -m src.forecasts live
.venv/bin/python -m src.imerg fetch --workers 8           # needs .env
.venv/bin/python -m src.attributes fetch
.venv/bin/python -m src.documents fetch
.venv/bin/python -m src.spi fetch
make data                                                  # verify manifest + rebuild every table
.venv/bin/python -m src.model_a train                      # A2, A3, A4 (needs IMERG)
.venv/bin/python -m src.analysis_a ndma && .venv/bin/python -m src.analysis_a report
make export                                                # frontend/public/data/status.json
make test
# document index (separate venv, ~8 min on CPU)
python3 -m venv .venv-insight && .venv-insight/bin/pip install -r requirements-insight.txt
.venv-insight/bin/python -m src.doc_index build
.venv-insight/bin/python -m src.doc_index query "flash floods in Buner August 2025"
```

## Flow log

| Run | Started (PKT) | State | Duration | Notes |
| --- | --- | --- | --- | --- |
| capable-puma (manual) | 21 Oct 01:28 | Completed | 28.5 min | 1,976 calls; forecasts now to 31 Oct 2024; IMERG skipped (no login) |
