"""Local HTTP API for the Insight Agent (R3/R5), used by the dashboard's Ask page.

    .venv-insight/bin/uvicorn src.insight_api:app --host 127.0.0.1 --port 8001

GET /api/ask?q=...&lang=en|ur -> {text, citations, row_ids, known, emergency}
Answers follow src.insight's rules (quotes with section ids, numbers with row ids,
"I don't know" below the retrieval threshold). Local only; not exposed publicly.
"""
from fastapi import FastAPI, HTTPException, Query

from src import doc_index, insight

app = FastAPI(title="FloodLens Insight Agent")


@app.on_event("startup")
def _warm() -> None:
    doc_index._model()
    doc_index._loaded()


@app.get("/api/ask")
def ask(q: str = Query(..., min_length=2, max_length=500), lang: str = Query("en", pattern="^(en|ur)$")) -> dict:
    try:
        return insight.answer(q, lang=lang).__dict__
    except FileNotFoundError as e:
        raise HTTPException(503, f"index not built: {e}") from e
