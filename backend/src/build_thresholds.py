"""Thresholds, labels and baseline climatology (task D6).

Needs: D5 (`rain_district_day` table in DuckDB).

Done when: `thresholds`, `labels` and `baseline_climatology` tables exist in DuckDB.

Definitions (from TASKS.md "Fixed decisions"):
  - threshold  : 95th percentile of wettest-pixel rain on WET days (rain > 0 mm)
                 in the calibration period 2015–2023, per district.
  - label      : 1 if wettest_pixel_mm > district threshold for that day, else 0.
                 Labels computed for 2024-01-01 onwards (out-of-sample).
  - baseline_climatology : mean wettest_pixel_mm grouped by (district_id, month),
                 computed over 2015–2023. Used as the climatology baseline in A2.

All tables are written deterministically (ORDER BY) so two builds give identical gold.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from src.config import DB_PATH, THRESHOLD_YEARS

LABEL_START = "2024-01-01"
CALIB_START = f"{THRESHOLD_YEARS[0]}-01-01"
CALIB_END = f"{THRESHOLD_YEARS[1]}-12-31"


def build(db_path: Path = DB_PATH) -> dict[str, int]:
    """Compute and store thresholds, labels and baseline_climatology.

    Returns a dict with row counts for each table.
    """
    with duckdb.connect(str(db_path)) as con:
        # ------------------------------------------------------------------
        # 1. Thresholds: 95th percentile of wettest-pixel on wet days per district
        # ------------------------------------------------------------------
        con.execute(f"""
            CREATE OR REPLACE TABLE thresholds AS
            SELECT
                district_id,
                quantile_cont(wettest_pixel_mm, 0.95) AS threshold_mm,
                count(*)                               AS n_wet_days,
                '{CALIB_START}'::DATE                  AS calib_start,
                '{CALIB_END}'::DATE                    AS calib_end
            FROM rain_district_day
            WHERE date_utc BETWEEN '{CALIB_START}' AND '{CALIB_END}'
              AND wettest_pixel_mm > 0          -- wet-day filter
              AND wettest_pixel_mm IS NOT NULL
            GROUP BY district_id
            ORDER BY district_id
        """)
        n_thresh = con.execute("SELECT count(*) FROM thresholds").fetchone()[0]

        # ------------------------------------------------------------------
        # 2. Labels: binary exceedance for 2024+
        # ------------------------------------------------------------------
        con.execute(f"""
            CREATE OR REPLACE TABLE labels AS
            SELECT
                r.district_id,
                r.date_utc,
                r.wettest_pixel_mm,
                t.threshold_mm,
                CASE
                    WHEN r.wettest_pixel_mm IS NULL THEN NULL
                    WHEN r.wettest_pixel_mm > t.threshold_mm THEN 1
                    ELSE 0
                END AS flood_label
            FROM rain_district_day r
            JOIN thresholds t USING (district_id)
            WHERE r.date_utc >= '{LABEL_START}'
            ORDER BY r.date_utc, r.district_id
        """)
        n_labels = con.execute("SELECT count(*) FROM labels").fetchone()[0]

        # ------------------------------------------------------------------
        # 3. Baseline climatology: district × month mean (calibration window)
        # ------------------------------------------------------------------
        con.execute(f"""
            CREATE OR REPLACE TABLE baseline_climatology AS
            SELECT
                district_id,
                month(date_utc)                        AS month,
                avg(wettest_pixel_mm)                  AS mean_wettest_pixel_mm,
                avg(mean_rain_mm)                      AS mean_district_rain_mm,
                count(*)                               AS n_days,
                '{CALIB_START}'::DATE                  AS calib_start,
                '{CALIB_END}'::DATE                    AS calib_end
            FROM rain_district_day
            WHERE date_utc BETWEEN '{CALIB_START}' AND '{CALIB_END}'
              AND wettest_pixel_mm IS NOT NULL
            GROUP BY district_id, month(date_utc)
            ORDER BY district_id, month
        """)
        n_clim = con.execute("SELECT count(*) FROM baseline_climatology").fetchone()[0]

    print(f"thresholds:           {n_thresh} districts")
    print(f"labels:               {n_labels} district-days (2024+)")
    print(f"baseline_climatology: {n_clim} district-month rows")

    return {"thresholds": n_thresh, "labels": n_labels, "baseline_climatology": n_clim}


if __name__ == "__main__":
    counts = build()
    for table, n in counts.items():
        print(f"  {table}: {n} rows")
    sys.exit(0)
