# Optimisation log

One row per model or pipeline change (TASKS.md rule 6).

| Date | Who | Change | Metric before | Metric after | Run time before / after | Memory before / after | Kept or rejected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-21 | Claude Code (overnight) | B4 baseline: no change | - | val MAE 1.665 pp | 0.0 s | 336 MB peak RSS | baseline |
| 2026-10-21 | Claude Code (overnight) | B4 quantile GBM (10/50/90) | no change 1.665 pp | val MAE 1.667 pp, 80% coverage 0.89 | 5.5 s | 336 MB peak RSS | rejected |
| 2026-10-21 | Claude Code (overnight) | A2 baseline: district-by-month climatology | - | val Brier 24h 0.0249 [0.0188, 0.0320] | 0.0 s | 593 MB peak RSS | baseline |
| 2026-10-21 | Claude Code (overnight) | A2 baseline: raw forecast cut at threshold | - | val Brier 24h 0.0290 [0.0217, 0.0371] | 0.0 s | 593 MB peak RSS | baseline |
| 2026-10-21 | Claude Code (overnight) | A3 logreg, Platt-calibrated on validation (cross-fitted by ISO week) | climatology 0.0249 | val Brier 24h 0.0238 [0.0182, 0.0305] | 2.9 s | 593 MB peak RSS | kept |
| 2026-10-21 | Claude Code (overnight) | A3 gbm, Platt-calibrated on validation (cross-fitted by ISO week) | logreg 0.0238 | val Brier 24h 0.0233 [0.0177, 0.0297] | 3.4 s | 593 MB peak RSS | kept |
| 2026-10-21 | Claude Code (overnight) | A2 baseline: district-by-month climatology | - | val Brier 24h 0.0249 [0.0188, 0.0320] | 0.0 s | 596 MB peak RSS | baseline |
| 2026-10-21 | Claude Code (overnight) | A2 baseline: raw forecast cut at threshold | - | val Brier 24h 0.0290 [0.0217, 0.0371] | 0.0 s | 596 MB peak RSS | baseline |
| 2026-10-21 | Claude Code (overnight) | A3 logreg, Platt-calibrated on validation (cross-fitted by ISO week) | climatology 0.0249 | val Brier 24h 0.0238 [0.0182, 0.0305] | 2.3 s | 596 MB peak RSS | kept |
| 2026-10-21 | Claude Code (overnight) | A3 gbm, Platt-calibrated on validation (cross-fitted by ISO week) | logreg 0.0238 | val Brier 24h 0.0233 [0.0177, 0.0297] | 3.4 s | 596 MB peak RSS | kept |
| 2026-10-21 | Claude Code | Note: the A2/A3 rows above were run twice; the second run (identical metrics, fixed seeds) re-saved the artifact with an importable class (20261021T0446Z_gbm). Paired day-block bootstrap, gbm minus climatology, 24 h: -0.0016 [-0.0025, -0.0008] | - | - | - | - | - |
| 2026-10-21 | Claude Code | IMERG: server-side crop to Pakistan (OPeNDAP) instead of global daily files | 33.3 MB per day (full granule, HEAD on data.gesdisc) | ~74 KB per day (4,307 days = 182 MB instead of ~143 GB) | download-bound either way | – | kept |
| 2026-10-21 | Claude Code | PBS SPI: cache parsed annexes by SHA-256 (data/clean/spi_parsed) | `spi.build` 286 s, 380 MB peak (pdfplumber over 114 PDFs) | 3.6 s on rebuild (only new files parsed) | 286 s / 3.6 s | 380 MB / – | kept |
| 2026-10-21 | Claude Code | Hourly build into a scratch DuckDB copy, swapped in only on success | a failed step could leave a half-built database | live database untouched by failed runs | +~1 s for the copy | +62 MB disk during the build | kept |
| 2026-10-21 | Claude Code | Open-Meteo budget per UTC day (9,000) read from the manifest, ≤2,000 calls per run | rolling 24 h window: backfill would finish Thu evening | backfill done Wed ~11:00; no daily-limit errors | ~28 min per run (rate pacing) | – | kept |
| 2026-10-21 | Claude Code | Full `make data` with IMERG (4,307 days) + model scoring | – | 305 s, 2.57 GB peak RSS | 305 s | 2.57 GB | measured |
| 2026-10-21 | Claude Code | Document index: multilingual-e5-small + FAISS flat index, 1,708 sections | – | build 449 s on CPU, 2.0 GB peak; query ~0.4 s via the API with the model kept loaded | 449 s | 2.0 GB | measured |
