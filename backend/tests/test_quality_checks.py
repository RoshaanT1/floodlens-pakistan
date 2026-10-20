"""Tests for src/quality_checks.py (task Q1) — offline, uses in-memory DuckDB.

Tests:
  - Valid districts table passes the pandera schema
  - Duplicate district_id is caught
  - Centroid out of Pakistan bounds is caught
  - Duplicate (district_id, date_utc, lead_days) in forecast_day is caught
  - IMERG fill value in rain_district_day is caught
  - Valid rain table passes
  - Missing tables are skipped gracefully (not a hard failure)
"""
from __future__ import annotations

import pandas as pd
import duckdb
import pytest
from datetime import date, timedelta

from src.quality_checks import run_checks


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _valid_districts(n=160):
    import numpy as np
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "district_id": [f"PK{i:03d}" for i in range(n)],
        "name": [f"District {i}" for i in range(n)],
        "province": ["Punjab"] * n,
        "province_id": ["PK03"] * n,
        "area_sqkm": [100.0] * n,
        "centroid_lat": rng.uniform(24.0, 37.0, n).tolist(),
        "centroid_lon": rng.uniform(61.0, 77.0, n).tolist(),
        "geometry_wkt": ["POINT(70 30)"] * n,
    })


def _valid_forecast():
    import numpy as np
    rng = np.random.default_rng(7)
    districts = [f"PK{i:03d}" for i in range(10)]
    dates = [date(2024, 2, 1) + timedelta(days=d) for d in range(10)]
    rows = []
    for d in districts:
        for dt in dates:
            for lead in [1, 2, 3]:
                rows.append({
                    "district_id": d, "date_utc": pd.Timestamp(dt),
                    "lead_days": lead,
                    "precip_sum_mm": float(rng.uniform(0, 50)),
                    "precip_max_hourly_mm": float(rng.uniform(0, 20)),
                    "rh_mean_pct": float(rng.uniform(30, 90)),
                    "pressure_mean_hpa": float(rng.uniform(950, 1020)),
                    "cloud_mean_pct": float(rng.uniform(0, 100)),
                    "wind_max_kmh": float(rng.uniform(0, 80)),
                    "n_hours": 24,
                })
    return pd.DataFrame(rows)


def _valid_rain():
    import numpy as np
    rng = np.random.default_rng(3)
    districts = [f"PK{i:03d}" for i in range(10)]
    dates = [date(2015, 1, 1) + timedelta(days=d) for d in range(30)]
    rows = []
    for d in districts:
        for dt in dates:
            rows.append({
                "district_id": d, "date_utc": pd.Timestamp(dt),
                "wettest_pixel_mm": float(rng.uniform(0, 50)),
                "mean_rain_mm": float(rng.uniform(0, 30)),
                "n_pixels": int(rng.integers(1, 20)),
            })
    return pd.DataFrame(rows)


def _write_db(db_path, df_d=None, df_f=None, df_r=None):
    """Write provided DataFrames to DuckDB tables."""
    with duckdb.connect(str(db_path)) as con:
        if df_d is not None:
            con.execute("CREATE OR REPLACE TABLE districts AS SELECT * FROM df_d")
        if df_f is not None:
            con.execute("CREATE OR REPLACE TABLE forecast_day AS SELECT * FROM df_f")
        if df_r is not None:
            con.execute("CREATE OR REPLACE TABLE rain_district_day AS SELECT * FROM df_r")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_valid_tables_pass(tmp_path):
    db_path = tmp_path / "qc_test.duckdb"
    df_d = _valid_districts()
    df_f = _valid_forecast()
    df_r = _valid_rain()
    _write_db(db_path, df_d, df_f, df_r)
    failures = run_checks(db_path)
    assert failures == [], f"Unexpected failures: {failures}"


def test_duplicate_district_id_caught(tmp_path):
    db_path = tmp_path / "qc_test.duckdb"
    df = _valid_districts()
    df.loc[1, "district_id"] = df.loc[0, "district_id"]   # introduce duplicate
    _write_db(db_path, df_d=df)
    failures = run_checks(db_path)
    assert any("districts" in f for f in failures), failures


def test_centroid_out_of_bounds_caught(tmp_path):
    db_path = tmp_path / "qc_test.duckdb"
    df = _valid_districts()
    df.loc[0, "centroid_lat"] = 50.0   # latitude > 38, outside Pakistan
    _write_db(db_path, df_d=df)
    failures = run_checks(db_path)
    assert any("districts" in f for f in failures), failures


def test_duplicate_forecast_row_caught(tmp_path):
    db_path = tmp_path / "qc_test.duckdb"
    df = _valid_forecast()
    dup = df.iloc[[0]].copy()
    df = pd.concat([df, dup], ignore_index=True)
    _write_db(db_path, df_f=df)
    failures = run_checks(db_path)
    # districts is also missing → that's a failure too; just confirm forecast checked
    assert any("forecast_day" in f for f in failures), failures


def test_fill_value_in_rain_caught(tmp_path):
    db_path = tmp_path / "qc_test.duckdb"
    df = _valid_rain()
    df.loc[0, "wettest_pixel_mm"] = -9999.9   # inject fill value
    _write_db(db_path, df_r=df)
    failures = run_checks(db_path)
    assert any("rain_district_day" in f for f in failures), failures


def test_missing_tables_skipped_gracefully(tmp_path):
    """An empty DB with no tables should not raise, just report missing districts."""
    db_path = tmp_path / "qc_test.duckdb"
    duckdb.connect(str(db_path)).close()   # create empty DB
    failures = run_checks(db_path)
    # districts is required → failure expected, but no exception
    assert any("districts" in f for f in failures)
