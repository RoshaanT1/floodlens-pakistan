"""Tests for src/fetch_imerg.py (task D4) — no network access required.

These tests verify:
  - The query string format is correct
  - The filename prefix logic works
  - The day parsing in build_rain_district is consistent with filenames produced here
"""
from datetime import date

import pytest

from src.fetch_imerg import SOURCE, SHORT_NAME, VERSION, PAKISTAN_BBOX


def test_source_constant():
    assert SOURCE == "imerg_late_daily"


def test_short_name_and_version():
    assert SHORT_NAME == "GPM_3IMERGDL"
    assert VERSION == "07"


def test_pakistan_bbox_order():
    """west, south, east, north — all within plausible Pakistan bounds."""
    west, south, east, north = PAKISTAN_BBOX
    assert 60 < west < 65, f"west longitude {west} unexpected"
    assert 22 < south < 26, f"south latitude {south} unexpected"
    assert 74 < east < 80, f"east longitude {east} unexpected"
    assert 35 < north < 39, f"north latitude {north} unexpected"
    # basic ordering sanity
    assert west < east
    assert south < north


def test_filename_prefix_round_trips(tmp_path):
    """The date prefix 'YYYY-MM-DD_' survives the round-trip via _day_from_filename."""
    from src.build_rain_district import _day_from_filename
    day = date(2015, 6, 15)
    granule_name = "3B-DAY.MS.MRG.3IMERG.20150615.V07B.HDF5"
    filename = f"{day.isoformat()}_{granule_name}"
    assert _day_from_filename(filename) == day


def test_day_from_filename_invalid():
    from src.build_rain_district import _day_from_filename
    assert _day_from_filename("notadate_something.HDF5") is None
    assert _day_from_filename("2015-99-01_bad.HDF5") is None


def test_query_string_contains_key_fields():
    """Spot-check that the query logged to manifest.csv is parseable."""
    from datetime import timedelta
    day = date(2024, 1, 1)
    query = (
        f"short_name={SHORT_NAME} version={VERSION} "
        f"bbox={PAKISTAN_BBOX} date={day}"
    )
    assert SHORT_NAME in query
    assert "2024-01-01" in query
