"""District rain table (task D5): wettest-pixel and mean rain per district per UTC day.

    python -m src.rain build   # raw IMERG days -> DuckDB `rain_district_day` (offline)

A pixel belongs to the district that contains its centre. Districts too small to contain
any pixel centre get the pixel nearest their centroid, so every district has a value.
Fill pixels (-9999.9) are excluded from max/mean and counted, never read as zero.

Row id is `<district_id>_<YYYY-MM-DD>`, stable across rebuilds.
"""
import re
import sys
from datetime import date, datetime

import duckdb
import numpy as np
import pandas as pd
import shapely

from src import imerg, manifest
from src.config import DB_PATH, ROOT

LOW_SAMPLE_CNT = 24  # fewer than 24 of 48 half-hourly retrievals -> low confidence (Q3)


def district_pixel_index(districts: pd.DataFrame, lon: np.ndarray, lat: np.ndarray) -> dict[str, np.ndarray]:
    """{district_id: flat indices into a (lon, lat) grid} for every district."""
    glon, glat = np.meshgrid(lon, lat, indexing="ij")
    flat_lon, flat_lat = glon.ravel(), glat.ravel()
    index = {}
    for d in districts.itertuples():
        geom = shapely.from_wkt(d.geometry_wkt)
        inside = np.flatnonzero(shapely.contains_xy(geom, flat_lon, flat_lat))
        if inside.size == 0:
            nearest = np.argmin((flat_lon - d.centroid_lon) ** 2 + (flat_lat - d.centroid_lat) ** 2)
            inside = np.array([nearest])
        index[d.district_id] = inside
    return index


def aggregate_day(index: dict[str, np.ndarray], precip: np.ndarray, cnt: np.ndarray | None,
                  day: date) -> list[dict]:
    """One day's grid (lon, lat), NaN = fill -> one row per district."""
    p, c = precip.ravel(), None if cnt is None else cnt.ravel()
    rows = []
    for district_id, idx in index.items():
        vals = p[idx]
        ok = ~np.isnan(vals)
        rows.append({
            "row_id": f"{district_id}_{day.isoformat()}",
            "district_id": district_id,
            "date_utc": day,
            "wettest_mm": float(vals[ok].max()) if ok.any() else None,
            "mean_mm": float(vals[ok].mean()) if ok.any() else None,
            "n_pixels": int(idx.size),
            "n_fill_pixels": int((~ok).sum()),
            "min_sample_cnt": None if c is None else int(c[idx].min()),
        })
    return rows


def imerg_days() -> list[tuple[date, dict]]:
    """Newest manifest row per IMERG day, sorted by day."""
    latest: dict[date, dict] = {}
    for r in manifest.read_manifest():
        if r["source"] != imerg.SOURCE:
            continue
        m = re.search(r"3IMERG\.(\d{8})-", r["path"])
        day = datetime.strptime(m.group(1), "%Y%m%d").date()
        if day not in latest or r["fetched_at_utc"] > latest[day]["fetched_at_utc"]:
            latest[day] = r
    return sorted(latest.items())


def build(db_path=DB_PATH) -> int:
    days = imerg_days()
    if not days:
        raise SystemExit("no IMERG days in manifest; run `python -m src.imerg fetch`")
    with duckdb.connect(str(db_path), read_only=True) as con:
        districts = con.execute("SELECT * FROM districts ORDER BY district_id").df()

    index, rows = None, []
    for n, (day, r) in enumerate(days, 1):
        ds = imerg.open_day(ROOT / r["path"])
        if index is None:
            index = district_pixel_index(districts, ds.lon.values, ds.lat.values)
        rows += aggregate_day(index, ds.precipitation.values[0], ds.precipitation_cnt.values[0], day)
        if n % 500 == 0:
            print(f"  {n}/{len(days)} days")

    df = pd.DataFrame(rows)
    df["low_confidence"] = df["min_sample_cnt"] < LOW_SAMPLE_CNT
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE rain_district_day AS SELECT * FROM df ORDER BY row_id")
        n = con.execute("SELECT count(*) FROM rain_district_day").fetchone()[0]
    print(f"rain_district_day: {n} rows ({len(days)} days)")
    return n


if __name__ == "__main__":
    {"build": build}[sys.argv[1]]()
