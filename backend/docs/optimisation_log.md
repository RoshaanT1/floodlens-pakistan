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
