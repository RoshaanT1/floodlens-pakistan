# Dataset Declaration

**Team:** Error 200
**Project:** FloodLens Pakistan: rain-risk and food-price early warning
**Track:** Climate and heat-health (disaster risk), with a secondary food-security model
**Commit time:** see git history (deadline 19 Oct 2026, 12:00 PM PKT)

## Problem and primary user

District disaster planners in Pakistan need one to three days of warning before dangerous rain to pre-position teams and supplies. The 2025 monsoon killed at least 1,037 people (NDMA figures, [compiled here](https://en.wikipedia.org/wiki/2025_Pakistan_floods)).

**Primary user and decision:** a district or PDMA planner deciding, 24 to 72 hours ahead, where to pre-position resources and where to issue local warnings.

## Sources

### Source 1: Archived weather forecasts

- **Name:** Open-Meteo Previous Runs API (forecasts issued 1 to 3 days before each date)
- **Publisher:** Open-Meteo, relaying national weather models (ECMWF, NOAA, DWD)
- **URL:** https://open-meteo.com/en/docs/previous-runs-api
- **Licence:** CC BY 4.0; free tier for non-commercial use
- **Update frequency:** global models every 6 hours; archive available from January 2024
- **Use:** Model A features

### Source 2: Satellite rainfall

- **Name:** NASA GPM IMERG V07: Late Run daily (GPM_3IMERGDL) for labels, thresholds and baseline; Early Run half-hourly (GPM_3IMERGHHE) for the live view
- **Publisher:** NASA Goddard Earth Sciences Data and Information Services Center (GES DISC)
- **URL:** https://disc.gsfc.nasa.gov (search the product short names above)
- **Licence:** openly shared without restriction under NASA's EOSDIS data use policy, cited as required
- **Update frequency:** 0.1 degree grid; Early Run about 4 hours after the fact, Late Run about 14 hours
- **Use:** Model A labels, danger thresholds and baseline; observed-rain features for both models

### Source 3: Food prices

- **Name:** Weekly Sensitive Price Indicator (summary and city-wise annex)
- **Publisher:** Pakistan Bureau of Statistics
- **URL:** https://www.pbs.gov.pk (example report: https://www.pbs.gov.pk/wp-content/uploads/2020/07/Executive-Summary-SPI-Report_20.08.2026.pdf)
- **Licence:** public government statistics; terms of use to be confirmed
- **Update frequency:** weekly, with weeks ending on Thursday; 51 items from 50 markets in 17 cities
- **Use:** Model B target and features

### Supporting sources

- **District boundaries:** OCHA Pakistan subnational boundaries via HDX (licence to be confirmed on the dataset page). Used to turn grid rainfall into district values.
- **Elevation:** Copernicus DEM GLO-90 via the Open-Meteo Elevation API (attribution required). Used for the district elevation feature and the mountain vs plain groups.
- **Flood-prone districts:** UNOSAT's satellite-detected flood extent for the 2022 floods, via HDX (licence to be confirmed). A district counts as flood-prone if 10% or more of its area flooded. If this dataset is unavailable, we use the districts officially declared calamity-hit in 2022. Used only to define an evaluation group.
- **Coastline:** Natural Earth (public domain). Used for the coastal vs inland groups.
- **Official documents:** NDMA, PDMA and PMD advisories and situation reports. Used for the Insight Agent's citations and for local validation, never for training.

### Reserve sources (used only if the stated condition occurs)

- **ERA5 rainfall** via the Open-Meteo Historical Weather API (Copernicus Climate Change Service; CC BY 4.0 via Open-Meteo). Used only if IMERG access fails. The same target, threshold and baseline definitions then apply, computed from ERA5 2015 to 2023, and we will state that labels are modelled rather than observed.
- **Station rainfall:** NOAA GHCN-Daily records for Pakistani stations (NOAA NCEI; terms and coverage to be confirmed). Used to cross-check IMERG at rain gauges.
- **District population:** 7th Population and Housing Census 2023 (Pakistan Bureau of Statistics). Used to report how many people live in flagged districts.

Reserve sources never change the declared definitions, baselines or splits. The ERA5 fallback only swaps the data behind them.

## Source not on the track list

NASA IMERG. It is NASA's standard multi-satellite rainfall product, produced independently of the weather models we use as inputs, so it gives a fair check on them. PBS weekly SPI is also off the list and is the official source of Pakistan's weekly consumer prices.

## Independence

Model A's inputs come from numerical weather models, and its labels come from satellite rainfall estimates: different publishers, different methods. PBS prices are independent of both.

## Expected volume

- **Model A:** about 160 districts × about 1,000 days (Jan 2024 to Oct 2026), roughly 160,000 district-days at three lead times.
- **Model B:** 51 items × 17 cities × about 190 weeks (Jan 2023 to Oct 2026), roughly 165,000 rows.

## Why this data fits

Planners need district-level warnings one to three days ahead. Archived forecasts give that lead time without leaking the future, satellite rainfall shows what actually fell even where no rain gauge exists, and PBS gives weekly city prices for the food impact.

## Declared baselines and evaluation (fixed before any results)

|  | Model A: district rain-risk (primary) | Model B: weekly food prices (secondary) |
| --- | --- | --- |
| Target | 1 if the district's daily wettest-pixel rainfall exceeds the 95th percentile of that same series on wet days (1 mm or more), computed from IMERG Late 2015 to 2023 | Next week's % change in each item's city average price |
| Baseline | District-by-month climatology: the share of days crossing the threshold in IMERG Late 2015 to 2023 | No change: next week's price equals this week's |
| Main metric | Brier score at 24 hours (48 and 72 hours also reported) | Mean absolute error of the weekly % change, plus 80% interval coverage |
| Also reported | The raw forecast cut at the same threshold; reliability; hit and false-alarm rates | Results split into staples, perishables and fuel |
| Training data | Jan 2024 to 30 Jun 2025 | Jan 2023 to 30 Jun 2025 |
| Validation | 1 Jul to 31 Dec 2025 | 1 Jul to 31 Dec 2025 |
| Test (run once) | 1 Jan to 30 Sep 2026 | 1 Jan to 30 Sep 2026 |

**What counts as better:** beating the declared baseline on the test set. For Model A, the gain must also hold in monsoon months, not only in dry months.

## Leakage rules

- Only forecast values issued 24 to 72 hours before the target day are used.
- Observed-rain features are lagged by at least 14 hours, matching IMERG Late Run latency.
- Thresholds, scalers and calibration are fitted on training or validation data only.

## What we will not claim

- Flood extent, damage or deaths. Model A predicts heavy rain, not floods.
- That rain caused any price change. Prices cover 17 cities, not rural markets.
- That outputs are official warnings. Users should follow NDMA and PDMA advisories and call Rescue 1122 in an emergency.
