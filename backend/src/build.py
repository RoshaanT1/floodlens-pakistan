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


# Warehouse layers as files (data/raw is written by the fetchers, never edited):
CLEAN_TABLES = ["districts", "district_attributes", "forecast_day", "forecast_live", "rain_district_day",
                "spi_price", "spi_week_quality", "documents", "quality_log"]
GOLD_TABLES = ["thresholds", "labels", "baseline_climatology", "features_a", "risk_live"]


def export_layers(db_path=None) -> None:
    """Write clean and processed (gold) tables to Parquet, atomically per file."""
    import duckdb
    from src.config import CLEAN, DB_PATH, GOLD
    with duckdb.connect(str(db_path or DB_PATH), read_only=True) as con:
        have = {t for (t,) in con.execute("SHOW TABLES").fetchall()}
        for layer, tables in ((CLEAN, CLEAN_TABLES), (GOLD, GOLD_TABLES)):
            layer.mkdir(parents=True, exist_ok=True)
            for t in tables:
                if t in have:
                    tmp = layer / f".{t}.parquet.tmp"
                    con.execute(f"COPY {t} TO '{tmp}' (FORMAT parquet)")
                    tmp.replace(layer / f"{t}.parquet")
    print(f"layers: data/clean ({len([t for t in CLEAN_TABLES if t in have])} tables), "
          f"data/gold ({len([t for t in GOLD_TABLES if t in have])} tables) as Parquet")


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
    export_layers()
    return 0


if __name__ == "__main__":
    sys.exit(main())
