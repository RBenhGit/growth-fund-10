"""
Data Source Adapter - מנרמל נתונים ממקורות שונים
Normalizes and validates data from different data sources
"""

from typing import Dict, Any
from models import FinancialData, MarketData
import logging

logger = logging.getLogger(__name__)


class DataSourceAdapter:
    """
    מתאם למקורות נתונים - מבצע נרמול ותיקוף של נתונים
    Adapter for data sources - performs normalization and validation
    """

    @staticmethod
    def validate_financial_data(data: FinancialData, symbol: str, source: str,
                               is_index_constituent: bool = False) -> bool:
        """
        תיקוף נתונים פיננסיים - בדיקת שלמות ואיכות
        Validate financial data - check completeness and quality

        Args:
            data: נתונים פיננסיים לתיקוף / Financial data to validate
            symbol: סימול המניה / Stock symbol
            source: שם מקור הנתונים / Data source name
            is_index_constituent: אם True, יישום כללים מקלים עבור מניות במדד רשמי
                                 If True, apply lenient rules for official index members

        Returns:
            bool: True אם הנתונים תקינים / True if data is valid
        """
        issues = []

        # Check for missing critical data
        if not data.revenues:
            issues.append("Missing revenues data")
        if not data.net_incomes:
            issues.append("Missing net income data")

        # NOTE: market_cap and current_price are NOT validated here.
        # When using separate data sources (e.g., TwelveData for financials,
        # yfinance for pricing), get_stock_financials() only fetches income
        # statement, balance sheet, and cash flow — it does NOT call /quote
        # or /statistics. market_cap and current_price belong to MarketData
        # and are validated in validate_market_data() instead.

        # Check for data quality
        if data.total_debt and data.total_equity:
            debt_ratio = data.debt_to_equity_ratio
            if debt_ratio and debt_ratio > 500:  # > 500% seems suspicious
                logger.warning(
                    f"{symbol}: Suspicious debt/equity ratio {debt_ratio:.1f}% from {source}"
                )

        # Check revenue data quality
        if data.revenues:
            revenue_values = [v for v in data.revenues.values() if v is not None and v > 0]
            if len(revenue_values) < 2:
                issues.append("Insufficient revenue history (need at least 2 years)")

        # Check net income data quality
        if data.net_incomes:
            income_values = [v for v in data.net_incomes.values() if v is not None]
            if len(income_values) < 2:
                issues.append("Insufficient net income history (need at least 2 years)")

        if issues:
            logger.error(f"{symbol}: Data quality issues from {source}: {', '.join(issues)}")
            return False

        logger.debug(f"{symbol}: Financial data validated from {source}")
        return True

    @staticmethod
    def validate_market_data(data: MarketData, symbol: str, source: str,
                            is_index_constituent: bool = False) -> bool:
        """
        תיקוף נתוני שוק
        Validate market data

        Args:
            data: נתוני שוק לתיקוף / Market data to validate
            symbol: סימול המניה / Stock symbol
            source: שם מקור הנתונים / Data source name
            is_index_constituent: אם True, יישום כללים מקלים עבור מניות במדד רשמי
                                 If True, apply lenient rules for official index members

        Returns:
            bool: True אם הנתונים תקינים / True if data is valid
        """
        issues = []

        if data.market_cap <= 0:
            issues.append(f"Invalid market cap: {data.market_cap}")

        # Lenient rule for index constituents - allow missing current price
        if data.current_price <= 0:
            if is_index_constituent:
                logger.warning(f"⚠️  {symbol}: Missing price but is index constituent, allowing")
            else:
                issues.append(f"Invalid current price: {data.current_price}")

        # CRITICAL FIX: Price history contains fiscal date snapshots (5-6 years), not daily trading data
        # This aligns with the credit-conserving design that fetches prices only for fiscal dates
        min_fiscal_dates = 3 if is_index_constituent else 5
        price_count = len(data.price_history) if data.price_history else 0

        if not data.price_history or price_count < min_fiscal_dates:
            if is_index_constituent and price_count >= 3:
                logger.warning(f"⚠️  {symbol}: Only {price_count} price points, but allowing (index constituent)")
            else:
                issues.append(f"Insufficient price history: {price_count} fiscal dates (need {min_fiscal_dates})")

        if issues:
            logger.error(f"{symbol}: Market data quality issues from {source}: {', '.join(issues)}")
            return False

        logger.debug(f"{symbol}: Market data validated from {source}")
        return True

    @staticmethod
    def compare_sources(
        symbol: str,
        data1: FinancialData,
        source1: str,
        data2: FinancialData,
        source2: str
    ) -> Dict[str, Any]:
        """
        השוואת נתונים משני מקורות - לצורכי debug
        Compare data from two sources - for debugging purposes

        Args:
            symbol: סימול המניה / Stock symbol
            data1: נתונים מהמקור הראשון / Data from first source
            source1: שם המקור הראשון / First source name
            data2: נתונים מהמקור השני / Data from second source
            source2: שם המקור השני / Second source name

        Returns:
            Dict with comparison results
        """
        comparison = {
            "symbol": symbol,
            "sources": [source1, source2],
            "market_cap_diff_pct": None,
            "price_diff_pct": None,
            "revenue_years_diff": None
        }

        # Compare market cap
        if data1.market_cap and data2.market_cap:
            diff = abs(data1.market_cap - data2.market_cap) / data1.market_cap * 100
            comparison["market_cap_diff_pct"] = diff
            if diff > 5:
                logger.warning(
                    f"{symbol}: Market cap differs {diff:.1f}% between {source1} and {source2}"
                )

        # Compare price
        if data1.current_price and data2.current_price:
            diff = abs(data1.current_price - data2.current_price) / data1.current_price * 100
            comparison["price_diff_pct"] = diff
            if diff > 2:
                logger.warning(
                    f"{symbol}: Price differs {diff:.1f}% between {source1} and {source2}"
                )

        # Compare available years
        years1 = set(data1.revenues.keys()) if data1.revenues else set()
        years2 = set(data2.revenues.keys()) if data2.revenues else set()
        comparison["revenue_years_diff"] = list(years1.symmetric_difference(years2))

        if comparison["revenue_years_diff"]:
            logger.info(
                f"{symbol}: Different revenue years between {source1} and {source2}: "
                f"{comparison['revenue_years_diff']}"
            )

        return comparison

    @staticmethod
    def normalize_symbol(symbol: str, index_name: str, source: str) -> str:
        """
        נרמול סימול מניה לפורמט הנכון למקור הנתונים
        Normalize stock symbol to the correct format for the data source

        Args:
            symbol: סימול מקורי / Original symbol
            index_name: שם המדד (TASE125/SP500) / Index name
            source: שם מקור הנתונים / Data source name

        Returns:
            str: סימול מנורמל / Normalized symbol

        Examples:
            - AAPL + alphavantage -> AAPL
            - LPSN.TA + yfinance -> LPSN.TA
        """
        # Remove existing suffix
        base_symbol = symbol.split('.')[0]

        # Apply source-specific formatting
        if source == "alphavantage":
            # Alpha Vantage uses plain symbols for US stocks
            if index_name == "SP500":
                return base_symbol
            elif index_name == "TASE125":
                return f"{base_symbol}.TA"
        elif source == "yfinance":
            # yfinance uses exchange suffix for all markets
            if index_name == "SP500":
                return base_symbol  # yfinance accepts AAPL for US stocks
            elif index_name == "TASE125":
                return f"{base_symbol}.TA"
        elif source == "twelvedata":
            # TwelveData uses plain symbols for US, .TA for TASE
            if index_name == "SP500":
                return base_symbol
            elif index_name == "TASE125":
                return f"{base_symbol}.TA"

        # Default: return original symbol
        return symbol
