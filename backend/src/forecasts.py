"""Archived forecasts (task D3): Open-Meteo Previous Runs API at every district centroid.

    python -m src.forecasts fetch [--start 2024-01-01] [--end YYYY-MM-DD] [--budget 9000]
    python -m src.forecasts build   # raw JSON -> DuckDB `forecast_day` (offline)

Fetching is chunked by calendar month and by batches of district centroids. A chunk whose
exact query is already in the manifest is skipped, so the command is safe to re-run and
resumes where it stopped. Hours are requested in GMT so daily values are UTC days.

Free-tier limits are 600 calls/min, 5,000/hour and 10,000/day, where one request counts as
locations x max(1, variables/10) x max(1, days/14) calls. The full period is ~16k calls,
so `--budget` stops a run before the daily cap and the next run continues.
"""
import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlparse

import duckdb
import pandas as pd
import requests

from src import manifest
from src.config import DB_PATH, FORECAST_START, ROOT

SOURCE = "open_meteo_previous_runs"
LIVE_SOURCE = "open_meteo_live_forecast"  # same endpoint, latest run, next 4 days (live view only)
LIVE_EVERY_HOURS = 6                      # models update every 6 h; don't pay for more
URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
VARIABLES = ["precipitation", "relative_humidity_2m", "pressure_msl", "cloud_cover", "wind_speed_10m"]
LEADS = [1, 2, 3]
BATCH = 40
HOURLY_CAP = 5000


def hourly_params() -> list[str]:
    return [f"{v}_previous_day{d}" for d in LEADS for v in VARIABLES]


def call_weight(n_locations: int, n_days: int) -> float:
    return n_locations * max(1.0, len(hourly_params()) / 10) * max(1.0, n_days / 14)


def month_chunks(start: date, end: date):
    cur = start.replace(day=1)
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield max(cur, start), min(nxt - timedelta(days=1), end)
        cur = nxt


def build_query(lats, lons, start: date, end: date) -> str:
    params = {
        "latitude": ",".join(f"{x:.4f}" for x in lats),
        "longitude": ",".join(f"{x:.4f}" for x in lons),
        "hourly": ",".join(hourly_params()),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": "GMT",
    }
    return f"{URL}?{urlencode(params)}"


def query_weight(query: str) -> float:
    """Free-tier calls a stored query cost, recomputed from its parameters."""
    q = parse_qs(urlparse(query).query)
    n_loc = len(q["latitude"][0].split(","))
    n_days = (date.fromisoformat(q["end_date"][0]) - date.fromisoformat(q["start_date"][0])).days + 1
    n_vars = len(q["hourly"][0].split(","))
    return n_loc * max(1.0, n_vars / 10) * max(1.0, n_days / 14)


def calls_spent(hours: float | None = None, now: datetime | None = None) -> float:
    """Calls charged to this machine, from the manifest (all forecast sources).

    hours=None counts the current UTC calendar day (the "per day" in the free-tier terms);
    a number counts a rolling window instead.
    """
    now = now or datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) if hours is None else now - timedelta(hours=hours)
    since = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    return sum(query_weight(r["query"]) for r in manifest.read_manifest()
               if r["source"] in (SOURCE, LIVE_SOURCE) and r["fetched_at_utc"] >= since)


class DailyLimitReached(Exception):
    pass


def get_with_retry(url: str, tries: int = 5) -> bytes:
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 429:
                reason = r.json().get("reason", "")
                if "daily" in reason.lower():
                    raise DailyLimitReached(f"daily limit reached: {reason}. Re-run tomorrow to resume.")
                print(f"  429 ({reason}); waiting 65 s")
                time.sleep(65)
                continue
            r.raise_for_status()
            json.loads(r.content)  # empty or truncated bodies happen; treat as a retry
            return r.content
        except (requests.RequestException, ValueError) as e:
            print(f"  attempt {attempt} failed: {e}")
            time.sleep(min(10 * attempt, 60))
    raise RuntimeError(f"giving up after {tries} attempts")


def districts(db_path=DB_PATH) -> pd.DataFrame:
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(
            "SELECT district_id, centroid_lat, centroid_lon FROM districts ORDER BY district_id"
        ).df()


def fetch(start: date, end: date, budget: float) -> None:
    d = districts()
    done = manifest.fetched_queries(SOURCE)
    spent = 0.0
    for c_start, c_end in month_chunks(start, end):
        for i in range(0, len(d), BATCH):
            b = d.iloc[i:i + BATCH]
            query = build_query(b.centroid_lat, b.centroid_lon, c_start, c_end)
            if query in done:
                continue
            w = call_weight(len(b), (c_end - c_start).days + 1)
            if spent + w > budget:
                print(f"budget reached ({spent:.0f} calls); re-run to continue")
                return
            print(f"{c_start}..{c_end} batch {i // BATCH} ({len(b)} districts, {w:.0f} calls)")
            content = get_with_retry(query)
            # the build step maps coordinates in the query back to district ids
            name = f"{c_start:%Y-%m}_{c_end:%d}_b{i // BATCH:02d}.json"
            manifest.save_raw(content, SOURCE, query, name)
            spent += w
            time.sleep(w / HOURLY_CAP * 3600)  # stay under the hourly cap
    print(f"fetch complete ({spent:.0f} calls this run)")


def fetch_live(now: datetime | None = None, db_path=DB_PATH) -> bool:
    """Latest-run forecast for today..today+3 at every centroid, at most once per 6 h.

    Used only for the live view and live scoring, never for training (training uses the
    archived `_previous_dayN` values). Returns True if a new file was saved.
    """
    now = now or datetime.now(timezone.utc)
    last = manifest.latest(LIVE_SOURCE)
    if last and last["fetched_at_utc"] >= (now - timedelta(hours=LIVE_EVERY_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"):
        print(f"live forecast fetched {last['fetched_at_utc']}; skipping")
        return False
    d = districts(db_path)
    today = now.date()
    params = {
        "latitude": ",".join(f"{x:.4f}" for x in d.centroid_lat),
        "longitude": ",".join(f"{x:.4f}" for x in d.centroid_lon),
        "hourly": ",".join(VARIABLES),
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=3)).isoformat(),
        "timezone": "GMT",
    }
    query = f"{URL}?{urlencode(params)}"
    content = get_with_retry(query)
    manifest.save_raw(content, LIVE_SOURCE, query, f"{now:%Y-%m-%dT%H%MZ}.json")
    print(f"live forecast saved ({query_weight(query):.0f} calls)")
    return True


def build_live(db_path=DB_PATH) -> int:
    """Newest live fetch -> `forecast_live` (district, UTC day, days ahead of the fetch day)."""
    row = manifest.latest(LIVE_SOURCE)
    if row is None:
        print("skip forecast_live: no live fetch yet")
        return 0
    d = districts(db_path)
    ids = {(f"{r.centroid_lat:.4f}", f"{r.centroid_lon:.4f}"): r.district_id for r in d.itertuples()}
    q = parse_qs(urlparse(row["query"]).query)
    payload = json.loads((ROOT / row["path"]).read_bytes())
    payload = payload if isinstance(payload, list) else [payload]
    frames = []
    for lat, lon, loc in zip(q["latitude"][0].split(","), q["longitude"][0].split(","), payload):
        df = pd.DataFrame({v: loc["hourly"][v] for v in VARIABLES})
        df["time_utc"] = pd.to_datetime(loc["hourly"]["time"])
        df["district_id"] = ids[(lat, lon)]
        frames.append(df)
    hourly = pd.concat(frames)  # noqa: F841 (read by DuckDB below)
    fetched = row["fetched_at_utc"]
    with duckdb.connect(str(db_path)) as con:
        con.execute(f"""
            CREATE OR REPLACE TABLE forecast_live AS
            SELECT district_id,
                   CAST(time_utc AS DATE)                                   AS date_utc,
                   date_diff('day', CAST(TIMESTAMP '{fetched[:19]}' AS DATE),
                             CAST(time_utc AS DATE))                        AS days_ahead,
                   sum(precipitation)                AS precip_sum_mm,
                   max(precipitation)                AS precip_max_hourly_mm,
                   avg(relative_humidity_2m)         AS rh_mean_pct,
                   avg(pressure_msl)                 AS pressure_mean_hpa,
                   avg(cloud_cover)                  AS cloud_mean_pct,
                   max(wind_speed_10m)               AS wind_max_kmh,
                   count(precipitation)              AS n_hours,
                   '{fetched}'                       AS fetched_at_utc
            FROM hourly
            GROUP BY ALL
            HAVING count(precipitation) > 0
            ORDER BY district_id, date_utc
        """)
        n = con.execute("SELECT count(*) FROM forecast_live").fetchone()[0]
    print(f"forecast_live: {n} rows (fetched {fetched})")
    return n


def parse_raw(path, query: str, ids_by_coord: dict) -> pd.DataFrame:
    """One raw response -> hourly rows (district_id, time_utc, lead_days, variable values)."""
    q = parse_qs(urlparse(query).query)
    lats = q["latitude"][0].split(",")
    lons = q["longitude"][0].split(",")
    payload = json.loads(path.read_bytes())
    if isinstance(payload, dict):
        payload = [payload]
    frames = []
    for lat, lon, loc in zip(lats, lons, payload):
        h = loc["hourly"]
        for lead in LEADS:
            df = pd.DataFrame({v: h[f"{v}_previous_day{lead}"] for v in VARIABLES})
            df["time_utc"] = pd.to_datetime(h["time"])
            df["lead_days"] = lead
            df["district_id"] = ids_by_coord[(lat, lon)]
            frames.append(df)
    return pd.concat(frames)


def build(db_path=DB_PATH) -> int:
    d = districts(db_path)
    ids = {(f"{r.centroid_lat:.4f}", f"{r.centroid_lon:.4f}"): r.district_id for r in d.itertuples()}
    rows = [r for r in manifest.read_manifest() if r["source"] == SOURCE]
    if not rows:
        raise SystemExit("no forecasts in manifest; run `python -m src.forecasts fetch`")
    # newest fetch wins when chunks overlap (e.g. a partial current month re-fetched later)
    rows.sort(key=lambda r: r["fetched_at_utc"])
    hourly = pd.concat([parse_raw(ROOT / r["path"], r["query"], ids) for r in rows])
    hourly = hourly.drop_duplicates(["district_id", "time_utc", "lead_days"], keep="last")

    with duckdb.connect(str(db_path)) as con:
        con.execute("""
            CREATE OR REPLACE TABLE forecast_day AS
            SELECT district_id,
                   CAST(time_utc AS DATE)            AS date_utc,
                   lead_days,
                   sum(precipitation)                AS precip_sum_mm,
                   max(precipitation)                AS precip_max_hourly_mm,
                   avg(relative_humidity_2m)         AS rh_mean_pct,
                   avg(pressure_msl)                 AS pressure_mean_hpa,
                   avg(cloud_cover)                  AS cloud_mean_pct,
                   max(wind_speed_10m)               AS wind_max_kmh,
                   count(precipitation)              AS n_hours
            FROM hourly
            GROUP BY ALL
            HAVING count(precipitation) > 0
            ORDER BY district_id, date_utc, lead_days
        """)
        n = con.execute("SELECT count(*) FROM forecast_day").fetchone()[0]
    print(f"forecast_day: {n} rows")
    return n


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["fetch", "build", "live", "build-live"])
    p.add_argument("--start", type=date.fromisoformat, default=FORECAST_START)
    p.add_argument("--end", type=date.fromisoformat,
                   default=datetime.now(timezone.utc).date() - timedelta(days=1))
    p.add_argument("--budget", type=float, default=9000)
    a = p.parse_args()
    {"fetch": lambda: fetch(a.start, a.end, a.budget), "build": build,
     "live": fetch_live, "build-live": build_live}[a.cmd]()
    sys.exit(0)
