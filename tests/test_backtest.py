"""
Unit tests for backtest.py — pure logic (no live network calls)

NOTE: backtest.py replaces sys.stdout at module level (Windows Hebrew encoding fix).
To keep pytest's capture layer intact, we restore the real stdout before importing.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, date


class _NoDetachWrapper:
    """
    Wraps sys.stdout so that backtest.py's module-level
    ``sys.stdout.detach()`` call returns a harmless BytesIO rather than
    detaching pytest's capture buffer.
    """
    def __init__(self, wrapped):
        self._wrapped = wrapped

    def detach(self):
        return io.BytesIO()

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


# Protect pytest's stdout capture from backtest.py's module-level detach.
_real_stdout = sys.stdout
sys.stdout = _NoDetachWrapper(_real_stdout)
from backtest import FundBacktest  # noqa: E402
sys.stdout = _real_stdout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_backtest(years=3) -> FundBacktest:
    bt = FundBacktest.__new__(FundBacktest)
    bt.fund_file = "dummy.md"
    bt.years = years
    bt.portfolio = {}
    bt.weights = {}
    bt.benchmarks = {}
    bt.end_date = datetime(2024, 12, 31)
    bt.start_date = datetime(2024 - years, 12, 31)
    bt.stock_data = pd.DataFrame()
    return bt


def make_daily_returns(n=252, value=0.001) -> pd.Series:
    """Synthetic constant daily returns over n trading days."""
    idx = pd.date_range("2024-01-02", periods=n, freq="B")
    return pd.Series([value] * n, index=idx)


# ---------------------------------------------------------------------------
# parse_fund_file
# ---------------------------------------------------------------------------

SAMPLE_FUND_MD = """\
# Fund

| שם חברה | סימול | סוג | משקל | ציון | מחיר נוכחי | מספר מניות ליחידת קרן |
|---------|-------|-----|------|------|------------|---------------------|
| Apple Inc | AAPL.US | בסיס | 18% | 85.5 | 185.50 | 1 |
| Microsoft | MSFT.US | בסיס | 16% | 80.0 | 420.00 | 1 |

**עלות מינימלית:** 1000
"""


class TestParseFundFile:
    def test_parses_symbols_and_weights(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                         delete=False, encoding="utf-8") as f:
            f.write(SAMPLE_FUND_MD)
            path = f.name

        bt = FundBacktest(path, years=3)
        bt.parse_fund_file()

        assert "AAPL" in bt.portfolio
        assert "MSFT" in bt.portfolio
        assert bt.weights["AAPL"] == pytest.approx(0.18)
        assert bt.weights["MSFT"] == pytest.approx(0.16)

        os.unlink(path)

    def test_strips_suffix_from_symbol(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                         delete=False, encoding="utf-8") as f:
            f.write(SAMPLE_FUND_MD)
            path = f.name

        bt = FundBacktest(path, years=3)
        bt.parse_fund_file()
        # AAPL.US → AAPL  (no dot in key)
        assert all("." not in sym for sym in bt.portfolio)

        os.unlink(path)


# ---------------------------------------------------------------------------
# calculate_portfolio_returns
# ---------------------------------------------------------------------------

class TestCalculatePortfolioReturns:
    def test_empty_stock_data_returns_empty(self):
        bt = make_backtest()
        result = bt.calculate_portfolio_returns()
        assert result.empty

    def test_single_stock_full_weight(self):
        bt = make_backtest()
        idx = pd.date_range("2024-01-02", periods=5, freq="B")
        prices = pd.DataFrame({"AAPL": [100, 101, 102, 103, 104]}, index=idx)
        bt.stock_data = prices
        bt.weights = {"AAPL": 1.0}
        bt.portfolio = {"AAPL": {"name": "Apple", "weight": 1.0}}

        returns = bt.calculate_portfolio_returns()
        # pct_change of [100,101,...] = [NaN, 0.01, 0.01, ...]
        assert len(returns) == 5
        assert returns.iloc[1] == pytest.approx(0.01)

    def test_two_stocks_weighted_average(self):
        bt = make_backtest()
        idx = pd.date_range("2024-01-02", periods=3, freq="B")
        prices = pd.DataFrame({"A": [100, 102, 104], "B": [200, 200, 200]}, index=idx)
        bt.stock_data = prices
        bt.weights = {"A": 0.5, "B": 0.5}
        bt.portfolio = {"A": {"name": "A", "weight": 0.5},
                        "B": {"name": "B", "weight": 0.5}}

        returns = bt.calculate_portfolio_returns()
        # A returns: NaN, 0.02, 0.0196; B returns: NaN, 0, 0
        # weighted: NaN, 0.01, ~0.0098
        assert returns.iloc[1] == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# calculate_metrics
# ---------------------------------------------------------------------------

class TestCalculateMetrics:
    def test_empty_returns_returns_empty_dict(self):
        bt = make_backtest()
        result = bt.calculate_metrics(pd.Series([], dtype=float))
        assert result == {}

    def test_all_nan_returns_empty_dict(self):
        bt = make_backtest()
        result = bt.calculate_metrics(pd.Series([float("nan")] * 5))
        assert result == {}

    def test_constant_positive_returns_produce_positive_cumulative(self):
        bt = make_backtest()
        returns = make_daily_returns(252, 0.001)
        metrics = bt.calculate_metrics(returns)
        assert metrics["cumulative_return"] > 0
        assert metrics["annual_return"] > 0

    def test_all_keys_present(self):
        bt = make_backtest()
        returns = make_daily_returns(252, 0.001)
        metrics = bt.calculate_metrics(returns)
        expected_keys = {
            "cumulative_return", "annual_return", "annual_volatility",
            "sharpe_ratio", "sortino_ratio", "calmar_ratio", "max_drawdown",
            "downside_deviation", "win_rate", "best_day", "worst_day",
            "monthly_win_rate", "positive_months", "total_months",
        }
        assert expected_keys.issubset(metrics.keys())

    def test_win_rate_is_one_for_all_positive_days(self):
        bt = make_backtest()
        returns = make_daily_returns(252, 0.001)
        metrics = bt.calculate_metrics(returns)
        assert metrics["win_rate"] == pytest.approx(1.0)

    def test_max_drawdown_zero_for_monotone_gains(self):
        bt = make_backtest()
        returns = make_daily_returns(252, 0.001)
        metrics = bt.calculate_metrics(returns)
        assert metrics["max_drawdown"] == pytest.approx(0.0, abs=1e-9)

    def test_beta_and_alpha_included_with_benchmark(self):
        bt = make_backtest()
        returns = make_daily_returns(252, 0.001)
        benchmark = make_daily_returns(252, 0.0008)
        metrics = bt.calculate_metrics(returns, benchmark)
        assert "beta" in metrics
        assert "alpha" in metrics

    def test_sharpe_positive_when_returns_exceed_risk_free(self):
        bt = make_backtest()
        # ~25% annual return — well above 2% risk-free — should produce positive Sharpe
        returns = make_daily_returns(252, 0.001)
        metrics = bt.calculate_metrics(returns)
        assert metrics["sharpe_ratio"] > 0
