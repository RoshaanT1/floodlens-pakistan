"""Raw-file store and manifest (task D1).

Every fetcher calls `save_raw`: the bytes are written untouched under data/raw/<source>/
and one row is appended to data/manifest.csv with source, query, fetch time (UTC),
SHA-256 and licence. `verify` re-hashes every file so `make data` can refuse a
tampered or missing snapshot.
"""
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from src.config import LICENCES, MANIFEST, RAW, ROOT

FIELDS = ["source", "query", "fetched_at_utc", "sha256", "bytes", "licence", "path"]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_raw(content: bytes, source: str, query: str, filename: str,
             manifest: Path = MANIFEST, raw_dir: Path = RAW) -> Path:
    """Write `content` untouched and append its manifest row. Returns the file path."""
    path = raw_dir / source / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    row = {
        "source": source,
        "query": query,
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": sha256_bytes(content),
        "bytes": len(content),
        "licence": LICENCES.get(source, "unknown"),
        "path": _rel(path),
    }
    new = not manifest.exists()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    return path


def read_manifest(manifest: Path = MANIFEST) -> list[dict]:
    if not manifest.exists():
        return []
    with open(manifest, newline="") as f:
        return list(csv.DictReader(f))


def latest(source: str, manifest: Path = MANIFEST) -> dict | None:
    """Most recent manifest row for a source, or None."""
    rows = [r for r in read_manifest(manifest) if r["source"] == source]
    return max(rows, key=lambda r: r["fetched_at_utc"]) if rows else None


def fetched_queries(source: str, manifest: Path = MANIFEST) -> set[str]:
    return {r["query"] for r in read_manifest(manifest) if r["source"] == source}


def verify(manifest: Path = MANIFEST) -> list[str]:
    """Return a list of problems; empty means every file matches its SHA-256."""
    problems = []
    for r in read_manifest(manifest):
        path = ROOT / r["path"]
        if not path.exists():
            problems.append(f"missing: {r['path']}")
        elif sha256_file(path) != r["sha256"]:
            problems.append(f"hash mismatch: {r['path']}")
    return problems


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


if __name__ == "__main__":
    import sys

    rows = read_manifest()
    problems = verify()
    for p in problems:
        print(p)
    print(f"manifest: {len(rows)} rows, {len(problems)} problems")
    sys.exit(1 if problems else 0)
