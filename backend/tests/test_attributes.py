import pandas as pd

from src import attributes


def test_flood_shares_skips_province_rows_and_takes_worse_week(tmp_path):
    header = ["name", "area"] + [f"c{i}" for i in range(2, 14)]
    rows = [header,
            ["SINDH", 1000] + [0, 0, 0, 500] + [0] * 4 + [0, 0, 0] + [0],
            ["JACOBABAD", 100] + [0, 0, 0, 30] + [0] * 4 + [60, 0, 0] + [0],
            ["Kotli", 200] + [0, 0, 0, 1] + [0] * 4 + [0, 0, 0] + [0]]
    path = tmp_path / "u.xlsx"
    with pd.ExcelWriter(path) as w:
        pd.DataFrame([["x"]]).to_excel(w, sheet_name="province", header=False, index=False)
        pd.DataFrame(rows).to_excel(w, sheet_name="district", header=False, index=False)
    shares = attributes.flood_shares(path)
    assert "sindh" not in shares
    assert shares["jacobabad"] == 0.6 and shares["kotli"] == 0.005
