from datetime import date

import duckdb
import numpy as np
import pandas as pd
import pytest

from src import quality


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(quality, "DECISIONS", tmp_path / "decisions.json")
    monkeypatch.setattr(quality.manifest, "latest", lambda source: None)
    return tmp_path / "t.duckdb"


def bad_forecasts():
    good = dict(district_id="PK101", lead_days=1, precip_sum_mm=3.0, precip_max_hourly_mm=1.0,
                rh_mean_pct=60.0, pressure_mean_hpa=1010.0, cloud_mean_pct=40.0, wind_max_kmh=20.0, n_hours=24)
    rows = [dict(good, date_utc=date(2024, 3, d)) for d in range(1, 8)]
    rows[1]["precip_sum_mm"] = -0.4          # fix: clip to 0
    rows[2]["rh_mean_pct"] = 104.0           # fix: clip to 100
    rows[3]["pressure_mean_hpa"] = None      # flag: missing
    rows[4]["n_hours"] = 20                  # flag: partial day
    rows.append(dict(rows[0]))               # fix: duplicate key dropped
    return pd.DataFrame(rows)


def build(db_path):
    df = bad_forecasts()
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE forecast_day AS SELECT * FROM df")
    log = quality.write_log(quality.run(["forecast_day"], db_path), db_path)
    with duckdb.connect(str(db_path)) as con:
        out = con.execute("SELECT * FROM forecast_day ORDER BY date_utc").df()
    return out, log


def test_rules_fix_fill_and_flag(db):
    out, log = build(db)
    rules = dict(zip(log.rule, zip(log.action, log.n_rows)))
    assert rules["forecast_key_unique"] == ("fix", 1)
    assert rules["forecast_precip_nonnegative"] == ("fix", 1)
    assert rules["forecast_rh_range"] == ("fix", 1)
    assert rules["forecast_pressure_mean_hpa_present"] == ("flag", 1)
    assert rules["forecast_full_day"] == ("flag", 1)

    assert len(out) == 7                                  # only the exact duplicate is dropped
    assert out.precip_sum_mm.min() == 0 and out.rh_mean_pct.max() == 100
    assert out.loc[3, "quality_flags"] == "forecast_pressure_mean_hpa_present;"
    assert out.loc[4, "quality_flags"] == "forecast_full_day;"
    assert np.isnan(out.loc[3, "pressure_mean_hpa"])     # flagged, never filled with a guess
    assert str(out.date_utc.dtype).startswith("datetime64") and log.decided_at_utc.notna().all()


def test_two_rebuilds_are_identical(db):
    out1, log1 = build(db)
    out2, log2 = build(db)  # decisions replayed from the cache, including timestamps
    pd.testing.assert_frame_equal(out1, out2)
    pd.testing.assert_frame_equal(log1, log2)
    assert quality.DECISIONS.exists()


def test_date_type_preserved(db):
    build(db)
    with duckdb.connect(str(db)) as con:
        types = dict(con.execute("SELECT column_name, data_type FROM information_schema.columns "
                                 "WHERE table_name = 'forecast_day'").fetchall())
    assert types["date_utc"] == "DATE" and types["quality_flags"] == "VARCHAR"
