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
