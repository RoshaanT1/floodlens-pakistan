from datetime import date

import pandas as pd

from src import spi


def _week(day, avg, city="Lahore", item=1):
    return {"week_end": day, "city": city, "item_no": item, "item": "Wheat Flour Bag", "unit": "20 Kg",
            "min_pkr": avg - 10, "avg_pkr": avg, "max_pkr": avg + 10}


def test_checks_flag_and_never_fill():
    rows = [_week(date(2026, 10, 1), 100), _week(date(2026, 10, 8), 0), _week(date(2026, 10, 15), 200)]
    rows.append({**_week(date(2026, 10, 15), 50, item=2), "min_pkr": 60})  # min > avg
    p, weeks = spi.check(pd.DataFrame(rows))
    by = p.set_index(["week_end", "item_no"])
    assert by.loc[(date(2026, 10, 8), 1), "quality_flags"] == "not_collected"
    assert pd.isna(by.loc[(date(2026, 10, 8), 1), "avg_pkr"])  # 0 -> NULL, not filled
    assert by.loc[(date(2026, 10, 15), 2), "quality_flags"] == "min_avg_max_order"
    assert by.loc[(date(2026, 10, 15), 2), "avg_pkr"] == 50  # value kept as published
    assert not weeks.complete.any()  # one city, not 17 x 51
