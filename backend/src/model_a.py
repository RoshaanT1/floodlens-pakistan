"""Model A: district heavy-rain risk 1 to 3 days ahead (tasks A1, A2, A3, A4).

    python -m src.model_a features   # A1: DuckDB `features_a`
    python -m src.model_a train      # A2 + A3 on train/validation, writes the A4 artifact

Target and baseline are the declared ones (labels / baseline_climatology from src.labels).
Splits are fixed in src.config. Test rows (1 Jan to 30 Sep 2026) are never loaded here:
`split()` refuses them unless the one-off test run sets FLOODLENS_RUN_TEST=1 (task E3,
done by the team, not by this module's commands).

Leakage rules (DATASET_DECLARATION.md):
- forecast inputs are only the `_previous_day1..3` archive values (forecast_day.lead_days);
- a day's hourly lead-N values come from runs issued between (D-N) 00:00 and 23:00 UTC, so
  the *earliest* issue time, (D-N) 00:00 UTC, is the one observed rain must precede;
- observed rain comes only from UTC days that ended at least 14 h before that issue time
  (IMERG Late latency). `last_observed_day` computes this; tests/test_model_a.py proves it.
"""
import json
import resource
import sys
import time
from datetime import date, datetime, timedelta, timezone

import duckdb
import joblib
import numpy as np
import pandas as pd

from src.config import DB_PATH, ROOT, TEST_START, TRAIN_END, VALID_END, VALID_START

LEADS = (1, 2, 3)
OBS_LAG = timedelta(hours=14)
SEED = 20251231
N_BOOT = 1000
MODEL_DIR = ROOT / "models" / "model_a"
OPT_LOG = ROOT / "docs" / "optimisation_log.md"
STAGE_LABEL = "validation-stage model (fitted on train, calibrated on validation; not test-evaluated)"

FEATURES = [
    "lead_days", "precip_sum_mm", "precip_max_hourly_mm", "rh_mean_pct", "pressure_mean_hpa",
    "cloud_mean_pct", "wind_max_kmh", "fc_over_threshold", "log_threshold_mm", "clim_p",
    "month_sin", "month_cos", "obs_wettest_mm", "obs_mean_3d_mm", "obs_mean_7d_mm",
    "elevation_m", "coastal", "flood_prone",  # D7; NULL when district_attributes is missing
]


# --------------------------------------------------------------------------- A1: features

def issue_time(target: date, lead: int) -> datetime:
    """Earliest issue time among the hourly lead-`lead` values for UTC day `target`."""
    d = target - timedelta(days=lead)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def last_observed_day(target: date, lead: int) -> date:
    """Newest UTC day whose end is at least 14 h before the forecast was issued."""
    latest_end = issue_time(target, lead) - OBS_LAG
    end_day = latest_end.date()  # a day ending at or before latest_end
    if datetime(end_day.year, end_day.month, end_day.day, tzinfo=timezone.utc) > latest_end:
        end_day -= timedelta(days=1)
    return end_day - timedelta(days=1)  # the day that ends at 00:00 of end_day


def obs_gap_days(lead: int) -> int:
    """target - last_observed_day, which does not depend on the target date."""
    gaps = {(t - last_observed_day(t, lead)).days for t in (date(2024, 1, 1), date(2025, 7, 15))}
    assert len(gaps) == 1
    return gaps.pop()


ASSEMBLE = """
    WITH fc AS ({forecast_sql}),
    obs AS (
        SELECT district_id, date_utc, wettest_mm, mean_mm FROM rain_district_day
    )
    SELECT f.district_id || '_' || CAST(f.date_utc AS VARCHAR) || '_L' || CAST(f.lead_days AS VARCHAR) AS row_id,
           f.district_id, f.date_utc, f.lead_days,
           f.precip_sum_mm, f.precip_max_hourly_mm, f.rh_mean_pct, f.pressure_mean_hpa,
           f.cloud_mean_pct, f.wind_max_kmh,
           f.precip_sum_mm / t.threshold_mm                 AS fc_over_threshold,
           ln(t.threshold_mm)                               AS log_threshold_mm,
           t.threshold_mm,
           b.p_exceed                                       AS clim_p,
           sin(2 * pi() * month(f.date_utc) / 12)           AS month_sin,
           cos(2 * pi() * month(f.date_utc) / 12)           AS month_cos,
           f.date_utc - f.gap                               AS obs_last_day,
           (SELECT o.wettest_mm FROM obs o WHERE o.district_id = f.district_id
              AND o.date_utc = f.date_utc - f.gap)          AS obs_wettest_mm,
           (SELECT avg(o.mean_mm) FROM obs o WHERE o.district_id = f.district_id
              AND o.date_utc BETWEEN f.date_utc - f.gap - 2 AND f.date_utc - f.gap) AS obs_mean_3d_mm,
           (SELECT avg(o.mean_mm) FROM obs o WHERE o.district_id = f.district_id
              AND o.date_utc BETWEEN f.date_utc - f.gap - 6 AND f.date_utc - f.gap) AS obs_mean_7d_mm
           {attr_cols}
           {label_cols}
    FROM fc f
    JOIN thresholds t USING (district_id)
    LEFT JOIN baseline_climatology b ON b.district_id = f.district_id AND b.month = month(f.date_utc)
    {attr_join}
    {label_join}
    ORDER BY row_id
"""


def _attr_sql(con) -> dict:
    have = {t for (t,) in con.execute("SHOW TABLES").fetchall()}
    if "district_attributes" in have:
        return {"attr_cols": ", a.elevation_m, a.coastal::INTEGER AS coastal, a.flood_prone::INTEGER AS flood_prone",
                "attr_join": "LEFT JOIN district_attributes a ON a.district_id = f.district_id"}
    return {"attr_cols": ", NULL::DOUBLE AS elevation_m, NULL::INTEGER AS coastal, NULL::INTEGER AS flood_prone",
            "attr_join": ""}


def _gap_case(lead_col: str) -> str:
    return "CASE " + " ".join(f"WHEN {lead_col} = {n} THEN {obs_gap_days(n)}" for n in LEADS) + " END"


def build_features(con) -> pd.DataFrame:
    """Archived forecasts + labels -> one row per district, UTC day and lead."""
    forecast_sql = f"""SELECT *, {_gap_case('lead_days')} AS gap FROM forecast_day
                       WHERE lead_days IN {LEADS}"""
    sql = ASSEMBLE.format(
        forecast_sql=forecast_sql, **_attr_sql(con),
        label_cols=", l.label, l.low_confidence",
        label_join="LEFT JOIN labels l ON l.district_id = f.district_id AND l.date_utc = f.date_utc")
    return con.execute(sql).df()


def build_live_features(con) -> pd.DataFrame:
    """Live forecast (days_ahead 1..3) -> the same features, no labels."""
    forecast_sql = f"""SELECT *, days_ahead AS lead_days, {_gap_case('days_ahead')} AS gap
                       FROM forecast_live WHERE days_ahead IN {LEADS}"""
    return con.execute(ASSEMBLE.format(forecast_sql=forecast_sql, label_cols="", label_join="",
                                       **_attr_sql(con))).df()


def features(db_path=DB_PATH) -> int:
    with duckdb.connect(str(db_path)) as con:
        df = build_features(con)
        con.execute("CREATE OR REPLACE TABLE features_a AS SELECT * FROM df ORDER BY row_id")
    print(f"features_a: {len(df)} rows")
    return len(df)


# --------------------------------------------------------------------------- splits

def split(df: pd.DataFrame, name: str) -> pd.DataFrame:
    d = pd.to_datetime(df["date_utc"]).dt.date
    if name == "train":
        out = df[d <= TRAIN_END]
    elif name == "validation":
        out = df[(d >= VALID_START) & (d <= VALID_END)]
    elif name == "test":
        import os
        if os.environ.get("FLOODLENS_RUN_TEST") != "1":
            raise PermissionError("test split is run once by the team (E3); set FLOODLENS_RUN_TEST=1")
        out = df[d >= TEST_START]
    else:
        raise ValueError(name)
    return out[out["label"].notna()]


# --------------------------------------------------------------------------- A2: scoring

def brier(y, p) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean((p - y) ** 2))


def brier_ci(y, p, dates, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Brier with a 95% bootstrap interval, resampling whole days (districts rain together)."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    codes, uniq = pd.factorize(pd.Series(dates))
    sse = np.bincount(codes, weights=(p - y) ** 2)
    cnt = np.bincount(codes)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    boot = sse[draws].sum(1) / cnt[draws].sum(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"brier": brier(y, p), "lo": float(lo), "hi": float(hi), "n": int(len(y))}


def baselines(df: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "climatology": df["clim_p"].fillna(0).to_numpy(),
        "raw_forecast_cut": (df["precip_sum_mm"] > df["threshold_mm"]).astype(float).to_numpy(),
    }


def score_by_lead(df: pd.DataFrame, p: np.ndarray) -> dict:
    out = {}
    for lead in LEADS:
        m = (df["lead_days"] == lead).to_numpy()
        out[f"{24 * lead}h"] = brier_ci(df.loc[m, "label"], p[m], df.loc[m, "date_utc"])
    return out


# --------------------------------------------------------------------------- A3: models

def make_model(kind: str):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if kind == "logreg":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(C=1.0, max_iter=2000, random_state=SEED))
    if kind == "gbm":
        return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                              min_samples_leaf=100, l2_regularization=1.0,
                                              early_stopping=False, random_state=SEED)
    raise ValueError(kind)


class Calibrated:
    """Fitted model + Platt scaling on the logit of its validation-set probabilities."""

    def __init__(self, model, features: list[str], a: float = 1.0, b: float = 0.0):
        self.model, self.features, self.a, self.b = model, features, a, b

    @staticmethod
    def _logit(p):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return np.log(p / (1 - p))

    def raw(self, X):
        return self.model.predict_proba(X[self.features])[:, 1]

    def fit_calibration(self, X, y):
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(C=1e6, max_iter=1000).fit(self._logit(self.raw(X)).reshape(-1, 1), y)
        self.a, self.b = float(lr.coef_[0, 0]), float(lr.intercept_[0])
        return self

    def predict(self, X):
        z = self.a * self._logit(self.raw(X)) + self.b
        return 1 / (1 + np.exp(-z))


def crossfit_calibrated(model, features: list[str], val: pd.DataFrame) -> np.ndarray:
    """Honest calibrated validation probabilities: calibrate on odd ISO weeks, score even, and swap."""
    week = pd.to_datetime(val["date_utc"]).dt.isocalendar().week.to_numpy() % 2
    p = np.empty(len(val))
    for k in (0, 1):
        fit, score = week != k, week == k
        c = Calibrated(model, features).fit_calibration(val[fit], val.loc[fit, "label"].astype(int))
        p[score] = c.predict(val[score])
    return p


def _peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def log_experiment(change: str, before: str, after: str, runtime_s: float, mem_mb: float, kept: str) -> None:
    row = (f"| {date.today().isoformat()} | Claude Code (overnight) | {change} | {before} | {after} | "
           f"{runtime_s:.1f} s | {mem_mb:.0f} MB peak RSS | {kept} |\n")
    with open(OPT_LOG, "a") as f:
        f.write(row)


def fmt(s: dict) -> str:
    return f"{s['brier']:.4f} [{s['lo']:.4f}, {s['hi']:.4f}]"


def train(db_path=DB_PATH) -> dict:
    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute("SELECT * FROM features_a").df()
    tr, val = split(df, "train"), split(df, "validation")
    if tr.empty or val.empty or tr["label"].nunique() < 2:
        raise SystemExit(f"not enough labelled rows (train {len(tr)}, validation {len(val)}); "
                         "needs IMERG through Dec 2025 and forecasts through Dec 2025")
    report = {"n_train": len(tr), "n_validation": len(val),
              "positive_rate_train": float(tr["label"].mean()),
              "positive_rate_validation": float(val["label"].mean()), "baselines": {}, "models": {}}

    for name, p in baselines(val).items():
        report["baselines"][name] = score_by_lead(val, p)
    clim24 = report["baselines"]["climatology"]["24h"]
    log_experiment("A2 baseline: district-by-month climatology", "-", f"val Brier 24h {fmt(clim24)}",
                   0, _peak_mb(), "baseline")
    raw24 = report["baselines"]["raw_forecast_cut"]["24h"]
    log_experiment("A2 baseline: raw forecast cut at threshold", "-", f"val Brier 24h {fmt(raw24)}",
                   0, _peak_mb(), "baseline")

    used = [f for f in FEATURES if tr[f].notna().any()]  # e.g. D7 columns before attributes exist
    report["features"] = used
    best, best_score = None, clim24["brier"]
    previous = f"climatology {clim24['brier']:.4f}"
    for kind in ("logreg", "gbm"):
        t0 = time.perf_counter()
        model = make_model(kind).fit(tr[used], tr["label"].astype(int))
        p_val = crossfit_calibrated(model, used, val)
        secs = time.perf_counter() - t0
        scores = score_by_lead(val, p_val)
        report["models"][kind] = {"validation": scores, "train_seconds": secs}
        s24 = scores["24h"]
        kept = s24["brier"] < best_score
        log_experiment(f"A3 {kind}, Platt-calibrated on validation (cross-fitted by ISO week)",
                       previous, f"val Brier 24h {fmt(s24)}", secs, _peak_mb(),
                       "kept" if kept else "rejected")
        if kept:
            best, best_score, previous = (kind, model), s24["brier"], f"{kind} {s24['brier']:.4f}"

    report["chosen"] = best[0] if best else None
    report["beats_climatology_on_validation"] = best is not None
    if best:
        kind, model = best
        final = Calibrated(model, used).fit_calibration(val, val["label"].astype(int))
        report["artifact"] = save_artifact(final, kind, report)
    else:
        print("no model beat climatology on validation; no artifact written, live view keeps climatology")
    (ROOT / "docs" / "model_a_validation.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "models"}, indent=2, default=str))
    return report


# --------------------------------------------------------------------------- A4: artifact

def save_artifact(model: Calibrated, kind: str, report: dict) -> str:
    version = f"{datetime.now(timezone.utc):%Y%m%dT%H%MZ}_{kind}"
    out = MODEL_DIR / version
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out / "model.joblib")
    meta = {"version": version, "kind": kind, "features": model.features, "label": STAGE_LABEL,
            "train_end": TRAIN_END.isoformat(), "validation": [VALID_START.isoformat(), VALID_END.isoformat()],
            "validation_scores": report["models"][kind]["validation"]}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    (MODEL_DIR / "current.json").write_text(json.dumps({"version": version}))
    print(f"artifact {version} is now current")
    return version


def load_current():
    """(model, meta) for the current artifact, or None. The flow only ever calls this."""
    pointer = MODEL_DIR / "current.json"
    if not pointer.exists():
        return None
    version = json.loads(pointer.read_text())["version"]
    meta = json.loads((MODEL_DIR / version / "meta.json").read_text())
    return joblib.load(MODEL_DIR / version / "model.joblib"), meta


def score_live(db_path=DB_PATH) -> int:
    """Current artifact x live forecast -> `risk_live`. No artifact or no inputs: no table."""
    loaded = load_current()
    with duckdb.connect(str(db_path)) as con:
        con.execute("DROP TABLE IF EXISTS risk_live")
        have = {t for (t,) in con.execute("SHOW TABLES").fetchall()}
        need = {"forecast_live", "rain_district_day", "thresholds", "baseline_climatology"}
        if loaded is None or not need <= have:
            why = "no model artifact yet" if loaded is None else f"missing {sorted(need - have)}"
            print(f"skip risk_live: {why}")
            return 0
        model, meta = loaded
        X = build_live_features(con)
        X["p_heavy_rain"] = model.predict(X)
        X["model_version"] = meta["version"]
        X["model_label"] = meta["label"]
        risk = X[["row_id", "district_id", "date_utc", "lead_days", "p_heavy_rain",
                  "model_version", "model_label"]]
        con.execute("CREATE TABLE risk_live AS SELECT * FROM risk ORDER BY row_id")
    print(f"risk_live: {len(risk)} rows from {meta['version']}")
    return len(risk)


if __name__ == "__main__":
    {"features": features, "train": train, "score": score_live}[sys.argv[1]]()
