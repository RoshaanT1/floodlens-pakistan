"""Paths and fixed decisions shared by every module.

The split dates and target definitions are frozen (see TASKS.md, "Fixed decisions").
"""
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
GOLD = DATA / "gold"
MANIFEST = DATA / "manifest.csv"
# The hourly flow builds into a scratch copy and swaps it in, so a failed run never
# touches the live database (flows/hourly.py).
DB_PATH = Path(os.environ.get("FLOODLENS_DB", DATA / "floodlens.duckdb"))

# Fixed splits (never change after seeing results)
TRAIN_END = date(2025, 6, 30)
VALID_START, VALID_END = date(2025, 7, 1), date(2025, 12, 31)
TEST_START, TEST_END = date(2026, 1, 1), date(2026, 9, 30)

# Data windows
# Previous Runs archive is empty before ~Feb 2024 (checked 2026-10-20); declaration says Jan
FORECAST_START = date(2024, 2, 1)
IMERG_START = date(2015, 1, 1)
THRESHOLD_YEARS = (2015, 2023)

# Pakistan bounding box (lat_min, lat_max, lon_min, lon_max), with a small margin
PAK_BBOX = (23.5, 37.2, 60.8, 77.9)

LICENCES = {
    "ocha_cod_ab": "CC BY-IGO (OCHA via HDX)",
    "open_meteo_previous_runs": "CC BY 4.0 (Open-Meteo)",
    "imerg_late_daily": "NASA EOSDIS open data policy",
    "open_meteo_live_forecast": "CC BY 4.0 (Open-Meteo)",
    "ndma_listing": "NDMA website EULA: limited licence for personal/organisational use; not redistributed",
    "ndma_sitrep": "NDMA website EULA: limited licence for personal/organisational use; not redistributed",
    "ndma_advisory": "NDMA website EULA: limited licence for personal/organisational use; not redistributed",
    "pmd_document": "Government of Pakistan (PMD) public document; terms not stated; not redistributed",
}
