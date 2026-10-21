# HackInsight participant guide: our answers

Team Spark H · FloodLens Pakistan · every number here comes from files in this repo (paths given).
Use this as the viva script: each member should be able to say every answer in their own words.

---

## Ch. 2: How we show each scoring point

| Criterion | Where to look |
| --- | --- |
| Automatic checks (40) | Baseline declared in `DATASET_DECLARATION.md` (committed Mon before 12:00); `make data` rebuilds everything and refuses changed raw files; nothing hard-coded (`frontend/public/data/status.json` is written by the pipeline) |
| Dataset (20) | `backend/data/manifest.csv` (every raw file: source, query, UTC fetch time, SHA-256, licence); `datasetproposal.pdf`; `backend/docs/sources.md` |
| Agentic design + automation (15) | Data Quality Agent decisions in `quality_log` / `backend/docs/quality_decisions.json`; hourly Prefect flow `backend/flows/hourly.py`; `prefect_runs.csv` |
| Scientific rigour (10) | Time splits; 95% day-block bootstrap intervals; per-group table `backend/docs/model_a_analysis.md`; leakage tests `backend/tests/test_model_a.py` |
| Usefulness + responsible AI (10) | Row IDs behind every number; Insight Agent cites sections and says "I don't know"; limits stated on the dashboard and in the README |
| Viva + demo (5) | this file; demo video |

**Pakistan Impact Bonus**
- Problem: district heavy-rain warnings for Pakistan's 160 districts (2025 monsoon: 1,037 deaths, NDMA).
- Data: Pakistan's districts (OCHA), satellite rain over Pakistan, PBS prices for 17 Pakistani cities, NDMA reports.
- Local usability: Urdu answers on the Ask page; district names as NDMA uses them; PKT times on the dashboard.
- Local validation: model flags compared with districts named in NDMA's 87 monsoon 2025 sitreps (`backend/docs/ndma_districts_2025.csv`, E2 in `model_a_analysis.md`).

**Optional extras we have:** Urdu output (Ask page). Not built: data-enrichment agent, supervisor agent, drift monitor, human-in-the-loop approval.

---

## Ch. 3: Problem analysis worksheet

- **Team name:** Spark H
- **Track:** Climate and heat-health (disaster risk), with a secondary food-security model.
- **Problem statement:** District planners in Pakistan get national and provincial rain alerts, but no
  district-specific, calibrated probability of unusually heavy rain 1–3 days ahead. FloodLens provides one, every hour.
- **Primary user and decision:** a district or PDMA disaster-management planner deciding, 24–72 hours ahead, where
  to pre-position rescue teams, pumps and relief stock and where to issue local warnings.
- **Why it matters in Pakistan (cited):** the 2025 monsoon killed 1,037 people and injured 1,067 between 26 June and
  1 October 2025; 509 of the deaths were in KP (NDMA, *Monsoon 2025 Final Consolidated Situation Report No. 87*,
  2 Oct 2025, stored in `backend/data/raw/ndma_sitrep/`).
- **Who is affected and where:** all 160 districts; we report errors by province, mountain vs plain, coastal vs
  inland, 2022 flood-prone vs not, and monsoon vs dry months.
- **Outcome predicted:** probability that a district's daily wettest-pixel rain (NASA IMERG Late, UTC day) exceeds
  that district's own 95th percentile of wet-day rain (2015–2023), for tomorrow, +2 and +3 days. Binary, daily, per district.
- **Baseline and what counts as better:** district-by-month climatology (share of 2015–2023 days over the
  threshold). Better = lower Brier score at 24 h on the test set, and the gain must also hold in monsoon months.
- **Limits and risks:** daily 0.1° satellite rain smooths out local cloudbursts; forecasts are taken at district
  centroids; the forecast archive starts in Feb 2024 (17 months of training); heavy rain ≠ flood.

---

## Ch. 4: Dataset declaration fields

- **Source 1:** Open-Meteo Previous Runs API (forecasts issued 1–3 days before each date, from ECMWF/NOAA/DWD
  models), open-meteo.com/en/docs/previous-runs-api, CC BY 4.0, models updated every 6 h.
- **Source 2:** NASA GPM IMERG V07 Late Run daily (GPM_3IMERGDL), NASA GES DISC, disc.gsfc.nasa.gov,
  NASA EOSDIS open data policy, daily (~14 h latency).
- **Not on the track list and why credible:** NASA IMERG, NASA's standard multi-satellite rainfall product,
  independent of the weather models we use as inputs. (Also PBS weekly SPI, Pakistan's official weekly prices.)
- **Expected / actual volume:** forecasts 476,640 district-day-lead rows; satellite rain 689,280 district-days
  (2015-01-01 to 2026-10-20); PBS prices 146,523 rows (169 weeks).
- **Why it fits:** archived forecasts give real lead time without leaking the future; satellite rain shows what fell
  even where there is no gauge; both cover every district.
- **Baseline declared before results:** district-by-month climatology (Model A); no change (Model B).

**Source checklist:** original publisher named ✓ · licence and robots.txt allow our access ✓ · covers Pakistan
2015–2026 ✓ · hourly-capable with replay ✓ · fields and units documented ✓ · independent sources ✓.

---

## Ch. 5: Warehouse and `make data`

- Raw: `backend/data/raw/<source>/` + `manifest.csv` (never edited; `save_raw` refuses to overwrite).
- Cleaned: `backend/data/clean/*.parquet` (9 tables). Processed ("gold"): `backend/data/gold/*.parquet`
  (thresholds, labels, baseline, Model A features, live risk), stable row IDs (e.g. `PK505_2025-08-15_L1`).
- `make data`: verifies every SHA-256 against the manifest, builds cleaned then processed layers, runs the quality
  checks, prints the summary, no manual step. Full build: 305 s, 2.57 GB peak.
- **Honest gap:** raw files are not in git (1.3 GB; NDMA's terms do not allow redistribution), so on an empty
  folder `make fetch` re-downloads them first; the Open-Meteo history takes about two days within the free
  daily limit.
- Traps handled: UTC stored, PKT only for display; IMERG fill −9999.9 never read as zero; duplicates removed by
  key; leakage tested; missing prices stay NULL.

---

## Ch. 6: Data Quality Agent: an example logged decision

> `spi_price · spi_price_collected · FLAG · 1,279 rows` — PBS published 0 or nothing for this city and item (not
> collected); kept NULL, never filled. Decided 2026-10-21, replayed on every rebuild.

Other logged decisions: `spi_min_le_avg_le_max` (flag, 822 rows, kept as PBS printed it), `spi_weekly_jump`
(flag, 399 rows, possible typo, not corrected). IMERG fill pixels, low sample counts and NASA re-issues also have rules.

**Why flag instead of fill:** a price PBS did not collect is unknown, not zero, and not "last week's price".
Filling it would invent a number that Model B would then learn from. A flag keeps the gap visible.

---

## Ch. 7: Baseline and model score

Validation (1 Jul to 31 Dec 2025), Brier at 24 h, lower is better, 95% day-block bootstrap:

| | 24 h | 48 h | 72 h |
| --- | --- | --- | --- |
| Climatology (baseline) | 0.0249 [0.0188, 0.0320] | 0.0249 | 0.0249 |
| Gradient boosting (chosen) | 0.0233 [0.0177, 0.0297] | 0.0236 | 0.0235 |

Paired difference at 24 h: −0.0016 [−0.0025, −0.0008] (the gain is larger than day-to-day noise).
**Weakest group:** Azad Kashmir (skill +0.015); a planner there should lean on PDMA AJK advisories.
**Test set (run once, 21 Oct, frozen model, Jan to Sep 2026):** climatology 0.0192 [0.0156, 0.0231] vs model
0.0177 [0.0146, 0.0213] at 24 h; paired difference −0.0014 [−0.0022, −0.0008]; monsoon months 0.0251 vs 0.0237.
Source: `backend/docs/model_a_test.json`.

---

## Ch. 8: Optimization log (full log: `backend/docs/optimisation_log.md`)

1. **Logistic regression → gradient boosting** (both calibrated on validation): val Brier 24 h 0.0238 → 0.0233;
   training 2.3 s → 3.4 s; ~600 MB peak both. Kept.
2. **IMERG server-side crop** instead of global daily files: 33.3 MB → ~74 KB per day; 4,307 days = 182 MB instead
   of ~143 GB. Same values (checked on 14 Aug 2025). Kept.
3. **Cache parsed PBS PDFs by SHA-256:** price build 286 s → 3.6 s on rebuild; identical tables. Kept.
- Also: hourly build into a scratch database swapped in only on success (+~1 s, a failed run cannot corrupt data);
  Model B quantile GBM rejected (MAE 1.667 vs 1.665 for "no change").

**Trade-off:** gradient boosting gained 0.0005 Brier over logistic regression for about a second more training and
a model that is harder to explain; we kept it because it also gained in monsoon months and in every group.

---

## Ch. 9: Insight Agent

**A good answer always has:** the quoted sentence with its document title, page and section id; any number with
its gold-table row id; "I don't know" when nothing passes the threshold; a reminder that it is not an official
warning (and Rescue 1122 / NDMA first for emergencies).

**Tests run (`backend/tests/test_insight.py`, 18 pass + 1 known weakness):**
- answerable question → cites the right document (e.g. Buner deaths → NDMA Sitrep No. 52/53) ✓
- unanswerable question (capital of France, photosynthesis) → "I don't know" ✓
- every number matches its stored row id, in English and Urdu ✓
- leading question ("Why did NDMA say Lahore was hit by a tsunami?") → no invented fact ✓
- emergency wording (English and Urdu) → Rescue 1122 and NDMA/PDMA first ✓
- known weakness: Urdu-only questions retrieve less well (marked as expected failure).
No LLM writes numbers: the wording is fixed templates, the numbers come from tables.

---

## Ch. 10: Run-day checklist

- Scheduler on a machine that stays on: this laptop, as systemd user services with a sleep inhibitor (it slept
  04:33–06:10 on Wed before we added that) ✓
- Secrets outside code and repo: `backend/.env` (gitignored, mode 600) ✓
- Retries set; a failed run cannot corrupt data (scratch database + atomic swap) ✓
- Dashboard updates from the latest run, not fixed numbers: the flow uploads `status.json` to the Space every run ✓
- Run history: `prefect_runs.csv` (Tue 4 PM to Wed 4 PM) + Prefect screenshot. First run at 01:28 Wed, so Tue
  16:00 to Wed 01:28 has no runs; one failed run at 07:05 (fixed, explained in `backend/docs/overnight_report.md`).

---

## Ch. 11: Business model worksheet

- **Primary user and decision:** district/PDMA planner; where to pre-position teams and stock 1–3 days ahead.
- **Payer:** PDMAs/NDMA (provincial preparedness budgets) or humanitarian donors funding anticipatory action.
- **Value proposition:** "For district disaster planners, who need to decide where to pre-position teams before
  heavy rain, FloodLens gives an hourly, calibrated probability of district-specific heavy rain 1–3 days ahead with
  its evidence, unlike today's provincial alerts that are not per district and not probabilistic."
- **Revenue / cost model:** free basic dashboard for the public; a contract or grant for PDMAs (alerts, support);
  anticipatory-action triggers for donors.
- **Main running costs (measured):** one CPU; ~28 min of rate-limited downloading plus ~5 min of rebuild per hour;
  ~1.3 GB storage growing ~10 MB a day; free data (NASA, OCHA, PBS); Open-Meteo free for non-commercial use, paid
  plan needed for commercial use (price to confirm); hosting free (Oracle Always Free) or ~€4/month (Hetzner).
- **Assumptions:** free-tier data terms stay as they are; PDMA staff check a dashboard daily in monsoon.
- **Biggest risks:** trust (mitigated by citations, row IDs and stated limits); a source changing or blocking access
  (gpm1.gesdisc blocked us on Wed; the flow logged it and we switched to NASA's cloud endpoint); drift after
  re-training; a user mistaking rain risk for an official flood warning (labelled everywhere).

---

## Ch. 11: Questions to practise (one sentence each)

1. **Why this problem, who is the user?** The 2025 monsoon killed 1,037 people (NDMA), and district planners have
   no district-specific, calibrated 1–3 day rain risk; our user is the district/PDMA planner.
2. **How do you know it is real?** NDMA's own sitreps: 87 reports in 2025, 125 districts named; the final report
   lists 1,037 deaths.
3. **Why these sources, licence, publisher?** Archived forecasts (Open-Meteo, CC BY 4.0, ECMWF/NOAA/DWD models) give
   honest lead time; NASA IMERG (open data) is an independent observation; both cover every district.
4. **Worst raw-data problem?** NASA's gpm1 server blocked our IP mid-download, and IMERG daily files are 33 MB
   each; we switched to NASA's cloud OPeNDAP and cropped server-side to ~74 KB per day.
5. **Why flag instead of fill?** A price PBS did not collect is unknown; filling it would invent data, so 1,279
   prices stay NULL and flagged.
6. **Baseline and margin?** On the test set (Jan to Sep 2026, run once): climatology 0.0192 vs model 0.0177
   Brier at 24 h, about 7% better, paired interval excludes zero, and it holds in monsoon months.
7. **Where is the model worst?** Azad Kashmir has the smallest gain, and single-valley cloudbursts like Buner on
   15 Aug 2025 are missed by the satellite labels themselves.
8. **How does the Insight Agent never invent a number?** No model writes numbers: code inserts them from gold tables
   with row IDs; text is quoted from documents with section IDs.
9. **Who uses it, who pays, how does it sustain itself?** PDMA planners use it; PDMAs or donors pay through
   preparedness or anticipatory-action budgets; it costs one small server.
10. **What did you optimize, at what cost?** Server-side cropping (143 GB → 182 MB), a parse cache (286 s → 3.6 s),
    and gradient boosting (+0.0005 Brier) at the cost of a less transparent model.

---

## Ch. 12: AI use

All AI help is in `AI_Use_Log.md` (tool and version, task, what we kept or changed, who can explain). Each member
must fill in the "what we verified" and "who can explain" columns for their rows.

---

## Ch. 13: Final submission checklist (status at 20:00, Wed 21 Oct)

| Item | Status |
| --- | --- |
| Repo tagged `v1.0-final` | ✓ on the final commit |
| Hugging Face Space (freshness, quality, last run) | ✓ https://huggingface.co/spaces/RoshaanT1/floodlens-pakistan (opens on the Situation Room; Live data shows freshness, quality status and last run) |
| `prefect_runs.csv` (Tue 4 PM to Wed 4 PM, unedited) + screenshot | ✓ `backend/docs/prefect_runs.csv` (15 runs: 14 completed, 1 failed), `backend/docs/screenshots/` |
| `Summary.pdf` (one page) | ✓ repo root |
| `datasetproposal.pdf` | ✓ repo root |
| Demo video (≤3 min, no login) | ✓ https://roshaant1-floodlens-pakistan.static.hf.space/demo.mp4 (2:52, captioned, silent) |
| `AI_Use_Log.md` honest and complete | ✓ every row has what we verified and who can explain it |
| `make data` rebuilds the cleaned and processed layers | ✓ (raw layer via `make fetch`; see ch. 5) |
| Manifest complete | ✓ |
| Baseline declared before results; model beats it | ✓ (test set, run once: 0.0177 vs 0.0192) |
| Uncertainty and errors by group | ✓ |
| Numbers from gold tables with row IDs; "I don't know" | ✓ |
| Simulated/unfinished labelled | ✓ (sample pages labelled; "validation-stage model") |
| Business model, optimization log ready | ✓ |

**Demo video plan:** 0:00 problem and user (NDMA 1,037 deaths, district planner) · 0:30 sources, manifest, quality
decisions · 1:15 Space: freshness, quality, last run, map; model vs baseline table; Ask page: one cited answer and
one "I don't know" (and Urdu) · 2:15 results by group, the Buner limit, impact.
