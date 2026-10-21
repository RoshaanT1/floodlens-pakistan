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


def test_risk_export_carries_row_ids_and_label(tmp_path):
    db = tmp_path / "r.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("""CREATE TABLE risk_live AS SELECT 'PK1_2026-10-22_L1' AS row_id, 'PK1' AS district_id,
            DATE '2026-10-22' AS date_utc, 1 AS lead_days, 0.12 AS p_heavy_rain,
            'v1' AS model_version, 'validation-stage model' AS model_label""")
        r = export_frontend.risk(con)
    assert r["label"] == "validation-stage model"
    assert r["by_district"]["PK1"]["24h"] == {"p": 0.12, "row_id": "PK1_2026-10-22_L1", "date_utc": "2026-10-22"}


def test_market_has_history_range_and_nearest_city(tmp_path):
    import pandas as pd
    db = tmp_path / "m.duckdb"
    weeks = pd.date_range("2025-10-02", periods=54, freq="7D").date
    prices = pd.DataFrame([{"city": "Lahore", "item_no": 1, "item": "Wheat Flour Bag", "unit": "20 Kg",
                            "week_end": w, "avg_pkr": 100.0 + i, "row_id": f"Lahore_1_{w}", "quality_flags": None}
                           for i, w in enumerate(weeks)])
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE spi_price AS SELECT * FROM prices")
        con.execute("""CREATE TABLE districts AS SELECT * FROM (VALUES ('PK1','Lahore',31.5,74.3),
                       ('PK2','Kasur',31.1,74.4)) t(district_id, name, centroid_lat, centroid_lon)""")
        m = export_frontend.market(con)
    row = m["cities"]["Lahore"][0]
    assert row["avg_pkr"] == 153.0 and row["wow_pct"] == round((153 / 152 - 1) * 100, 2)
    assert row["p10"] < row["p90"] < 153.0  # range is from earlier weeks only
    assert m["nearest_city"]["PK2"]["city"] == "Lahore" and "history" in m["range_label"]
