"""
Unit tests for models/financial_data.py, models/stock.py, models/fund.py
"""

import pytest
from models.financial_data import FinancialData, MarketData, PricePoint
from models.stock import Stock
from models.fund import Fund, FundPosition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_financial_data(**overrides) -> FinancialData:
    defaults = dict(
        symbol="TEST",
        revenues={2020: 100, 2021: 110, 2022: 120, 2023: 130, 2024: 140},
        net_incomes={2020: 10, 2021: 12, 2022: 14, 2023: 16, 2024: 18},
        operating_incomes={2020: 8, 2021: 9, 2022: 11, 2023: 13, 2024: 15},
        operating_cash_flows={2020: 5, 2021: 6, 2022: 7, 2023: 8, 2024: 9},
        total_debt=20.0,
        total_equity=100.0,
    )
    defaults.update(overrides)
    return FinancialData(**defaults)


def make_market_data(**overrides) -> MarketData:
    defaults = dict(
        symbol="TEST",
        name="Test Corp",
        market_cap=1_000_000,
        current_price=100.0,
        pe_ratio=20.0,
        price_history={"2023-01-01": 80.0, "2024-01-01": 100.0},
    )
    defaults.update(overrides)
    return MarketData(**defaults)


def make_stock(financial_data=None, market_data=None, **overrides) -> Stock:
    defaults = dict(symbol="TEST", name="Test Corp", index="SP500")
    defaults.update(overrides)
    stock = Stock(**defaults)
    stock.financial_data = financial_data
    stock.market_data = market_data
    return stock


# ---------------------------------------------------------------------------
# FinancialData
# ---------------------------------------------------------------------------

class TestFinancialDataDebtRatio:
    def test_positive_equity_with_debt(self):
        fd = make_financial_data(total_debt=30.0, total_equity=100.0)
        assert fd.debt_to_equity_ratio == pytest.approx(0.30)

    def test_zero_debt(self):
        fd = make_financial_data(total_debt=None, total_equity=100.0)
        assert fd.debt_to_equity_ratio == 0.0

    def test_zero_equity_returns_none(self):
        fd = make_financial_data(total_debt=50.0, total_equity=0.0)
        assert fd.debt_to_equity_ratio is None

    def test_none_equity_returns_none(self):
        fd = make_financial_data(total_debt=50.0, total_equity=None)
        assert fd.debt_to_equity_ratio is None


class TestHasProfitableYears:
    def test_all_recent_years_profitable(self):
        fd = make_financial_data(net_incomes={2020: 1, 2021: 2, 2022: 3, 2023: 4, 2024: 5})
        assert fd.has_profitable_years(5) is True

    def test_insufficient_data(self):
        fd = make_financial_data(net_incomes={2023: 10, 2024: 20})
        assert fd.has_profitable_years(5) is False

    def test_most_recent_year_negative(self):
        fd = make_financial_data(net_incomes={2020: 1, 2021: 2, 2022: 3, 2023: 4, 2024: -1})
        assert fd.has_profitable_years(5) is False

    def test_exactly_two_profitable_years(self):
        fd = make_financial_data(net_incomes={2023: 5, 2024: 10})
        assert fd.has_profitable_years(2) is True

    def test_one_negative_out_of_recent_two(self):
        fd = make_financial_data(net_incomes={2023: -1, 2024: 10})
        assert fd.has_profitable_years(2) is False


class TestHasOperatingProfitYears:
    def test_all_five_years_profitable(self):
        fd = make_financial_data(operating_incomes={2020: 1, 2021: 2, 2022: 3, 2023: 4, 2024: 5})
        assert fd.has_operating_profit_years(4, 5) is True

    def test_four_out_of_five_profitable(self):
        fd = make_financial_data(operating_incomes={2020: -1, 2021: 2, 2022: 3, 2023: 4, 2024: 5})
        assert fd.has_operating_profit_years(4, 5) is True

    def test_three_out_of_five_not_enough(self):
        fd = make_financial_data(operating_incomes={2020: -1, 2021: -2, 2022: 3, 2023: 4, 2024: 5})
        assert fd.has_operating_profit_years(4, 5) is False

    def test_insufficient_years_of_data(self):
        fd = make_financial_data(operating_incomes={2023: 5, 2024: 6})
        assert fd.has_operating_profit_years(4, 5) is False


class TestHasPositiveCashFlow:
    def test_all_positive(self):
        fd = make_financial_data(operating_cash_flows={2020: 1, 2021: 2, 2022: 3})
        assert fd.has_positive_cash_flow() is True

    def test_majority_positive(self):
        fd = make_financial_data(operating_cash_flows={2020: -1, 2021: 2, 2022: 3})
        assert fd.has_positive_cash_flow() is True

    def test_majority_negative(self):
        fd = make_financial_data(operating_cash_flows={2020: -1, 2021: -2, 2022: 3})
        assert fd.has_positive_cash_flow() is False

    def test_empty_cash_flows(self):
        fd = make_financial_data(operating_cash_flows={})
        assert fd.has_positive_cash_flow() is False

    def test_exactly_half_positive_not_enough(self):
        fd = make_financial_data(operating_cash_flows={2020: -1, 2021: -2, 2022: 3, 2023: 4})
        # 2 positive out of 4 → 0.5, not > 0.5
        assert fd.has_positive_cash_flow() is False


# ---------------------------------------------------------------------------
# MarketData
# ---------------------------------------------------------------------------

class TestMarketDataGetPrice:
    def test_existing_date(self):
        md = make_market_data(price_history={"2024-01-01": 90.0})
        assert md.get_price_on_date("2024-01-01") == 90.0

    def test_missing_date_returns_none(self):
        md = make_market_data(price_history={"2024-01-01": 90.0})
        assert md.get_price_on_date("2023-01-01") is None


class TestMarketDataMomentum:
    def test_positive_momentum(self):
        # oldest price 80, current price 100 → (100-80)/80 * 100 = 25%
        md = make_market_data(
            current_price=100.0,
            price_history={"2023-01-01": 80.0, "2024-01-01": 100.0}
        )
        result = md.calculate_momentum()
        assert result == pytest.approx(25.0)

    def test_no_history_returns_none(self):
        md = make_market_data(price_history={})
        assert md.calculate_momentum() is None

    def test_single_price_returns_none(self):
        md = make_market_data(price_history={"2024-01-01": 100.0})
        assert md.calculate_momentum() is None

    def test_anchored_lookback_uses_one_year_price_not_oldest(self):
        # 3 yearly snapshots. momentum(365) must use the ~1-year-ago snapshot
        # (2024-06-30 = 100), NOT the oldest (2023-06-30 = 50).
        # current 120 vs 100 → 20% (a since-oldest calc would give (120-50)/50 = 140%).
        md = make_market_data(
            current_price=120.0,
            price_history={"2023-06-30": 50.0, "2024-06-30": 100.0, "2025-06-30": 115.0},
        )
        assert md.calculate_momentum(365) == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# PricePoint
# ---------------------------------------------------------------------------

class TestPricePoint:
    def test_construction(self):
        pp = PricePoint(date="2024-03-15", price=123.45)
        assert pp.date == "2024-03-15"
        assert pp.price == pytest.approx(123.45)


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

class TestStockProperties:
    def test_current_price_from_market_data(self):
        md = make_market_data(current_price=55.0)
        stock = make_stock(market_data=md)
        assert stock.current_price == 55.0

    def test_current_price_fallback_to_financial_data(self):
        fd = make_financial_data(current_price=42.0)
        stock = make_stock(financial_data=fd)
        assert stock.current_price == 42.0

    def test_current_price_none_when_no_data(self):
        stock = make_stock()
        assert stock.current_price is None


class TestCheckBaseEligibility:
    def test_eligible_stock_passes_all_criteria(self):
        fd = make_financial_data(total_debt=30.0, total_equity=100.0)
        stock = make_stock(financial_data=fd)
        assert stock.check_base_eligibility() is True
        assert stock.is_eligible_for_base is True

    def test_no_financial_data_fails(self):
        stock = make_stock()
        assert stock.check_base_eligibility() is False

    def test_insufficient_profitable_years_fails(self):
        fd = make_financial_data(net_incomes={2023: 5, 2024: 10})
        stock = make_stock(financial_data=fd)
        assert stock.check_base_eligibility() is False

    def test_too_high_debt_ratio_fails(self):
        fd = make_financial_data(total_debt=80.0, total_equity=100.0)  # 80% > 60%
        stock = make_stock(financial_data=fd)
        assert stock.check_base_eligibility() is False

    def test_negative_cash_flow_majority_fails(self):
        fd = make_financial_data(operating_cash_flows={2020: -5, 2021: -3, 2022: 1})
        stock = make_stock(financial_data=fd)
        assert stock.check_base_eligibility() is False

    def test_none_debt_does_not_fail_on_ratio(self):
        fd = make_financial_data(total_debt=None, total_equity=100.0)
        stock = make_stock(financial_data=fd)
        # debt_to_equity_ratio → 0.0 (no debt), should not fail on ratio check
        assert stock.check_base_eligibility() is True

    def test_negative_equity_fails(self):
        # Negative equity makes debt_to_equity_ratio return None (which would pass);
        # the explicit solvency check must reject it.
        fd = make_financial_data(total_debt=10.0, total_equity=-50.0)
        stock = make_stock(financial_data=fd)
        assert stock.check_base_eligibility() is False

    def test_insufficient_revenue_history_fails(self):
        # Only 2 revenue years → revenue CAGR would be a fake 0.0; reject at the gate.
        fd = make_financial_data(revenues={2023: 120, 2024: 140})
        stock = make_stock(financial_data=fd)
        assert stock.check_base_eligibility() is False

    def test_recheck_can_revoke_eligibility(self):
        # A stock previously marked eligible (e.g. loaded from cache) must lose the
        # flag when its refreshed data no longer qualifies — the ratchet-bug fix.
        stock = make_stock(financial_data=make_financial_data(total_debt=30.0, total_equity=100.0))
        assert stock.check_base_eligibility() is True
        assert stock.is_eligible_for_base is True
        # Latest year turns to a loss, breaking the 5-year profitability streak.
        stock.financial_data = make_financial_data(
            net_incomes={2020: 10, 2021: 12, 2022: 14, 2023: 16, 2024: -5}
        )
        assert stock.check_base_eligibility() is False
        assert stock.is_eligible_for_base is False


class TestCheckPotentialEligibility:
    def test_eligible_with_three_profitable_years(self):
        fd = make_financial_data(
            net_incomes={2022: 3, 2023: 5, 2024: 10},
            revenues={2022: 80, 2023: 100, 2024: 120},
        )
        stock = make_stock(financial_data=fd)
        assert stock.check_potential_eligibility() is True
        assert stock.is_eligible_for_potential is True

    def test_only_two_profitable_years_fails(self):
        fd = make_financial_data(
            net_incomes={2023: 5, 2024: 10},
            revenues={2023: 100, 2024: 120},
        )
        stock = make_stock(financial_data=fd)
        assert stock.check_potential_eligibility() is False

    def test_no_financial_data_fails(self):
        stock = make_stock()
        assert stock.check_potential_eligibility() is False

    def test_only_one_profitable_year_fails(self):
        fd = make_financial_data(net_incomes={2024: 10}, revenues={2024: 100})
        stock = make_stock(financial_data=fd)
        assert stock.check_potential_eligibility() is False

    def test_insufficient_revenue_data_fails(self):
        fd = make_financial_data(net_incomes={2022: 3, 2023: 5, 2024: 10}, revenues={2024: 100})
        stock = make_stock(financial_data=fd)
        assert stock.check_potential_eligibility() is False


# ---------------------------------------------------------------------------
# FundPosition
# ---------------------------------------------------------------------------

class TestFundPosition:
    def _make_position(self, price, shares):
        md = make_market_data(current_price=price)
        stock = make_stock(market_data=md)
        return FundPosition(stock=stock, weight=0.18, shares_per_unit=shares, position_type="base")

    def test_position_value_per_unit(self):
        pos = self._make_position(price=50.0, shares=10)
        assert pos.position_value_per_unit == pytest.approx(500.0)

    def test_position_value_zero_when_no_price(self):
        stock = make_stock()
        pos = FundPosition(stock=stock, weight=0.18, shares_per_unit=5, position_type="base")
        assert pos.position_value_per_unit == 0.0


# ---------------------------------------------------------------------------
# Fund
# ---------------------------------------------------------------------------

class TestFund:
    def _make_fund(self):
        return Fund(name="Fund_10_SP500_Q1_2026", index="SP500", quarter="Q1", year=2026)

    def _add_position(self, fund, weight, price, position_type="base"):
        md = make_market_data(current_price=price)
        stock = make_stock(market_data=md)
        fund.add_position(stock=stock, weight=weight, shares_per_unit=10, position_type=position_type)

    def test_add_position_updates_total_weight(self):
        fund = self._make_fund()
        self._add_position(fund, 0.18, 100.0)
        self._add_position(fund, 0.16, 200.0)
        assert fund.total_weight == pytest.approx(0.34)
        assert len(fund.positions) == 2

    def test_get_base_positions(self):
        # Production creates positions with Hebrew type labels ("בסיס"/"פוטנציאל").
        fund = self._make_fund()
        self._add_position(fund, 0.18, 100.0, "בסיס")
        self._add_position(fund, 0.06, 50.0, "פוטנציאל")
        assert len(fund.get_base_positions()) == 1
        assert len(fund.get_potential_positions()) == 1

    def test_calculate_total_value_per_unit(self):
        fund = self._make_fund()
        self._add_position(fund, 0.18, 100.0)  # 10 shares × 100 = 1000
        self._add_position(fund, 0.16, 200.0)  # 10 shares × 200 = 2000
        assert fund.calculate_total_value_per_unit() == pytest.approx(3000.0)

    def test_get_stocks_summary(self):
        fund = self._make_fund()
        self._add_position(fund, 0.18, 100.0, "base")
        self._add_position(fund, 0.16, 100.0, "base")
        self._add_position(fund, 0.06, 50.0, "potential")
        summary = fund.get_stocks_summary()
        assert summary["total_positions"] == 3
        assert summary["base_stocks"] == 2
        assert summary["potential_stocks"] == 1
        assert summary["total_weight"] == pytest.approx(0.40)
