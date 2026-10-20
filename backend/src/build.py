"""`make data`: verify the raw snapshot against the manifest, then rebuild clean/gold tables.

Offline only (D8). Sources not fetched yet are skipped with a message, so the thin slice
builds before every fetcher exists; once D1 through D6 are all fetched, every step is
mandatory and the pipeline will fail if any SHA-256 doesn't match.

Run order enforced by the dependency chain in TASKS.md:
  D1 manifest -> D2 districts -> D3 forecasts -> D4 IMERG -> D5 rain_district_day
  -> D6 thresholds/labels/climatology -> Q1 quality checks
"""
import sys

from src import districts, forecasts, manifest
from src import build_rain_district, build_thresholds, quality_checks


def main() -> int:
    # ------------------------------------------------------------------
    # Step 0: SHA-256 verification against manifest (D8 "Done when" check)
    # ------------------------------------------------------------------
    problems = manifest.verify()
    rows = manifest.read_manifest()
    print(f"manifest: {len(rows)} raw files, {len(problems)} problems")
    if problems:
        for p in problems:
            print("  " + p)
        return 1

    sources = {r["source"] for r in rows}

    # ------------------------------------------------------------------
    # Step 1: District boundaries (D2)
    # ------------------------------------------------------------------
    if districts.SOURCE in sources:
        districts.build()
    else:
        print(f"skip {districts.SOURCE}: not in manifest yet")

    # ------------------------------------------------------------------
    # Step 2: Forecast day table (D3)
    # ------------------------------------------------------------------
    if forecasts.SOURCE in sources:
        forecasts.build()
    else:
        print(f"skip {forecasts.SOURCE}: not in manifest yet")

    # ------------------------------------------------------------------
    # Step 3: District rain table (D5)
    # ------------------------------------------------------------------
    if build_rain_district.SOURCE in sources:
        build_rain_district.build()
    else:
        print(f"skip {build_rain_district.SOURCE}: not in manifest yet")

    # ------------------------------------------------------------------
    # Step 4: Thresholds, labels, baseline climatology (D6)
    # ------------------------------------------------------------------
    import duckdb
    from src.config import DB_PATH
    try:
        with duckdb.connect(str(DB_PATH), read_only=True) as con:
            has_rain = con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name='rain_district_day'"
            ).fetchone()[0] > 0
    except Exception:
        has_rain = False

    if has_rain:
        build_thresholds.build()
    else:
        print("skip thresholds/labels/climatology: rain_district_day not ready yet")

    # ------------------------------------------------------------------
    # Step 5: Quality checks (Q1)
    # ------------------------------------------------------------------
    rc = quality_checks.main()
    if rc != 0:
        return rc

    return 0


if __name__ == "__main__":
    sys.exit(main())
