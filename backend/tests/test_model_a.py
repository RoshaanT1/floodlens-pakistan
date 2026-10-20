"""Model A tests. The fixture tables are made-up test inputs, never real data."""
from datetime import date, datetime, timedelta, timezone

import duckdb
import numpy as np
import pandas as pd
import pytest

from src import model_a

DISTRICTS = ["PK1", "PK2"]


def _fixture_db(path, seed=0):
    rng = np.random.default_rng(seed)
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D").date
    rain = pd.DataFrame([{"row_id": f"{d}_{day}", "district_id": d, "date_utc": day,
                          "wettest_mm": float(rng.gamma(0.5, 8)), "mean_mm": float(rng.gamma(0.5, 3))}
                         for d in DISTRICTS for day in days])
    fc = pd.DataFrame([{"district_id": r.district_id, "date_utc": r.date_utc, "lead_days": lead,
                        "precip_sum_mm": r.wettest_mm * 0.6 + float(rng.gamma(0.5, 2)),
                        "precip_max_hourly_mm": 1.0, "rh_mean_pct": 60.0, "pressure_mean_hpa": 1005.0,
                        "cloud_mean_pct": 50.0, "wind_max_kmh": 10.0}
                       for r in rain.itertuples() for lead in (1, 2, 3)])
    thresholds = pd.DataFrame({"district_id": DISTRICTS, "threshold_mm": [20.0, 25.0]})
    clim = pd.DataFrame([{"district_id": d, "month": m, "p_exceed": 0.05} for d in DISTRICTS for m in range(1, 13)])
    labels = rain.merge(thresholds, on="district_id")
    labels["label"] = (labels.wettest_mm > labels.threshold_mm).astype(int)
    labels["low_confidence"] = False
    with duckdb.connect(str(path)) as con:
        for name, df in [("rain_district_day", rain), ("forecast_day", fc), ("thresholds", thresholds),
                         ("baseline_climatology", clim), ("labels", labels)]:
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
    return path


@pytest.mark.parametrize("lead", [1, 2, 3])
def test_observed_days_end_14h_before_issue(lead):
    for target in pd.date_range("2024-01-01", "2025-12-31", freq="7D").date:
        obs = model_a.last_observed_day(target, lead)
        end = datetime(obs.year, obs.month, obs.day, tzinfo=timezone.utc) + timedelta(days=1)
        assert end + timedelta(hours=14) <= model_a.issue_time(target, lead)
        nxt_end = end + timedelta(days=1)  # the next day is too recent
        assert nxt_end + timedelta(hours=14) > model_a.issue_time(target, lead)


def test_issue_time_is_earliest_run_for_the_day():
    # lead-1 values for 10 Aug come from runs 24 h before each hour: earliest 9 Aug 00:00 UTC
    assert model_a.issue_time(date(2025, 8, 10), 1) == datetime(2025, 8, 9, tzinfo=timezone.utc)


def test_features_never_see_rain_after_cutoff(tmp_path):
    db = _fixture_db(tmp_path / "a.duckdb")
    with duckdb.connect(str(db)) as con:
        before = model_a.build_features(con).set_index("row_id")
        target, lead = date(2025, 8, 15), 2
        row_id = f"PK1_{target}_L{lead}"
        cutoff = model_a.last_observed_day(target, lead)
        assert before.loc[row_id, "obs_last_day"].date() == cutoff
        # make every later day absurd; the row's observed features must not move
        con.execute("UPDATE rain_district_day SET wettest_mm = 9999, mean_mm = 9999 WHERE date_utc > ?", [cutoff])
        after = model_a.build_features(con).set_index("row_id")
    obs_cols = ["obs_wettest_mm", "obs_mean_3d_mm", "obs_mean_7d_mm"]
    pd.testing.assert_series_equal(before.loc[row_id, obs_cols], after.loc[row_id, obs_cols])


def test_features_use_only_previous_day_leads(tmp_path):
    db = _fixture_db(tmp_path / "a.duckdb")
    with duckdb.connect(str(db)) as con:
        con.execute("INSERT INTO forecast_day SELECT district_id, date_utc, 0, precip_sum_mm, 1, 60, 1005, 50, 10 "
                    "FROM forecast_day WHERE lead_days = 1")  # a lead-0 row must never be used
        df = model_a.build_features(con)
    assert set(df.lead_days) == {1, 2, 3}
    assert (pd.to_datetime(df.date_utc) - pd.to_datetime(df.obs_last_day)).dt.days.eq(df.lead_days + 2).all()


def test_test_split_is_refused(monkeypatch):
    df = pd.DataFrame({"date_utc": [date(2026, 2, 1)], "label": [1]})
    monkeypatch.delenv("FLOODLENS_RUN_TEST", raising=False)
    with pytest.raises(PermissionError):
        model_a.split(df, "test")


def test_splits_are_disjoint_and_fixed():
    df = pd.DataFrame({"date_utc": pd.date_range("2024-01-01", "2026-09-30").date, "label": 0})
    tr, val = model_a.split(df, "train"), model_a.split(df, "validation")
    assert max(tr.date_utc) == date(2025, 6, 30)
    assert (min(val.date_utc), max(val.date_utc)) == (date(2025, 7, 1), date(2025, 12, 31))


def test_brier_interval_brackets_point():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 500)
    p = np.clip(y * 0.6 + rng.random(500) * 0.3, 0, 1)
    s = model_a.brier_ci(y, p, np.repeat(np.arange(100), 5), n_boot=200)
    assert s["lo"] <= s["brier"] <= s["hi"]


def test_train_writes_loadable_artifact_and_log(tmp_path, monkeypatch):
    db = _fixture_db(tmp_path / "a.duckdb")
    monkeypatch.setattr(model_a, "MODEL_DIR", tmp_path / "models")
    monkeypatch.setattr(model_a, "OPT_LOG", tmp_path / "opt.md")
    monkeypatch.setattr(model_a, "ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(model_a, "N_BOOT", 50)
    model_a.features(db)
    report = model_a.train(db)
    assert set(report["baselines"]) == {"climatology", "raw_forecast_cut"}
    assert (tmp_path / "opt.md").read_text().count("\n") >= 4
    if report["chosen"]:
        model, meta = model_a.load_current()
        assert meta["label"].startswith("validation-stage")
