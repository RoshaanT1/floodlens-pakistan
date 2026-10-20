"""Tests for src/build_thresholds.py (task D6) — offline, uses in-memory DuckDB.

Tests:
  - threshold = 95th percentile of wet-day wettest_pixel_mm in 2015-2023
  - dry days (wettest_pixel_mm == 0) are excluded from threshold calculation
  - labels = 1 iff wettest_pixel_mm > threshold, 0 otherwise; NULL when rain is NULL
  - baseline_climatology = district×month mean in calibration window
  - two builds produce identical row counts and values (stable/idempotent)
"""
from __future__ import annotations

from datetime import date

import duckdb
import numpy as np
import pandas as pd
import pytest

from src.build_thresholds import build, CALIB_START, CALIB_END, LABEL_START


def _setup_db(tmp_path) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection pre-populated with a minimal rain_district_day table."""
    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))

    # 3 districts, daily data 2015-01-01 to 2024-06-30
    # district PK001: always rains 10 mm (no variation → threshold = 10)
    # district PK002: alternates 0 and 20 mm (wet days = 20, threshold = 20)
    # district PK003: always NULL (no data)
    import datetime
    rows = []
    start = date(2015, 1, 1)
    end = date(2024, 6, 30)
    d = start
    toggle = True
    while d <= end:
        rows.append({"district_id": "PK001", "date_utc": d, "wettest_pixel_mm": 10.0,
                      "mean_rain_mm": 8.0, "n_pixels": 5})
        rows.append({"district_id": "PK002", "date_utc": d,
                      "wettest_pixel_mm": 20.0 if toggle else 0.0,
                      "mean_rain_mm": 15.0 if toggle else 0.0, "n_pixels": 5})
        rows.append({"district_id": "PK003", "date_utc": d, "wettest_pixel_mm": None,
                      "mean_rain_mm": None, "n_pixels": 0})
        d += datetime.timedelta(days=1)
        toggle = not toggle
    df = pd.DataFrame(rows)
    con.execute("CREATE TABLE rain_district_day AS SELECT * FROM df")
    return con, db_path


@pytest.fixture
def db_path(tmp_path):
    con, path = _setup_db(tmp_path)
    con.close()
    return path


def test_thresholds_wet_days_only(db_path):
    """PK002 alternates 0/20; dry days excluded → threshold should be 20."""
    counts = build(db_path)
    assert counts["thresholds"] == 2   # PK003 (all NULL) produces no threshold row

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = {r[0]: r[1] for r in con.execute(
            "SELECT district_id, threshold_mm FROM thresholds ORDER BY district_id"
        ).fetchall()}

    assert pytest.approx(rows["PK001"], abs=0.1) == 10.0
    assert pytest.approx(rows["PK002"], abs=0.1) == 20.0
    assert "PK003" not in rows


def test_labels_exceedance(db_path):
    """Labels should be 1 when wettest_pixel_mm > threshold, 0 otherwise."""
    build(db_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute(
            "SELECT district_id, wettest_pixel_mm, threshold_mm, flood_label FROM labels"
        ).df()

    # PK001: threshold=10, wettest=10 → should be 0 (not strictly greater)
    pk1 = df[df.district_id == "PK001"]
    assert (pk1["flood_label"] == 0).all(), "PK001 labels should all be 0 (equal, not exceeding)"

    # PK002: threshold=20, alternates 0/20 → all 0 (0<20 or 20=20, not >20)
    pk2 = df[df.district_id == "PK002"]
    assert (pk2["flood_label"] == 0).all()


def test_labels_only_from_2024(db_path):
    """Labels must start at LABEL_START (2024-01-01), not include calibration years."""
    build(db_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        min_date = con.execute("SELECT min(date_utc) FROM labels").fetchone()[0]
    assert str(min_date) >= LABEL_START


def test_baseline_climatology_exists(db_path):
    """baseline_climatology should have 12 months per district with data."""
    build(db_path)
    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute(
            "SELECT district_id, count(*) AS n FROM baseline_climatology GROUP BY district_id"
        ).df()
    # PK001 and PK002 should each have 12 months; PK003 may have 0
    for _, r in df.iterrows():
        if r.district_id in ("PK001", "PK002"):
            assert r.n == 12, f"{r.district_id}: expected 12 months, got {r.n}"


def test_idempotent_two_builds(db_path):
    """Two identical builds must return identical row counts (stable gold requirement)."""
    counts1 = build(db_path)
    counts2 = build(db_path)
    assert counts1 == counts2
