"""`make data`: verify the raw snapshot against the manifest, then rebuild clean/gold tables.

Offline only. Sources not fetched yet are skipped with a message, so the thin slice
builds before every fetcher exists; D8 makes every step mandatory.
"""
import sys

from src import districts, forecasts, manifest


def main() -> int:
    problems = manifest.verify()
    rows = manifest.read_manifest()
    print(f"manifest: {len(rows)} raw files, {len(problems)} problems")
    if problems:
        for p in problems:
            print("  " + p)
        return 1

    sources = {r["source"] for r in rows}
    steps = [(districts.SOURCE, districts.build), (forecasts.SOURCE, forecasts.build)]
    for source, step in steps:
        if source in sources:
            step()
        else:
            print(f"skip {source}: not in manifest yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
