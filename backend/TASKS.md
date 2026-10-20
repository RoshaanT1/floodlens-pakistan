.ven# FloodLens task board

Nobody owns a lane. Pick a task, say "On D3" in the group chat, finish it, tick it here.

## Rules

1. Take the first open **[CP]** (critical path) task in the current phase whose "Needs" are done. If every open [CP] task already has someone on it, take any other task in the phase.
2. Model B tasks (marked **[B]**) are a side lane: at most one person on them at a time, and only while every open [CP] task is covered.
3. One task per person at a time. Claim it in chat ("On D3") and release it in chat if you stop.
4. Done means the "Done when" line is true, the code is on `main`, and `make data` still passes. Then tick it with your name: `- [x] **D3** ... (Ron)`.
5. Stuck for 45 minutes? Say so in chat, then pair up or release the task.
6. Every model or pipeline change gets a line in `docs/optimisation_log.md`: metric, run time and memory before and after, kept or rejected.
7. Any material AI help goes into `AI_Use_Log.md` in the same commit.
8. When you finish a task, post three lines in chat on what you built and why, so all three of us can explain it in the viva.

## Fixed decisions (never change after seeing results)

- **Splits:** train to 30 Jun 2025, validate 1 Jul to 31 Dec 2025, test 1 Jan to 30 Sep 2026, run once.
- **Model A target:** daily wettest-pixel rain above the district's 95th percentile of wet-day rain (IMERG Late, 2015 to 2023). Baseline: district-by-month climatology.
- **Model B target:** next week's % price change per item and city. Baseline: no change.
- **Days:** UTC days (05:00 to 05:00 PKT), matching the IMERG daily product. Store UTC; convert to PKT only for display.

## Deadlines

| When (PKT) | What |
| --- | --- |
| Mon 12:00 | Dataset Declaration pushed |
| Mon night | Thin end-to-end slice works |
| Tue 14:00 | Deployed flow frozen; Model B in or out |
| Tue 16:00 to Wed 16:00 | Run-history window (24 hourly runs) |
| Wed 22:00 | Tag `v1.0-final` and submit |

## Phase 0: now to Mon 12:00 PM

- [ ] **S1 [CP]** Create the repo `floodlens-pakistan` with folders `data/raw`, `data/clean`, `data/gold`, `src`, `flows`, `app`, `tests` and `docs`. `.gitignore` covers `.env` and large data files.
  - Done when: all three of us can clone and push.
- [ ] **S2 [CP]** Check on NASA GES DISC that the IMERG Late daily product (GPM_3IMERGDL) goes back to 2015.
  - Done when: confirmed, or the team agrees new threshold years before S3.
- [ ] **S3 [CP]** Fill in the team name and push `DATASET_DECLARATION.md` and `AI_Use_Log.md`.
  - Needs: S1, S2. Done when: the commit is on GitHub before 12:00 PM.
- [ ] **S4 [CP]** Create a NASA Earthdata login and authorise GES DISC. Credentials live in `.env`, never in git.
  - Done when: a script downloads one day of IMERG Late for Pakistan.

## Phase 1: Mon 12:00 PM to Mon night (thin slice, ugly is fine)

### Data

- [ ] **D1 [CP]** Manifest writer: every fetcher saves the raw file untouched and appends source, query, fetch time (UTC), SHA-256 and licence to `manifest.csv`.
  - Done when: any fetch adds its manifest row automatically.
- [ ] **D2 [CP]** District boundaries (OCHA admin level 2, via HDX) into DuckDB with id, name, province and centroid.
  - Needs: D1. Done when: about 160 districts load with centroids.
- [ ] **D3 [CP]** Forecast fetcher: Open-Meteo Previous Runs for every district centroid, `_previous_day1` to `_previous_day3` values for precipitation, humidity, pressure, cloud cover and wind, Jan 2024 to now. Batch coordinates per call; the free tier allows 10,000 calls a day.
  - Needs: D1, D2. Done when: the full period is stored with manifest rows.
- [ ] **D4 [CP]** IMERG fetcher: Late Run daily, cropped to Pakistan's bounding box, 2015 to now.
  - Needs: D1, S4. Done when: every day is stored with manifest rows.
- [ ] **D5 [CP]** District rain table: wettest-pixel and mean rain per district per UTC day.
  - Needs: D2, D4. Done when: `rain_district_day` gold table exists with stable row IDs.
- [ ] **D6 [CP]** Thresholds, labels and baseline: each district's 95th percentile of wet-day wettest-pixel rain (2015 to 2023), labels for 2024 onward, and district-by-month climatology.
  - Needs: D5. Done when: `thresholds`, `labels` and `baseline_climatology` tables exist.
- [ ] **D7** District attributes: elevation (Open-Meteo Elevation API), coastal flag (Natural Earth coastline), flood-prone flag (UNOSAT 2022 flood extent, else the 2022 calamity-hit list).
  - Needs: D2. Done when: `district_attributes` table exists.
- [ ] **D8 [CP]** `make data`: rebuilds the clean and gold layers from the frozen raw snapshot, checks every SHA-256 against the manifest, prints the quality summary, and needs no manual step.
  - Needs: D1 to D6. Done when: it works from a fresh clone on Linux.

### Data Quality Agent

- [ ] **Q1 [CP]** Checks with pandera: schema, ranges, missing values, duplicates and timeliness for forecasts, IMERG and districts.
  - Needs: a sample from D3 and D4. Done when: checks run inside `make data`.
- [ ] **Q2 [CP]** Decisions: each failed check becomes fix, fill or flag, logged with rule, reason, row count and timestamp in `quality_log`. Decisions are cached and replayed on rebuild.
  - Needs: Q1. Done when: two rebuilds give identical gold tables and logs.
- [ ] **Q3** IMERG rules: -9999.9 is flagged, never read as zero; low sample counts mark a district-day low confidence; Late values revised later are flagged.
  - Needs: Q2.

### Model A

- [ ] **A1 [CP]** Feature table per district, day and lead (1, 2 and 3 days): forecast values from D3, month, and observed rain only from days that ended at least 14 hours before the forecast was issued. Add D7 attributes when ready.
  - Needs: D3, D5. Done when: `features_a` exists with row IDs, plus a test proving no feature comes from after issue time.
- [ ] **A2 [CP]** Baseline scores on validation: Brier score for climatology and for the raw forecast cut at the threshold.
  - Needs: A1, D6. Done when: the first entry is in `docs/optimisation_log.md`.

### Pipeline and dashboard

- [ ] **P1 [CP]** Prefect flow, run locally: fetch only new data, write raw files and manifest rows, clean, run the quality agent, rebuild gold tables, score districts (climatology is fine until A3 lands), publish `status.json`.
  - Needs: D8, Q2, D6. Done when: one local run completes end to end.
- [ ] **P2 [CP]** Hugging Face Space v0 that only reads the published status: freshness per source against its own cadence, quality status, last successful run, district risk table.
  - Needs: P1. Done when: the Space URL shows a real run.

## Phase 2: Tue morning to Tue 2 PM (make the hourly run boring)

- [ ] **P3 [CP]** Deploy to an always-on host, never a laptop. Secrets stay outside the repo; schedule `5 * * * *`; retries on; writes safe to repeat.
  - Needs: P1. Done when: 6 green runs in a row.
- [ ] **A3 [CP]** Model A: v1 logistic regression, v2 gradient boosting, probabilities calibrated on validation.
  - Needs: A2. Done when: validation Brier is compared with both baselines and logged.
- [ ] **A4** Model swap: the flow loads whichever model artifact is current, so upgrades never touch flow code.
  - Needs: P3, A3.
- [ ] **P4 [CP]** Freeze the deployed flow at 2 PM. After this, only model artifacts change.
  - Needs: P3.
- [ ] **P5** Write the `prefect_runs.csv` export script now; run it on Wednesday.
  - Needs: P3.
- [ ] **R1** Document library: NDMA and PDMA advisories and situation reports, PMD outlooks and PBS SPI reports, each stored raw with a manifest row.
- [ ] **R2** Index: split documents into sections, embed with a multilingual model that handles Urdu, store in Chroma or FAISS.
  - Needs: R1. Done when: a query returns sections with source and section IDs.

## Phase 3: Tue 4 PM to Wed 4 PM (run window; improve in branches)

- [ ] **E1 [CP]** Watch the hourly runs. If one fails, fix it in a branch, test locally, then deploy, and say so in chat.
- [ ] **R3** Answer builder: the LLM writes words around placeholders, code inserts numbers from gold tables with row IDs, every claim cites a section, and no match above the retrieval threshold means "I don't know".
  - Needs: R2.
- [ ] **R4** Insight tests: the right citation for answerable questions, "I don't know" when unsupported, numbers matching row IDs in both languages, no invented fact for a leading question, and emergencies pointed to NDMA, PDMA and Rescue 1122.
  - Needs: R3.
- [ ] **R5** Urdu output, with an Urdu toggle on the Space.
  - Needs: R3.
- [ ] **A5** Uncertainty and groups: bootstrap intervals and a per-group table (province, mountain vs plain, coastal vs inland, flood-prone vs not, monsoon vs dry). Name the weakest group.
  - Needs: A3.
- [ ] **A6** Buner case study: what the model said for 14 and 15 Aug 2025, hit or miss, and why.
  - Needs: A3.
- [ ] **E2** Local validation: districts flagged during the 2025 monsoon compared with districts named in NDMA situation reports.
  - Needs: A3, R1.
- [ ] **P6** Replay mode: run the flow over 10 to 20 Aug 2025 into a separate store, clearly labelled, never mixed into the live run history.
  - Needs: P3.
- [ ] **P7** District map on the Space.
  - Needs: P2.
- [ ] **Q4** Human approval for large fills, shown on the Space (optional extra).
  - Needs: Q2, P2.

## Model B lane [B] (start once the open Phase 1 [CP] tasks are covered)

- [ ] **B1 [B]** Find the URL pattern for PBS's weekly city-wise annex and download every week from Jan 2023, with manifest rows.
  - Needs: D1.
- [ ] **B2 [B]** PDF extractor: item, city, week, minimum, average, maximum and unit.
  - Done when: one full year parses and passes B3.
- [ ] **B3 [B]** PBS quality rules: minimum ≤ average ≤ maximum, 17 cities × 51 items each week, units kept, ranges checked against each item's history, bad weeks flagged and never filled.
  - Needs: B2, Q2.
- [ ] **B4 [B]** Model B: features (1, 4 and 12-week changes, same week last year, item group, fuel change, nearby rain anomaly), the no-change baseline, and quantile gradient boosting at the 10th, 50th and 90th percentiles.
  - Needs: B3, D5. Done when: validation error and interval coverage for staples, perishables and fuel are logged.
- [ ] **B5 [B]** Gate at Tue 2 PM: Model B joins the hourly flow only if it is stable; otherwise it ships as a separate panel built by `make data`.
- [ ] **B6 [B]** Market watch on the Space: latest prices for the city nearest each flagged district, plus a typical-range band labelled as history, not a forecast.
  - Needs: B4, P2.

## Phase 4: Wed 4 PM to 10 PM (package and submit)

- [ ] **E3 [CP]** Run the test set once (Jan to Sep 2026) for both models and save the results. No tuning after this.
- [ ] **E4 [CP]** Export `prefect_runs.csv` for Tue 4 PM to Wed 4 PM, unedited, plus Prefect and Space screenshots.
  - Needs: P5.
- [ ] **E5 [CP]** Fresh-clone check on Linux: `make data` and all tests pass.
- [ ] **X1** README: problem, architecture, how to run, results, limits, data sources and licences.
- [ ] **X2** Business model section: user, payer, value, running costs measured during the event, risks.
- [ ] **X3** `Summary.pdf`, one page.
- [ ] **X4** Demo video, 3 minutes or less, opening without a login: problem and user, data and quality decisions, dashboard and replay, model vs baseline, one cited answer and one "I don't know", groups and limits, Pakistan impact.
- [ ] **X5** Complete `AI_Use_Log.md`.
- [ ] **X6 [CP]** Tag `v1.0-final` by 10 PM and submit the form: repo, Space link, `prefect_runs.csv`, Summary.pdf, video and AI log.
  - Needs: E3 to E5, X1 to X5.
- [ ] **X7** Viva prep: each of us explains every module. Rehearse "What does this add over PMD's forecasts?" and "Where does the model fail?".
