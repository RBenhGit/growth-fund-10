"""
Unit tests for fund_builder/builder.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fund_builder.builder import FundBuilder
from models.financial_data import FinancialData, MarketData
from models.stock import Stock
from utils.dedup import get_base_company_name, select_stocks_skip_duplicates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_builder() -> FundBuilder:
    return FundBuilder("SP500")


def make_stock_with_data(symbol="AAPL", revenues=None, net_incomes=None,
                          operating_incomes=None, operating_cash_flows=None,
                          market_cap=1_000_000, current_price=100.0,
                          price_history=None, pe_ratio=None) -> Stock:
    revenues = revenues or {2020: 100, 2021: 110, 2022: 120, 2023: 130, 2024: 140}
    net_incomes = net_incomes or {2020: 10, 2021: 12, 2022: 14, 2023: 16, 2024: 18}
    operating_incomes = operating_incomes or {2020: 8, 2021: 9, 2022: 11, 2023: 13, 2024: 15}
    operating_cash_flows = operating_cash_flows or {2020: 5, 2021: 6, 2022: 7, 2023: 8, 2024: 9}
    price_history = price_history or {"2023-01-01": 80.0, "2024-01-01": 100.0}

    fd = FinancialData(
        symbol=symbol,
        revenues=revenues,
        net_incomes=net_incomes,
        operating_incomes=operating_incomes,
        operating_cash_flows=operating_cash_flows,
        total_debt=20.0,
        total_equity=100.0,
        market_cap=market_cap,
        current_price=current_price,
        pe_ratio=pe_ratio,
    )
    md = MarketData(
        symbol=symbol,
        name=symbol,
        market_cap=market_cap,
        current_price=current_price,
        pe_ratio=pe_ratio,
        price_history=price_history,
    )
    stock = Stock(symbol=symbol, name=symbol, index="SP500",
                  financial_data=fd, market_data=md)
    return stock


# ---------------------------------------------------------------------------
# calculate_growth_rate
# ---------------------------------------------------------------------------

class TestCalculateGrowthRate:
    def test_positive_growth(self):
        builder = make_builder()
        # 100 → 121 over 2 periods (years=3 means start=sorted_years[2], end=sorted_years[0])
        values = {2022: 100, 2023: 110, 2024: 121}
        result = builder.calculate_growth_rate(values, years=3)
        assert result is not None
        assert result == pytest.approx(10.0, rel=0.01)  # 10% CAGR

    def test_insufficient_years_returns_none(self):
        builder = make_builder()
        assert builder.calculate_growth_rate({2024: 100}, years=3) is None

    def test_zero_start_value_returns_none(self):
        builder = make_builder()
        result = builder.calculate_growth_rate({2022: 0, 2023: 50, 2024: 100}, years=3)
        assert result is None

    def test_negative_start_value_returns_none(self):
        builder = make_builder()
        result = builder.calculate_growth_rate({2022: -10, 2023: 50, 2024: 100}, years=3)
        assert result is None

    def test_empty_values_returns_none(self):
        builder = make_builder()
        assert builder.calculate_growth_rate({}, years=3) is None

    def test_flat_values_return_zero(self):
        builder = make_builder()
        result = builder.calculate_growth_rate({2022: 100, 2023: 100, 2024: 100}, years=3)
        assert result == pytest.approx(0.0, abs=0.001)


# ---------------------------------------------------------------------------
# rank_percentile (replaces min-max normalize_score)
# ---------------------------------------------------------------------------

class TestRankPercentile:
    def test_normalizes_to_0_and_100(self):
        builder = make_builder()
        result = builder.rank_percentile([0.0, 50.0, 100.0])
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(100.0)

    def test_all_equal_values_returns_50(self):
        builder = make_builder()
        result = builder.rank_percentile([42.0, 42.0, 42.0])
        assert all(v == 50.0 for v in result)

    def test_empty_input_returns_empty(self):
        builder = make_builder()
        assert builder.rank_percentile([]) == []

    def test_single_value_returns_50(self):
        builder = make_builder()
        result = builder.rank_percentile([99.0])
        assert result == [50.0]

    def test_relative_ordering_preserved(self):
        builder = make_builder()
        result = builder.rank_percentile([10.0, 20.0, 30.0])
        assert result[0] < result[1] < result[2]

    def test_ties_get_average_rank(self):
        builder = make_builder()
        # [10, 20, 20, 30] -> ranks [0, 1.5, 1.5, 3] -> [0%, 50%, 50%, 100%]
        result = builder.rank_percentile([10.0, 20.0, 20.0, 30.0])
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(50.0)
        assert result[2] == pytest.approx(50.0)
        assert result[3] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# calculate_base_score
# ---------------------------------------------------------------------------

class TestCalculateBaseScore:
    def test_returns_dict_with_expected_keys(self):
        builder = make_builder()
        stock = make_stock_with_data()
        result = builder.calculate_base_score(stock)
        assert isinstance(result, dict)
        assert "net_income_growth" in result
        assert "revenue_growth" in result
        assert "market_cap" in result

    def test_no_financial_data_returns_zero(self):
        builder = make_builder()
        stock = Stock(symbol="EMPTY", name="Empty", index="SP500")
        result = builder.calculate_base_score(stock)
        assert result == {
            "net_income_growth": 0.0,
            "net_income_stability": 0.0,
            "revenue_growth": 0.0,
            "revenue_stability": 0.0,
            "market_cap": 0.0
        }

    def test_market_cap_matches_stock(self):
        builder = make_builder()
        stock = make_stock_with_data(market_cap=5_000_000)
        result = builder.calculate_base_score(stock)
        assert result["market_cap"] == 5_000_000


# ---------------------------------------------------------------------------
# calculate_potential_score
# ---------------------------------------------------------------------------

class TestCalculatePotentialScore:
    def test_returns_dict_with_expected_keys(self):
        builder = make_builder()
        stock = make_stock_with_data()
        result = builder.calculate_potential_score(stock)
        assert isinstance(result, dict)
        assert "future_growth" in result
        assert "momentum" in result
        # Valuation (PE) was intentionally removed from potential scoring; it must NOT reappear.
        assert "valuation" not in result

    def test_no_data_returns_zeros(self):
        builder = make_builder()
        stock = Stock(symbol="EMPTY", name="Empty", index="SP500")
        result = builder.calculate_potential_score(stock)
        assert result == {"future_growth": 0.0, "momentum": 0.0}


# ---------------------------------------------------------------------------
# score_and_rank_base_stocks
# ---------------------------------------------------------------------------

class TestScoreAndRankBaseStocks:
    def test_returns_sorted_by_score_descending(self):
        builder = make_builder()
        # Need 5 years of data for the 4-year CAGR calculation
        s1 = make_stock_with_data("LOW",
                                   revenues={2020: 10, 2021: 11, 2022: 12, 2023: 13, 2024: 14},
                                   net_incomes={2020: 1, 2021: 1, 2022: 1, 2023: 1, 2024: 1},
                                   market_cap=100)
        s2 = make_stock_with_data("HIGH",
                                   revenues={2020: 100, 2021: 150, 2022: 200, 2023: 300, 2024: 400},
                                   net_incomes={2020: 10, 2021: 15, 2022: 20, 2023: 30, 2024: 40},
                                   market_cap=1_000_000)
        ranked = builder.score_and_rank_base_stocks([s1, s2])
        assert ranked[0].symbol == "HIGH"

    def test_base_score_assigned_after_ranking(self):
        builder = make_builder()
        stock = make_stock_with_data()
        ranked = builder.score_and_rank_base_stocks([stock])
        assert ranked[0].base_score is not None

    def test_empty_list_returns_empty(self):
        builder = make_builder()
        assert builder.score_and_rank_base_stocks([]) == []


# ---------------------------------------------------------------------------
# get_base_company_name / select_stocks_skip_duplicates
# ---------------------------------------------------------------------------

def make_named_stock(symbol: str, name: str, score: float = 50.0) -> Stock:
    stock = Stock(symbol=symbol, name=name, index="SP500")
    stock.base_score = score
    return stock


class TestGetBaseCompanyName:
    def test_class_a_suffix_stripped(self):
        s = make_named_stock("GOOGL.US", "Alphabet Inc Class A")
        assert get_base_company_name(s) == "ALPHABET"

    def test_class_c_suffix_stripped(self):
        s = make_named_stock("GOOG.US", "Alphabet Inc Class C")
        assert get_base_company_name(s) == "ALPHABET"

    def test_bare_letter_a_stripped(self):
        s = make_named_stock("NWSA.US", "News Corp A")
        assert get_base_company_name(s) == "NEWS CORP"

    def test_bare_letter_b_stripped(self):
        s = make_named_stock("NWS.US", "News Corp B")
        assert get_base_company_name(s) == "NEWS CORP"

    def test_both_news_corp_classes_equal(self):
        nws  = make_named_stock("NWS.US",  "News Corp B")
        nwsa = make_named_stock("NWSA.US", "News Corp A")
        assert get_base_company_name(nws) == get_base_company_name(nwsa)

    def test_unrelated_letter_not_stripped(self):
        # "AT&T Inc" ends in "T" which is not A/B/C — should not be touched
        s = make_named_stock("T.US", "AT&T Inc")
        assert "AT" in get_base_company_name(s)


class TestSelectStocksSkipDuplicates:
    def test_news_corp_deduplication_keeps_higher_ranked(self):
        nws  = make_named_stock("NWS.US",  "News Corp B", score=40.0)
        nwsa = make_named_stock("NWSA.US", "News Corp A", score=39.9)
        result = select_stocks_skip_duplicates([nws, nwsa], 2)
        assert len(result) == 1
        assert result[0].symbol == "NWS.US"

    def test_alphabet_deduplication(self):
        googl = make_named_stock("GOOGL.US", "Alphabet Inc Class A", score=51.0)
        goog  = make_named_stock("GOOG.US",  "Alphabet Inc Class C", score=50.9)
        result = select_stocks_skip_duplicates([googl, goog], 2)
        assert len(result) == 1
        assert result[0].symbol == "GOOGL.US"

    def test_distinct_companies_both_selected(self):
        nvda = make_named_stock("NVDA.US", "NVIDIA Corporation", score=84.0)
        ste  = make_named_stock("STE.US",  "STERIS plc",         score=46.0)
        result = select_stocks_skip_duplicates([nvda, ste], 2)
        assert len(result) == 2
