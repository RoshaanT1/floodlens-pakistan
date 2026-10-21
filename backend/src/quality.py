"""Data Quality Agent (tasks Q1, Q2).

Q1: every rule is a pandera check (schema, ranges, missing values, duplicates, timeliness).
Q2: every failed rule becomes a decision, fix, fill or flag, logged in `quality_log` with
rule, reason, row count and decision time. Decisions live in docs/quality_decisions.json
(tracked in git). A rule seen for the first time gets its default decision, stamped and
saved; later rebuilds replay the cached decision and timestamp, so two rebuilds of the
same snapshot give identical tables and logs.

Actions:
  fix  - correct the value in place (e.g. clip a physical impossibility) or drop a duplicate
  fill - replace a missing value with a documented substitute
  flag - keep the row unchanged and add the rule name to its `quality_flags`
Rows are never silently dropped except exact-key duplicates (fix).
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import duckdb
import pandas as pd
import pandera.pandas as pa

from src import manifest
from src.config import DB_PATH, PAK_BBOX, ROOT

DECISIONS = ROOT / "docs" / "quality_decisions.json"
LOG_COLUMNS = ["table_name", "rule", "action", "reason", "n_rows", "decided_at_utc"]


@dataclass
class Rule:
    name: str
    table: str
    schema: pa.DataFrameSchema           # one check; failing rows are the rule's rows
    action: str                          # default decision: fix | fill | flag
    reason: str
    fix: Callable[[pd.DataFrame, pd.Index], pd.DataFrame] | None = None


def col(column, check=None, nullable=True, name=None):
    """One-column schema; `check` is a pandera Check or a vectorised function."""
    if check is None:
        checks = []
    else:
        checks = [check if isinstance(check, pa.Check) else pa.Check(check, name=name)]
    return pa.DataFrameSchema({column: pa.Column(checks=checks, nullable=nullable)}, coerce=False)


def clip(column, lo, hi):
    def f(df, idx):
        df.loc[idx, column] = df.loc[idx, column].clip(lo, hi)
        return df
    return f


def drop_rows(df, idx):
    return df.drop(index=idx)


lat_min, lat_max, lon_min, lon_max = PAK_BBOX
FORECAST_VALUES = ["precip_sum_mm", "rh_mean_pct", "pressure_mean_hpa", "cloud_mean_pct", "wind_max_kmh"]

RULES = [
    # districts
    Rule("district_id_unique", "districts", pa.DataFrameSchema(unique=["district_id"]), "fix",
         "duplicate district id; keep the first", drop_rows),
    Rule("district_centroid_in_pakistan", "districts",
         pa.DataFrameSchema({"centroid_lat": pa.Column(checks=pa.Check.in_range(lat_min, lat_max)),
                             "centroid_lon": pa.Column(checks=pa.Check.in_range(lon_min, lon_max))}),
         "flag", "centroid outside Pakistan bounding box"),

    # forecasts
    Rule("forecast_key_unique", "forecast_day",
         pa.DataFrameSchema(unique=["district_id", "date_utc", "lead_days"]), "fix",
         "duplicate district/day/lead; keep the first", drop_rows),
    *[Rule(f"forecast_{c}_present", "forecast_day", col(c, nullable=False), "flag",
           f"{c} missing; left NULL for the model to handle, never filled with a guess")
      for c in FORECAST_VALUES],
    Rule("forecast_full_day", "forecast_day", col("n_hours", lambda s: s == 24, name="full_day"), "flag",
         "fewer than 24 hourly values in the UTC day; daily sum may be low"),
    Rule("forecast_precip_nonnegative", "forecast_day", col("precip_sum_mm", lambda s: s >= 0, name="nonneg"),
         "fix", "negative rain is impossible; clip to 0", clip("precip_sum_mm", 0, None)),
    Rule("forecast_precip_plausible", "forecast_day",
         col("precip_sum_mm", lambda s: s <= 500, name="plausible"), "flag",
         "over 500 mm/day forecast; kept but flagged for review"),
    Rule("forecast_rh_range", "forecast_day", col("rh_mean_pct", pa.Check.in_range(0, 100)),
         "fix", "humidity outside 0-100%; clip", clip("rh_mean_pct", 0, 100)),
    Rule("forecast_cloud_range", "forecast_day",
         col("cloud_mean_pct", pa.Check.in_range(0, 100)),
         "fix", "cloud cover outside 0-100%; clip", clip("cloud_mean_pct", 0, 100)),
    Rule("forecast_pressure_range", "forecast_day",
         col("pressure_mean_hpa", pa.Check.in_range(870, 1085)),
         "flag", "sea-level pressure outside recorded extremes"),
    Rule("forecast_wind_range", "forecast_day",
         col("wind_max_kmh", pa.Check.in_range(0, 250)),
         "flag", "wind outside 0-250 km/h"),

    # district rain (IMERG)
    Rule("rain_key_unique", "rain_district_day", pa.DataFrameSchema(unique=["row_id"]), "fix",
         "duplicate district/day; keep the first", drop_rows),
    Rule("rain_present", "rain_district_day", col("wettest_mm", nullable=False), "flag",
         "no valid IMERG pixel in the district; label stays NULL, never read as zero"),
    Rule("rain_no_fill_pixels", "rain_district_day",
         col("n_fill_pixels", lambda s: s == 0, name="no_fill"), "flag",
         "some pixels were -9999.9 fill; excluded from max and mean"),
    Rule("rain_sample_count", "rain_district_day",
         col("low_confidence", lambda s: ~s.fillna(False).astype(bool), name="enough_samples"), "flag",
         "fewer than 24 of 48 half-hourly retrievals; low confidence"),
    Rule("rain_nonnegative", "rain_district_day", col("wettest_mm", lambda s: s >= 0, name="nonneg"),
         "fix", "negative rain is impossible; clip to 0", clip("wettest_mm", 0, None)),
    Rule("rain_not_revised", "rain_district_day",
         col("revised", lambda s: ~s.fillna(False).astype(bool), name="not_revised"), "flag",
         "NASA re-issued this day; the newest value is used and the earlier one kept in revised_from_mm"),
    Rule("rain_max_ge_mean", "rain_district_day",
         pa.DataFrameSchema(checks=pa.Check(lambda d: d.wettest_mm.isna() | (d.wettest_mm >= d.mean_mm - 1e-9),
                                            name="max_ge_mean")),
         "flag", "wettest pixel below district mean; aggregation error"),
]

# timeliness: newest data day vs the snapshot's own fetch time (not the wall clock, so
# rebuilds of the same snapshot agree)
TIMELINESS = {
    "forecast_day": ("open_meteo_previous_runs", "date_utc", timedelta(days=2)),
    "rain_district_day": ("imerg_late_daily", "date_utc", timedelta(days=3)),
}


def failing_index(rule: Rule, df: pd.DataFrame) -> pd.Index:
    try:
        rule.schema.validate(df, lazy=True)
        return pd.Index([])
    except pa.errors.SchemaErrors as e:
        idx = e.failure_cases["index"].dropna().unique()
        if rule.action == "fix" and rule.fix is drop_rows:
            # for duplicates keep the first occurrence
            dup_cols = rule.schema.unique
            idx = df.index[df.duplicated(subset=dup_cols, keep="first")]
        return pd.Index(idx)


def load_decisions() -> dict:
    return json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}


def save_decisions(d: dict) -> None:
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    DECISIONS.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")


def decide(decisions: dict, rule: Rule) -> dict:
    """Replay the cached decision, or record the default one the first time a rule fires."""
    key = f"{rule.table}.{rule.name}"
    if key not in decisions:
        decisions[key] = {"action": rule.action, "reason": rule.reason,
                          "decided_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    return decisions[key]


def check_table(con, table: str, decisions: dict) -> list[dict]:
    types = {name: typ for name, typ, *_ in con.execute(f"DESCRIBE {table}").fetchall()
             if name != "quality_flags"}
    df = con.execute(f"SELECT * FROM {table}").df()
    df["quality_flags"] = ""
    log = []
    for rule in [r for r in RULES if r.table == table]:
        idx = failing_index(rule, df)
        if len(idx) == 0:
            continue
        d = decide(decisions, rule)
        if d["action"] == "flag":
            df.loc[idx, "quality_flags"] += rule.name + ";"
        elif rule.fix is not None:
            df = rule.fix(df, idx)
        log.append({"table_name": table, "rule": rule.name, "action": d["action"], "reason": d["reason"],
                    "n_rows": len(idx), "decided_at_utc": d["decided_at_utc"]})

    if table in TIMELINESS:
        source, column, max_lag = TIMELINESS[table]
        row = manifest.latest(source)
        if row is not None:
            fetched = datetime.strptime(row["fetched_at_utc"], "%Y-%m-%dT%H:%M:%SZ").date()
            newest = pd.to_datetime(df[column]).max().date()
            if fetched - newest > max_lag:
                rule = Rule(f"{table}_timely", table, pa.DataFrameSchema(), "flag",
                            f"newest day more than {max_lag.days} days before the latest fetch; "
                            "dashboard shows the source as stale")
                d = decide(decisions, rule)
                log.append({"table_name": table, "rule": rule.name, "action": d["action"],
                            "reason": f"{d['reason']} (newest {newest}, fetched {fetched})",
                            "n_rows": 0, "decided_at_utc": d["decided_at_utc"]})

    # write back with the original column types (pandas turns DATE into a timestamp)
    casts = ", ".join(f'CAST("{c}" AS {t}) AS "{c}"' for c, t in types.items())
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT {casts}, quality_flags FROM df")
    return log


def run(tables: list[str], db_path=DB_PATH) -> list[dict]:
    """Check and fix each table once; returns its log rows (write them with `write_log`)."""
    decisions = load_decisions()
    with duckdb.connect(str(db_path)) as con:
        present = {t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
        log = []
        for t in tables:
            if t in present:
                log += check_table(con, t, decisions)
    save_decisions(decisions)
    return log


def write_log(log: list[dict], db_path=DB_PATH) -> pd.DataFrame:
    log_df = pd.DataFrame(log, columns=LOG_COLUMNS)
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE quality_log AS SELECT * FROM log_df ORDER BY table_name, rule")
    return log_df


def summary(log: pd.DataFrame) -> str:
    if log.empty:
        return "quality: all checks passed"
    lines = ["quality summary:"]
    for r in log.itertuples():
        lines.append(f"  {r.table_name:<18} {r.rule:<32} {r.action:<5} {r.n_rows:>7} rows  {r.reason}")
    return "\n".join(lines)
