"""Local HTTP API for the Insight Agent (R3/R5), used by the dashboard's Ask page.

    .venv-insight/bin/uvicorn src.insight_api:app --host 127.0.0.1 --port 8001

GET /api/ask?q=...&lang=en|ur -> {text, citations, row_ids, known, emergency}
Answers follow src.insight's rules (quotes with section ids, numbers with row ids,
"I don't know" below the retrieval threshold). Exposed read-only through deploy/tunnel.sh
(Cloudflare quick tunnel) so the public dashboard's Ask page can reach it.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src import doc_index, insight

app = FastAPI(title="FloodLens Insight Agent")
# read-only GET endpoint, called from the Hugging Face Space through a Cloudflare tunnel
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


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
