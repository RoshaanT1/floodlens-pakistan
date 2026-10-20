# Sources

Every raw file is saved untouched under `data/raw/<source>/`, with a row in
`data/manifest.csv` (source, exact query or URL, fetch time in UTC, SHA-256, bytes,
licence). The `source` column below is that manifest key.

## Model inputs and labels

| Source key | What | Publisher | URL | Licence / terms | Used for |
| --- | --- | --- | --- | --- | --- |
| `ocha_cod_ab` | Admin-2 district boundaries | OCHA via HDX | https://data.humdata.org/dataset/cod-ab-pak | CC BY-IGO | districts, centroids, D5 pixel mapping |
| `open_meteo_previous_runs` | Archived forecasts (`_previous_day1..3`) | Open-Meteo (ECMWF, NOAA, DWD models) | https://open-meteo.com/en/docs/previous-runs-api | CC BY 4.0; free tier for non-commercial use (<10,000 calls a day) | Model A features (training and validation) |
| `open_meteo_live_forecast` | Latest forecast run, next 4 days | Open-Meteo | same endpoint, plain variables | CC BY 4.0 | live view and live scoring only, never training |
| `imerg_late_daily` | GPM IMERG V07 Late daily (GPM_3IMERGDL), cropped | NASA GES DISC | https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary | NASA EOSDIS open data policy (cite) | labels, thresholds, baseline, observed-rain features. **Needs an Earthdata login in `backend/.env`.** |

## District attributes (D7)

| Source key | What | Publisher | URL | Licence | Used for |
| --- | --- | --- | --- | --- | --- |
| `open_meteo_elevation` | Elevation at district centroids (Copernicus DEM GLO-90) | Open-Meteo | https://open-meteo.com/en/docs/elevation-api | CC BY 4.0; DEM © Copernicus (attribution required) | mountain vs plain group; feature |
| `natural_earth_coastline` | 1:10m coastline | Natural Earth | https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip | Public domain | coastal vs inland group; feature |
| `unosat_flood_2022` | Satellite-detected flood water per district, 25 Aug to 7 Sep 2022 | UNOSAT (UNITAR), via HDX | https://data.humdata.org/dataset/preliminary-satellite-derived-flood-evolution-assessment-islamic-republic-of-pakistan-9-se | CC BY-SA (per HDX) | flood-prone group (10% or more of area flooded); feature |

## Document library (R1): citations and local validation only, never training

| Source key | What | Publisher | URL | Terms | Used for |
| --- | --- | --- | --- | --- | --- |
| `ndma_listing` | Listing pages (titles and dates of the PDFs) | NDMA | https://www.ndma.gov.pk/sitreps?cat_id=1, https://www.ndma.gov.pk/advisories | NDMA website EULA: limited licence for personal or organisational use. Copies are kept locally and not redistributed. robots.txt allows these paths. | document catalogue |
| `ndma_sitrep` | Monsoon 2025 daily situation reports, No. 1 to 87 | NDMA | https://www.ndma.gov.pk/storage/sitreps/… | as above | Insight Agent citations; E2 local validation |
| `ndma_advisory` | Advisories issued Jun to Oct 2025 | NDMA | https://www.ndma.gov.pk/storage/advisories/… | as above | Insight Agent citations |
| `pmd_document` | Pakistan Monsoon 2025 Rainfall Update | PMD (Climate Data Processing Centre) | https://cdpc.pmd.gov.pk/Monsoon_2025_update/Pakistan_Monsoon_2025_Rainfall_Update.pdf | Government of Pakistan public document; terms not stated. Not redistributed. | Insight Agent citations |

## Found but not fetched yet

- **PBS weekly SPI** (Model B, B1). Each week has a post at
  `https://www.pbs.gov.pk/weekly-sensitive-price-indicator-spi-for-the-week-ended-on-DD-MM-YYYY/`
  that links the city-wise annex as **xlsx** and PDF, e.g.
  `https://www.pbs.gov.pk/wp-content/uploads/2020/07/Annex_30.10.2025.xlsx`. The
  `wp-content/uploads/2020/07/Annex_DD.MM.YYYY.xlsx` pattern works for recent weeks
  (16 and 30 Oct 2025 checked) but returns 404 for 2023 to mid-2025, so older weeks must be
  found from the post pages or the WordPress sitemaps, not by guessing names.
  robots.txt on pbs.gov.pk allows everything.
- **PMD**: `www.pmd.gov.pk` and `cdpc.pmd.gov.pk/robots.txt` returned server errors on
  21 Oct 2026 (01:30 PKT). Only the one known monsoon-update PDF was fetched.
- **PDMA** sites (Punjab, Sindh, KP, Balochistan) were not crawled tonight.
