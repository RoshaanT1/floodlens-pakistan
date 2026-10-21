from datetime import date

import numpy as np
import pandas as pd

from src import rain

# 0.1 deg grid: lon 70.05..70.95, lat 30.05..30.95 (10 x 10)
LON = np.round(np.arange(70.05, 71.0, 0.1), 2)
LAT = np.round(np.arange(30.05, 31.0, 0.1), 2)

DISTRICTS = pd.DataFrame([
    # west half of the grid: 5 x 10 = 50 pixel centres
    {"district_id": "W", "centroid_lat": 30.5, "centroid_lon": 70.25,
     "geometry_wkt": "POLYGON((70 30, 70.5 30, 70.5 31, 70 31, 70 30))"},
    # east half
    {"district_id": "E", "centroid_lat": 30.5, "centroid_lon": 70.75,
     "geometry_wkt": "POLYGON((70.5 30, 71 30, 71 31, 70.5 31, 70.5 30))"},
    # tiny district between pixel centres: falls back to nearest pixel
    {"district_id": "T", "centroid_lat": 30.06, "centroid_lon": 70.06,
     "geometry_wkt": "POLYGON((70.06 30.06, 70.08 30.06, 70.08 30.08, 70.06 30.08, 70.06 30.06))"},
])


def test_every_district_gets_pixels():
    idx = rain.district_pixel_index(DISTRICTS, LON, LAT)
    assert idx["W"].size == 50 and idx["E"].size == 50
    assert idx["T"].tolist() == [0]  # nearest pixel centre (70.05, 30.05)


def test_aggregate_day_wettest_mean_and_fill():
    idx = rain.district_pixel_index(DISTRICTS, LON, LAT)
    p = np.zeros((10, 10))
    p[1, 3] = 40.0        # west district, wettest pixel
    p[2, 2] = np.nan      # west district, fill pixel
    p[7, :] = 5.0         # east district, one wet column
    cnt = np.full((10, 10), 48)
    cnt[8, 8] = 10

    rows = {r["district_id"]: r for r in rain.aggregate_day(idx, p, cnt, date(2024, 8, 1))}
    w, e = rows["W"], rows["E"]
    assert w["row_id"] == "W_2024-08-01"
    assert w["wettest_mm"] == 40.0 and w["n_fill_pixels"] == 1
    assert w["mean_mm"] == 40.0 / 49   # fill excluded, not read as zero
    assert e["wettest_mm"] == 5.0 and e["mean_mm"] == 1.0  # 10 of 50 pixels at 5 mm
    assert e["min_sample_cnt"] == 10 and w["min_sample_cnt"] == 48


def test_all_fill_district_gives_null_not_zero():
    idx = rain.district_pixel_index(DISTRICTS, LON, LAT)
    p = np.full((10, 10), np.nan)
    rows = rain.aggregate_day(idx, p, None, date(2024, 8, 1))
    assert all(r["wettest_mm"] is None and r["mean_mm"] is None for r in rows)


def test_reissued_day_uses_newest_and_keeps_earlier_value(tmp_path, monkeypatch):
    """Q3: two versions of one day (made-up grids): the newest wins and the row is flagged."""
    import duckdb
    import xarray as xr

    def grid(peak):
        p = np.zeros((1, 10, 10))
        p[0, 1, 3] = peak
        return xr.Dataset({"precipitation": (("time", "lon", "lat"), p),
                           "precipitation_cnt": (("time", "lon", "lat"), np.full((1, 10, 10), 48))},
                          coords={"lon": LON, "lat": LAT})

    day = date(2025, 8, 15)
    versions = [{"path": "old.nc4", "fetched_at_utc": "2025-08-16T14:00:00Z"},
                {"path": "new.nc4", "fetched_at_utc": "2025-09-20T00:00:00Z"}]
    monkeypatch.setattr(rain, "imerg_versions", lambda: {day: versions})
    monkeypatch.setattr(rain.imerg, "open_day", lambda p: grid(40.0 if p.name == "old.nc4" else 55.0))
    db = tmp_path / "r.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE districts AS SELECT * FROM DISTRICTS")
    rain.build(db)
    with duckdb.connect(str(db)) as con:
        w = con.execute("SELECT wettest_mm, revised_from_mm, revised FROM rain_district_day "
                        "WHERE district_id = 'W'").fetchone()
        e = con.execute("SELECT revised FROM rain_district_day WHERE district_id = 'E'").fetchone()
    assert w == (55.0, 40.0, True)
    assert e == (False,)  # unchanged district is not flagged
