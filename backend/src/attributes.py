"""District attributes (task D7): elevation, coastal flag, flood-prone flag.

    python -m src.attributes fetch   # elevation, coastline, UNOSAT table -> raw + manifest (network)
    python -m src.attributes build   # -> DuckDB `district_attributes` (offline)

- elevation_m: Copernicus DEM GLO-90 via the Open-Meteo Elevation API at the district
  centroid (one point; a whole-district mean would cost ~25x the calls).
  mountain = elevation_m >= MOUNTAIN_M. That cut-off is an evaluation-group choice made
  here, before any model results exist; it is not one of the declared fixed decisions.
- coastal: the district polygon comes within COAST_KM of the Natural Earth 10m coastline.
- flood_prone: UNOSAT's satellite-detected maximum flood water in the district covered
  10% or more of its area in either 25-31 Aug or 1-7 Sep 2022 (the declared rule).
  Districts UNOSAT does not list (no name match) get NULL, never False.
Used only to define evaluation groups (A5) and, where noted, as model features.
"""
import io
import re
import sys
import zipfile
from urllib.parse import urlencode

import duckdb
import geopandas as gpd
import pandas as pd
import requests
import shapely

from src import manifest
from src.config import DB_PATH, ROOT

ELEV_SOURCE = "open_meteo_elevation"
COAST_SOURCE = "natural_earth_coastline"
UNOSAT_SOURCE = "unosat_flood_2022"
ELEV_URL = "https://api.open-meteo.com/v1/elevation"
COAST_URL = "https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip"
UNOSAT_URL = ("https://unosat.org/static/unosat_filesystem/3350/UNOSAT_Population_Exposure_"
              "FL20220808PAK_20220825_20220831_20220901_20220907_Updated14Sep2022.xlsx")
MOUNTAIN_M = 1000
COAST_KM = 10
FLOOD_SHARE = 0.10
# province subtotal rows; Islamabad is both a province and a district row, so the
# district row (listed second) wins in flood_shares
PROVINCES = {"PAKISTAN", "AZAD KASHMIR", "BALOCHISTAN", "GILGIT BALTISTAN", "GILGIT-BALTISTAN",
             "KHYBER PAKHTUNKHWA", "PUNJAB", "SINDH", "FATA", "ICT"}
# OCHA name (lower case) -> UNOSAT spelling, where the two differ (none needed for the 14 Sep table)
ALIASES: dict[str, str] = {}


def _districts(db_path=DB_PATH) -> pd.DataFrame:
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute("SELECT district_id, name, province, centroid_lat, centroid_lon, geometry_wkt "
                           "FROM districts ORDER BY district_id").df()


def fetch(db_path=DB_PATH) -> None:
    d = _districts(db_path)
    done = set().union(*(manifest.fetched_queries(s) for s in (ELEV_SOURCE, COAST_SOURCE, UNOSAT_SOURCE)))
    for i in range(0, len(d), 100):  # the API takes up to 100 points per request
        b = d.iloc[i:i + 100]
        q = f"{ELEV_URL}?" + urlencode({"latitude": ",".join(f"{x:.4f}" for x in b.centroid_lat),
                                        "longitude": ",".join(f"{x:.4f}" for x in b.centroid_lon)})
        if q not in done:
            r = requests.get(q, timeout=120)
            r.raise_for_status()
            manifest.save_raw(r.content, ELEV_SOURCE, q, f"elevation_b{i // 100:02d}.json")
    for url, source, name in [(COAST_URL, COAST_SOURCE, "ne_10m_coastline.zip"),
                              (UNOSAT_URL, UNOSAT_SOURCE, "UNOSAT_Population_Exposure_FL20220808PAK_Updated14Sep2022.xlsx")]:
        if url not in done:
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            manifest.save_raw(r.content, source, url, name)
    print("attributes fetched")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z]", "", name.lower())


def flood_shares(xlsx_path) -> dict[str, float]:
    """{normalised district name: max share of area under flood water, 25 Aug - 7 Sep 2022}."""
    df = pd.read_excel(xlsx_path, sheet_name=1, header=None).iloc[1:, [0, 1, 5, 10]]
    df.columns = ["name", "area_km2", "flood_aug_km2", "flood_sep_km2"]
    df = df[df["name"].notna() & ~df["name"].astype(str).str.strip().str.upper().isin(PROVINCES)]
    df = df[pd.to_numeric(df["area_km2"], errors="coerce") > 0]
    share = df[["flood_aug_km2", "flood_sep_km2"]].apply(pd.to_numeric, errors="coerce").max(axis=1) \
        / df["area_km2"].astype(float)
    return dict(zip(df["name"].astype(str).map(_norm), share))


def build(db_path=DB_PATH) -> int:
    rows = {s: manifest.latest(s) for s in (ELEV_SOURCE, COAST_SOURCE, UNOSAT_SOURCE)}
    if any(r is None for r in rows.values()):
        raise SystemExit("run `python -m src.attributes fetch` first")
    d = _districts(db_path)

    import json
    elev = {}
    for r in manifest.read_manifest():
        if r["source"] == ELEV_SOURCE:
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(r["query"]).query)
            pts = zip(q["latitude"][0].split(","), q["longitude"][0].split(","))
            elev.update(zip(pts, json.loads((ROOT / r["path"]).read_bytes())["elevation"]))
    d["elevation_m"] = [elev.get((f"{a:.4f}", f"{b:.4f}")) for a, b in zip(d.centroid_lat, d.centroid_lon)]
    d["mountain"] = d["elevation_m"] >= MOUNTAIN_M

    with zipfile.ZipFile(io.BytesIO((ROOT / rows[COAST_SOURCE]["path"]).read_bytes())) as z:
        shp = next(n for n in z.namelist() if n.endswith(".shp"))
        z.extractall(ROOT / "data" / "clean" / "ne_coastline")
    coast = gpd.read_file(ROOT / "data" / "clean" / "ne_coastline" / shp)
    coast = coast.cx[60:78, 22:38].to_crs(32642)  # UTM 42N, metres
    near = coast.buffer(COAST_KM * 1000).union_all()
    geoms = gpd.GeoSeries(shapely.from_wkt(d.geometry_wkt), crs=4326).to_crs(32642)
    d["coastal"] = geoms.intersects(near).to_numpy()

    shares = flood_shares(ROOT / rows[UNOSAT_SOURCE]["path"])
    d["flood_share_2022"] = [shares.get(_norm(ALIASES.get(n.lower(), n))) for n in d.name]
    d["flood_prone"] = d["flood_share_2022"].map(lambda s: None if pd.isna(s) else bool(s >= FLOOD_SHARE))
    unmatched = d.loc[d.flood_share_2022.isna(), "name"].tolist()

    out = d[["district_id", "name", "province", "elevation_m", "mountain", "coastal",
             "flood_share_2022", "flood_prone"]]
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE district_attributes AS SELECT * FROM out ORDER BY district_id")
    print(f"district_attributes: {len(out)} rows; {int(out.mountain.sum())} mountain, "
          f"{int(out.coastal.sum())} coastal, {int((out.flood_prone == True).sum())} flood-prone; "  # noqa: E712
          f"{len(unmatched)} not in UNOSAT table: {unmatched}")
    return len(out)


if __name__ == "__main__":
    {"fetch": fetch, "build": build}[sys.argv[1]]()
