import numpy as np
import xarray as xr

from src import imerg
from src.config import PAK_BBOX


def test_grid_slices_cover_bbox():
    (i0, i1), (j0, j1) = imerg.grid_slices()
    lat_min, lat_max, lon_min, lon_max = PAK_BBOX
    lon = lambda i: -179.95 + 0.1 * i
    lat = lambda j: -89.95 + 0.1 * j
    assert lon(i0) <= lon_min + 0.1 and lon(i1) >= lon_max - 0.1
    assert lat(j0) <= lat_min + 0.1 and lat(j1) >= lat_max - 0.1


def test_query_is_a_cropped_opendap_request():
    q = imerg.build_query("3B-DAY-L.MS.MRG.3IMERG.20150101-S000000-E235959.V07B.nc4",
                          __import__("datetime").date(2015, 1, 1))
    assert q.startswith(imerg.DAP_URL + "/2015/01/3B-DAY-L")
    assert ".nc4.nc4?precipitation[0:1:0][" in q and "precipitation_cnt[" in q


def test_open_day_masks_fill_and_never_reads_it_as_zero(tmp_path):
    (i0, i1), (j0, j1) = imerg.grid_slices()
    lon = -179.95 + 0.1 * np.arange(i0, i1 + 1)
    lat = -89.95 + 0.1 * np.arange(j0, j1 + 1)
    p = np.full((1, lon.size, lat.size), 2.5, dtype="float32")
    p[0, 0, 0] = imerg.FILL
    ds = xr.Dataset({"precipitation": (("time", "lon", "lat"), p),
                     "precipitation_cnt": (("time", "lon", "lat"), np.full(p.shape, 48, "int16"))},
                    coords={"lon": lon, "lat": lat})
    path = tmp_path / "day.nc4"
    ds.to_netcdf(path, engine="h5netcdf")

    out = imerg.open_day(path)
    assert bool(out.is_fill[0, 0, 0]) and np.isnan(out.precipitation[0, 0, 0])
    assert int(out.is_fill.sum()) == 1
    assert float(out.precipitation.max()) == 2.5


def test_session_prefers_token(monkeypatch):
    from src import imerg
    monkeypatch.setattr(imerg, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("EARTHDATA_TOKEN", "abc")
    monkeypatch.setenv("EARTHDATA_USERNAME", "u")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "p")
    s = imerg.session()
    assert s.headers["Authorization"] == "Bearer abc" and s.auth is None
    assert imerg.has_credentials()
