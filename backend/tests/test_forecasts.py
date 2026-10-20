from datetime import date

from src import forecasts


def test_month_chunks_cover_range_without_gaps():
    chunks = list(forecasts.month_chunks(date(2024, 2, 10), date(2024, 4, 5)))
    assert chunks == [(date(2024, 2, 10), date(2024, 2, 29)),
                      (date(2024, 3, 1), date(2024, 3, 31)),
                      (date(2024, 4, 1), date(2024, 4, 5))]


def test_call_weight_matches_free_tier_rule():
    # 15 variables -> 1.5x; 31 days -> 31/14x
    assert round(forecasts.call_weight(40, 31), 2) == round(40 * 1.5 * 31 / 14, 2)
    assert forecasts.call_weight(1, 7) == 1.5


def test_query_weight_matches_call_weight():
    q = forecasts.build_query([30.0] * 40, [70.0] * 40, date(2024, 7, 1), date(2024, 7, 31))
    assert round(forecasts.query_weight(q), 6) == round(forecasts.call_weight(40, 31), 6)


def test_calls_spent_counts_only_last_24h(monkeypatch):
    from datetime import datetime, timezone
    q = forecasts.build_query([30.0] * 10, [70.0] * 10, date(2024, 7, 1), date(2024, 7, 7))
    rows = [{"source": forecasts.SOURCE, "query": q, "fetched_at_utc": "2026-10-20T10:00:00Z"},
            {"source": forecasts.SOURCE, "query": q, "fetched_at_utc": "2026-10-19T09:00:00Z"},
            {"source": "ocha_cod_ab", "query": "x", "fetched_at_utc": "2026-10-20T10:00:00Z"}]
    monkeypatch.setattr(forecasts.manifest, "read_manifest", lambda: rows)
    now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    assert forecasts.calls_spent(24, now) == forecasts.query_weight(q)
