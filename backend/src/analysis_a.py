"""Model A analysis on validation data only (tasks A5, A6, E2).

    python -m src.analysis_a ndma     # E2 half 1: districts named in NDMA monsoon 2025 sitreps
    python -m src.analysis_a report   # A5 + A6 + E2 -> docs/model_a_analysis.md (needs `model_a train`)

Reads `validation_predictions_a` (cross-fitted validation probabilities written by
src.model_a.train), never test-period rows.

Fixed choices for this analysis (made before any model results existed):
- groups: province; mountain vs plain, coastal vs inland, flood-prone vs not (D7);
  monsoon (Jun to Sep) vs dry months;
- "weakest group" = lowest Brier skill score against climatology at 24 h;
- a district is "flagged" on a day when the model's 24 h probability is >= FLAG_P;
- Buner case (A6): 14 and 15 Aug 2025, all three leads, hit = flagged on a day labelled 1.
"""
import json
import re
import sys
from collections import Counter

import duckdb
import numpy as np
import pandas as pd

from src import manifest
from src.config import DB_PATH, ROOT
from src.model_a import brier_ci

FLAG_P = 0.5
MONSOON = {6, 7, 8, 9}
OUT = ROOT / "docs" / "model_a_analysis.md"
NDMA_OUT = ROOT / "docs" / "ndma_districts_2025.csv"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def ndma_mentions(db_path=DB_PATH) -> pd.DataFrame:
    """How many NDMA monsoon 2025 sitreps name each district (whole-word, case-insensitive)."""
    from pypdf import PdfReader

    with duckdb.connect(str(db_path), read_only=True) as con:
        d = con.execute("SELECT district_id, name, province FROM districts").df()
        monsoon_2025 = {p for (p,) in con.execute(
            "SELECT path FROM documents WHERE source = 'ndma_sitrep' AND title ILIKE '%monsoon 2025%'").fetchall()}
    rows = [r for r in manifest.read_manifest() if r["source"] == "ndma_sitrep" and r["path"] in monsoon_2025]
    hits: Counter = Counter()
    for r in rows:
        try:
            text = " ".join(p.extract_text() or "" for p in PdfReader(ROOT / r["path"]).pages)
        except Exception as e:  # a broken PDF is logged and skipped, never guessed
            print(f"  could not read {r['path']}: {e}")
            continue
        text = re.sub(r"\s+", " ", text.lower())
        for name in d.name:
            if re.search(r"\b" + re.escape(name.lower()) + r"\b", text):
                hits[name] += 1
    d["n_sitreps_naming"] = d.name.map(lambda n: hits.get(n, 0))
    d["n_sitreps_read"] = len(rows)
    d.sort_values("n_sitreps_naming", ascending=False).to_csv(NDMA_OUT, index=False)
    print(f"{len(rows)} sitreps read; {int((d.n_sitreps_naming > 0).sum())} districts named at least once "
          f"-> {NDMA_OUT}")
    return d


def _skill(df: pd.DataFrame, col: str) -> dict:
    m = brier_ci(df.label, df[col], df.date_utc, n_boot=500)
    c = brier_ci(df.label, df.p_climatology, df.date_utc, n_boot=500)
    return {"n": m["n"], "positives": int(df.label.sum()), "brier": m["brier"], "lo": m["lo"], "hi": m["hi"],
            "clim": c["brier"], "bss": 1 - m["brier"] / c["brier"] if c["brier"] > 0 else np.nan}


def report(db_path=DB_PATH) -> str:
    with duckdb.connect(str(db_path), read_only=True) as con:
        v = con.execute("""
            SELECT v.*, d.name, d.province, a.mountain, a.coastal, a.flood_prone, f.precip_sum_mm,
                   f.threshold_mm, l.wettest_mm
            FROM validation_predictions_a v
            JOIN districts d USING (district_id)
            LEFT JOIN district_attributes a USING (district_id)
            LEFT JOIN features_a f USING (row_id)
            LEFT JOIN labels l ON l.district_id = v.district_id AND l.date_utc = v.date_utc""").df()
    meta = json.loads((ROOT / "docs" / "model_a_validation.json").read_text())
    chosen = meta.get("chosen") or "logreg"  # no winner: analyse logreg, the first candidate
    model_col = f"p_{chosen}"
    v24 = v[v.lead_days == 1].copy()
    v24["month"] = pd.to_datetime(v24.date_utc).dt.month
    v24["season"] = np.where(v24.month.isin(MONSOON), "monsoon (Jun-Sep)", "dry (Oct-Dec)")
    groupings = {
        "province": v24.province,
        "terrain": v24.mountain.map({True: "mountain", False: "plain"}),
        "coast": v24.coastal.map({True: "coastal", False: "inland"}),
        "2022 flooding": v24.flood_prone.map({True: "flood-prone", False: "not flood-prone"}),
        "season": v24.season,
    }
    lines = [f"# Model A analysis (validation, 1 Jul to 31 Dec 2025)\n",
             f"Model: `{chosen}` ({len(meta.get('features', []))} features), "
             f"probabilities cross-fitted on validation. Brier at 24 h with 95% day-block bootstrap "
             f"intervals; BSS = 1 - Brier / climatology Brier. Validation-stage results, not test results.\n",
             "## A5: groups\n", "| Grouping | Group | Rows | Events | Model Brier [95% CI] | Climatology Brier | BSS |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    worst = None
    for gname, g in groupings.items():
        for key, part in v24.groupby(g):
            s = _skill(part, model_col)
            lines.append(f"| {gname} | {key} | {s['n']} | {s['positives']} | {s['brier']:.4f} "
                         f"[{s['lo']:.4f}, {s['hi']:.4f}] | {s['clim']:.4f} | {s['bss']:+.3f} |")
            if s["positives"] >= 5 and (worst is None or s["bss"] < worst[2]):
                worst = (gname, key, s["bss"])
    if worst:
        lines.append(f"\n**Weakest group** (lowest BSS among groups with at least 5 events): "
                     f"{worst[0]} = {worst[1]}, BSS {worst[2]:+.3f}.\n")

    lines += ["## A6: Buner, 14 and 15 Aug 2025\n",
              f"Flag rule: probability >= {FLAG_P}. Hit = flagged on a day whose label is 1.\n",
              "| Day | Lead | Forecast rain (mm, centroid) | Threshold (mm) | Observed wettest pixel (mm) | Label "
              "| Model p | Climatology p | Outcome |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    b = v[(v.name == "Buner") & v.date_utc.astype(str).isin(["2025-08-14", "2025-08-15"])].sort_values(
        ["date_utc", "lead_days"])
    for r in b.itertuples():
        flagged = getattr(r, model_col) >= FLAG_P
        outcome = {(True, 1): "hit", (False, 1): "miss", (True, 0): "false alarm", (False, 0): "correct quiet"}[
            (bool(flagged), int(r.label))]
        lines.append(f"| {pd.Timestamp(r.date_utc).date()} | {r.lead_days} | {r.precip_sum_mm:.1f} | {r.threshold_mm:.1f} | "
                     f"{r.wettest_mm:.1f} | {int(r.label)} | {getattr(r, model_col):.3f} | {r.p_climatology:.3f} | {outcome} |")
    if b.empty:
        lines.append("| no Buner rows for these days (missing forecast or label) | | | | | | | | |")

    if NDMA_OUT.exists():
        nd = pd.read_csv(NDMA_OUT)
        named = set(nd.loc[nd.n_sitreps_naming > 0, "name"])
        mon = v24[v24.month.isin({7, 8, 9})]
        flagged = set(mon.loc[mon[model_col] >= FLAG_P, "name"])
        both, only_model, only_ndma = flagged & named, flagged - named, named - flagged
        lines += ["\n## E2: model flags vs NDMA sitreps, Jul to Sep 2025\n",
                  f"Districts flagged at least once at 24 h (p >= {FLAG_P}): {len(flagged)}. "
                  f"Districts named in at least one NDMA monsoon 2025 sitrep: {len(named)}.\n",
                  f"- both: {len(both)} ({', '.join(sorted(both)) or 'none'})",
                  f"- flagged, not named by NDMA: {len(only_model)} ({', '.join(sorted(only_model)) or 'none'})",
                  f"- named by NDMA, never flagged: {len(only_ndma)} ({', '.join(sorted(only_ndma)) or 'none'})",
                  "\nNDMA naming a district means it reported impacts or warnings there, not that rain "
                  "crossed our threshold, so this is a sense check, not a score. Districts named in "
                  "every sitrep (Islamabad, Lahore, Rawalpindi on 21 Oct) are mostly boilerplate "
                  "(NDMA's address, rainfall station tables), not impact reports."]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"-> {OUT}")
    return str(OUT)


if __name__ == "__main__":
    {"ndma": ndma_mentions, "report": report}[sys.argv[1]]()
