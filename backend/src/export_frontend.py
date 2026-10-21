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
import pandas as pd
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
    label = rows[0][6]
    test_file = ROOT / "docs" / "model_a_test.json"
    if test_file.exists():  # the one-off test run (E3) of this same artifact
        t = json.loads(test_file.read_text())
        if t.get("model_version") == rows[0][5]:
            m, c = t["scores"]["model"]["all"]["24h"], t["scores"]["climatology"]["all"]["24h"]
            label = (f"test-evaluated once on Jan-Sep 2026: Brier 24 h {m['brier']:.4f} vs climatology "
                     f"{c['brier']:.4f}")
    out: dict = {"model_version": rows[0][5], "label": label, "by_district": defaultdict(dict)}
    for district_id, lead, p, row_id, day, _, _ in rows:
        out["by_district"][district_id][f"{24 * lead}h"] = {
            "p": round(float(p), 4), "row_id": row_id, "date_utc": day.isoformat()}
    return out


MARKET_GROUPS = {"staples": {1, 2, 3, 4, 10, 12, 13, 14, 15, 17, 18, 19, 20, 24, 25, 26, 27, 29},
                 "perishables": {5, 6, 7, 8, 9, 11, 16, 21, 22, 23, 28},
                 "fuel": {41, 42, 43, 47, 48, 49}}
CITY_DISTRICT = {"Karachi": "South Karachi", "D.I. Khan": "D. I. Khan"}  # SPI city -> OCHA district


def market(con) -> dict | None:
    """B6: latest PBS SPI prices per city with the previous 52 weeks' 10th-90th percentile range.

    The range is history, not a forecast. Item names come from the newest week (PBS xlsx), whose
    text is clean; older PDF-parsed weeks only contribute numbers.
    """
    group_of = {i: g for g, items in MARKET_GROUPS.items() for i in items}
    keep = sorted(group_of)
    rows = con.execute(f"""
        WITH latest AS (SELECT max(week_end) AS w FROM spi_price),
        names AS (SELECT item_no, any_value(item) AS item, any_value(unit) AS unit FROM spi_price, latest
                  WHERE week_end = latest.w GROUP BY item_no),
        cur AS (SELECT city, item_no, avg_pkr, row_id, quality_flags FROM spi_price, latest WHERE week_end = latest.w),
        prev AS (SELECT city, item_no, avg_pkr FROM spi_price, latest WHERE week_end = latest.w - INTERVAL 7 DAY),
        hist AS (SELECT city, item_no, quantile_cont(avg_pkr, 0.1) AS p10, quantile_cont(avg_pkr, 0.9) AS p90,
                        count(avg_pkr) AS n_weeks
                 FROM spi_price, latest WHERE week_end < latest.w AND week_end >= latest.w - INTERVAL 364 DAY
                 GROUP BY ALL)
        SELECT c.city, c.item_no, n.item, n.unit, c.avg_pkr, p.avg_pkr, h.p10, h.p90, h.n_weeks, c.row_id,
               c.quality_flags, (SELECT w FROM latest)
        FROM cur c JOIN names n USING (item_no) LEFT JOIN prev p USING (city, item_no)
        LEFT JOIN hist h USING (city, item_no)
        WHERE c.item_no IN ({",".join(map(str, keep))})
        ORDER BY c.city, c.item_no""").fetchall()
    if not rows:
        return None
    out: dict = {"week_end": rows[0][11].isoformat(), "source": "PBS weekly SPI, city-wise annex",
                 "range_label": "10th-90th percentile of the previous 52 weeks (history, not a forecast)",
                 "cities": defaultdict(list)}
    for city, no, item, unit, avg, prev, p10, p90, n, row_id, flags, _ in rows:
        r = lambda v: None if v is None else round(float(v), 2)  # noqa: E731
        out["cities"][city].append({
            "item_no": no, "item": item, "unit": unit, "group": group_of[no], "avg_pkr": r(avg),
            "wow_pct": None if avg is None or not prev else round((avg / prev - 1) * 100, 2),
            "p10": r(p10), "p90": r(p90), "n_weeks": n, "row_id": row_id, "quality_flags": flags})
    # nearest SPI city to every district, by centroid distance (km, equirectangular)
    cents = dict(con.execute("SELECT name, [centroid_lat::DOUBLE, centroid_lon::DOUBLE] FROM districts").fetchall())
    city_xy = {c: cents.get(CITY_DISTRICT.get(c, c)) for c in out["cities"]}
    city_xy = {c: xy for c, xy in city_xy.items() if xy}

    def km(a, b):
        import math
        x = (b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
        return 111.2 * math.hypot(b[0] - a[0], x)
    out["city_xy"] = {c: [round(xy[0], 4), round(xy[1], 4)] for c, xy in city_xy.items()}
    out["nearest_city"] = {}
    for did, lat, lon in con.execute(
            "SELECT district_id, centroid_lat::DOUBLE, centroid_lon::DOUBLE FROM districts").fetchall():
        city, xy = min(city_xy.items(), key=lambda kv: km((lat, lon), kv[1]))
        out["nearest_city"][did] = {"city": city, "km": round(km((lat, lon), xy))}
    return out


def district_info(con, have: set[str]) -> dict:
    """Per-district facts for the map's layers and click card (all from gold/clean tables)."""
    out: dict = defaultdict(dict)
    if "thresholds" in have:
        for did, thr in con.execute("SELECT district_id, threshold_mm FROM thresholds").fetchall():
            out[did]["threshold_mm"] = round(float(thr), 1)
    if "rain_district_day" in have:
        newest = con.execute("SELECT max(date_utc) FROM rain_district_day").fetchone()[0]
        for did, total, wettest in con.execute("""
                SELECT district_id, sum(mean_mm), max(wettest_mm) FROM rain_district_day
                WHERE date_utc > ? - INTERVAL 7 DAY GROUP BY district_id""", [newest]).fetchall():
            out[did]["obs_7d_mm"] = None if total is None else round(float(total), 1)
            out[did]["obs_7d_wettest_mm"] = None if wettest is None else round(float(wettest), 1)
        out["_meta"]["obs_until"] = newest.isoformat()
        for did, day, wettest in con.execute("""
                SELECT district_id, date_utc, wettest_mm FROM rain_district_day
                WHERE date_utc > ? - INTERVAL 10 DAY ORDER BY date_utc""", [newest]).fetchall():
            out[did].setdefault("obs_daily_wettest_mm", {})[day.isoformat()] = (
                None if wettest is None else round(float(wettest), 1))
    if "baseline_climatology" in have:  # the declared baseline: this month's share of heavy-rain days
        month = datetime.now(timezone.utc).month
        for did, p in con.execute("SELECT district_id, p_exceed FROM baseline_climatology WHERE month = ?",
                                  [month]).fetchall():
            out[did]["clim_p_month"] = None if p is None else round(float(p), 4)
    if "district_attributes" in have:
        for did, elev, coastal, share, prone in con.execute(
                "SELECT district_id, elevation_m, coastal, flood_share_2022, flood_prone FROM district_attributes").fetchall():
            out[did].update({"elevation_m": None if elev is None else round(float(elev)),
                             "coastal": bool(coastal),
                             "flood_share_2022": None if share is None else round(float(share), 3),
                             "flood_prone": prone})
    return out


def alerts(con) -> list[dict]:
    """Newest official NDMA documents (advisories and sitreps) with dates and links; real titles only."""
    rows = con.execute("""
        SELECT title, published, url, source FROM documents
        WHERE source IN ('ndma_advisory', 'ndma_sitrep') AND published IS NOT NULL
        ORDER BY published DESC, title LIMIT 15""").fetchall()
    return [{"title": t, "published": str(p)[:10], "url": u,
             "kind": "advisory" if s == "ndma_advisory" else "situation report"} for t, p, u, s in rows]


FOOD_ITEMS = {1: "Wheat flour", 2: "Rice (basmati)", 3: "Rice (IRRI-6)", 23: "Tomatoes", 22: "Onions",
              21: "Potatoes", 20: "Pulses (gram)", 24: "Sugar", 7: "Chicken (live)", 11: "Eggs", 13: "Cooking oil",
              49: "LPG cylinder"}


def food_series(con) -> dict | None:
    """52 weeks of PBS city prices for the Food Prices page, plus each series' past 4-week changes
    (10th/90th percentile over its whole history: the typical range around a no-change forecast)."""
    rows = con.execute(f"""
        WITH units AS (  -- unit text from the newest week (PBS xlsx; older PDF weeks can be garbled)
            SELECT item_no, any_value(unit) AS unit FROM spi_price
            WHERE week_end = (SELECT max(week_end) FROM spi_price) GROUP BY item_no)
        SELECT s.city, s.item_no, s.week_end, s.avg_pkr, u.unit
        FROM spi_price s JOIN units u USING (item_no)
        WHERE s.item_no IN ({",".join(map(str, FOOD_ITEMS))}) ORDER BY s.city, s.item_no, s.week_end""").df()
    if rows.empty:
        return None
    out: dict = {"items": FOOD_ITEMS, "series": {}}
    latest = rows.week_end.max()
    for (city, item), g in rows.groupby(["city", "item_no"]):
        g = g.dropna(subset=["avg_pkr"]).sort_values("week_end")
        if g.empty:
            continue
        chg4 = (g.avg_pkr / g.avg_pkr.shift(4) - 1).dropna() * 100
        recent = g[g.week_end > latest - pd.Timedelta(days=365)]
        out["series"].setdefault(city, {})[str(item)] = {
            "unit": g.unit.iloc[-1],
            "history": [[str(w.date()), round(float(p), 2)] for w, p in zip(recent.week_end, recent.avg_pkr)],
            "chg4_p10": None if chg4.empty else round(float(chg4.quantile(0.1)), 2),
            "chg4_p90": None if chg4.empty else round(float(chg4.quantile(0.9)), 2),
        }
    return out


def replay_summary() -> dict | None:
    """P6 replay (10-20 Aug 2025, 24 h lead): per day, real heavy-rain districts and the model's ranking."""
    path = DATA / "replay.duckdb"
    if not path.exists():
        return None
    with duckdb.connect(str(path), read_only=True) as con:
        df = con.execute("""SELECT name, province, date_utc, p_heavy_rain, clim_p, label FROM risk_replay
                            WHERE lead_days = 1 AND label IS NOT NULL""").df()
    days = []
    for day, g in df.groupby("date_utc"):
        g = g.sort_values("p_heavy_rain", ascending=False).reset_index(drop=True)
        g["rank"] = g.index + 1
        events = g[g.label == 1]
        days.append({"day": str(pd.Timestamp(day).date()), "districts": len(g), "events": len(events),
                     "hits_top10": int(g.head(10).label.sum()),
                     "top": [{"name": r.name, "p": round(float(r.p_heavy_rain), 3), "event": int(r.label)}
                             for r in g.head(5).itertuples()],
                     "event_districts": [{"name": r.name, "rank": int(r.rank), "p": round(float(r.p_heavy_rain), 3)}
                                         for r in events.itertuples()]})
    return {"label": "Replay of 10-20 Aug 2025 with the current model (validation period; not live, not a test result)",
            "days": days}


def model_results() -> dict:
    """Model A test/validation and Model B validation results, straight from the result files."""
    docs = ROOT / "docs"
    out: dict = {}
    t = docs / "model_a_test.json"
    if t.exists():
        r = json.loads(t.read_text())
        out["a_test"] = {"model_version": r["model_version"], "n": r["n_test"], "positive_rate": r["positive_rate"],
                         "model": r["scores"]["model"], "climatology": r["scores"]["climatology"],
                         "raw_forecast_cut": r["scores"]["raw_forecast_cut"],
                         "diff_vs_climatology": r["model_minus_climatology"]}
    v = docs / "model_a_validation.json"
    if v.exists():
        r = json.loads(v.read_text())
        out["a_validation"] = {"chosen": r.get("chosen"), "n_train": r["n_train"], "n_validation": r["n_validation"],
                               "baselines": r["baselines"],
                               "models": {k: m["validation"] for k, m in r.get("models", {}).items()},
                               "features": r.get("features", [])}
    g = docs / "model_a_groups.json"
    if g.exists():
        out["a_groups"] = json.loads(g.read_text())
    b = docs / "model_b_validation.json"
    if b.exists():
        r = json.loads(b.read_text())
        out["b_validation"] = {"n_train": r["n_train"], "n_validation": r["n_validation"], "by_group": r["by_group"],
                               "beats_no_change": r["beats_no_change_on_validation"]}
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
            "market": market(con) if {"spi_price", "districts"} <= have else None,
            "district_info": district_info(con, have),
            "alerts": alerts(con) if "documents" in have else [],
            "model_results": model_results(),
            "food": food_series(con) if "spi_price" in have else None,
            "replay": replay_summary(),
            # public URL of the Insight API (Cloudflare tunnel, deploy/tunnel.sh); None when not running
            "insight_url": (DATA / "insight_url.txt").read_text().strip() if (DATA / "insight_url.txt").exists() else None,
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
