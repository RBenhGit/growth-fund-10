"""
בדיקות עבור מערכת העדכון הרבעוני

מכסה: update_parser, cache_loader, ltm_calculator, changelog, date_utils helpers
"""

import json
import pytest
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.update_parser import parse_update_file, _parse_ranked_table, _parse_composition_table
from utils.cache_loader import load_cached_stock, load_cached_stocks
from utils.ltm_calculator import calculate_ltm, merge_ltm_into_stock
from utils.changelog import append_to_changelog
from utils.date_utils import (
    get_fund_output_dir,
    find_latest_fund_dir,
    find_previous_fund_dir,
    _quarter_sort_key,
)
from models.stock import Stock
from models.financial_data import FinancialData, MarketData


# ==================== date_utils tests ====================

class TestQuarterSortKey:
    def test_sort_order(self):
        assert _quarter_sort_key("Q1", 2026) > _quarter_sort_key("Q4", 2025)
        assert _quarter_sort_key("Q4", 2025) > _quarter_sort_key("Q3", 2025)
        assert _quarter_sort_key("Q1", 2025) < _quarter_sort_key("Q2", 2025)

    def test_same_quarter(self):
        assert _quarter_sort_key("Q1", 2026) == _quarter_sort_key("Q1", 2026)


class TestGetFundOutputDir:
    def test_path_format(self):
        result = get_fund_output_dir(Path("Fund_Docs"), "SP500", "Q1", 2026)
        assert result == Path("Fund_Docs/SP500/Q1_2026")

    def test_tase(self):
        result = get_fund_output_dir(Path("Fund_Docs"), "TASE125", "Q4", 2025)
        assert result == Path("Fund_Docs/TASE125/Q4_2025")


class TestFindLatestFundDir:
    def test_finds_latest(self, tmp_path):
        # Create quarter directories
        (tmp_path / "SP500" / "Q4_2025").mkdir(parents=True)
        (tmp_path / "SP500" / "Q1_2026").mkdir(parents=True)

        result = find_latest_fund_dir(tmp_path, "SP500")
        assert result.name == "Q1_2026"

    def test_returns_none_if_empty(self, tmp_path):
        result = find_latest_fund_dir(tmp_path, "SP500")
        assert result is None

    def test_ignores_non_quarter_dirs(self, tmp_path):
        (tmp_path / "SP500" / "Q1_2026").mkdir(parents=True)
        (tmp_path / "SP500" / "Reports").mkdir(parents=True)
        (tmp_path / "SP500" / "random_file.txt").parent.mkdir(parents=True, exist_ok=True)

        result = find_latest_fund_dir(tmp_path, "SP500")
        assert result.name == "Q1_2026"


class TestFindPreviousFundDir:
    def test_finds_previous(self, tmp_path):
        (tmp_path / "SP500" / "Q4_2025").mkdir(parents=True)
        (tmp_path / "SP500" / "Q1_2026").mkdir(parents=True)

        result = find_previous_fund_dir(tmp_path, "SP500", "Q1", 2026)
        assert result.name == "Q4_2025"

    def test_returns_none_if_no_previous(self, tmp_path):
        (tmp_path / "SP500" / "Q4_2025").mkdir(parents=True)

        result = find_previous_fund_dir(tmp_path, "SP500", "Q4", 2025)
        assert result is None


# ==================== update_parser tests ====================

SAMPLE_UPDATE_MD = """# עדכון קרן Fund_10_SP500_Q1_2026

תאריך עדכון: 2026-02-11

## מניות בסיס מדורגות

| דירוג | שם חברה | סימול | ציון |
|-------|---------|-------|------|
| 1 | NVIDIA Corporation | NVDA.US | 89.69 |
| 2 | Salesforce.com Inc | CRM.US | 49.79 |
| 3 | Microsoft Corporation | MSFT.US | 34.76 |

## מניות פוטנציאל מדורגות

| דירוג | שם חברה | סימול | ציון |
|-------|---------|-------|------|
| 1 | Coinbase Global Inc | COIN.US | 71.18 |
| 2 | Micron Technology Inc | MU.US | 55.57 |

## הרכב קרן סופי

| שם חברה | סימול | סוג | משקל | ציון | מחיר נוכחי | מספר מניות ליחידת קרן |
|---------|-------|-----|------|------|------------|---------------------|
| NVIDIA Corporation | NVDA.US | בסיס | 18.0% | 89.69 | 188.54 | 4 |
| Salesforce.com Inc | CRM.US | בסיס | 16.0% | 49.79 | 193.45 | 3 |
"""


class TestUpdateParser:
    def test_parse_base_candidates(self, tmp_path):
        f = tmp_path / "update.md"
        f.write_text(SAMPLE_UPDATE_MD, encoding="utf-8")

        data = parse_update_file(f, top_base=10, top_potential=10)

        assert len(data["base_candidates"]) == 3
        assert data["base_candidates"][0]["symbol"] == "NVDA.US"
        assert data["base_candidates"][0]["score"] == 89.69
        assert data["base_candidates"][2]["name"] == "Microsoft Corporation"

    def test_parse_potential_candidates(self, tmp_path):
        f = tmp_path / "update.md"
        f.write_text(SAMPLE_UPDATE_MD, encoding="utf-8")

        data = parse_update_file(f, top_base=10, top_potential=10)

        assert len(data["potential_candidates"]) == 2
        assert data["potential_candidates"][0]["symbol"] == "COIN.US"

    def test_parse_selected_stocks(self, tmp_path):
        f = tmp_path / "update.md"
        f.write_text(SAMPLE_UPDATE_MD, encoding="utf-8")

        data = parse_update_file(f)

        assert len(data["selected_stocks"]) == 2
        assert data["selected_stocks"][0]["weight"] == 0.18
        assert data["selected_stocks"][0]["price"] == 188.54
        assert data["selected_stocks"][0]["shares"] == 4

    def test_parse_fund_metadata(self, tmp_path):
        f = tmp_path / "update.md"
        f.write_text(SAMPLE_UPDATE_MD, encoding="utf-8")

        data = parse_update_file(f)

        assert data["fund_name"] == "Fund_10_SP500_Q1_2026"
        assert data["date"] == "2026-02-11"

    def test_top_limit(self, tmp_path):
        f = tmp_path / "update.md"
        f.write_text(SAMPLE_UPDATE_MD, encoding="utf-8")

        data = parse_update_file(f, top_base=2, top_potential=1)

        assert len(data["base_candidates"]) == 2
        assert len(data["potential_candidates"]) == 1


# ==================== cache_loader tests ====================

class TestCacheLoader:
    def test_load_existing_stock(self, tmp_path):
        stock_data = {
            "symbol": "AAPL.US",
            "name": "Apple Inc",
            "index": "SP500",
            "financial_data": {
                "symbol": "AAPL.US",
                "revenues": {"2024": 385000000000},
                "net_incomes": {"2024": 97000000000},
                "operating_incomes": {},
                "operating_cash_flows": {},
            },
        }
        (tmp_path / "AAPL_US.json").write_text(json.dumps(stock_data), encoding="utf-8")

        stock = load_cached_stock("AAPL.US", tmp_path)
        assert stock is not None
        assert stock.symbol == "AAPL.US"
        assert stock.name == "Apple Inc"

    def test_load_missing_stock(self, tmp_path):
        stock = load_cached_stock("FAKE.US", tmp_path)
        assert stock is None

    def test_load_multiple(self, tmp_path):
        for sym in ["AAPL", "GOOG"]:
            data = {
                "symbol": f"{sym}.US",
                "name": f"{sym} Corp",
                "index": "SP500",
            }
            (tmp_path / f"{sym}_US.json").write_text(json.dumps(data), encoding="utf-8")

        result = load_cached_stocks(["AAPL.US", "GOOG.US", "FAKE.US"], tmp_path)
        assert len(result) == 2
        assert "AAPL.US" in result
        assert "FAKE.US" not in result


# ==================== ltm_calculator tests ====================

class TestLTMCalculator:
    def test_calculate_ltm_basic(self):
        quarterly_data = {
            "quarterly_revenues": [
                ("2025-12-31", 50000), ("2025-09-30", 48000),
                ("2025-06-30", 45000), ("2025-03-31", 42000),
            ],
            "quarterly_net_incomes": [
                ("2025-12-31", 10000), ("2025-09-30", 9500),
                ("2025-06-30", 9000), ("2025-03-31", 8500),
            ],
            "quarterly_operating_incomes": [
                ("2025-12-31", 15000), ("2025-09-30", 14000),
                ("2025-06-30", 13000), ("2025-03-31", 12000),
            ],
            "quarterly_operating_cash_flows": [
                ("2025-12-31", 12000), ("2025-09-30", 11000),
                ("2025-06-30", 10000), ("2025-03-31", 9000),
            ],
            "total_debt": 5000,
            "total_equity": 100000,
        }

        ltm = calculate_ltm(quarterly_data)

        assert ltm["ltm_revenue"] == 185000  # 50+48+45+42
        assert ltm["ltm_net_income"] == 37000  # 10+9.5+9+8.5
        assert ltm["ltm_operating_income"] == 54000
        assert ltm["ltm_operating_cash_flow"] == 42000
        assert ltm["ltm_year"] == 2025
        assert ltm["quarters_used"] == 4

    def test_calculate_ltm_empty_raises(self):
        with pytest.raises(ValueError):
            calculate_ltm({"quarterly_revenues": []})

    def test_merge_ltm_into_stock(self):
        stock = Stock(
            symbol="AAPL.US",
            name="Apple Inc",
            index="SP500",
            financial_data=FinancialData(
                symbol="AAPL.US",
                revenues={2024: 380000, 2023: 370000, 2022: 360000},
                net_incomes={2024: 95000, 2023: 90000, 2022: 85000},
                operating_incomes={2024: 110000},
                operating_cash_flows={2024: 100000},
                total_debt=10000,
                total_equity=200000,
            ),
            market_data=MarketData(
                symbol="AAPL",
                name="Apple Inc",
                market_cap=3000000000000,
                current_price=185.0,
                price_history={},
            ),
            base_score=75.0,
        )

        ltm_data = {
            "ltm_revenue": 400000,
            "ltm_net_income": 100000,
            "ltm_operating_income": 120000,
            "ltm_operating_cash_flow": 110000,
            "total_debt": 12000,
            "total_equity": 210000,
            "ltm_year": 2025,
            "quarters_used": 4,
            "fiscal_dates": ["2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"],
        }

        updated = merge_ltm_into_stock(stock, ltm_data, current_price=190.0, market_cap=3100000000000)

        # LTM year added
        assert 2025 in updated.financial_data.revenues
        assert updated.financial_data.revenues[2025] == 400000

        # Historical data preserved
        assert 2024 in updated.financial_data.revenues
        assert updated.financial_data.revenues[2024] == 380000

        # Debt/equity updated
        assert updated.financial_data.total_debt == 12000
        assert updated.financial_data.total_equity == 210000

        # Market data updated
        assert updated.market_data.current_price == 190.0
        assert updated.market_data.market_cap == 3100000000000

        # Scores reset
        assert updated.base_score is None

        # Original unchanged
        assert stock.base_score == 75.0
        assert stock.financial_data.total_debt == 10000


# ==================== changelog tests ====================

class TestChangelog:
    def test_append_creates_file(self, tmp_path):
        changelog_path = tmp_path / "CHANGELOG.md"

        comparison = {
            "added": [{"name": "NVDA", "symbol": "NVDA.US", "type": "בסיס", "weight": 0.18, "score": 89.69}],
            "removed": [],
            "retained": [],
            "added_count": 1,
            "removed_count": 0,
            "retained_count": 0,
            "previous_fund_name": "Fund_10_SP500_Q4_2025",
            "previous_date": "2025-12-17",
        }

        append_to_changelog(
            comparison=comparison,
            fund_name="Fund_10_SP500_Q1_2026",
            minimum_cost=4258.65,
            index_name="SP500",
            changelog_path=changelog_path,
        )

        assert changelog_path.exists()
        content = changelog_path.read_text(encoding="utf-8")
        assert "Fund_10_SP500_Q1_2026" in content
        assert "$4,258.65" in content
        assert "NVDA" in content

    def test_append_to_existing(self, tmp_path):
        changelog_path = tmp_path / "CHANGELOG.md"
        changelog_path.write_text("# Changelog\n\n---\n\n", encoding="utf-8")

        comparison = {
            "added": [],
            "removed": [],
            "retained": [],
            "added_count": 0,
            "removed_count": 0,
            "retained_count": 10,
            "previous_fund_name": "Fund_10_SP500_Q1_2026",
            "previous_date": "2026-02-11",
        }

        append_to_changelog(
            comparison=comparison,
            fund_name="Fund_10_SP500_Q2_2026",
            minimum_cost=5000.0,
            index_name="SP500",
            changelog_path=changelog_path,
        )

        content = changelog_path.read_text(encoding="utf-8")
        assert "# Changelog" in content  # Header preserved
        assert "Fund_10_SP500_Q2_2026" in content


# ==================== integration test with real data ====================

class TestIntegrationWithRealData:
    """Tests that run against real project files (skip if not available)"""

    @pytest.fixture
    def project_root(self):
        root = Path(__file__).parent.parent
        if not (root / "Fund_Docs").exists():
            pytest.skip("Project Fund_Docs not available")
        return root

    def test_parse_real_update_file(self, project_root):
        from utils.update_parser import find_latest_update_file

        update_file = find_latest_update_file(project_root / "Fund_Docs", "SP500")
        if update_file is None:
            pytest.skip("No SP500 Update.md found")

        data = parse_update_file(update_file, top_base=30, top_potential=20)

        assert len(data["base_candidates"]) == 30
        assert len(data["potential_candidates"]) == 20
        assert len(data["selected_stocks"]) == 10
        assert data["fund_name"] != ""

    def test_load_real_cached_stocks(self, project_root):
        cache_dir = project_root / "cache" / "stocks_data"
        if not cache_dir.exists():
            pytest.skip("Cache directory not available")

        stocks = load_cached_stocks(["NVDA.US", "CRM.US"], cache_dir)
        assert len(stocks) == 2
        assert stocks["NVDA.US"].financial_data is not None

    def test_find_latest_fund_dir_real(self, project_root):
        result = find_latest_fund_dir(project_root / "Fund_Docs", "SP500")
        assert result is not None
        assert "Q" in result.name
