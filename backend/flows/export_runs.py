"""Export the run history for the judged window (task P5 / E4). Run once, on Wednesday.

    .venv/bin/python -m flows.export_runs                      # Tue 20 Oct 16:00 to Wed 21 Oct 16:00 PKT
    .venv/bin/python -m flows.export_runs --start ... --end ...  # ISO datetimes with offset

Reads every `floodlens-hourly` run whose scheduled or actual start falls in the window from
the Prefect API (PREFECT_API_URL) and writes docs/prefect_runs.csv unedited: one row per run,
sorted by expected start, with state, timings and the final state message.
"""
import argparse
import asyncio
import csv
from datetime import datetime

from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    FlowFilter, FlowFilterName, FlowRunFilter, FlowRunFilterExpectedStartTime,
)
from prefect.client.schemas.sorting import FlowRunSort

from src.config import ROOT

WINDOW = ("2026-10-20T16:00:00+05:00", "2026-10-21T16:00:00+05:00")
OUT = ROOT / "docs" / "prefect_runs.csv"
FIELDS = ["flow_run_id", "name", "deployment_id", "state", "state_message",
          "expected_start_utc", "start_utc", "end_utc", "duration_s", "run_count"]


def _iso(t) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else ""


async def fetch(start: datetime, end: datetime) -> list[dict]:
    async with get_client() as client:
        runs, offset = [], 0
        while True:
            page = await client.read_flow_runs(
                flow_filter=FlowFilter(name=FlowFilterName(any_=["floodlens-hourly"])),
                flow_run_filter=FlowRunFilter(
                    expected_start_time=FlowRunFilterExpectedStartTime(after_=start, before_=end)),
                sort=FlowRunSort.EXPECTED_START_TIME_ASC, limit=200, offset=offset)
            runs += page
            if len(page) < 200:
                break
            offset += 200
    return [{
        "flow_run_id": str(r.id), "name": r.name,
        "deployment_id": str(r.deployment_id or ""),
        "state": r.state_name, "state_message": (r.state.message or "") if r.state else "",
        "expected_start_utc": _iso(r.expected_start_time), "start_utc": _iso(r.start_time),
        "end_utc": _iso(r.end_time), "duration_s": round(r.total_run_time.total_seconds()),
        "run_count": r.run_count,
    } for r in runs]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=datetime.fromisoformat, default=datetime.fromisoformat(WINDOW[0]))
    p.add_argument("--end", type=datetime.fromisoformat, default=datetime.fromisoformat(WINDOW[1]))
    p.add_argument("--out", default=str(OUT))
    a = p.parse_args()
    rows = asyncio.run(fetch(a.start, a.end))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    states = {}
    for r in rows:
        states[r["state"]] = states.get(r["state"], 0) + 1
    print(f"{len(rows)} runs -> {a.out}: {states}")


if __name__ == "__main__":
    main()
