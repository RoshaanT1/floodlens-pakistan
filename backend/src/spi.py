"""PBS weekly SPI city-wise prices (tasks B1, B2, B3). Model B groundwork only.

    python -m src.spi fetch   # media listing + every weekly Annex_DD.MM.YYYY.xlsx -> raw + manifest
    python -m src.spi build   # -> DuckDB `spi_price` (long) and `spi_week_quality`

B1: PBS's WordPress media API lists the weekly annex files. As of 21 Oct 2026 it has the
xlsx annex only from the week ending 30 Apr 2025. Older weeks (Jan 2023 onward, as declared)
are not in that listing under "annex" and still need finding; see docs/sources.md.
B2: the xlsx "Appendix-A" sheet holds three blocks of 51 items, 17 cities, each city with
MIN / AVG / MAX columns, for the week's "PRICES ON DD-MM-YYYY" date.
B3: checks only flag, never fill or drop prices:
  - min <= avg <= max;  - a 0 price means "not collected" and becomes NULL + flag;
  - 17 cities x 51 items per week, else the whole week is flagged;
  - avg more than 50% away from the same item and city's previous week is flagged.
"""
import json
import re
import sys
import time
from datetime import datetime

import duckdb
import pandas as pd
import requests

from src import manifest
from src.config import DB_PATH, ROOT

SOURCE = "pbs_spi_annex"
LISTING = "pbs_media_listing"
MEDIA_API = "https://www.pbs.gov.pk/wp-json/wp/v2/media?search=annex&per_page=100&page={page}&_fields=id,date,source_url"
UA = {"User-Agent": "FloodLens-Pakistan research (HackInsight 2026; contact via GitHub RoshaanT1)"}
ANNEX = re.compile(r"/Annex_(\d{2})\.(\d{2})\.(\d{4})\.xlsx$")
N_CITIES, N_ITEMS = 17, 51
JUMP = 0.5
DELAY_S = 2.0


def fetch() -> None:
    urls = []
    for page in range(1, 20):
        time.sleep(DELAY_S)
        r = requests.get(MEDIA_API.format(page=page), headers=UA, timeout=120)
        if r.status_code == 400:  # past the last page
            break
        r.raise_for_status()
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M")
        manifest.save_raw(r.content, LISTING, MEDIA_API.format(page=page), f"media_annex_p{page}_{stamp}.json")
        items = json.loads(r.content)
        urls += [m["source_url"] for m in items if ANNEX.search(m["source_url"])]
        if len(items) < 100:
            break
    done = manifest.fetched_queries(SOURCE)
    new = 0
    for url in sorted(set(urls)):
        if url in done:
            continue
        time.sleep(DELAY_S)
        r = requests.get(url, headers=UA, timeout=120)
        if r.status_code != 200:
            print(f"  {url}: HTTP {r.status_code}; logged, moving on")
            continue
        manifest.save_raw(r.content, SOURCE, url, url.rsplit("/", 1)[-1])
        new += 1
    print(f"spi: {len(set(urls))} weekly annex files listed, {new} new")


def parse_annex(path) -> pd.DataFrame:
    """Appendix-A -> one row per city and item: week_end, city, item_no, item, unit, min, avg, max."""
    df = pd.read_excel(path, sheet_name="Appendix-A", header=None)
    rows = []
    starts = [i for i, v in df[0].items() if str(v).strip() == "SL."]
    for s in starts:
        header = df.iloc[s]
        cities = [(c, re.sub(r"\s*\(\d+\)\s*$", "", str(header[c])).strip()) for c in range(3, df.shape[1])
                  if re.search(r"\(\d+\)\s*$", str(header[c]))]
        date_row = next(i for i in range(s, s + 6) if "PRICES ON" in " ".join(map(str, df.iloc[i].values)))
        m = re.search(r"PRICES ON (\d{2}-\d{2}-\d{4})", " ".join(map(str, df.iloc[date_row].values)))
        week_end = datetime.strptime(m.group(1), "%d-%m-%Y").date()
        for i in range(date_row + 1, min(date_row + 1 + N_ITEMS, len(df))):
            r = df.iloc[i]
            if pd.isna(r[0]) or not str(r[0]).strip().isdigit():
                continue
            for c, city in cities:
                rows.append({"week_end": week_end, "city": city, "item_no": int(r[0]), "item": str(r[1]).strip(),
                             "unit": str(r[2]).strip(), "min_pkr": r[c], "avg_pkr": r[c + 1], "max_pkr": r[c + 2]})
    out = pd.DataFrame(rows)
    for col in ("min_pkr", "avg_pkr", "max_pkr"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def check(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """B3 flags on the long table, plus one quality row per week. Values are never changed except 0 -> NULL."""
    p = prices.sort_values(["city", "item_no", "week_end"]).copy()
    flags = pd.Series([[] for _ in range(len(p))], index=p.index)
    zero = (p[["min_pkr", "avg_pkr", "max_pkr"]] == 0).any(axis=1)
    p.loc[zero, ["min_pkr", "avg_pkr", "max_pkr"]] = None  # not collected, never a real zero price
    for i in p.index[zero]:
        flags[i].append("not_collected")
    order = ~((p.min_pkr <= p.avg_pkr) & (p.avg_pkr <= p.max_pkr)) & p.avg_pkr.notna()
    for i in p.index[order]:
        flags[i].append("min_avg_max_order")
    prev = p.groupby(["city", "item_no"]).avg_pkr.shift(1)
    jump = ((p.avg_pkr - prev).abs() / prev > JUMP) & prev.notna()
    for i in p.index[jump]:
        flags[i].append("weekly_jump_over_50pct")
    p["quality_flags"] = flags.map(lambda f: ",".join(f) or None)

    weeks = p.groupby("week_end").agg(n_cities=("city", "nunique"), n_items=("item_no", "nunique"),
                                      n_rows=("item_no", "size"), n_flagged=("quality_flags", "count")).reset_index()
    weeks["complete"] = (weeks.n_cities == N_CITIES) & (weeks.n_items == N_ITEMS) & \
                        (weeks.n_rows == N_CITIES * N_ITEMS)
    weeks["week_flag"] = weeks.complete.map({True: None, False: "incomplete_week"})
    return p, weeks


def build(db_path=DB_PATH) -> int:
    rows = [r for r in manifest.read_manifest() if r["source"] == SOURCE]
    if not rows:
        raise SystemExit("no SPI files in manifest; run `python -m src.spi fetch`")
    frames = []
    for r in rows:
        try:
            frames.append(parse_annex(ROOT / r["path"]))
        except Exception as e:  # a layout we cannot read is logged, never guessed
            print(f"  could not parse {r['path']}: {e}")
    prices, weeks = check(pd.concat(frames).drop_duplicates(["week_end", "city", "item_no"], keep="last"))
    prices["row_id"] = prices.city.str.replace(" ", "_") + "_" + prices.item_no.astype(str) + "_" + \
        prices.week_end.astype(str)
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE spi_price AS SELECT * FROM prices ORDER BY row_id")
        con.execute("CREATE OR REPLACE TABLE spi_week_quality AS SELECT * FROM weeks ORDER BY week_end")
    print(f"spi_price: {len(prices)} rows, {len(weeks)} weeks "
          f"({int((~weeks.complete).sum())} incomplete); {int(prices.quality_flags.notna().sum())} flagged rows")
    return len(prices)


if __name__ == "__main__":
    {"fetch": fetch, "build": build}[sys.argv[1]]()
