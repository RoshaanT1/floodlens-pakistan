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
