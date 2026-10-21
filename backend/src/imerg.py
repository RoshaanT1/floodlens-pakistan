"""Satellite rainfall (task D4): NASA GPM IMERG V07 Late Run daily (GPM_3IMERGDL), 2015 to now.

    python -m src.imerg fetch [--start 2015-01-01] [--end YYYY-MM-DD] [--workers 4]

Each day is requested from GES DISC OPeNDAP already cropped to Pakistan's bounding box
(precipitation, precipitation_cnt, lat, lon), so a day is ~100 KB instead of a global file.
The response is stored untouched with its manifest row; a day whose query is already in the
manifest is skipped, so the command resumes after an interruption.

File names carry a processing version (V07B for older days, V07C for recent ones), so names
come from the public monthly directory listing rather than being built by hand.

Downloads need a NASA Earthdata login with GES DISC authorised, read from .env:
EARTHDATA_TOKEN (preferred), or EARTHDATA_USERNAME + EARTHDATA_PASSWORD.
"""
import argparse
import io
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

import requests
import xarray as xr
from dotenv import load_dotenv

from src import manifest
from src.config import IMERG_START, PAK_BBOX, ROOT

SOURCE = "imerg_late_daily"
DATA_URL = "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDL.07"
DAP_URL = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDL.07"
VARIABLES = ["precipitation", "precipitation_cnt"]
FILL = -9999.9
URS_HOST = "urs.earthdata.nasa.gov"
NETCDF_MAGIC = (b"\x89HDF", b"CDF")  # netCDF-4 (HDF5) or classic
# Earthdata Cloud copy of the same collection, with a server-side-subsetting OPeNDAP (DAP4).
# Used by default since 21 Oct 2026, when gpm1 stopped answering this machine; same bytes
# per pixel (checked on 14 Aug 2025: identical grid and maximum).
CLOUD_COLLECTION = "C2723754859-GES_DISC"
CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"
CLOUD_DAP = "https://opendap.earthdata.nasa.gov/collections/{cid}/granules/GPM_3IMERGDL.07%3A{name}"


def grid_slices(bbox=PAK_BBOX) -> tuple[tuple[int, int], tuple[int, int]]:
    """Index ranges (inclusive) on the 0.1 deg grid: lon[i] = -179.95 + 0.1 i, lat[j] = -89.95 + 0.1 j."""
    lat_min, lat_max, lon_min, lon_max = bbox
    lon = (int((lon_min + 180) * 10), int((lon_max + 180) * 10))
    lat = (int((lat_min + 90) * 10), int((lat_max + 90) * 10))
    return lon, lat


def build_query(filename: str, day: date) -> str:
    (i0, i1), (j0, j1) = grid_slices()
    arrays = [f"{v}[0:1:0][{i0}:1:{i1}][{j0}:1:{j1}]" for v in VARIABLES]
    arrays += [f"lon[{i0}:1:{i1}]", f"lat[{j0}:1:{j1}]"]
    return f"{DAP_URL}/{day:%Y/%m}/{filename}.nc4?" + ",".join(arrays)


class EarthdataSession(requests.Session):
    """Keeps credentials across the redirect to and from urs.earthdata.nasa.gov (NASA's recipe)."""

    def rebuild_auth(self, prepared, response):
        if "Authorization" in prepared.headers:
            old = requests.utils.urlparse(response.request.url).hostname
            new = requests.utils.urlparse(prepared.url).hostname
            if old != new and URS_HOST not in (old, new):
                del prepared.headers["Authorization"]


def has_credentials() -> bool:
    load_dotenv(ROOT / ".env")
    return bool(os.getenv("EARTHDATA_TOKEN")
                or (os.getenv("EARTHDATA_USERNAME") and os.getenv("EARTHDATA_PASSWORD")))


def session() -> EarthdataSession:
    """Earthdata token (preferred: revocable, expires) or username + password, from .env."""
    load_dotenv(ROOT / ".env")
    s = EarthdataSession()
    token = (os.getenv("EARTHDATA_TOKEN") or "").strip()
    user, pw = os.getenv("EARTHDATA_USERNAME"), os.getenv("EARTHDATA_PASSWORD")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    elif user and pw:
        s.auth = (user, pw)
    else:
        raise SystemExit("set EARTHDATA_TOKEN (or EARTHDATA_USERNAME and EARTHDATA_PASSWORD) in .env")
    return s


def list_month_cmr(year: int, month: int) -> dict[date, str]:
    """{day: granule file name} for one month, from NASA's public CMR search (no login)."""
    start = date(year, month, 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    out, page = {}, 1
    while True:
        for attempt in range(1, 6):
            try:
                r = requests.get(CMR_GRANULES, timeout=120, params={
                    "collection_concept_id": CLOUD_COLLECTION, "page_size": 100, "page_num": page,
                    "temporal": f"{start}T00:00:00Z,{end - timedelta(days=1)}T23:59:59Z"})
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(10 * attempt)
        entries = r.json()["feed"]["entry"]
        for g in entries:
            name = g["title"].split(":", 1)[-1]
            m = re.search(r"3IMERG\.(\d{8})-", name)
            out[datetime.strptime(m.group(1), "%Y%m%d").date()] = name
        if len(entries) < 100:
            return out
        page += 1


def build_cloud_query(filename: str) -> str:
    (i0, i1), (j0, j1) = grid_slices()
    ce = ";".join([f"/{v}[0:1:0][{i0}:1:{i1}][{j0}:1:{j1}]" for v in VARIABLES]
                  + [f"/lon[{i0}:1:{i1}]", f"/lat[{j0}:1:{j1}]"])
    from urllib.parse import quote
    return CLOUD_DAP.format(cid=CLOUD_COLLECTION, name=filename) + ".dap.nc4?dap4.ce=" + quote(ce, safe="/:;")


def list_month(s: requests.Session, year: int, month: int) -> dict[date, str]:
    """{day: filename} for one month, from the public directory listing."""
    for attempt in range(1, 6):  # the listing host drops the odd TLS handshake
        try:
            r = s.get(f"{DATA_URL}/{year}/{month:02d}/", timeout=120)
            break
        except requests.RequestException as e:
            print(f"  listing {year}-{month:02d} attempt {attempt} failed: {e.__class__.__name__}")
            if attempt == 5:
                raise
            time.sleep(10 * attempt)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    out = {}
    for name in set(re.findall(r'href="(3B-DAY-L\.MS\.MRG\.3IMERG\.(\d{8})-[^"]+?\.nc4)"', r.text)):
        out[datetime.strptime(name[1], "%Y%m%d").date()] = name[0]
    return out


def download(s: requests.Session, query: str, tries: int = 5) -> bytes:
    for attempt in range(1, tries + 1):
        try:
            r = s.get(query, timeout=300)
            if r.status_code == 401:
                raise SystemExit("Earthdata login rejected (401): check .env and that GES DISC is authorised")
            r.raise_for_status()
            if not r.content.startswith(NETCDF_MAGIC):  # login page or error text instead of data
                raise ValueError(f"not a netCDF response ({r.headers.get('content-type')})")
            return r.content
        except (requests.RequestException, ValueError) as e:
            print(f"  attempt {attempt} failed: {e}")
            if attempt == tries:
                raise
    raise AssertionError("unreachable")


def fetched_days() -> set[date]:
    """Days already stored, whichever endpoint served them."""
    days = set()
    for r in manifest.read_manifest():
        if r["source"] == SOURCE:
            m = re.search(r"3IMERG\.(\d{8})-", r["path"])
            days.add(datetime.strptime(m.group(1), "%Y%m%d").date())
    return days


LOCK = ROOT / "data" / ".imerg_fetch.lock"


def fetch_lock():
    """Exclusive, non-blocking lock so the hourly flow and a manual backfill never overlap.
    Returns the open lock file (keep it referenced), or None if another fetch holds it."""
    import fcntl
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fh = open(LOCK, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        return None
    return fh


def fetch(start: date, end: date, workers: int, max_days: int | None = None, endpoint: str = "cloud") -> None:
    lock = fetch_lock()
    if lock is None:
        print("another IMERG fetch is running; skipping")
        return
    s = session()
    done = fetched_days()
    todo = []
    month = start.replace(day=1)
    while month <= end:
        listing = (list_month_cmr(month.year, month.month) if endpoint == "cloud"
                   else list_month(s, month.year, month.month))
        for day, filename in sorted(listing.items()):
            q = build_cloud_query(filename) if endpoint == "cloud" else build_query(filename, day)
            if start <= day <= end and day not in done:
                todo.append((day, filename, q))
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    if max_days is not None and len(todo) > max_days:
        print(f"{len(todo)} days missing; fetching the first {max_days} this run")
        todo = todo[:max_days]
    print(f"{len(todo)} days to fetch")

    # downloads run in threads; manifest writes stay on this thread
    with ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(download, s, q): (day, filename, q) for day, filename, q in todo}
        failed = 0
        for n, f in enumerate(as_completed(futures), 1):
            day, filename, q = futures[f]
            try:
                manifest.save_raw(f.result(), SOURCE, q, f"{day:%Y/%m}/{filename}.subset.nc4")
            except FileExistsError:
                print(f"  {day} already stored by another fetch; kept that file")
            except (requests.RequestException, ValueError) as e:
                failed += 1
                print(f"  {day} failed, will retry on next run: {e}")
            if n % 50 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)} (last {day})")
    print(f"fetch complete: {len(todo) - failed} saved, {failed} failed")


def open_day(path) -> xr.Dataset:
    """Raw subset file -> Dataset with fill values as NaN and a check that the crop is Pakistan."""
    content = path.read_bytes()
    engine = "h5netcdf" if content.startswith(b"\x89HDF") else "scipy"
    ds = xr.open_dataset(io.BytesIO(content), engine=engine, mask_and_scale=False).load()
    lat_min, lat_max, lon_min, lon_max = PAK_BBOX
    if not (abs(float(ds.lat.min()) - lat_min) < 0.15 and abs(float(ds.lat.max()) - lat_max) < 0.15
            and abs(float(ds.lon.min()) - lon_min) < 0.15 and abs(float(ds.lon.max()) - lon_max) < 0.15):
        raise ValueError(f"{path}: crop does not match PAK_BBOX")
    # keep the raw fill visible to the quality agent; never read it as zero rain (Q3)
    ds["is_fill"] = ds.precipitation <= FILL + 0.1
    ds["precipitation"] = ds.precipitation.where(~ds.is_fill)
    return ds


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["fetch"])
    p.add_argument("--start", type=date.fromisoformat, default=IMERG_START)
    p.add_argument("--end", type=date.fromisoformat,
                   default=datetime.now(timezone.utc).date() - timedelta(days=1))
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--endpoint", choices=["cloud", "gesdisc"], default="cloud")
    a = p.parse_args()
    fetch(a.start, a.end, a.workers, endpoint=a.endpoint)
