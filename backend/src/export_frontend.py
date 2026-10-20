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
from src.config import DATA, DB_PATH, ROOT

OUT = ROOT.parent / "frontend" / "public" / "data" / "status.json"
FLOW_STATUS = DATA / "flow_status.json"  # written by flows/hourly.py after each successful build
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


def live_forecast(con) -> dict:
    """Latest-run forecast rain per district and day; raw forecast, not a risk score."""
    rows = con.execute("""
        SELECT district_id, date_utc, days_ahead, precip_sum_mm, fetched_at_utc
        FROM forecast_live WHERE days_ahead BETWEEN 1 AND 3 ORDER BY district_id, date_utc""").fetchall()
    out: dict = {"fetched_at_utc": rows[0][4] if rows else None,
                 "label": "Raw forecast rainfall (Open-Meteo latest run), not a model risk score",
                 "precip_mm": defaultdict(dict)}
    for district_id, day, ahead, precip, _ in rows:
        out["precip_mm"][district_id][str(ahead)] = round(precip, 2)
    return out


def risk(con) -> dict | None:
    """Model A probability of heavy rain per district at 24/48/72 h, each with its row id."""
    rows = con.execute("""
        SELECT district_id, lead_days, p_heavy_rain, row_id, date_utc, model_version, model_label
        FROM risk_live ORDER BY district_id, lead_days""").fetchall()
    if not rows:
        return None
    out: dict = {"model_version": rows[0][5], "label": rows[0][6], "by_district": defaultdict(dict)}
    for district_id, lead, p, row_id, day, _, _ in rows:
        out["by_district"][district_id][f"{24 * lead}h"] = {
            "p": round(float(p), 4), "row_id": row_id, "date_utc": day.isoformat()}
    return out


def build(db_path=DB_PATH, out: Path = OUT) -> Path:
    with duckdb.connect(str(db_path), read_only=True) as con:
        have = _tables(con)
        status = {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sources": sources(),
            "districts": districts(con) if "districts" in have else [],
            "forecast": latest_forecast(con) if "forecast_day" in have else None,
            "quality": quality(con) if "quality_log" in have else [],
            "live_forecast": live_forecast(con) if "forecast_live" in have else None,
            "risk": risk(con) if "risk_live" in have else None,
            "pipeline": json.loads(FLOW_STATUS.read_text()) if FLOW_STATUS.exists() else None,
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(status, separators=(",", ":")))
    tmp.replace(out)  # atomic: the dashboard never reads a half-written file
    print(f"status.json: {len(status['districts'])} districts, "
          f"{len(status['quality'])} quality decisions, {out.stat().st_size // 1024} KB -> {out}")
    return out


if __name__ == "__main__":
    build()
    sys.exit(0)
