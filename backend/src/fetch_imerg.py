"""IMERG Late Run daily fetcher, cropped to Pakistan's bounding box, 2015 to now (task D4).

Needs: D1 (manifest writer), S4 (Earthdata auth).
Done when: every day is stored with manifest rows.

Downloads via earthaccess (NASA's Earthdata client), then hands the raw bytes to
src.manifest.save_raw so every fetcher in the repo writes the same manifest.csv
format and lands files under the same data/raw/<source>/ layout.

SETUP:
    pip install earthaccess python-dotenv
    .env must have EARTHDATA_TOKEN (or EARTHDATA_USERNAME + EARTHDATA_PASSWORD).

Uses the "imerg_late_daily" key already present in src/config.py's LICENCES dict.
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import earthaccess
from dotenv import load_dotenv

from src.manifest import save_raw

SOURCE = "imerg_late_daily"
SHORT_NAME = "GPM_3IMERGDL"   # IMERG Late Run, daily
VERSION = "07"

# Pakistan bounding box: (west, south, east, north)
PAKISTAN_BBOX = (60.9, 23.6, 77.8, 37.1)

START_DATE = date(2015, 1, 1)   # per S2 — confirm coverage before relying on this
END_DATE = date.today()


def login():
    import os
    load_dotenv()
    # .env may store the token as EARTH_DATA_TOKEN (legacy name); remap so
    # earthaccess can find it under the canonical EARTHDATA_TOKEN key.
    if not os.getenv("EARTHDATA_TOKEN") and os.getenv("EARTH_DATA_TOKEN"):
        os.environ["EARTHDATA_TOKEN"] = os.environ["EARTH_DATA_TOKEN"].strip()
    auth = earthaccess.login(strategy="environment")
    if not auth.authenticated:
        raise RuntimeError(
            "Earthdata auth failed — check EARTHDATA_TOKEN (or EARTH_DATA_TOKEN) "
            "and EARTHDATA_USERNAME/EARTHDATA_PASSWORD in .env"
        )
    return auth


def fetch_day(day: date) -> list[Path]:
    """Download + save the IMERG Late granule for one UTC day via save_raw. Returns saved paths."""
    start = day.isoformat()
    end = (day + timedelta(days=1)).isoformat()
    query = f"short_name={SHORT_NAME} version={VERSION} bbox={PAKISTAN_BBOX} date={day}"

    results = earthaccess.search_data(
        short_name=SHORT_NAME,
        version=VERSION,
        bounding_box=PAKISTAN_BBOX,
        temporal=(start, end),
    )
    if not results:
        print(f"  no granule found for {day}")
        return []

    saved_paths = []
    with tempfile.TemporaryDirectory() as tmp:
        downloaded = earthaccess.download(results, tmp)
        for f in downloaded:
            f = Path(f)
            content = f.read_bytes()
            # keep the original granule filename, prefixed by date for easy sorting
            filename = f"{day.isoformat()}_{f.name}"
            saved_path = save_raw(
                content=content,
                source=SOURCE,
                query=query,
                filename=filename,
            )
            saved_paths.append(saved_path)
    return saved_paths


def fetch_range(start_date: date, end_date: date) -> None:
    login()
    day = start_date
    total = (end_date - start_date).days + 1
    done = 0
    while day <= end_date:
        print(f"[{done + 1}/{total}] fetching {day} ...")
        try:
            fetch_day(day)
        except Exception as e:
            print(f"  FAILED for {day}: {e}")
        day += timedelta(days=1)
        done += 1


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "--test-one-day":
        # S4 "done when" check: one day only
        login()
        fetch_day(date(2024, 1, 1))
    else:
        fetch_range(START_DATE, END_DATE)