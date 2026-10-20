"""Thresholds, labels and baseline (task D6), exactly as declared in DATASET_DECLARATION.md.

    python -m src.labels build   # rain_district_day -> thresholds, labels, baseline_climatology

- threshold: 95th percentile of the district's daily wettest-pixel rain on wet days
  (>= 1 mm), IMERG Late 2015-2023.
- label: 1 if that day's wettest-pixel rain exceeds the threshold, for 2024 onward.
  Days with no valid pixel get a NULL label, never 0.
- baseline: district-by-month share of 2015-2023 days crossing the threshold.
"""
import sys

import duckdb

from src.config import DB_PATH, THRESHOLD_YEARS

WET_DAY_MM = 1.0
LABEL_START = "2024-01-01"


def build(con: duckdb.DuckDBPyConnection) -> None:
    y0, y1 = THRESHOLD_YEARS
    con.execute("""
        CREATE OR REPLACE TABLE thresholds AS
        SELECT district_id,
               quantile_cont(wettest_mm, 0.95)  AS threshold_mm,
               count(*)                         AS n_wet_days
        FROM rain_district_day
        WHERE year(date_utc) BETWEEN $y0 AND $y1 AND wettest_mm >= $wet
        GROUP BY district_id
        ORDER BY district_id
    """, {"y0": y0, "y1": y1, "wet": WET_DAY_MM})

    con.execute("""
        CREATE OR REPLACE TABLE labels AS
        SELECT r.row_id, r.district_id, r.date_utc, r.wettest_mm, t.threshold_mm,
               CASE WHEN r.wettest_mm IS NULL THEN NULL
                    ELSE (r.wettest_mm > t.threshold_mm)::INTEGER END AS label,
               r.low_confidence
        FROM rain_district_day r JOIN thresholds t USING (district_id)
        WHERE r.date_utc >= $label_start::DATE
        ORDER BY r.row_id
    """, {"label_start": LABEL_START})

    con.execute("""
        CREATE OR REPLACE TABLE baseline_climatology AS
        SELECT r.district_id,
               month(r.date_utc)                                   AS month,
               avg((r.wettest_mm > t.threshold_mm)::INTEGER)       AS p_exceed,
               count(*)                                            AS n_days
        FROM rain_district_day r JOIN thresholds t USING (district_id)
        WHERE year(r.date_utc) BETWEEN $y0 AND $y1 AND r.wettest_mm IS NOT NULL
        GROUP BY ALL
        ORDER BY r.district_id, month
    """, {"y0": y0, "y1": y1})

    for t in ["thresholds", "labels", "baseline_climatology"]:
        print(f"{t}: {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]} rows")


def main(db_path=DB_PATH) -> None:
    with duckdb.connect(str(db_path)) as con:
        build(con)


if __name__ == "__main__":
    {"build": main}[sys.argv[1]]()
