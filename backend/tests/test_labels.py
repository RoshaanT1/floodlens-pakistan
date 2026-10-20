from datetime import date, timedelta

import duckdb
import pandas as pd

from src import labels


def make_rain(rows):
    return pd.DataFrame(rows, columns=["district_id", "date_utc", "wettest_mm", "low_confidence"]).assign(
        row_id=lambda d: d.district_id + "_" + d.date_utc.astype(str))


def test_thresholds_labels_and_baseline():
    rows = []
    # 2015-2023, district A: wet days 1..100 mm on 100 July days, plus dry days with 0.5 mm
    d0 = date(2015, 7, 1)
    for i in range(100):
        rows.append(["A", d0 + timedelta(days=i % 31) + timedelta(days=365 * (i // 31)), float(i + 1), False])
    for i in range(50):
        rows.append(["A", date(2016, 1, 1) + timedelta(days=i), 0.5, False])
    # label period
    rows += [["A", date(2024, 7, 1), 99.0, False],
             ["A", date(2024, 7, 2), 10.0, False],
             ["A", date(2024, 7, 3), None, True],
             ["A", date(2023, 12, 31), 200.0, False]]  # before label start: no label
    con = duckdb.connect()
    rain_district_day = make_rain(rows)
    con.execute("CREATE TABLE rain_district_day AS SELECT * FROM rain_district_day")
    labels.build(con)

    thr, n_wet = con.execute("SELECT threshold_mm, n_wet_days FROM thresholds").fetchone()
    # wet days are 1..100 plus the 200 mm day in 2023; 0.5 mm days are excluded
    expected = pd.Series([*range(1, 101), 200.0]).quantile(0.95)
    assert n_wet == 101 and abs(thr - expected) < 1e-9

    got = dict(con.execute("SELECT date_utc, label FROM labels ORDER BY date_utc").fetchall())
    assert got == {date(2024, 7, 1): 1, date(2024, 7, 2): 0, date(2024, 7, 3): None}

    # January: only 0.5 mm days -> never exceeds
    jan = con.execute("SELECT p_exceed FROM baseline_climatology WHERE month = 1").fetchone()[0]
    assert jan == 0.0
    jul, n = con.execute("SELECT p_exceed, n_days FROM baseline_climatology WHERE month = 7").fetchone()
    assert 0 < jul < 0.1 and n > 0
