"""Insight Agent answer builder (task R3, R5). Runs in .venv-insight (needs the R2 index).

    .venv-insight/bin/python -m src.insight "Deaths in Buner in August 2025?"
    .venv-insight/bin/python -m src.insight --lang ur "Buner forecast"

Rules (TASKS.md R3/R4):
- every sentence taken from a document is a quote with its section id;
- every number comes from a gold table and carries its row id; nothing is generated;
- no section scoring at least MIN_SCORE (and no matching table fact) -> "I don't know";
- questions that sound like an emergency get NDMA/PDMA and Rescue 1122 first;
- outputs are not official warnings.
The wording around quotes and numbers is fixed templates (English or Urdu), so no model
writes free text. An LLM rewrite can be layered on later without changing these rules.
"""
import argparse
import json
import re
from dataclasses import dataclass, field

import duckdb

from src.config import DB_PATH

MIN_SCORE = 0.83        # cosine; chosen with the hazard-word gate on tests/test_insight.py questions
# The documents are all about hazards, so a question must name one before any section is
# quoted: cosine alone let "Explain photosynthesis" (0.849) outscore real questions (0.847).
HAZARD = re.compile(r"\b(flood|rain|river|monsoon|death|died|dead|deceased|injur|damage|house|warning|alert|"
                    r"advisory|glof|glacial|landslide|storm|cyclone|casualt|missing|evacuat|relief)|"
                    r"سیلاب|بارش|دریا|ہلاک|موت|نقصان|وارننگ|الرٹ|طوفان|مون سون", re.I)  # \b: not "train"
TOP_K = 8
MAX_QUOTES = 3
EMERGENCY = re.compile(r"\b(help|trapped|stuck|drowning|rescue|emergency|injured|missing person)\b|"
                       r"مدد|پھنس|ڈوب|ریسکیو|ایمرجنسی|زخمی", re.I)
ALIASES = {"bunner": "Buner", "d.i. khan": "D. I. Khan", "dera ismail khan": "D. I. Khan",
           "karachi": "South Karachi"}

TEXT = {
    "en": {
        "emergency": "If you or others are in danger now, call Rescue 1122 and follow NDMA/PDMA "
                     "instructions (ndma.gov.pk). FloodLens is not an emergency service.",
        "idk": "I don't know. None of the documents or tables I have answer this well enough.",
        "docs": "From official documents:",
        "data": "From FloodLens data:",
        "rain": "Forecast rain for {name} on {day}: {mm} mm (raw forecast, not a risk score)",
        "risk": "Model A probability of heavy rain in {name} on {day}: {pct}% ({label})",
        "price": "Average price of {item} ({unit}) in {city}, week ending {day}: Rs {pkr}",
        "disclaimer": "Not an official warning. Follow NDMA and PDMA advisories.",
    },
    "ur": {
        "emergency": "اگر آپ یا کوئی اور ابھی خطرے میں ہے تو ریسکیو 1122 پر کال کریں اور این ڈی ایم اے / "
                     "پی ڈی ایم اے کی ہدایات پر عمل کریں۔ فلڈ لینز ایمرجنسی سروس نہیں ہے۔",
        "idk": "مجھے معلوم نہیں۔ میرے پاس موجود دستاویزات یا ڈیٹا اس سوال کا قابلِ اعتماد جواب نہیں دیتے۔",
        "docs": "سرکاری دستاویزات سے (انگریزی اقتباس):",
        "data": "فلڈ لینز ڈیٹا سے:",
        "rain": "{name} میں {day} کو متوقع بارش: {mm} ملی میٹر (خام پیش گوئی، خطرے کا اسکور نہیں)",
        "risk": "{name} میں {day} کو شدید بارش کا امکان (ماڈل اے): {pct} فیصد ({label})",
        "price": "{city} میں {item} ({unit}) کی اوسط قیمت، ہفتہ ختم {day}: {pkr} روپے",
        "disclaimer": "یہ سرکاری وارننگ نہیں ہے۔ این ڈی ایم اے اور پی ڈی ایم اے کی ہدایات پر عمل کریں۔",
    },
}


@dataclass
class Answer:
    text: str
    citations: list[str] = field(default_factory=list)   # section ids
    row_ids: list[str] = field(default_factory=list)     # gold-table row ids
    known: bool = True
    emergency: bool = False


def _districts(con) -> list[str]:
    return [n for (n,) in con.execute("SELECT name FROM districts").fetchall()]


def find_district(question: str, names: list[str]) -> str | None:
    q = question.lower()
    for alias, name in ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", q):
            return name
    hits = [n for n in names if re.search(r"\b" + re.escape(n.lower()) + r"\b", q)]
    return max(hits, key=len) if hits else None


def table_facts(con, question: str, lang: str) -> tuple[list[str], list[str]]:
    """Numbers from gold tables, each line ending with its row id."""
    t, lines, ids = TEXT[lang], [], []
    have = {n for (n,) in con.execute("SHOW TABLES").fetchall()}
    name = find_district(question, _districts(con)) if "districts" in have else None
    q = question.lower()
    if name and re.search(r"\b(rain|forecast|risk)|بارش|پیش گوئی|خطر", q):
        if "risk_live" in have:
            for row_id, day, p, label in con.execute("""
                    SELECT r.row_id, r.date_utc, r.p_heavy_rain, r.model_label FROM risk_live r
                    JOIN districts d USING (district_id) WHERE d.name = ? ORDER BY lead_days""", [name]).fetchall():
                lines.append(t["risk"].format(name=name, day=day, pct=round(100 * p), label=label) + f" [{row_id}]")
                ids.append(row_id)
        if "forecast_live" in have:
            for did, day, mm in con.execute("""
                    SELECT f.district_id, f.date_utc, f.precip_sum_mm FROM forecast_live f
                    JOIN districts d USING (district_id) WHERE d.name = ? AND days_ahead BETWEEN 1 AND 3
                    ORDER BY date_utc""", [name]).fetchall():
                row_id = f"{did}_{day}_live"
                lines.append(t["rain"].format(name=name, day=day, mm=round(mm, 1)) + f" [{row_id}]")
                ids.append(row_id)
    if "spi_price" in have and re.search(r"\b(price|cost|rs\b|rupee)|قیمت", q):
        cities = [c for (c,) in con.execute("SELECT DISTINCT city FROM spi_price").fetchall()]
        city = next((c for c in cities if c.lower() in q), None)
        items = con.execute("SELECT DISTINCT item_no, item FROM spi_price").fetchall()
        words = set(re.findall(r"[a-z]{4,}", q)) - {"price", "prices", "cost", "week", "average"}
        item = max(items, key=lambda it: len(words & set(re.findall(r"[a-z]{4,}", it[1].lower())))) if words else None
        if city and item and words & set(re.findall(r"[a-z]{4,}", item[1].lower())):
            row = con.execute("""
                SELECT row_id, week_end, item, unit, avg_pkr FROM spi_price
                WHERE city = ? AND item_no = ? AND avg_pkr IS NOT NULL ORDER BY week_end DESC LIMIT 1""",
                              [city, item[0]]).fetchone()
            if row:
                lines.append(t["price"].format(city=city, day=row[1], item=row[2], unit=row[3],
                                               pkr=f"{row[4]:,.2f}") + f" [{row[0]}]")
                ids.append(row[0])
    return lines, ids


GENERIC = {"august", "july", "june", "september", "october", "2025", "2026", "monsoon", "sitrep",
           "ndma", "pdma", "report", "situation", "daily", "flood", "floods", "many", "what", "which",
           "when", "where", "during", "about", "people"}
WINDOW = 160


def _best_quote(text: str, question: str, district: str | None) -> str:
    """A verbatim excerpt: around the district name if named, else the best-matching sentence."""
    if district:
        m = re.search(re.escape(district), text, re.I) or re.search("bunner", text, re.I)
        if m:
            a, b = max(0, m.start() - WINDOW), min(len(text), m.end() + WINDOW)
            return ("…" if a else "") + text[a:b].strip() + ("…" if b < len(text) else "")
    words = set(re.findall(r"\w{4,}", question.lower())) - GENERIC
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20] or [text]
    best = max(sentences, key=lambda s: len(words & set(re.findall(r"\w{4,}", s.lower()))))
    return best[:400]


def retrieve(question: str, district: str | None) -> list[dict]:
    from src import doc_index
    if not HAZARD.search(question):
        return []
    hits = [h for h in doc_index.query(question, k=TOP_K) if h["score"] >= MIN_SCORE]
    if district:  # a named district must appear in the quoted section
        names = {district.lower()} | {a for a, n in ALIASES.items() if n == district}
        hits = [h for h in hits if any(n in h["text_full"].lower() for n in names)]
    return hits[:MAX_QUOTES]


def answer(question: str, lang: str = "en", db_path=DB_PATH) -> Answer:
    t = TEXT[lang]
    parts, out = [], Answer(text="")
    if EMERGENCY.search(question):
        parts.append(t["emergency"])
        out.emergency = True
    with duckdb.connect(str(db_path), read_only=True) as con:
        facts, out.row_ids = table_facts(con, question, lang)
        district = find_district(question, _districts(con))
    hits = retrieve(question, district)
    if hits:
        parts.append(t["docs"])
        for h in hits:
            parts.append(f'- "{_best_quote(h["text_full"], question, district)}" ({h["title"]}, p. {h["page"]}) '
                         f'[{h["section_id"]}]')
            out.citations.append(h["section_id"])
    if facts:
        parts.append(t["data"])
        parts += [f"- {f}" for f in facts]
    if not hits and not facts:
        parts.append(t["idk"])
        out.known = False
    parts.append(t["disclaimer"])
    out.text = "\n".join(parts)
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question", nargs="+")
    p.add_argument("--lang", choices=["en", "ur"], default="en")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    res = answer(" ".join(a.question), a.lang)
    print(json.dumps(res.__dict__, ensure_ascii=False, indent=2) if a.json else res.text)
