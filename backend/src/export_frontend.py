"""Publish `status.json` for the dashboard in ../frontend (start of P1/P2).

    python -m src.export_frontend          # writes ../frontend/public/data/status.json

Offline: reads the DuckDB gold tables and the manifest only. The frontend loads this file
at startup and falls back to its mock data for anything not in it (risk, gauges, prices).
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from shapely import wkt

from src import manifest
from src.config import DB_PATH, ROOT

OUT = ROOT.parent / "frontend" / "public" / "data" / "status.json"
SIMPLIFY_DEG = 0.01  # ~1 km; keeps the file small enough to ship with the page


def _outline(geometry_wkt: str) -> list[list[float]]:
    """Largest exterior ring as [lat, lon] pairs, the order Leaflet expects."""
    geom = wkt.loads(geometry_wkt).simplify(SIMPLIFY_DEG, preserve_topology=True)
    poly = max(getattr(geom, "geoms", [geom]), key=lambda g: g.area)
    return [[round(y, 4), round(x, 4)] for x, y in poly.exterior.coords]


def _tables(con) -> set[str]:
    return {t for (t,) in con.execute("SHOW TABLES").fetchall()}


def districts(con) -> list[dict]:
    rows = con.execute("""
        SELECT district_id, name, province, centroid_lat, centroid_lon, geometry_wkt
        FROM districts ORDER BY district_id""").fetchall()
    return [{"id": d, "name": n, "province": p, "centroid": [round(float(lat), 4), round(float(lon), 4)],
             "polygon": _outline(g)} for d, n, p, lat, lon, g in rows]


def latest_forecast(con) -> dict:
    """Newest forecast day per district, precipitation by lead time."""
    rows = con.execute("""
        WITH newest AS (SELECT max(date_utc) AS d FROM forecast_day)
        SELECT district_id, date_utc, lead_days, precip_sum_mm
        FROM forecast_day, newest WHERE date_utc = newest.d""").fetchall()
    out: dict = {"date_utc": None, "precip_mm_by_lead": defaultdict(dict)}
    for district_id, day, lead, precip in rows:
        out["date_utc"] = day.isoformat()
        out["precip_mm_by_lead"][district_id][str(lead)] = precip
    return out


def sources() -> list[dict]:
    by_source: dict[str, dict] = {}
    for r in manifest.read_manifest():
        s = by_source.setdefault(r["source"], {"source": r["source"], "licence": r["licence"],
                                               "files": 0, "bytes": 0, "last_fetched_utc": ""})
        s["files"] += 1
        s["bytes"] += int(r["bytes"])
        s["last_fetched_utc"] = max(s["last_fetched_utc"], r["fetched_at_utc"])
    return list(by_source.values())


def quality(con) -> list[dict]:
    rows = con.execute("""
        SELECT table_name, rule, action, reason, n_rows, decided_at_utc
        FROM quality_log ORDER BY table_name, rule""").fetchall()
    keys = ["table", "rule", "action", "reason", "n_rows", "decided_at_utc"]
    return [dict(zip(keys, r)) for r in rows]


def build(db_path=DB_PATH, out: Path = OUT) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        have = _tables(con)
        status = {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sources": sources(),
            "districts": districts(con) if "districts" in have else [],
            "forecast": latest_forecast(con) if "forecast_day" in have else None,
            "quality": quality(con) if "quality_log" in have else [],
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, separators=(",", ":")))
    print(f"status.json: {len(status['districts'])} districts, "
          f"{len(status['quality'])} quality decisions, {out.stat().st_size // 1024} KB -> {out}")
    return out


if __name__ == "__main__":
    build()
    sys.exit(0)
