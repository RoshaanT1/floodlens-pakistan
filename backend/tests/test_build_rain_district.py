"""Tests for src/build_rain_district.py (task D5) — no network, no real HDF5 required.

Key tests:
  - aggregate_one_file produces correct wettest/mean from a synthetic numpy grid
  - IMERG fill value -9999.9 is masked before aggregation
  - Stable row IDs: two identical builds produce bit-identical sorted output
  - Districts with no pixels inside produce NaN, n_pixels=0 (not a crash)
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon, box


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake HDF5 in tmp_path
# ---------------------------------------------------------------------------

def _make_fake_hdf5(path: Path, lat_vals, lon_vals, precip_2d):
    """Write a minimal HDF5 that mimics the IMERG Late V07 structure."""
    import h5py
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        g = f.create_group("Grid")
        g.create_dataset("lat", data=np.array(lat_vals, dtype=np.float32))
        g.create_dataset("lon", data=np.array(lon_vals, dtype=np.float32))
        # precipitationCal shape: (time=1, nlon, nlat)
        data = np.array(precip_2d, dtype=np.float32).T[np.newaxis, :, :]
        g.create_dataset("precipitationCal", data=data)


def _minimal_gdf(geom):
    """Return a one-row GeoDataFrame for testing."""
    import geopandas as gpd
    return gpd.GeoDataFrame(
        [{"district_id": "PK001", "geometry": geom}],
        crs="EPSG:4326",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_aggregate_one_file_basic(tmp_path):
    """A 3×3 grid with known values → correct max and mean."""
    from src.build_rain_district import aggregate_one_file

    lat = np.array([24.05, 24.15, 24.25])
    lon = np.array([67.05, 67.15, 67.25])
    precip_2d = np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ], dtype=float)   # shape (lat, lon)

    hdf_path = tmp_path / "test.HDF5"
    _make_fake_hdf5(hdf_path, lat, lon, precip_2d)

    geom = box(67.0, 24.0, 67.3, 24.3)   # covers all 9 pixels
    gdf = _minimal_gdf(geom)

    day = date(2020, 8, 1)
    result = aggregate_one_file(hdf_path, gdf, day)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["district_id"] == "PK001"
    assert row["date_utc"] == day
    assert row["n_pixels"] == 9
    assert pytest.approx(row["wettest_pixel_mm"], abs=1e-4) == 9.0
    assert pytest.approx(row["mean_rain_mm"], abs=1e-4) == 5.0


def test_fill_value_is_masked(tmp_path):
    """IMERG fill value -9999.9 must be treated as NaN, never as rain."""
    from src.build_rain_district import aggregate_one_file

    lat = np.array([24.05, 24.15])
    lon = np.array([67.05, 67.15])
    precip_2d = np.array([
        [-9999.9, 5.0],
        [3.0, -9999.9],
    ], dtype=float)

    hdf_path = tmp_path / "fill_test.HDF5"
    _make_fake_hdf5(hdf_path, lat, lon, precip_2d)

    geom = box(67.0, 24.0, 67.2, 24.2)
    gdf = _minimal_gdf(geom)

    result = aggregate_one_file(hdf_path, gdf, date(2020, 1, 1))
    row = result.iloc[0]

    assert row["n_pixels"] == 2   # only the non-fill pixels
    assert pytest.approx(row["wettest_pixel_mm"], abs=1e-4) == 5.0
    assert pytest.approx(row["mean_rain_mm"], abs=1e-4) == 4.0   # (5+3)/2


def test_district_with_no_pixels_returns_nan(tmp_path):
    """A polygon that covers no pixel centres → NaN values, n_pixels=0, no crash."""
    from src.build_rain_district import aggregate_one_file

    lat = np.array([24.05])
    lon = np.array([67.05])
    precip_2d = np.array([[1.0]])

    hdf_path = tmp_path / "nopix.HDF5"
    _make_fake_hdf5(hdf_path, lat, lon, precip_2d)

    # polygon far from the grid pixel
    geom = box(70.0, 30.0, 71.0, 31.0)
    gdf = _minimal_gdf(geom)

    result = aggregate_one_file(hdf_path, gdf, date(2020, 1, 1))
    row = result.iloc[0]

    assert row["n_pixels"] == 0
    assert np.isnan(row["wettest_pixel_mm"])
    assert np.isnan(row["mean_rain_mm"])


def test_stable_row_ids_across_two_builds(tmp_path):
    """Two identical calls to build() must produce bit-identical sorted output (D8 req)."""
    from src.build_rain_district import aggregate_one_file

    lat = np.array([24.05, 24.15])
    lon = np.array([67.05, 67.15])
    precip_2d = np.array([[2.0, 3.0], [4.0, 5.0]])
    hdf_path = tmp_path / "stable.HDF5"
    _make_fake_hdf5(hdf_path, lat, lon, precip_2d)

    import geopandas as gpd
    gdf = gpd.GeoDataFrame(
        [
            {"district_id": "PK001", "geometry": box(67.0, 24.0, 67.1, 24.1)},
            {"district_id": "PK002", "geometry": box(67.1, 24.1, 67.2, 24.2)},
        ],
        crs="EPSG:4326",
    )
    day = date(2021, 6, 1)

    df1 = aggregate_one_file(hdf_path, gdf, day).sort_values(
        ["date_utc", "district_id"]
    ).reset_index(drop=True)

    df2 = aggregate_one_file(hdf_path, gdf, day).sort_values(
        ["date_utc", "district_id"]
    ).reset_index(drop=True)

    pd.testing.assert_frame_equal(df1, df2)


def test_day_from_filename_valid():
    from src.build_rain_district import _day_from_filename
    assert _day_from_filename("2015-01-01_granule.HDF5") == date(2015, 1, 1)
    assert _day_from_filename("2023-12-31_foo.HDF5") == date(2023, 12, 31)
