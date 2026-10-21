"""Insight Agent answer builder (task R3, R5). Runs in .venv-insight (needs the R2 index).

    .venv-insight/bin/python -m src.insight "Deaths in Buner in August 2025?"
    .venv-insight/bin/python -m src.insight --lang ur "Buner forecast"

Rules (TASKS.md R3/R4):
- every sentence taken from a document is a quote with its section id;
- every number comes from a gold table (or a results file in docs/) and carries its row id;
- no section scoring at least MIN_SCORE (and no matching table fact) -> "I don't know";
- questions that sound like an emergency get NDMA/PDMA and Rescue 1122 first;
- outputs are not official warnings.
Each answer opens with a plain-language lead: fixed templates (English or Urdu) filled only with
numbers from the evidence lines below it, so no model writes free text.
"""
import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import duckdb

from src.config import DB_PATH, ROOT

MIN_SCORE = 0.83        # cosine; chosen with the hazard-word gate on tests/test_insight.py questions
# The documents are all about hazards, so a question must name one before any section is
# quoted: cosine alone let "Explain photosynthesis" (0.849) outscore real questions (0.847).
HAZARD = re.compile(r"\b(flood|rain|river|monsoon|death|died|dead|deceased|injur|damage|house|warning|alert|"
                    r"advisory|glof|glacial|landslide|storm|cyclone|casualt|missing|evacuat|relief)|"
                    r"سیلاب|بارش|دریا|ہلاک|موت|نقصان|وارننگ|الرٹ|طوفان|مون سون", re.I)  # \b: not "train"
TOP_K = 8
TOP_K_DISTRICT = 60     # a named district filters hits afterwards, so search deeper first
MAX_QUOTES = 3
EMERGENCY = re.compile(r"\b(help|trapped|stuck|drowning|rescue|emergency|injured|missing person)\b|"
                       r"مدد|پھنس|ڈوب|ریسکیو|ایمرجنسی|زخمی", re.I)
ALIASES = {"bunner": "Buner", "d.i. khan": "D. I. Khan", "dera ismail khan": "D. I. Khan",
           "karachi": "South Karachi"}
PLACE_LABEL = {"karachi": "Karachi (South Karachi district)"}

GREETING = re.compile(r"^\s*(hi|hello|hey|salam|assalam\w*|aoa|good (morning|afternoon|evening))\b|"
                      r"\b(who are you|what can you do|what do you do|how do you work)\b|"
                      r"^\s*(ہیلو|السلام|سلام)|آپ کون|کیا کر سکت", re.I)
THANKS = re.compile(r"^\s*(thanks|thank you|thx|shukriya|jazakallah)\b|^\s*شکریہ", re.I)
MODEL_Q = re.compile(r"\b(accura\w*|how good|brier|reliab\w*|trust\w*|baseline|skill|your model|the model)\b|"
                     r"درست|ماڈل", re.I)
FORECASTY = re.compile(r"\b(when|will|tomorrow|today|tonight|forecast|next|coming|this week|outlook|going to|"
                       r"chance|risk|expected)\b|کب|کل|پیش گوئی|ہوگی|متوقع", re.I)
PAST = re.compile(r"\b(19|20)\d\d\b|\b(died|deaths?|dead|damage\w*|killed|injur\w*|happened|houses?|casualt\w*|"
                  r"last (year|month)|advis\w*|warning)\b|ہلاک|نقصان|وارننگ", re.I)
LONG_HORIZON = re.compile(r"\b(next week|this month|next month|7 days|seven days|weekend|10 days)\b", re.I)
MONTHS = {"en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                 "October", "November", "December"],
          "ur": ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"]}
WEEKDAY_UR = ["پیر", "منگل", "بدھ", "جمعرات", "جمعہ", "ہفتہ", "اتوار"]

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
        "day_line": "{day}: {mm} mm forecast · heavy-rain chance {pct} (normal for {month}: {clim})",
        "model_line": "Test set, 1 Jan–16 Oct 2026 ({n} district-days), Brier at {h}: model {m} vs climatology {c} "
                      "(lower is better)",
        "hello": "Hi! I'm FloodLens. I watch rain risk for Pakistan's 160 districts, weekly food prices in 17 cities "
                 "and NDMA's reports. Ask me things like \"Will it rain in Karachi?\", \"What's happening right now?\" "
                 "or \"How many died in Buner in August 2025?\" I show where every number comes from.",
        "thanks": "Anytime! Stay safe, and check back: I refresh every hour.",
        "idk_lead": "Hmm, I can't answer that one from what I know. I stick to Pakistan's rain and flood risk, "
                    "food prices and NDMA reports, and I won't guess.",
        "dry": "Looks dry in {place}: the latest forecast shows {total} mm in total from {d1} to {d3}.",
        "no_rain": "Looks dry in {place}: no rain in the forecast from {d1} to {d3}.",
        "wet": "Rain looks likely in {place} on {day}, about {mm} mm.",
        "wet_more": " More is forecast on {days}.",
        "risk_high": " Heads up: the chance of heavy rain reaches {pct} on {day}, about {ratio}× what's normal "
                     "for {month}.",
        "risk_calm": " Nothing unusual though: the heavy-rain chance stays {cap}, close to normal for {month}.",
        "horizon": " (I can only see three days ahead.)",
        "digest_alert": "Heads up: {name} stands out, with a {pct} chance of heavy rain in the next 24 h, "
                        "{ratio}× its normal.",
        "digest_calm": "Fairly calm across Pakistan right now: no district has an unusual heavy-rain risk in the "
                       "next 24 h.",
        "digest_rain": " The wettest forecast is {name}, with {mm} mm over the next three days.",
        "digest_price": " Biggest food-price move this week: {item} in {city}, {sign}{pct}%.",
        "rain_lead": "Over the next three days the most rain is forecast for {names}. Here are the numbers:",
        "rain_lead_dry": "Hardly any rain anywhere in the next three days: the wettest district, {name}, "
                         "gets {mm} mm.",
        "price_lead": "The biggest moves in this week's PBS prices: {item} in {city} {sign}{pct}%, and more below.",
        "price_one": "{item} costs Rs {pkr} on average in {city} (PBS, week ending {day}).",
        "model_lead": "Good question. On data it never saw (1 Jan–16 Oct 2026, scored once), my heavy-rain model beats "
                      "the district-by-month climatology baseline: Brier {m} vs {c} at 24 h, about {gain}% better. "
                      "It's weakest in {weak}.",
        "docs_lead": "Here's what NDMA's own reports say. I found {n} relevant passages:",
        "docs_lead_place": "Here's what NDMA's own reports say about {place}:",
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
        "day_line": "{day}: متوقع بارش {mm} ملی میٹر · شدید بارش کا امکان {pct} ({month} کا معمول: {clim})",
        "model_line": "ٹیسٹ سیٹ، جنوری تا ستمبر 2026 ({n} ضلعی دن)، {h} پر Brier: ماڈل {m} بمقابلہ کلائمیٹولوجی {c} "
                      "(کم بہتر ہے)",
        "hello": "السلام علیکم! میں فلڈ لینز ہوں۔ میں پاکستان کے 160 اضلاع میں بارش کے خطرے، 17 شہروں میں اشیائے "
                 "خور و نوش کی قیمتوں اور این ڈی ایم اے کی رپورٹس پر نظر رکھتا ہوں۔ پوچھیں: \"کراچی میں بارش کب ہوگی؟\" "
                 "یا \"آج کی صورتحال کیا ہے؟\"",
        "thanks": "خوشی ہوئی! محفوظ رہیں، میں ہر گھنٹے اپ ڈیٹ ہوتا ہوں۔",
        "idk_lead": "معاف کیجیے، میں اس کا جواب نہیں دے سکتا۔ میں صرف پاکستان میں بارش، سیلاب کے خطرے، قیمتوں اور "
                    "این ڈی ایم اے رپورٹس کے بارے میں بتاتا ہوں، اور اندازے نہیں لگاتا۔",
        "dry": "{place} میں موسم خشک لگتا ہے: {d1} سے {d3} تک کل {total} ملی میٹر بارش کی پیش گوئی ہے۔",
        "no_rain": "{place} میں موسم خشک لگتا ہے: {d1} سے {d3} تک بارش کی کوئی پیش گوئی نہیں۔",
        "wet": "{place} میں {day} کو بارش متوقع ہے، تقریباً {mm} ملی میٹر۔",
        "wet_more": " {days} کو بھی بارش کی پیش گوئی ہے۔",
        "risk_high": " توجہ دیں: {day} کو شدید بارش کا امکان {pct} ہے، جو {month} کے معمول سے تقریباً {ratio} گنا ہے۔",
        "risk_calm": " کوئی غیر معمولی بات نہیں: شدید بارش کا امکان {cap} ہے، {month} کے معمول کے قریب۔",
        "horizon": " (میں صرف تین دن آگے تک دیکھ سکتا ہوں۔)",
        "digest_alert": "توجہ دیں: {name} نمایاں ہے، اگلے 24 گھنٹوں میں شدید بارش کا امکان {pct}، معمول کا {ratio} گنا۔",
        "digest_calm": "اس وقت پاکستان بھر میں صورتحال پرسکون ہے: اگلے 24 گھنٹوں میں کسی ضلع میں غیر معمولی خطرہ نہیں۔",
        "digest_rain": " سب سے زیادہ متوقع بارش {name} میں ہے، اگلے تین دنوں میں {mm} ملی میٹر۔",
        "digest_price": " اس ہفتے قیمت میں سب سے بڑی تبدیلی: {city} میں {item}، {sign}{pct} فیصد۔",
        "rain_lead": "اگلے تین دنوں میں سب سے زیادہ بارش {names} میں متوقع ہے۔ تفصیل:",
        "rain_lead_dry": "اگلے تین دنوں میں کہیں خاص بارش نہیں: سب سے زیادہ {name} میں {mm} ملی میٹر۔",
        "price_lead": "اس ہفتے کی سب سے بڑی تبدیلیاں: {city} میں {item} {sign}{pct} فیصد، باقی نیچے۔",
        "price_one": "{city} میں {item} کی اوسط قیمت {pkr} روپے ہے (ہفتہ ختم {day})۔",
        "model_lead": "اچھا سوال۔ ان دیکھے ڈیٹا (جنوری تا ستمبر 2026) پر میرا ماڈل کلائمیٹولوجی سے بہتر ہے: 24 گھنٹے پر "
                      "Brier {m} بمقابلہ {c}، تقریباً {gain} فیصد بہتر۔ سب سے کمزور: {weak}۔",
        "docs_lead": "این ڈی ایم اے کی اپنی رپورٹس یہ کہتی ہیں۔ {n} متعلقہ اقتباسات:",
        "docs_lead_place": "{place} کے بارے میں این ڈی ایم اے کی رپورٹس یہ کہتی ہیں:",
    },
}


@dataclass
class Answer:
    text: str
    citations: list[str] = field(default_factory=list)   # section ids
    row_ids: list[str] = field(default_factory=list)     # gold-table row ids (or a docs/ results file)
    known: bool = True
    emergency: bool = False
    lead: str = ""                                       # plain-language summary, also the first line of text


def _districts(con) -> list[str]:
    return [n for (n,) in con.execute("SELECT name FROM districts").fetchall()]


def find_district(question: str, names: list[str]) -> str | None:
    q = question.lower()
    for alias, name in ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", q):
            return name
    hits = [n for n in names if re.search(r"\b" + re.escape(n.lower()) + r"\b", q)]
    return max(hits, key=len) if hits else None


def _place(question: str, name: str) -> str:
    q = question.lower()
    return next((label for alias, label in PLACE_LABEL.items() if re.search(r"\b" + alias + r"\b", q)), name)


def _day(d, lang: str) -> str:
    d = d.date() if isinstance(d, datetime) else d
    return d.strftime("%a %-d %b") if lang == "en" else f"{WEEKDAY_UR[d.weekday()]} {d.isoformat()}"


def _pct(p: float) -> str:
    return "<1%" if 0 < p < 0.01 else f"{round(100 * p)}%"


DIGEST = re.compile(r"\b(now|today|latest|happening|last 24|update|news|new|summary|overview|situation|what.?s up)\b|ابھی|آج|تازہ|صورتحال", re.I)
RAIN_WHERE = re.compile(r"\bwhere\b.*\brain|\brain\b.*\b(next|coming|tomorrow|this week)|\bwhich districts?\b|کہاں.*بارش|بارش.*کہاں", re.I)
PRICE_MOVES = re.compile(r"\b(food|prices?)\b.*\b(jump|rise|rose|fell|drop|change|moved?|week|up|down)|\b(which|what)\b.*\bprices?\b|قیمت", re.I)


# Each helper returns (evidence line, row id, values the lead may use).
def _risk_top(con, t, n):
    rows = con.execute(f"""
        SELECT r.row_id, d.name, d.province, r.p_heavy_rain, b.p_exceed
        FROM risk_live r JOIN districts d USING (district_id)
        LEFT JOIN baseline_climatology b ON b.district_id = r.district_id AND b.month = month(r.date_utc)
        WHERE r.lead_days = 1 ORDER BY r.p_heavy_rain DESC LIMIT {n}""").fetchall()
    out = []
    for row_id, name, prov, p, clim in rows:
        ratio = f"{p / clim:.1f}×" if clim else "n/a"
        out.append((t["risk_top"].format(name=name, prov=prov, pct=round(100 * p, 1), ratio=ratio) + f" [{row_id}]",
                    row_id, {"name": name, "p": p, "clim": clim}))
    return out


def _rain_top(con, t, n):
    rows = con.execute(f"""
        SELECT f.district_id, d.name, d.province, sum(f.precip_sum_mm) AS mm, min(f.date_utc) AS d0
        FROM forecast_live f JOIN districts d USING (district_id)
        WHERE f.days_ahead BETWEEN 1 AND 3 GROUP BY ALL ORDER BY mm DESC LIMIT {n}""").fetchall()
    return [(t["rain_top"].format(name=name, prov=prov, mm=round(mm, 1)) + f" [{did}_{d0}_live+3d]",
             f"{did}_{d0}_live+3d", {"name": name, "mm": round(mm, 1)})
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
                                    old=f"{old:,.0f}", new=f"{new:,.0f}", day=day) + f" [{row_id}]", row_id,
             {"item": item, "city": city, "sign": "+" if pct > 0 else "", "pct": round(pct, 1)})
            for row_id, city, item, day, old, new, pct in rows]


def _latest_doc(con, t):
    row = con.execute("""SELECT doc_id, title, published, url, source FROM documents
                         WHERE source IN ('ndma_advisory', 'ndma_sitrep') AND published IS NOT NULL
                         ORDER BY published DESC LIMIT 1""").fetchone()
    if not row:
        return []
    doc_id, title, day, url, src = row
    kind = "advisory" if src == "ndma_advisory" else "situation report"
    return [(t["latest_doc"].format(title=title.rstrip(" -"), kind=kind, day=str(day)[:10], url=url) + f" [{doc_id}]",
             doc_id, {})]


def digest_facts(con, question: str, lang: str) -> tuple[str, list[tuple[str, str, dict]]]:
    """Country-wide answers for 'what's happening' style questions, from live tables only: (lead, facts)."""
    t = TEXT[lang]
    have = {n for (n,) in con.execute("SHOW TABLES").fetchall()}
    q = question.lower()
    lead, out = "", []
    if DIGEST.search(q):
        risk = _risk_top(con, t, 3) if "risk_live" in have else []
        rain = _rain_top(con, t, 3) if "forecast_live" in have else []
        price = _price_moves(con, t, 3) if "spi_price" in have else []
        out = risk + rain + price + (_latest_doc(con, t) if "documents" in have else [])
        if risk:
            v = risk[0][2]
            ratio = v["p"] / v["clim"] if v["clim"] else 0
            lead = (t["digest_alert"].format(name=v["name"], pct=_pct(v["p"]), ratio=f"{ratio:.0f}")
                    if ratio >= 3 and v["p"] >= 0.02 else t["digest_calm"])
        if rain:
            lead += t["digest_rain"].format(**rain[0][2])
        if price:
            lead += t["digest_price"].format(**price[0][2])
    else:
        if RAIN_WHERE.search(q) and "forecast_live" in have:
            rain = _rain_top(con, t, 5)
            out += rain
            if rain:
                lead = (t["rain_lead"].format(names=", ".join(r[2]["name"] for r in rain[:3]))
                        if rain[0][2]["mm"] >= 5 else t["rain_lead_dry"].format(**rain[0][2]))
        if PRICE_MOVES.search(q) and "spi_price" in have:
            price = _price_moves(con, t, 6)
            out += price
            if price and not lead:
                lead = t["price_lead"].format(**price[0][2])
    return lead.strip(), out


def outlook(con, question: str, name: str, lang: str) -> tuple[str, list[str], list[str]]:
    """Three-day outlook for one district: forecast rain and Model A risk per day, against its normal."""
    t, m = TEXT[lang], MONTHS[lang]
    have = {n for (n,) in con.execute("SHOW TABLES").fetchall()}
    if "forecast_live" not in have:
        return "", [], []
    risk = "risk_live" in have
    rows = con.execute(f"""
        SELECT f.date_utc::DATE AS day, f.precip_sum_mm, f.district_id,
               {"r.row_id, r.p_heavy_rain" if risk else "NULL, NULL"}, b.p_exceed
        FROM forecast_live f JOIN districts d USING (district_id)
        {"LEFT JOIN risk_live r ON r.district_id = f.district_id AND r.date_utc::DATE = f.date_utc::DATE" if risk else ""}
        LEFT JOIN baseline_climatology b ON b.district_id = f.district_id AND b.month = month(f.date_utc)
        WHERE d.name = ? AND f.days_ahead BETWEEN 1 AND 3 ORDER BY day""", [name]).fetchall()
    if not rows:
        return "", [], []
    lines, ids = [], []
    for day, mm, did, risk_id, p, clim in rows:
        live_id = f"{did}_{day}_live"
        tag = live_id + (f" · {risk_id}" if risk_id else "")
        lines.append(t["day_line"].format(day=_day(day, lang), mm=round(mm, 1), pct="n/a" if p is None else _pct(p),
                                          month=m[day.month - 1], clim="n/a" if clim is None else _pct(clim))
                     + f" [{tag}]")
        ids += [live_id] + ([risk_id] if risk_id else [])

    place = _place(question, name)
    d1, d3 = _day(rows[0][0], lang), _day(rows[-1][0], lang)
    wet = [(day, mm) for day, mm, *_ in rows if mm >= 1]
    total = sum(mm for _, mm, *_ in rows)
    if wet:
        lead = t["wet"].format(place=place, day=_day(wet[0][0], lang), mm=round(wet[0][1]))
        if len(wet) > 1:
            lead += t["wet_more"].format(days=", ".join(_day(d, lang) for d, _ in wet[1:]))
    elif total < 0.1:
        lead = t["no_rain"].format(place=place, d1=d1, d3=d3)
    else:
        lead = t["dry"].format(place=place, total=round(total, 1), d1=d1, d3=d3)
    scored = [(p, clim, day) for day, _, _, _, p, clim in rows if p is not None]
    if scored:
        p, clim, day = max(scored, key=lambda r: r[0])
        month = m[day.month - 1]
        if clim and p >= 3 * clim and p >= 0.02:
            lead += t["risk_high"].format(pct=_pct(p), day=_day(day, lang), ratio=f"{p / clim:.0f}", month=month)
        else:
            cap = ({"en": "under 1%", "ur": "1% سے کم"} if p < 0.01 else
                   {"en": f"at {_pct(p)} or less", "ur": f"زیادہ سے زیادہ {_pct(p)}"})[lang]
            lead += t["risk_calm"].format(cap=cap, month=month)
    if LONG_HORIZON.search(question):
        lead += t["horizon"]
    return lead, lines, ids


def model_card(lang: str) -> tuple[str, list[str], list[str]]:
    """How good Model A is, from the one-off test run (docs/model_a_test.json)."""
    t = TEXT[lang]
    test_file, groups_file = ROOT / "docs" / "model_a_test.json", ROOT / "docs" / "model_a_groups.json"
    if not test_file.exists():
        return "", [], []
    res = json.loads(test_file.read_text())
    model, clim = res["scores"]["model"]["all"], res["scores"]["climatology"]["all"]
    weak = "n/a"
    if groups_file.exists():
        weak = (json.loads(groups_file.read_text()).get("weakest") or {}).get("group", "n/a")
    tag = "docs/model_a_test.json"
    lines = [t["model_line"].format(n=f"{model[h]['n']:,}", h=h, m=f"{model[h]['brier']:.4f}",
                                    c=f"{clim[h]['brier']:.4f}") + f" [{tag}]" for h in ("24h", "48h", "72h")]
    m24, c24 = model["24h"]["brier"], clim["24h"]["brier"]
    lead = t["model_lead"].format(m=f"{m24:.4f}", c=f"{c24:.4f}", gain=round(100 * (1 - m24 / c24)), weak=weak)
    return lead, lines, [tag]


def table_facts(con, question: str, lang: str) -> tuple[str, list[str], list[str]]:
    """Numbers from gold tables, each line ending with its row id: (lead, lines, row ids)."""
    t, lead, lines, ids = TEXT[lang], "", [], []
    have = {n for (n,) in con.execute("SHOW TABLES").fetchall()}
    name = find_district(question, _districts(con)) if "districts" in have else None
    q = question.lower()
    if name and re.search(r"\b(rain|forecast|risk|weather|wet|dry|storm)|بارش|پیش گوئی|خطر|موسم", q) \
            and (FORECASTY.search(q) or not PAST.search(q)):
        lead, lines, ids = outlook(con, question, name, lang)
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
                lead = lead or t["price_one"].format(item=row[2], pkr=f"{row[4]:,.2f}", city=city, day=row[1])
    return lead, lines, ids


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
    hits = [h for h in doc_index.query(question, k=TOP_K_DISTRICT if district else TOP_K) if h["score"] >= MIN_SCORE]
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
    if not out.emergency and (THANKS.search(question) or GREETING.search(question)):
        out.lead = t["thanks"] if THANKS.search(question) else t["hello"]
        out.text = "\n".join([out.lead, t["disclaimer"]])
        return out
    with duckdb.connect(str(db_path), read_only=True) as con:
        lead, facts, out.row_ids = table_facts(con, question, lang)
        district = find_district(question, _districts(con))
        live = bool(facts) and not PAST.search(question)
        if not facts and not district and MODEL_Q.search(question):
            lead, facts, out.row_ids = model_card(lang)
            live = bool(facts)
        if not facts and not district:  # country-wide questions: what's happening, where rain, which prices
            lead, triples = digest_facts(con, question, lang)
            facts, out.row_ids = [f for f, _, _ in triples], [r for _, r, _ in triples]
            live = bool(triples)
    # questions answered from live tables are about now: old advisories would mislead, so no quotes
    hits = [] if live else retrieve(question, district)
    if hits and not lead:
        lead = (t["docs_lead_place"].format(place=_place(question, district)) if district
                else t["docs_lead"].format(n=len(hits)))
    if not hits and not facts:
        lead = t["idk_lead"]
        out.known = False
    out.lead = lead
    parts.append(lead)
    if hits:
        parts.append(t["docs"])
        for h in hits:
            parts.append(f'- "{_best_quote(h["text_full"], question, district)}" ({h["title"]}, p. {h["page"]}) '
                         f'[{h["section_id"]}]')
            out.citations.append(h["section_id"])
    if facts:
        parts.append(t["data"])
        parts += [f"- {f}" for f in facts]
    if not out.known:
        parts.append(t["idk"])
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
