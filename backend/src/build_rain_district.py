"""District rain table (task D5): wettest-pixel and mean rain per district per UTC day.

Needs: D2 (districts in DuckDB), D4 (IMERG Late HDF5 files in data/raw/imerg_late_daily/).

Done when: `rain_district_day` gold table exists with stable row IDs
(district_id, date_utc) — two identical builds give bit-identical output.

Each IMERG Late daily HDF5 holds a (lat, lon) precipitation grid at 0.1° resolution.
For every district polygon we:
  1. Find all grid pixels whose centre falls within the polygon boundary box and then
     filter by the actual polygon using vectorised point-in-polygon.
  2. Record wettest_pixel_mm (max of those pixels) and mean_rain_mm (mean, NaN-safe).
  3. IMERG fill value is -9999.9 — always replaced with NaN before any aggregation.

Running offline from a frozen raw snapshot is idempotent: the same HDF5 files always
produce the same rows, so SHA-256 verification in D8 will pass.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.config import DB_PATH, MANIFEST, RAW, ROOT
from src.manifest import read_manifest

SOURCE = "imerg_late_daily"
FILL = -9999.9
# IMERG Late daily V07 variable path inside HDF5
PRECIP_PATH = "Grid/precipitationCal"
LAT_PATH = "Grid/lat"
LON_PATH = "Grid/lon"


def _load_hdf5_grid(hdf_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (lat, lon, precip_2d) from one IMERG Late daily HDF5 file.

    precip_2d shape is (lat, lon); fill values already replaced with NaN.
    Raises ImportError if h5py is not installed (caught by the caller).
    """
    import h5py  # deferred so the module is importable without h5py for unit tests

    with h5py.File(hdf_path, "r") as f:
        lat = f[LAT_PATH][:]          # shape (nlat,)
        lon = f[LON_PATH][:]          # shape (nlon,)
        # precipitationCal is (time, lon, lat) in V07 — squeeze time, then transpose
        raw = f[PRECIP_PATH][0, :, :]   # (nlon, nlat)
        precip = raw.T.astype(float)    # -> (nlat, nlon)
    precip[precip <= FILL * 0.9] = np.nan   # mask fill, allow tiny negatives
    return lat, lon, precip


def _pixels_for_district(
    lat: np.ndarray, lon: np.ndarray, geom
) -> tuple[np.ndarray, np.ndarray]:
    """Return index arrays (lat_idxs, lon_idxs) of pixels inside *geom*.

    Uses the geometry bounding box for a fast pre-filter, then shapely 2.x
    contains_xy for vectorised point-in-polygon. Returns empty arrays when
    no pixel centre falls inside.
    """
    import shapely

    minx, miny, maxx, maxy = geom.bounds

    # fast index ranges
    lat_mask = (lat >= miny) & (lat <= maxy)
    lon_mask = (lon >= minx) & (lon <= maxx)
    li = np.where(lat_mask)[0]
    lo = np.where(lon_mask)[0]

    if li.size == 0 or lo.size == 0:
        return np.array([], dtype=int), np.array([], dtype=int)

    # grid of candidate centres
    grid_lats = lat[li]
    grid_lons = lon[lo]
    llon, llat = np.meshgrid(grid_lons, grid_lats)   # both (len(li), len(lo))

    # shapely 2.x vectorised contains_xy(geometry, x, y)
    inside = shapely.contains_xy(geom, llon.ravel(), llat.ravel())
    inside = inside.reshape(llon.shape)

    ri, ci = np.where(inside)
    return li[ri], lo[ci]


def aggregate_one_file(
    hdf_path: Path,
    districts_gdf,
    day: date,
) -> pd.DataFrame:
    """Aggregate one HDF5 granule to per-district rain stats.

    Parameters
    ----------
    hdf_path : Path to an IMERG Late daily HDF5 file.
    districts_gdf : GeoDataFrame with columns [district_id, geometry].
    day : The UTC calendar day the granule represents.

    Returns
    -------
    DataFrame with columns: district_id, date_utc, wettest_pixel_mm, mean_rain_mm, n_pixels.
    """
    lat, lon, precip = _load_hdf5_grid(hdf_path)

    rows = []
    for _, row in districts_gdf.iterrows():
        li, lo = _pixels_for_district(lat, lon, row.geometry)
        if li.size == 0:
            wettest = np.nan
            mean_rain = np.nan
            n_pixels = 0
        else:
            # element-wise indexing: each (li[k], lo[k]) is one pixel centre
            vals = precip[li, lo].ravel()
            vals = vals[~np.isnan(vals)]
            if vals.size == 0:
                wettest = np.nan
                mean_rain = np.nan
                n_pixels = 0
            else:
                wettest = float(np.max(vals))
                mean_rain = float(np.mean(vals))
                n_pixels = int(vals.size)

        rows.append({
            "district_id": row.district_id,
            "date_utc": day,
            "wettest_pixel_mm": wettest,
            "mean_rain_mm": mean_rain,
            "n_pixels": n_pixels,
        })

    return pd.DataFrame(rows)


def _day_from_filename(filename: str) -> date | None:
    """Parse UTC date from the manifest filename prefix 'YYYY-MM-DD_<granule>.HDF5'."""
    try:
        return date.fromisoformat(filename[:10])
    except ValueError:
        return None


def build(db_path: Path = DB_PATH, raw_dir: Path = RAW, manifest_path: Path = MANIFEST) -> int:
    """Build `rain_district_day` gold table in DuckDB from raw IMERG HDF5 files.

    Idempotent: re-running produces the same output (files sorted by date_utc, district_id).
    Returns the number of rows written.
    """
    # load districts geometry
    import geopandas as gpd
    from shapely import wkt

    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute(
            "SELECT district_id, geometry_wkt FROM districts ORDER BY district_id"
        ).df()

    if df.empty:
        raise SystemExit("districts table is empty; run `python -m src.districts build`")

    districts_gdf = gpd.GeoDataFrame(
        df,
        geometry=df["geometry_wkt"].apply(wkt.loads),
        crs="EPSG:4326",
    )

    # find IMERG files from manifest
    rows = [r for r in read_manifest(manifest_path) if r["source"] == SOURCE]
    if not rows:
        raise SystemExit(
            "No IMERG files in manifest; run `python -m src.fetch_imerg --test-one-day`"
        )

    frames = []
    for r in sorted(rows, key=lambda x: x["path"]):
        hdf_path = ROOT / r["path"]
        filename = hdf_path.name
        day = _day_from_filename(filename)
        if day is None:
            print(f"  skip {filename}: cannot parse date from name")
            continue
        if not hdf_path.exists():
            print(f"  skip {filename}: file missing (run fetch first)")
            continue
        print(f"  aggregating {day} from {filename} ...")
        frame = aggregate_one_file(hdf_path, districts_gdf, day)
        frames.append(frame)

    if not frames:
        raise SystemExit("No processable IMERG granules found.")

    rain = pd.concat(frames, ignore_index=True)
    # stable sort → reproducible order for D8 SHA-256 check
    rain = rain.sort_values(["date_utc", "district_id"]).reset_index(drop=True)

    with duckdb.connect(str(db_path)) as con:
        con.execute("""
            CREATE OR REPLACE TABLE rain_district_day AS
            SELECT
                district_id,
                CAST(date_utc AS DATE)  AS date_utc,
                wettest_pixel_mm,
                mean_rain_mm,
                n_pixels
            FROM rain
            ORDER BY date_utc, district_id
        """)
        n = con.execute("SELECT count(*) FROM rain_district_day").fetchone()[0]

    print(f"rain_district_day: {n} rows")
    return n


if __name__ == "__main__":
    build()
    sys.exit(0)
