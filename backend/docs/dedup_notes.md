# Duplicate D4–D6 and Q1 implementations

Two people built D4, D5, D6 and Q1 in parallel on 20 Oct. Both versions are on `main`
and nothing has been deleted. `src/build.py` currently runs the first column. This note
compares the two so the team can pick one. Nothing here has been removed or changed.

Neither version has run on real IMERG data on this machine, because there is no
Earthdata login in `backend/.env`.

| | A: `imerg.py`, `rain.py`, `labels.py`, `quality.py` (Roshaan + Claude Code) | B: `fetch_imerg.py`, `build_rain_district.py`, `build_thresholds.py`, `quality_checks.py` (Hammad + Antigravity) |
| --- | --- | --- |
| **D4 download** | GES DISC OPeNDAP, cropped server-side to `PAK_BBOX` (~100 KB per day). Manifest query is the exact OPeNDAP URL, so reruns skip finished days. Threaded; `max_days` cap per run. | `earthaccess` search + download of the full global granule. Manifest query is a descriptive string (`short_name=… date=…`), not a re-runnable URL. One day at a time, and no skip-if-done, so a rerun downloads everything again. |
| **D4 auth** | `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` | `EARTHDATA_TOKEN`, or username + password |
| **D5 input** | `xarray` on the cropped netCDF: `precipitation`, `precipitation_cnt` | `h5py`, reading `Grid/precipitationCal`. **That is the V06 variable name; V07 calls it `Grid/precipitation`.** Check this on one real V07 file before choosing B. |
| **D5 output** | `rain_district_day(row_id, district_id, date_utc, wettest_mm, mean_mm, n_pixels, n_fill_pixels, min_sample_cnt, low_confidence)` | `rain_district_day(district_id, date_utc, wettest_pixel_mm, mean_rain_mm, n_pixels)`. No `row_id`, which D5's "Done when" asks for. |
| **Small districts** (no pixel centre inside, e.g. some Karachi districts) | nearest pixel to the centroid | NULL every day |
| **Fill −9999.9 / Q3** | masked, counted in `n_fill_pixels`; `low_confidence` when fewer than 24 of 48 samples | masked; no sample count |
| **D6 wet day** | `wettest_mm >= 1` (**as declared**) | `wettest_pixel_mm > 0` (**differs from the declaration**, which says 1 mm or more) |
| **D6 baseline** | share of 2015–2023 days over the threshold, per district and month (**as declared**) | mean rain per district and month. That is not a probability, so it can't be scored with Brier against the label. |
| **D6 label column** | `label`, plus `row_id`, `low_confidence` | `flood_label` |
| **Q1/Q2** | pandera rules, each with a fix/fill/flag decision cached in `docs/quality_decisions.json` and logged to `quality_log` (Q2 done) | pandera schemas; any failure fails `make data` (exit 1). No decisions log (Q2 not covered). |
| **Tests** | `test_imerg` 3, `test_rain` 3, `test_labels` 1, `test_quality` 3 | `test_fetch_imerg` 6, `test_build_rain_district` 5, `test_build_thresholds` 5, `test_quality_checks` 6 |
| **Used by** | `src/build.py`, `src/model_a.py` (features), `flows/hourly.py` | nothing at present |

## The clash to watch

Both versions write tables with the **same names** (`rain_district_day`, `thresholds`,
`labels`, `baseline_climatology`) but **different columns**. If both ever run in one build,
the last one silently wins and everything downstream breaks. Only one should be wired
into `build.py` at a time.

## Recommendation

Keep A as the pipeline. A matches the declaration on the two fixed decisions where B
differs (the 1 mm wet-day rule and the exceedance-share baseline). It also has row IDs,
Q2 and Q3, and Model A and the hourly flow are already built on it.

From B, take what A lacks:
- the token login (`EARTHDATA_TOKEN`) as a second auth option in `src/imerg.py`;
- B's extra test cases, moved over to A's column names.

Then move B's four modules and four test files into a `legacy/` folder, or delete them
once Hammad agrees. That decision is the team's; nothing has been removed.
