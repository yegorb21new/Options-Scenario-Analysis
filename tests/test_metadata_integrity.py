import pandas as pd

from src.cockpit import prepare_return_horizon_data
from src.etf_metadata import get_metadata


def test_specific_metadata_labels():
    assert get_metadata("USO")["description"] == "United States Oil Fund"
    assert get_metadata("USO")["category"] == "Commodities"
    assert get_metadata("UNG")["description"] == "United States Natural Gas Fund"
    assert get_metadata("UNG")["category"] == "Commodities"
    assert get_metadata("IWM")["description"] == "iShares Russell 2000 ETF"
    assert get_metadata("IWM")["category"] == "Benchmark"
    assert get_metadata("XLF")["description"] == "Financial Select Sector SPDR Fund"
    assert get_metadata("XLF")["category"] == "Sector"


def test_sorting_preserves_ticker_metadata_alignment():
    universe = pd.DataFrame(
        {
            "ticker": ["USO", "UNG", "IWM", "XLF"],
            "daily_return": [0.02, -0.01, 0.03, 0.00],
            "approx_30d_iv": [0.40, 0.45, 0.20, 0.25],
            "z_score_daily_return": [1.0, -0.5, 1.5, 0.0],
        }
    )
    out = prepare_return_horizon_data(universe, ret_col="daily_return", z_col="z_score_daily_return", days=1)
    sorted_out = out.sort_values("return").reset_index(drop=True)
    uso_row = sorted_out[sorted_out["ticker"] == "USO"].iloc[0]
    ung_row = sorted_out[sorted_out["ticker"] == "UNG"].iloc[0]
    assert uso_row["description"] == "United States Oil Fund"
    assert uso_row["category"] == "Commodities"
    assert ung_row["description"] == "United States Natural Gas Fund"
    assert ung_row["category"] == "Commodities"


def test_return_horizon_prep_columns_exist():
    universe = pd.DataFrame(
        {
            "ticker": ["SPY"],
            "daily_return": [0.01],
            "approx_30d_iv": [0.20],
            "z_score_daily_return": [0.8],
        }
    )
    out = prepare_return_horizon_data(universe, ret_col="daily_return", z_col="z_score_daily_return", days=1)
    needed = {"ticker", "description", "category", "return", "z_score", "implied_vol", "period_start", "period_end"}
    assert needed.issubset(set(out.columns))
