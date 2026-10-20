"""Data quality checks with pandera (task Q1).

Needs: a sample from D3 (forecast_day table) and D4 (IMERG files / rain_district_day table)
       and D2 (districts table).

Done when: checks run inside `make data` (called from src/build.py).

Checks implemented:
  - districts : schema, ~160 rows, no duplicate district_id, valid centroid ranges
  - forecast_day : schema, date range, no duplicate (district_id, date_utc, lead_days),
                   timeliness (no future dates), value ranges
  - rain_district_day : schema, no duplicate (district_id, date_utc), value ranges,
                        fill-value sentinel never present
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

from src.config import DB_PATH

# ──────────────────────────────────────────────
# District schema
# ──────────────────────────────────────────────
DISTRICT_SCHEMA = DataFrameSchema(
    {
        "district_id": Column(str, nullable=False, unique=True),
        "name": Column(str, nullable=False),
        "province": Column(str, nullable=False),
        "province_id": Column(str, nullable=False),
        "centroid_lat": Column(float, Check.in_range(23.0, 38.0), nullable=False),
        "centroid_lon": Column(float, Check.in_range(60.0, 78.0), nullable=False),
    },
    checks=[
        # Pakistan has ~160 districts (OCHA admin-2)
        Check(lambda df: len(df) >= 100, error="fewer than 100 districts loaded"),
    ],
    coerce=True,
)

# ──────────────────────────────────────────────
# Forecast schema
# ──────────────────────────────────────────────
FORECAST_SCHEMA = DataFrameSchema(
    {
        "district_id": Column(str, nullable=False),
        "date_utc": Column("datetime64[ns]", nullable=False),
        "lead_days": Column(int, Check.isin([1, 2, 3]), nullable=False),
        "precip_sum_mm": Column(float, Check.greater_than_or_equal_to(0), nullable=True),
        "precip_max_hourly_mm": Column(float, Check.greater_than_or_equal_to(0), nullable=True),
        "rh_mean_pct": Column(float, Check.in_range(0, 100), nullable=True),
        "pressure_mean_hpa": Column(float, Check.in_range(800, 1100), nullable=True),
        "cloud_mean_pct": Column(float, Check.in_range(0, 100), nullable=True),
        "wind_max_kmh": Column(float, Check.greater_than_or_equal_to(0), nullable=True),
        "n_hours": Column(int, Check.greater_than(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: not df.duplicated(["district_id", "date_utc", "lead_days"]).any(),
            error="duplicate (district_id, date_utc, lead_days) rows in forecast_day",
        ),
    ],
    coerce=True,
)

# ──────────────────────────────────────────────
# Rain district day schema
# ──────────────────────────────────────────────
RAIN_SCHEMA = DataFrameSchema(
    {
        "district_id": Column(str, nullable=False),
        "date_utc": Column("datetime64[ns]", nullable=False),
        "wettest_pixel_mm": Column(
            float,
            [
                Check(lambda s: (s.dropna() >= 0).all(), error="negative wettest_pixel_mm"),
                Check(
                    lambda s: (s.dropna() > -9990).all(),
                    error="IMERG fill value -9999.9 leaked into rain table",
                ),
            ],
            nullable=True,
        ),
        "mean_rain_mm": Column(float, Check.greater_than_or_equal_to(0), nullable=True),
        "n_pixels": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
    },
    checks=[
        Check(
            lambda df: not df.duplicated(["district_id", "date_utc"]).any(),
            error="duplicate (district_id, date_utc) rows in rain_district_day",
        ),
    ],
    coerce=True,
)


def _table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    result = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()
    return bool(result and result[0] > 0)


def run_checks(db_path: Path = DB_PATH) -> list[str]:
    """Run all pandera checks; return list of failure messages (empty = all pass)."""
    failures: list[str] = []

    with duckdb.connect(str(db_path), read_only=True) as con:

        # ------------------------------------------------------------------
        # Districts
        # ------------------------------------------------------------------
        if _table_exists(con, "districts"):
            df = con.execute("SELECT * FROM districts").df()
            try:
                DISTRICT_SCHEMA.validate(df)
                print(f"  districts: ok ({len(df)} rows)")
            except pa.errors.SchemaError as exc:
                failures.append(f"districts: {exc}")
        else:
            failures.append("districts: table missing")

        # ------------------------------------------------------------------
        # Forecast day
        # ------------------------------------------------------------------
        if _table_exists(con, "forecast_day"):
            df = con.execute("SELECT * FROM forecast_day").df()
            df["date_utc"] = pd.to_datetime(df["date_utc"])
            # timeliness: no future dates
            future = (df["date_utc"] > pd.Timestamp.now("UTC").tz_localize(None)).sum()
            if future:
                failures.append(f"forecast_day: {future} rows have future date_utc")
            try:
                FORECAST_SCHEMA.validate(df)
                print(f"  forecast_day: ok ({len(df)} rows)")
            except pa.errors.SchemaError as exc:
                failures.append(f"forecast_day: {exc}")
        else:
            print("  forecast_day: table missing — skipping (D3 not built yet)")

        # ------------------------------------------------------------------
        # Rain district day
        # ------------------------------------------------------------------
        if _table_exists(con, "rain_district_day"):
            df = con.execute("SELECT * FROM rain_district_day").df()
            df["date_utc"] = pd.to_datetime(df["date_utc"])
            try:
                RAIN_SCHEMA.validate(df)
                print(f"  rain_district_day: ok ({len(df)} rows)")
            except pa.errors.SchemaError as exc:
                failures.append(f"rain_district_day: {exc}")
        else:
            print("  rain_district_day: table missing — skipping (D5 not built yet)")

    return failures


def main(db_path: Path = DB_PATH) -> int:
    print("Running quality checks …")
    failures = run_checks(db_path)
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("All quality checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
