"""Insight Agent tests (task R4) on the real document index and gold tables.

    .venv-insight/bin/python -m pytest -q tests/test_insight.py

Skipped in the pipeline venv (no FAISS) or before the index is built. MIN_SCORE and the
hazard-word gate were chosen on these same questions, so this is a check of the rules,
not an unbiased accuracy estimate.
"""
import re

import duckdb
import pytest

faiss = pytest.importorskip("faiss")
from src import doc_index, insight  # noqa: E402
from src.config import DB_PATH  # noqa: E402

pytestmark = pytest.mark.skipif(not doc_index.INDEX.exists(), reason="run `src.doc_index build` first")

ANSWERABLE = [  # (question, text the cited section's title must contain)
    ("How many people died in Buner flash floods in August 2025?", "Situation Report"),
    ("What did NDMA advise about the Chenab river?", "CHENAB"),
    ("Deaths in Swat during monsoon 2025", "Situation Report"),
    ("Flood warning for river Sutlej", "SUTLEJ"),
    ("Glacial lake outburst flood alert Gilgit-Baltistan", "GLOF"),
    ("دریائے چناب میں سیلاب کی وارننگ", "CHENAB"),
]
UNANSWERABLE = [
    "What is the capital of France?", "Who won the cricket world cup in 2023?",
    "How do I bake a chocolate cake?", "Explain photosynthesis", "Train timings from Lahore to Karachi",
    "پیرس کس ملک کا دارالحکومت ہے؟",
]
SECTION = re.compile(r"\[([0-9a-f]{16}-p\d+-s\d+)\]$")


@pytest.mark.parametrize("question,title", ANSWERABLE)
def test_answerable_questions_cite_the_right_document(question, title):
    a = insight.answer(question)
    assert a.known and a.citations
    sections = {h["section_id"]: h for h in doc_index.query(question, k=insight.TOP_K)}
    assert any(title.lower() in sections[c]["title"].lower() for c in a.citations)


@pytest.mark.xfail(reason="known weakness: Urdu-only questions retrieve poorly with multilingual-e5-small")
def test_urdu_casualty_question_finds_swat_sitrep():
    a = insight.answer("سوات میں سیلاب سے ہلاکتیں")
    sections = {h["section_id"]: h for h in doc_index.query("سوات میں سیلاب سے ہلاکتیں", k=insight.TOP_K)}
    assert any("Situation Report" in sections[c]["title"] for c in a.citations)


@pytest.mark.parametrize("question", UNANSWERABLE)
def test_unsupported_questions_get_i_dont_know(question):
    a = insight.answer(question)
    assert not a.known and not a.citations and not a.row_ids


@pytest.mark.parametrize("lang", ["en", "ur"])
def test_numbers_match_their_row_ids(lang):
    a = insight.answer("Price of wheat flour in Lahore", lang=lang)
    assert a.row_ids
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        for row_id in a.row_ids:
            avg = con.execute("SELECT avg_pkr FROM spi_price WHERE row_id = ?", [row_id]).fetchone()[0]
            line = next(l for l in a.text.splitlines() if l.endswith(f"[{row_id}]"))
            assert f"{avg:,.2f}" in line


def test_leading_question_gets_no_invented_fact():
    a = insight.answer("Why did NDMA say Lahore was hit by a tsunami in 2025?")
    assert "tsunami" not in a.text.replace("Why did NDMA say", "").lower() or not a.known


def test_every_line_is_a_template_a_quote_or_a_table_fact():
    a = insight.answer("How many people died in Buner flash floods in August 2025?")
    templates = set(insight.TEXT["en"].values())
    for line in a.text.splitlines():
        if line == a.lead:  # the lead is a template filled from the facts below it
            continue
        assert line in templates or SECTION.search(line) or re.search(r"\[[^\]]+\]$", line), line


@pytest.mark.parametrize("question,lang", [("We are trapped by flood water, please help", "en"),
                                           ("ہم سیلاب میں پھنس گئے ہیں، مدد کریں", "ur")])
def test_emergencies_point_to_1122_and_ndma(question, lang):
    a = insight.answer(question, lang=lang)
    assert a.emergency and "1122" in a.text.splitlines()[0]


def test_greetings_get_an_introduction_not_a_fact():
    a = insight.answer("hello")
    assert a.known and a.lead == insight.TEXT["en"]["hello"] and not a.citations and not a.row_ids


def test_forecast_questions_use_live_rows_not_old_advisories():
    a = insight.answer("When will it rain in Karachi?")
    assert "Karachi" in a.lead and not a.citations
    assert a.row_ids and all(r.startswith("PK721_") for r in a.row_ids)


def test_model_question_cites_the_test_results_file():
    a = insight.answer("How accurate is your model?")
    assert a.row_ids == ["docs/model_a_test.json"] and "0.0177" in a.lead


def test_short_district_question_still_finds_its_reports():
    a = insight.answer("how many died in buner in august 2025")
    assert a.known and a.citations and "Buner" in a.lead
