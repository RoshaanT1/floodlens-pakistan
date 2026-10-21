"""Section index for the Insight Agent (task R2). Runs in the separate .venv-insight.

    .venv-insight/bin/python -m src.doc_index build          # PDFs -> sections -> FAISS index
    .venv-insight/bin/python -m src.doc_index query "..."    # top sections with source and section ids

Sections: each PDF page's text is split on blank lines into chunks of at most MAX_CHARS
characters. section_id = <doc_id>-p<page>-s<k>, stable for the same raw file.
Embeddings: intfloat/multilingual-e5-small (MIT licence; 100 languages including Urdu),
using the model's "passage: " / "query: " prefixes, L2-normalised, so inner product is
cosine similarity. The index lives in data/gold (rebuilt from raw, not tracked in git).
"""
import json
import re
import sys

import numpy as np
import pandas as pd

from src import documents, manifest
from src.config import GOLD, ROOT

MODEL = "intfloat/multilingual-e5-small"
MAX_CHARS = 900
SOURCES = ("ndma_sitrep", "ndma_advisory", "pmd_document")
INDEX = GOLD / "doc_index.faiss"
SECTIONS = GOLD / "doc_sections.parquet"


def split_page(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Blank-line paragraphs, packed into chunks of at most max_chars (long ones cut at sentences)."""
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    pieces = []
    for p in filter(None, paras):
        while len(p) > max_chars:
            cut = p.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > max_chars // 3 else max_chars
            pieces.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            pieces.append(p)
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + 1 + len(p) > max_chars:
            chunks.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    return chunks + ([cur] if cur else [])


def sections() -> pd.DataFrame:
    from pypdf import PdfReader

    meta = {}
    for r in sorted(manifest.read_manifest(), key=lambda r: r["fetched_at_utc"]):
        if r["source"] == documents.LISTING:
            for c in documents.parse_cards((ROOT / r["path"]).read_text("utf-8", "replace")):
                meta[c["url"]] = c
    rows, seen = [], set()
    for r in manifest.read_manifest():
        if r["source"] not in SOURCES or r["sha256"] in seen:
            continue
        seen.add(r["sha256"])
        doc_id = r["sha256"][:16]
        m = meta.get(r["query"], {})
        try:
            pages = PdfReader(ROOT / r["path"]).pages
            texts = [p.extract_text() or "" for p in pages]
        except Exception as e:
            print(f"  skip {r['path']}: {e}")
            continue
        for page_no, text in enumerate(texts, 1):
            for k, chunk in enumerate(split_page(text)):
                if len(chunk) < 40:  # page furniture: headers, page numbers
                    continue
                rows.append({"section_id": f"{doc_id}-p{page_no}-s{k}", "doc_id": doc_id, "source": r["source"],
                             "title": m.get("title") or r["query"].rsplit("/", 1)[-1],
                             "published": str(m.get("published") or ""), "url": r["query"],
                             "page": page_no, "text": chunk})
    return pd.DataFrame(rows)


def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL, device="cpu")


def build() -> int:
    import faiss

    df = sections()
    if df.empty:
        raise SystemExit("no documents in manifest; run `python -m src.documents fetch`")
    emb = _model().encode(["passage: " + t for t in df.text], batch_size=64, normalize_embeddings=True,
                          show_progress_bar=False).astype(np.float32)
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    GOLD.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX))
    df.to_parquet(SECTIONS, index=False)
    print(f"doc index: {len(df)} sections from {df.doc_id.nunique()} documents -> {INDEX}")
    return len(df)


def query(text: str, k: int = 5) -> list[dict]:
    import faiss

    index = faiss.read_index(str(INDEX))
    df = pd.read_parquet(SECTIONS)
    q = _model().encode(["query: " + text], normalize_embeddings=True).astype(np.float32)
    scores, ids = index.search(q, k)
    return [{**df.iloc[i][["section_id", "source", "title", "published", "url", "page"]].to_dict(),
             "score": float(s), "text": df.iloc[i].text[:300], "text_full": df.iloc[i].text}
            for s, i in zip(scores[0], ids[0]) if i >= 0]


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build()
    elif sys.argv[1] == "query":
        print(json.dumps(query(" ".join(sys.argv[2:])), ensure_ascii=False, indent=2))
