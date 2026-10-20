"""District boundaries (task D2): OCHA COD-AB admin level 2 via HDX.

    python -m src.districts fetch   # download raw zip + manifest row (network)
    python -m src.districts build   # raw zip -> DuckDB table `districts` (offline)
"""
import sys
import zipfile

import duckdb
import geopandas as gpd
import requests

from src import manifest
from src.config import DB_PATH, ROOT

SOURCE = "ocha_cod_ab"
URL = ("https://data.humdata.org/dataset/a64d1ff2-7158-48c7-887d-6af69ce21906/resource/"
       "c6521e04-75e1-41be-8e02-0554a424d9f4/download/pak_admin_boundaries.geojson.zip")
LAYER = "pak_admin2.geojson"


def fetch() -> None:
    if URL in manifest.fetched_queries(SOURCE):
        print("district boundaries already fetched; skipping")
        return
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    path = manifest.save_raw(r.content, SOURCE, URL, "pak_admin_boundaries.geojson.zip")
    print(f"saved {path} ({len(r.content):,} bytes)")


def load_admin2() -> gpd.GeoDataFrame:
    row = manifest.latest(SOURCE)
    if row is None:
        raise SystemExit("no district boundaries in manifest; run `python -m src.districts fetch`")
    with zipfile.ZipFile(ROOT / row["path"]) as z, z.open(LAYER) as f:
        gdf = gpd.read_file(f)
    return gdf.to_crs("EPSG:4326")


def build(db_path=DB_PATH) -> int:
    gdf = load_admin2()
    # OCHA ships a centre point; fall back to a point guaranteed inside the polygon
    inside = gdf.geometry.representative_point()
    gdf["centroid_lat"] = gdf["center_lat"].fillna(inside.y)
    gdf["centroid_lon"] = gdf["center_lon"].fillna(inside.x)

    df = gdf.rename(columns={"adm2_pcode": "district_id", "adm2_name": "name",
                             "adm1_name": "province", "adm1_pcode": "province_id"})
    df["geometry_wkt"] = gdf.geometry.to_wkt()
    df = df[["district_id", "name", "province", "province_id", "area_sqkm",
             "centroid_lat", "centroid_lon", "geometry_wkt"]].sort_values("district_id")

    if df["district_id"].duplicated().any():
        raise ValueError("duplicate district ids in admin2 layer")

    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE districts AS SELECT * FROM df")
        n = con.execute("SELECT count(*) FROM districts").fetchone()[0]
    print(f"districts: {n} rows")
    return n


if __name__ == "__main__":
    {"fetch": fetch, "build": build}[sys.argv[1]]()
