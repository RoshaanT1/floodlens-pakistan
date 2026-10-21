"""Document library for the Insight Agent (task R1).

    python -m src.documents fetch    # listing pages + PDFs -> data/raw/<source>/ with manifest rows
    python -m src.documents build    # listing pages -> DuckDB `documents` (title, date, url, path)

Sources (see docs/sources.md for publishers and licences):
  ndma_sitrep    NDMA Monsoon 2025 daily situation reports   ndma.gov.pk/sitreps?cat_id=1
  ndma_advisory  NDMA advisories, Jun to Oct 2025             ndma.gov.pk/advisories?page=N
  pmd_document   PMD monsoon 2025 outlook / rainfall updates  fixed URLs below

Politeness: robots.txt on ndma.gov.pk disallows only /admin and /api; requests are spaced
DELAY_S apart, and a URL already in the manifest is never downloaded again. Documents are
used for citations and local validation only, never for training (DATASET_DECLARATION.md).
"""
import html
import re
import sys
import time
from datetime import date, datetime

import duckdb
import pandas as pd
import requests

from src import manifest
from src.config import DB_PATH, ROOT

DELAY_S = 2.0
UA = {"User-Agent": "FloodLens-Pakistan research (HackInsight 2026; contact via GitHub RoshaanT1)"}
NDMA = "https://www.ndma.gov.pk"
SITREP_LIST = NDMA + "/sitreps?cat_id=1&page={page}"
ADVISORY_LIST = NDMA + "/advisories?page={page}"
ADVISORY_WINDOW = (date(2025, 6, 1), date(2025, 10, 31))
PMD_DOCS = [
    "https://cdpc.pmd.gov.pk/Monsoon_2025_update/Pakistan_Monsoon_2025_Rainfall_Update.pdf",
]
LISTING = "ndma_listing"
CARD = re.compile(r'<a href="([^"]+\.pdf)"[^>]*>(.*?)</a>', re.S)
DATE = re.compile(r"(\d{1,2} [A-Z][a-z]{2} \d{4})")


def _get(url: str) -> requests.Response:
    time.sleep(DELAY_S)
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    return r


def parse_cards(page_html: str) -> list[dict]:
    """(url, title, date) for every PDF card on an NDMA listing page."""
    out = []
    for url, body in CARD.findall(page_html):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
        m = DATE.search(text)
        published = datetime.strptime(m.group(1), "%d %b %Y").date() if m else None
        title = DATE.split(text)[0].strip() if m else text.replace(" View", "").strip()
        out.append({"url": url.replace("gov.pk//", "gov.pk/"), "title": title, "published": published})
    return out


def _save_listing(url: str) -> list[dict]:
    content = _get(url).content
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")  # listings change; raw files never do
    manifest.save_raw(content, LISTING, url, re.sub(r"[^A-Za-z0-9]+", "_", url.split("gov.pk/")[1]) + f"_{stamp}.html")
    return parse_cards(content.decode("utf-8", "replace"))


def _save_pdf(url: str, source: str, done: set[str]) -> bool:
    if url in done:
        return False
    try:
        r = _get(url)
    except requests.RequestException as e:
        print(f"  {source}: {url} failed ({e}); logged, moving on")
        return False
    if not r.content.startswith(b"%PDF"):
        print(f"  {source}: {url} is not a PDF ({r.headers.get('content-type')}); skipped")
        return False
    manifest.save_raw(r.content, source, url, url.rsplit("/", 2)[-2] + "_" + url.rsplit("/", 1)[-1])
    done.add(url)
    return True


def fetch() -> None:
    done = {q for s in ("ndma_sitrep", "ndma_advisory", "pmd_document") for q in manifest.fetched_queries(s)}
    n = 0
    # NDMA monsoon 2025 sitreps: walk pages until one has no cards
    for page in range(1, 30):
        cards = _save_listing(SITREP_LIST.format(page=page))
        if not cards:
            break
        n += sum(_save_pdf(c["url"], "ndma_sitrep", done) for c in cards)
    # NDMA advisories: newest first; stop once a whole page is older than the window
    for page in range(1, 60):
        cards = _save_listing(ADVISORY_LIST.format(page=page))
        if not cards:
            break
        n += sum(_save_pdf(c["url"], "ndma_advisory", done) for c in cards
                 if c["published"] and ADVISORY_WINDOW[0] <= c["published"] <= ADVISORY_WINDOW[1])
        if all(c["published"] and c["published"] < ADVISORY_WINDOW[0] for c in cards):
            break
    for url in PMD_DOCS:
        n += _save_pdf(url, "pmd_document", done)
    print(f"documents: {n} new files")


RECENT_SITREP_CATS = (2, 3)  # Special Sitreps 2026, Monsoon Sitreps 2026
RECENT_DAYS = 60


def fetch_recent(today: date | None = None) -> int:
    """Daily top-up for the flow: newest NDMA advisories and 2026 sitreps (first pages only)."""
    today = today or date.today()
    done = {q for s in ("ndma_sitrep", "ndma_advisory") for q in manifest.fetched_queries(s)}
    n = 0
    for cat in RECENT_SITREP_CATS:
        for c in _save_listing(f"{NDMA}/sitreps?cat_id={cat}&page=1"):
            n += _save_pdf(c["url"], "ndma_sitrep", done)
    for page in (1, 2):
        cards = _save_listing(ADVISORY_LIST.format(page=page))
        n += sum(_save_pdf(c["url"], "ndma_advisory", done) for c in cards
                 if c["published"] and (today - c["published"]).days <= RECENT_DAYS)
    print(f"documents (recent): {n} new files")
    return n


def build(db_path=DB_PATH) -> int:
    """Catalogue of stored documents, titles and dates taken from the newest listing pages."""
    meta = {}
    for r in sorted(manifest.read_manifest(), key=lambda r: r["fetched_at_utc"]):
        if r["source"] == LISTING:
            for c in parse_cards((ROOT / r["path"]).read_text("utf-8", "replace")):
                meta[c["url"]] = c
    rows = []
    for r in manifest.read_manifest():
        if r["source"] in ("ndma_sitrep", "ndma_advisory", "pmd_document"):
            m = meta.get(r["query"], {})
            rows.append({"doc_id": r["sha256"][:16], "source": r["source"], "url": r["query"],
                         "title": m.get("title") or r["query"].rsplit("/", 1)[-1],
                         "published": m.get("published"), "path": r["path"], "sha256": r["sha256"]})
    df = pd.DataFrame(rows).drop_duplicates("doc_id")
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE OR REPLACE TABLE documents AS SELECT * FROM df ORDER BY published, doc_id")
    print(f"documents: {len(df)} rows")
    return len(df)


if __name__ == "__main__":
    {"fetch": fetch, "recent": fetch_recent, "build": build}[sys.argv[1]]()
