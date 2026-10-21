"""Hourly pipeline (tasks P1, P3): fetch new data, rebuild, publish status.json.

    .venv/bin/python -m flows.hourly run     # one run now, no schedule
    .venv/bin/python -m flows.hourly serve   # long-running: a run at 5 past every hour

Each run:
  1. fetches what is new: archived forecasts (Previous Runs backfill, inside a
     per-UTC-day call budget read from the manifest), the live forecast (at most every 6 h) and
     IMERG Late days (skipped, with a logged reason, while .env has no Earthdata login),
     and once a day the PBS weekly prices and the newest NDMA advisories and sitreps;
  2. rebuilds every table (`make data`) into a scratch copy of the database and swaps it
     in only if the build passes, so a failed run never touches the live database;
  3. exports frontend/public/data/status.json (atomic write).

Safe to repeat: fetchers skip queries already in the manifest, and the build is a pure
function of the raw snapshot. One run at a time (limit=1); a run still going at the next
slot makes that slot wait rather than overlap.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

from prefect import flow, get_run_logger, task

from src import documents, forecasts, imerg, manifest, spi
from src.config import DB_PATH, FORECAST_START, ROOT

CALLS_PER_DAY = 9000       # per UTC day; Open-Meteo free tier is 10,000; keep headroom for retries
CALLS_PER_RUN = 2000       # ~25 min of paced requests, so a run ends well inside its hour
IMERG_DAYS_PER_RUN = 300   # ~1 h of downloads once a login exists; resumes next run
STATUS = ROOT / "data" / "flow_status.json"


def _yesterday() -> date:
    return datetime.now(timezone.utc).date() - timedelta(days=1)


@task(retries=2, retry_delay_seconds=120)
def fetch_archived_forecasts() -> str:
    log = get_run_logger()
    spent = forecasts.calls_spent()
    budget = min(CALLS_PER_RUN, CALLS_PER_DAY - spent)
    if budget < 150:  # one batch costs ~130
        msg = f"skipped: {spent:.0f} calls used today (UTC; cap {CALLS_PER_DAY})"
        log.info(msg)
        return msg
    try:
        forecasts.fetch(FORECAST_START, _yesterday(), budget)
    except forecasts.DailyLimitReached as e:
        log.warning(str(e))
        return f"stopped: {e}"
    return f"ok: {forecasts.calls_spent() - spent:.0f} calls this run"


@task(retries=2, retry_delay_seconds=120)
def fetch_live_forecast() -> str:
    if forecasts.calls_spent() > CALLS_PER_DAY:
        return "skipped: daily call budget used"
    try:
        return "ok: new file" if forecasts.fetch_live() else "ok: fresh enough"
    except forecasts.DailyLimitReached as e:
        return f"stopped: {e}"


@task(retries=1, retry_delay_seconds=300)
def fetch_imerg() -> str:
    log = get_run_logger()
    if not imerg.has_credentials():
        msg = "skipped: no EARTHDATA_TOKEN (or username/password) in backend/.env"
        log.warning(msg)
        return msg
    try:
        imerg.fetch(imerg.IMERG_START, _yesterday(), workers=4, max_days=IMERG_DAYS_PER_RUN)
    except SystemExit as e:  # login rejected; keep the rest of the run going
        log.error(str(e))
        return f"failed: {e}"
    return "ok"


def _due(listing_source: str, hours: int = 24) -> bool:
    last = manifest.latest(listing_source)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return last is None or last["fetched_at_utc"] < since


@task(retries=1, retry_delay_seconds=300)
def fetch_spi_daily() -> str:
    """PBS publishes one week each Thursday; checking daily is plenty."""
    if not _due(spi.LISTING):
        return "ok: checked in the last 24 h"
    try:
        spi.fetch()
    except Exception as e:  # PBS down must not stop the forecast pipeline
        get_run_logger().error(f"pbs: {e}")
        return f"failed: {e.__class__.__name__}; retried next run"
    return "ok: checked"


@task(retries=1, retry_delay_seconds=300)
def fetch_documents_daily() -> str:
    if not _due(documents.LISTING):
        return "ok: checked in the last 24 h"
    try:
        return f"ok: {documents.fetch_recent()} new documents"
    except Exception as e:  # NDMA down must not stop the forecast pipeline
        get_run_logger().error(f"ndma: {e}")
        return f"failed: {e.__class__.__name__}; retried next run"


def _run(cmd: list[str], env: dict) -> None:
    log = get_run_logger()
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    for line in (p.stdout + p.stderr).strip().splitlines()[-40:]:
        log.info(line)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} exited {p.returncode}")


@task(retries=1, retry_delay_seconds=60)
def rebuild() -> None:
    """`make data` against a scratch copy; swapped in only on success."""
    scratch = DB_PATH.with_suffix(".building.duckdb")
    scratch.unlink(missing_ok=True)
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, scratch)
    env = {**os.environ, "FLOODLENS_DB": str(scratch)}
    try:
        _run([sys.executable, "-m", "src.build"], env)
    except Exception:
        scratch.unlink(missing_ok=True)
        raise
    scratch.replace(DB_PATH)


@task(retries=1, retry_delay_seconds=60)
def export() -> None:
    _run([sys.executable, "-m", "src.export_frontend"], dict(os.environ))


@flow(name="floodlens-hourly")
def hourly() -> dict:
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fetched = {
        "open_meteo_previous_runs": fetch_archived_forecasts(),
        "open_meteo_live_forecast": fetch_live_forecast(),
        "imerg_late_daily": fetch_imerg(),
        "pbs_spi_annex": fetch_spi_daily(),
        "ndma_documents": fetch_documents_daily(),
    }
    rebuild()
    status = {"last_success_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "run_started_utc": started, "fetch": fetched}
    STATUS.write_text(json.dumps(status, indent=2))  # read by export_frontend
    export()
    return status


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        hourly()
    elif sys.argv[1:] == ["serve"]:
        hourly.serve(name="hourly", cron="5 * * * *", limit=1)
    else:
        raise SystemExit("usage: python -m flows.hourly run|serve")
