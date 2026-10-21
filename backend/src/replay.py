"""Replay mode (task P6): what the current model would have said for 10-20 Aug 2025.

    python -m src.replay      # -> data/replay.duckdb `risk_replay` + frontend/public/data/replay.json

Clearly labelled as a replay and kept in its own database and file; it never enters the
live tables, status.json or the Prefect run history. Each row uses only what was known when
that forecast was issued: `features_a` rows are already built under the leakage rules (forecast
issued 1-3 days ahead, observed rain from days that ended >= 14 h before issue).
The window is inside the validation period, which the model was calibrated on, so this is a
demonstration, not an independent test.
"""
import json
import sys
from datetime import date

import duckdb

from src import model_a
from src.config import DATA, DB_PATH, ROOT

WINDOW = (date(2025, 8, 10), date(2025, 8, 20))
REPLAY_DB = DATA / "replay.duckdb"
OUT = ROOT.parent / "frontend" / "public" / "data" / "replay.json"
LABEL = "REPLAY of 10-20 Aug 2025 (historical; validation period; not live, not a test result)"


def build(db_path=DB_PATH) -> int:
    loaded = model_a.load_current()
    if loaded is None:
        raise SystemExit("no Model A artifact; run `python -m src.model_a train` first")
    model, meta = loaded
    with duckdb.connect(str(db_path), read_only=True) as con:
        X = con.execute("""
            SELECT f.*, d.name, d.province FROM features_a f JOIN districts d USING (district_id)
            WHERE f.date_utc BETWEEN ? AND ?""", list(WINDOW)).df()
    if X.empty:
        raise SystemExit("no features for the replay window (needs forecasts and IMERG for Aug 2025)")
    X["p_heavy_rain"] = model.predict(X)
    X["model_version"] = meta["version"]
    X["replay_label"] = LABEL
    cols = ["row_id", "district_id", "name", "province", "date_utc", "lead_days", "p_heavy_rain",
            "clim_p", "precip_sum_mm", "threshold_mm", "label", "model_version", "replay_label"]
    rows = X[cols].sort_values(["date_utc", "lead_days", "district_id"])
    with duckdb.connect(str(REPLAY_DB)) as con:
        con.execute("CREATE OR REPLACE TABLE risk_replay AS SELECT * FROM rows")
    payload = {"label": LABEL, "model_version": meta["version"], "window": [str(w) for w in WINDOW],
               "rows": json.loads(rows.assign(date_utc=rows.date_utc.astype(str)).to_json(orient="records"))}
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")))
    tmp.replace(OUT)
    print(f"replay: {len(rows)} rows ({rows.date_utc.nunique()} days) -> {REPLAY_DB.name}, {OUT}")
    return len(rows)


if __name__ == "__main__":
    build()
    sys.exit(0)
