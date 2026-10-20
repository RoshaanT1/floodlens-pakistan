from src import manifest


def test_save_raw_appends_row_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest, "ROOT", tmp_path)
    m = tmp_path / "manifest.csv"
    path = manifest.save_raw(b"hello", "ocha_cod_ab", "http://x?q=1", "a.bin",
                             manifest=m, raw_dir=tmp_path / "raw")

    assert path.read_bytes() == b"hello"
    rows = manifest.read_manifest(m)
    assert len(rows) == 1
    assert rows[0]["sha256"] == manifest.sha256_bytes(b"hello")
    assert rows[0]["licence"].startswith("CC BY-IGO")
    assert rows[0]["fetched_at_utc"].endswith("Z")
    assert manifest.verify(m) == []

    manifest.save_raw(b"again", "ocha_cod_ab", "http://x?q=2", "b.bin",
                      manifest=m, raw_dir=tmp_path / "raw")
    assert manifest.fetched_queries("ocha_cod_ab", m) == {"http://x?q=1", "http://x?q=2"}


def test_verify_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest, "ROOT", tmp_path)
    m = tmp_path / "manifest.csv"
    path = manifest.save_raw(b"hello", "s", "q", "a.bin", manifest=m, raw_dir=tmp_path / "raw")
    path.write_bytes(b"changed")
    assert manifest.verify(m) == [f"hash mismatch: {path.relative_to(tmp_path)}"]
    path.unlink()
    assert manifest.verify(m) == [f"missing: {path.relative_to(tmp_path)}"]
