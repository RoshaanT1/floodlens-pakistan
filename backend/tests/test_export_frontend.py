import json

import duckdb

from src import export_frontend


def test_outline_takes_largest_part_as_lat_lon():
    small = "((70 30, 70.1 30, 70.1 30.1, 70 30))"
    big = "((60 25, 62 25, 62 27, 60 27, 60 25))"
    ring = export_frontend._outline(f"MULTIPOLYGON({small}, {big})")
    assert [25.0, 60.0] in ring and [27.0, 62.0] in ring  # [lat, lon], big part only
    assert all(lat < 28 for lat, _ in ring)


def test_build_writes_status_without_optional_tables(tmp_path, monkeypatch):
    db = tmp_path / "t.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("""CREATE TABLE districts AS SELECT 'PK1' AS district_id, 'Dadu' AS name,
            'Sindh' AS province, 26.7 AS centroid_lat, 67.8 AS centroid_lon,
            'POLYGON((67 26, 68 26, 68 27, 67 26))' AS geometry_wkt""")
    monkeypatch.setattr(export_frontend.manifest, "read_manifest", lambda: [])
    out = export_frontend.build(db_path=db, out=tmp_path / "status.json")
    status = json.loads(out.read_text())
    assert status["districts"][0]["name"] == "Dadu"
    assert status["forecast"] is None and status["quality"] == []
