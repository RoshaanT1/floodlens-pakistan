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
        "risk_top": "Highest heavy-rain risk, next 24 h: {name} ({prov}) {pct}%, {ratio} its normal for this month",
        "rain_top": "Most forecast rain, next 3 days: {name} ({prov}) {mm} mm",
        "price_move": "{item} in {city}: {sign}{pct}% this week (Rs {old} to Rs {new}, PBS week ending {day})",
        "latest_doc": "Latest NDMA document: \"{title}\" ({kind}, {day}) {url}",
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
        "risk_top": "اگلے 24 گھنٹوں میں شدید بارش کا سب سے زیادہ امکان: {name} ({prov}) {pct} فیصد، اس مہینے کے معمول کا {ratio}",
        "rain_top": "اگلے 3 دنوں میں سب سے زیادہ متوقع بارش: {name} ({prov}) {mm} ملی میٹر",
        "price_move": "{city} میں {item}: اس ہفتے {sign}{pct} فیصد (Rs {old} سے Rs {new}، ہفتہ ختم {day})",
        "latest_doc": "این ڈی ایم اے کی تازہ ترین دستاویز: \"{title}\" ({kind}، {day}) {url}",
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


DIGEST = re.compile(r"\b(now|today|latest|happening|last 24|update|news|new|summary|overview|situation|what.?s up)\b|ابھی|آج|تازہ|صورتحال", re.I)
RAIN_WHERE = re.compile(r"\bwhere\b.*\brain|\brain\b.*\b(next|coming|tomorrow|this week)|\bwhich districts?\b|کہاں.*بارش|بارش.*کہاں", re.I)
PRICE_MOVES = re.compile(r"\b(food|prices?)\b.*\b(jump|rise|rose|fell|drop|change|moved?|week|up|down)|\b(which|what)\b.*\bprices?\b|قیمت", re.I)


def _risk_top(con, t, n):
    rows = con.execute(f"""
        SELECT r.row_id, d.name, d.province, r.p_heavy_rain, b.p_exceed
        FROM risk_live r JOIN districts d USING (district_id)
        LEFT JOIN baseline_climatology b ON b.district_id = r.district_id AND b.month = month(r.date_utc)
        WHERE r.lead_days = 1 ORDER BY r.p_heavy_rain DESC LIMIT {n}""").fetchall()
    out = []
    for row_id, name, prov, p, clim in rows:
        ratio = f"{p / clim:.1f}×" if clim else "n/a"
        out.append((t["risk_top"].format(name=name, prov=prov, pct=round(100 * p, 1), ratio=ratio) + f" [{row_id}]", row_id))
    return out


def _rain_top(con, t, n):
    rows = con.execute(f"""
        SELECT f.district_id, d.name, d.province, sum(f.precip_sum_mm) AS mm, min(f.date_utc) AS d0
        FROM forecast_live f JOIN districts d USING (district_id)
        WHERE f.days_ahead BETWEEN 1 AND 3 GROUP BY ALL ORDER BY mm DESC LIMIT {n}""").fetchall()
    return [(t["rain_top"].format(name=name, prov=prov, mm=round(mm, 1)) + f" [{did}_{d0}_live+3d]", f"{did}_{d0}_live+3d")
            for did, name, prov, mm, d0 in rows]


def _price_moves(con, t, n):
    rows = con.execute(f"""
        WITH w AS (SELECT max(week_end) AS w FROM spi_price),
        cur AS (SELECT s.* FROM spi_price s, w WHERE s.week_end = w.w AND s.avg_pkr IS NOT NULL),
        prev AS (SELECT s.city, s.item_no, s.avg_pkr FROM spi_price s, w WHERE s.week_end = w.w - INTERVAL 7 DAY)
        SELECT c.row_id, c.city, c.item, c.week_end, p.avg_pkr, c.avg_pkr, (c.avg_pkr / p.avg_pkr - 1) * 100 AS pct
        FROM cur c JOIN prev p USING (city, item_no) WHERE p.avg_pkr > 0
        ORDER BY abs(pct) DESC LIMIT {n}""").fetchall()
    return [(t["price_move"].format(item=item, city=city, sign="+" if pct > 0 else "", pct=round(pct, 1),
                                    old=f"{old:,.0f}", new=f"{new:,.0f}", day=day) + f" [{row_id}]", row_id)
            for row_id, city, item, day, old, new, pct in rows]


def _latest_doc(con, t):
    row = con.execute("""SELECT doc_id, title, published, url, source FROM documents
                         WHERE source IN ('ndma_advisory', 'ndma_sitrep') AND published IS NOT NULL
                         ORDER BY published DESC LIMIT 1""").fetchone()
    if not row:
        return []
    doc_id, title, day, url, src = row
    kind = "advisory" if src == "ndma_advisory" else "situation report"
    return [(t["latest_doc"].format(title=title.rstrip(" -"), kind=kind, day=str(day)[:10], url=url) + f" [{doc_id}]", doc_id)]


def digest_facts(con, question: str, lang: str) -> list[tuple[str, str]]:
    """Country-wide answers for 'what's happening' style questions, from live tables only."""
    t = TEXT[lang]
    have = {n for (n,) in con.execute("SHOW TABLES").fetchall()}
    q = question.lower()
    out: list[tuple[str, str]] = []
    if DIGEST.search(q):
        if "risk_live" in have:
            out += _risk_top(con, t, 3)
        if "forecast_live" in have:
            out += _rain_top(con, t, 3)
        if "spi_price" in have:
            out += _price_moves(con, t, 3)
        if "documents" in have:
            out += _latest_doc(con, t)
    else:
        if RAIN_WHERE.search(q) and "forecast_live" in have:
            out += _rain_top(con, t, 5)
        if PRICE_MOVES.search(q) and "spi_price" in have:
            out += _price_moves(con, t, 6)
    return out


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
        live = False
        if not facts and not district:  # country-wide questions: what's happening, where rain, which prices
            pairs = digest_facts(con, question, lang)
            facts, out.row_ids = [f for f, _ in pairs], [r for _, r in pairs]
            live = bool(pairs)
    # questions answered from live tables are about now: old advisories would mislead, so no quotes
    hits = [] if live else retrieve(question, district)
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
