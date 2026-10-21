"""Model B: next week's % price change per item and city (task B4), train/validation only.

    python -m src.model_b train   # baseline vs quantile GBM on validation -> docs/model_b_validation.json

Declared (DATASET_DECLARATION.md): target = next week's % change in the city average price;
baseline = no change; metric = MAE of the % change plus 80% interval coverage, split into
staples, perishables and fuel. Train Jan 2023 to 30 Jun 2025, validate 1 Jul to 31 Dec 2025;
test rows are never loaded (src.model_a.split guards the test split).

Features for week t (all known when week t's prices are published):
- 1, 4 and 12-week % changes of the item's city average; the same item-city change one year ago;
- item group; national average petrol + diesel 1-week % change;
- rain anomaly: the city's district mean rain over the 7 UTC days ending the day before
  week t ends, minus that district's 2015-2023 mean for those calendar days (NULL without IMERG).
Prices flagged by the quality rules are kept; prices PBS did not collect are NULL, never filled.
"""
import json
import sys
import time

import duckdb
import numpy as np
import pandas as pd

from src.config import DB_PATH, ROOT
from src.model_a import SEED, _peak_mb, log_experiment, split

QUANTILES = (0.1, 0.5, 0.9)
GROUPS = {
    "staples": {1, 2, 3, 4, 10, 12, 13, 14, 15, 17, 18, 19, 20, 24, 25, 26, 27, 29},
    "perishables": {5, 6, 7, 8, 9, 11, 16, 21, 22, 23, 28},
    "fuel": {41, 42, 43, 47, 48, 49},
}
FEATURES = ["chg_1w", "chg_4w", "chg_12w", "chg_next_last_year", "group_code", "fuel_chg_1w",
            "rain_anom_7d_mm", "item_no"]


def group_of(item_no: int) -> str:
    return next((g for g, items in GROUPS.items() if item_no in items), "other")


def build_table(con) -> pd.DataFrame:
    p = con.execute("SELECT city, item_no, week_end, avg_pkr FROM spi_price ORDER BY city, item_no, week_end").df()
    p["week_end"] = pd.to_datetime(p.week_end)
    g = p.groupby(["city", "item_no"]).avg_pkr
    pct = lambda k: (p.avg_pkr / g.shift(k) - 1) * 100  # noqa: E731
    p["chg_1w"], p["chg_4w"], p["chg_12w"] = pct(1), pct(4), pct(12)
    p["target"] = (g.shift(-1) / p.avg_pkr - 1) * 100
    gap = p.groupby(["city", "item_no"]).week_end.shift(-1) - p.week_end
    p.loc[gap != pd.Timedelta(days=7), "target"] = np.nan  # next published week must be the next week
    p["chg_next_last_year"] = p.groupby(["city", "item_no"]).target.shift(52)
    p["group"] = p.item_no.map(group_of)
    p["group_code"] = p.group.map({"staples": 0, "perishables": 1, "fuel": 2, "other": 3})
    fuel = (p[p.item_no.isin([47, 48])].groupby("week_end").avg_pkr.mean().sort_index())
    p["fuel_chg_1w"] = p.week_end.map((fuel / fuel.shift(1) - 1) * 100)

    have = {t for (t,) in con.execute("SHOW TABLES").fetchall()}
    if {"rain_district_day", "districts"} <= have:
        rain = con.execute("""
            WITH city AS (SELECT DISTINCT s.city, d.district_id FROM spi_price s
                          JOIN districts d ON lower(d.name) = lower(s.city)
                             OR (s.city = 'Karachi' AND d.name = 'South Karachi')
                             OR (s.city = 'D.I. Khan' AND d.name = 'D. I. Khan')),
            weeks AS (SELECT DISTINCT week_end FROM spi_price),
            clim AS (SELECT district_id, dayofyear(date_utc) AS doy, avg(mean_mm) AS m FROM rain_district_day
                     WHERE year(date_utc) BETWEEN 2015 AND 2023 GROUP BY ALL)
            SELECT c.city, w.week_end, avg(r.mean_mm - k.m) * 7 AS rain_anom_7d_mm
            FROM city c, weeks w
            JOIN rain_district_day r ON r.district_id = c.district_id
                 AND r.date_utc BETWEEN w.week_end - INTERVAL 7 DAY AND w.week_end - INTERVAL 1 DAY
            JOIN clim k ON k.district_id = r.district_id AND k.doy = dayofyear(r.date_utc)
            GROUP BY ALL""").df()
        rain["week_end"] = pd.to_datetime(rain.week_end)
        p = p.merge(rain, on=["city", "week_end"], how="left")
    else:
        p["rain_anom_7d_mm"] = np.nan
    p["date_utc"] = p.week_end.dt.date
    p["label"] = p.target  # split() keeps rows whose label is not NULL
    return p


def interval_stats(y, lo, hi) -> float:
    return float(np.mean((y >= lo) & (y <= hi)))


def train(db_path=DB_PATH) -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor

    with duckdb.connect(str(db_path), read_only=True) as con:
        df = build_table(con)
    tr, val = split(df, "train"), split(df, "validation")
    tr = tr[tr.chg_1w.notna()]
    val = val[val.chg_1w.notna()]
    used = [f for f in FEATURES if tr[f].notna().any()]
    t0 = time.perf_counter()
    preds = {}
    for q in QUANTILES:
        m = HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=300, learning_rate=0.05,
                                          max_leaf_nodes=31, min_samples_leaf=200, random_state=SEED,
                                          categorical_features=[used.index("group_code")])
        preds[q] = m.fit(tr[used], tr.target).predict(val[used])
    secs = time.perf_counter() - t0
    y = val.target.to_numpy()
    report = {"n_train": len(tr), "n_validation": len(val), "features": used, "by_group": {}}
    for name, mask in [("all", np.ones(len(val), bool))] + [(g, (val.group == g).to_numpy())
                                                          for g in ("staples", "perishables", "fuel", "other")]:
        if not mask.any():
            continue
        report["by_group"][name] = {
            "n": int(mask.sum()),
            "mae_no_change": float(np.mean(np.abs(y[mask]))),
            "mae_gbm_median": float(np.mean(np.abs(y[mask] - preds[0.5][mask]))),
            "coverage_80": interval_stats(y[mask], preds[0.1][mask], preds[0.9][mask]),
        }
    a = report["by_group"]["all"]
    kept = a["mae_gbm_median"] < a["mae_no_change"]
    report["beats_no_change_on_validation"] = kept
    log_experiment("B4 baseline: no change", "-", f"val MAE {a['mae_no_change']:.3f} pp", 0, _peak_mb(), "baseline")
    log_experiment("B4 quantile GBM (10/50/90)", f"no change {a['mae_no_change']:.3f} pp",
                   f"val MAE {a['mae_gbm_median']:.3f} pp, 80% coverage {a['coverage_80']:.2f}", secs, _peak_mb(),
                   "kept" if kept else "rejected")
    (ROOT / "docs" / "model_b_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    {"train": train}[sys.argv[1]]()
