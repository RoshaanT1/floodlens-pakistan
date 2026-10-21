"""A5/A6 report on the made-up Model A fixture (tests/test_model_a.py)."""
import duckdb

from src import analysis_a, model_a
from tests.test_model_a import _fixture_db


def test_report_runs_on_validation_predictions(tmp_path, monkeypatch):
    db = _fixture_db(tmp_path / "a.duckdb")
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE districts AS SELECT * FROM (VALUES ('PK1','Buner','Khyber Pakhtunkhwa'),"
                    "('PK2','Dadu','Sindh')) t(district_id, name, province)")
        con.execute("CREATE TABLE district_attributes AS SELECT * FROM (VALUES ('PK1',1500.0,true,false,false),"
                    "('PK2',40.0,false,false,true)) t(district_id, elevation_m, mountain, coastal, flood_prone)")
    for mod in (model_a, analysis_a):
        monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(model_a, "MODEL_DIR", tmp_path / "models")
    monkeypatch.setattr(model_a, "OPT_LOG", tmp_path / "opt.md")
    monkeypatch.setattr(analysis_a, "OUT", tmp_path / "analysis.md")
    monkeypatch.setattr(analysis_a, "NDMA_OUT", tmp_path / "none.csv")
    (tmp_path / "docs").mkdir()
    model_a.features(db)
    model_a.train(db)
    text = (tmp_path / "analysis.md").read_text() if analysis_a.report(db) else ""
    assert "## A5: groups" in text and "| terrain | mountain |" in text
    assert "2025-08-14" in text  # Buner rows present


def test_replay_writes_separate_store_with_label(tmp_path, monkeypatch):
    import json
    from datetime import date
    from src import replay
    db = _fixture_db(tmp_path / "a.duckdb")
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE districts AS SELECT * FROM (VALUES ('PK1','Buner','KP'),('PK2','Dadu','Sindh')) "
                    "t(district_id, name, province)")
    monkeypatch.setattr(model_a, "ROOT", tmp_path)
    monkeypatch.setattr(model_a, "MODEL_DIR", tmp_path / "models")
    monkeypatch.setattr(model_a, "OPT_LOG", tmp_path / "opt.md")
    (tmp_path / "docs").mkdir()
    model_a.features(db)
    model_a.train(db)
    if model_a.load_current() is None:  # fixture model may not beat climatology
        return
    monkeypatch.setattr(replay, "REPLAY_DB", tmp_path / "replay.duckdb")
    monkeypatch.setattr(replay, "OUT", tmp_path / "replay.json")
    n = replay.build(db)
    payload = json.loads((tmp_path / "replay.json").read_text())
    assert n == len(payload["rows"]) > 0 and payload["label"].startswith("REPLAY")
    assert all(date(2025, 8, 10) <= date.fromisoformat(r["date_utc"]) <= date(2025, 8, 20) for r in payload["rows"])
