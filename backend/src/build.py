"""`make data`: verify the raw snapshot against the manifest, then rebuild clean/gold tables.

Offline only. Sources not fetched yet are skipped with a message, so the thin slice
builds before every fetcher exists; D8 makes every step mandatory.
"""
import sys

from src import attributes, districts, documents, forecasts, imerg, labels, manifest, model_a, quality, rain, spi

# (source the step needs, step, tables the quality agent checks after it)
STEPS = [
    (districts.SOURCE, districts.build, ["districts"]),
    (forecasts.SOURCE, forecasts.build, ["forecast_day"]),
    (forecasts.LIVE_SOURCE, forecasts.build_live, []),  # live view only; never a training input
    (attributes.UNOSAT_SOURCE, attributes.build, []),   # D7; needs all three attribute sources
    ("ndma_sitrep", documents.build, []),               # R1 catalogue; citations only, never training
    (spi.SOURCE, spi.build, []),                         # B2/B3: prices flagged, never filled
    (imerg.SOURCE, rain.build, ["rain_district_day"]),
    (imerg.SOURCE, labels.main, []),  # labels are built from quality-checked rain
    (imerg.SOURCE, model_a.features, []),
    (imerg.SOURCE, model_a.score_live, []),  # whichever artifact is current (A4); none -> skipped
]


def main() -> int:
    problems = manifest.verify()
    rows = manifest.read_manifest()
    print(f"manifest: {len(rows)} raw files, {len(problems)} problems")
    if problems:
        for p in problems:
            print("  " + p)
        return 1

    sources = {r["source"] for r in rows}
    log = []
    for source, step, tables in STEPS:
        if source not in sources:
            print(f"skip {step.__module__}.{step.__name__}: {source} not in manifest yet")
            continue
        step()
        log += quality.run(tables)  # each table is checked exactly once, right after it is built
    print(quality.summary(quality.write_log(log)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
